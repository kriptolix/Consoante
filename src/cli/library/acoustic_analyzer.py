"""
Processa análise acústica de forma assíncrona, em segundo plano.
Nunca bloqueia reprodução ou interface.
Normaliza todos os atributos para escala 0–1 antes de persistir.
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Optional

from database import queries

_analysis_queue: queue.Queue[tuple[int, Path]] = queue.Queue()
_worker_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


# ──────────────────────────────────────────────
# Extração acústica
# ──────────────────────────────────────────────

def _extract_features(path: Path) -> Optional[dict]:
    """
    Extrai e deriva atributos acústicos via Librosa/FFmpeg.
    Retorna None em caso de falha.
    """
    try:
        import librosa
        import numpy as np

        y, sr = librosa.load(str(path), sr=None, mono=True, duration=120)

        # BPM — normalizado para 0–1 considerando faixa 30–250 BPM
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        bpm_raw = float(tempo)
        bpm_normalized = max(0.0, min(1.0, (bpm_raw - 30.0) / (250.0 - 30.0)))

        # Energy — RMS médio normalizado
        rms = librosa.feature.rms(y=y)[0]
        rms_mean = float(np.mean(rms))
        rms_max = float(np.max(rms)) if np.max(rms) > 0 else 1.0
        energy = rms_mean / rms_max

        # Loudness — obtido do RMS em escala dBFS equivalente
        # Converte para dBFS e normaliza de [-60, 0] para [0, 1]
        rms_global = float(np.sqrt(np.mean(y ** 2)))
        dbfs = 20 * np.log10(rms_global + 1e-9)
        loudness = max(0.0, min(1.0, (dbfs + 60.0) / 60.0))

        # Acousticness — razão energia harmônica / percussiva
        y_harmonic, y_percussive = librosa.effects.hpss(y)
        harmonic_energy = float(np.mean(y_harmonic ** 2))
        percussive_energy = float(np.mean(y_percussive ** 2))
        total = harmonic_energy + percussive_energy
        acousticness = harmonic_energy / total if total > 0 else 0.5

        # Brightness — spectral centroid normalizado pelo Nyquist
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_centroid_raw = float(np.mean(centroid))
        nyquist = sr / 2.0
        brightness = min(1.0, spectral_centroid_raw / nyquist)

        # Rhythmic regularity — 1 − CV dos intervalos entre beats
        if len(beat_frames) > 1:
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            intervals = np.diff(beat_times)
            cv = float(np.std(intervals) / (np.mean(intervals) + 1e-9))
            rhythmic_regularity = max(0.0, min(1.0, 1.0 - cv))
        else:
            rhythmic_regularity = 0.5

        return {
            "bpm":                 bpm_normalized,
            "energy":              energy,
            "loudness":            loudness,
            "acousticness":        acousticness,
            "brightness":          brightness,
            "rhythmic_regularity": rhythmic_regularity,
            "spectral_centroid":   spectral_centroid_raw,  # valor bruto em Hz
        }

    except Exception as exc:
        print(f"[acoustic_analyzer] Erro ao analisar {path}: {exc}")
        return None


# ──────────────────────────────────────────────
# Worker thread
# ──────────────────────────────────────────────

def _worker() -> None:
    while not _stop_event.is_set():
        try:
            track_id, path = _analysis_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        features = _extract_features(path)
        if features is not None:
            queries.update_acoustic_features(track_id, **features)

        _analysis_queue.task_done()


# ──────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────

def enqueue(track_id: int, path: Path) -> None:
    """Adiciona faixa à fila de análise assíncrona."""
    _analysis_queue.put((track_id, path))


def start() -> None:
    """Inicia o worker em background. Seguro chamar múltiplas vezes."""
    global _worker_thread
    if _worker_thread is not None and _worker_thread.is_alive():
        return
    _stop_event.clear()
    _worker_thread = threading.Thread(target=_worker, daemon=True, name="acoustic-analyzer")
    _worker_thread.start()


def stop() -> None:
    """Sinaliza parada e aguarda o worker terminar."""
    _stop_event.set()
    if _worker_thread is not None:
        _worker_thread.join(timeout=5.0)


def queue_size() -> int:
    return _analysis_queue.qsize()
