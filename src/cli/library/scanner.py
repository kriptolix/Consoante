"""
Percorre recursivamente diretórios configurados, detecta arquivos de áudio,
insere/atualiza registros em `tracks` e marca removidos como inativos.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Callable, Optional

from database import queries

AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".ogg", ".opus", ".m4a", ".aac",
    ".wav", ".wv", ".ape", ".mpc", ".aiff", ".aif",
}


def _compute_file_hash(path: Path) -> str:
    """Hash dos primeiros 64KB do arquivo (rápido, suficiente para identificação)."""
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        chunk = f.read(65536)
        hasher.update(chunk)
    # Inclui tamanho total para reduzir colisões
    hasher.update(str(os.path.getsize(path)).encode())
    return hasher.hexdigest()


def _is_audio(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_EXTENSIONS


def scan(
    directories: list[str | Path],
    on_new_track: Optional[Callable[[int, Path], None]] = None,
) -> dict:
    """
    Escaneia os diretórios e sincroniza o banco.

    Args:
        directories: Lista de caminhos a escanear recursivamente.
        on_new_track: Callback chamado com (track_id, path) para cada faixa
                      nova ou não analisada — usada para enfileirar análise acústica.

    Returns:
        Dicionário com contadores: added, updated, deactivated.
    """
    from library import metadata as meta_mod

    counters = {"added": 0, "updated": 0, "deactivated": 0}

    # Coleta todos os caminhos de áudio encontrados
    found_paths: set[str] = set()
    for directory in directories:
        root = Path(directory)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and _is_audio(path):
                found_paths.add(str(path.resolve()))

    # Paths atualmente ativos no banco
    known_paths = queries.get_active_file_paths()

    # Marca removidos como inativos
    for old_path in known_paths - found_paths:
        queries.mark_track_inactive(old_path)
        counters["deactivated"] += 1

    # Processa cada arquivo encontrado
    for file_str in found_paths:
        path = Path(file_str)
        file_hash = _compute_file_hash(path)

        # Tenta reconciliar faixa movida
        existing_id = queries.reconcile_moved_track(file_hash, file_str)
        if existing_id is not None:
            counters["updated"] += 1
            if on_new_track:
                on_new_track(existing_id, path)
            continue

        # Extrai metadata básica
        meta = meta_mod.extract(path)

        if file_str in known_paths:
            # Faixa já conhecida — atualiza metadata
            track_id = queries.upsert_track(
                file_path=file_str,
                file_hash=file_hash,
                **meta,
            )
            counters["updated"] += 1
        else:
            # Faixa nova
            track_id = queries.upsert_track(
                file_path=file_str,
                file_hash=file_hash,
                **meta,
            )
            counters["added"] += 1

        if on_new_track:
            on_new_track(track_id, path)

    return counters
