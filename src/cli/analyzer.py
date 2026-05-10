import librosa
import numpy as np
import pyloudnorm as pyln

import os
import time
from multiprocessing import Process
from db_manager import DatabaseManager


def safe_mean(x):
    return float(np.mean(x)) if x is not None else 0.0


def extract_features(file_path):
    try:
        y, sr = librosa.load(file_path, sr=None, mono=True)

        if y is None or len(y) < 2048:
            raise ValueError("Áudio inválido ou muito curto")

        # BPM
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo) if tempo is not None else 0.0

        # Energy
        rms = librosa.feature.rms(y=y)
        energy = safe_mean(rms)

        # Loudness (EBU R128)
        meter = pyln.Meter(sr)
        try:
            loudness = float(meter.integrated_loudness(y))
        except Exception:
            loudness = 0.0

        # Spectral centroid
        spectral_centroid = safe_mean(
            librosa.feature.spectral_centroid(y=y, sr=sr)
        )

        # Valence proxy (mais seguro)
        try:
            y_harmonic = librosa.effects.harmonic(y)
            tonnetz = librosa.feature.tonnetz(y=y_harmonic, sr=sr)
            valence = safe_mean(tonnetz)
        except Exception:
            valence = 0.5

        # Danceability proxy
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        if np.mean(onset_env) > 0:
            danceability = float(np.std(onset_env) / (np.mean(onset_env) + 1e-6))
        else:
            danceability = 0.0

        return {
            "bpm": bpm,
            "energy": energy,
            "valence": valence,
            "danceability": danceability,
            "loudness": loudness,
            "spectral_centroid": spectral_centroid,
        }

    except Exception as e:
        print(f"[extract_features ERROR] {file_path}: {e}")
        return None
    
def analysis_worker_process(db_path):
    """Worker que roda em um processo separado para não afetar a reprodução."""
    # Baixa a prioridade do processo para não competir com o áudio (Linux/macOS)
    if hasattr(os, 'nice'):
        os.nice(15)

    db = DatabaseManager(db_path)
    pending = db.get_pending_analysis()
    
    if not pending:
        return

    for track_id, file_path in pending:
        try:
            features = extract_features(file_path)
            if features:
                db.update_audio_features(track_id, features)

            time.sleep(0.5)
        except Exception:
            continue

def start_background_analysis(db_path):
    p = Process(target=analysis_worker_process, args=(db_path,))
    # Define como daemon para que o processo morra quando o player fechar
    p.daemon = True
    p.start()
    return p