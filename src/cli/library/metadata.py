"""
Extrai metadata de arquivos de áudio via Mutagen.
Normaliza tags inconsistentes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def _try_mutagen(path: Path) -> dict:
    try:
        import mutagen
        from mutagen.id3 import ID3NoHeaderError

        audio = mutagen.File(path, easy=True)
        if audio is None:
            return {}

        def _first(tag: Optional[list]) -> Optional[str]:
            if not tag:
                return None
            val = tag[0]
            return str(val).strip() or None

        duration: Optional[float] = None
        if hasattr(audio, "info") and hasattr(audio.info, "length"):
            duration = float(audio.info.length)

        return {
            "title":    _first(audio.get("title")),
            "artist":   _first(audio.get("artist")),
            "album":    _first(audio.get("album")),
            "duration": duration,
            "year":     _first(audio.get("date")),
            "genre":    _first(audio.get("genre")),
        }
    except Exception:
        return {}


def _fallback(path: Path) -> dict:
    """Metadados mínimos derivados do nome do arquivo."""
    return {
        "title":    path.stem,
        "artist":   None,
        "album":    None,
        "duration": None,
        "year":     None,
        "genre":    None,
    }


def extract(path: Path) -> dict:
    """
    Retorna dict com keys: title, artist, album, duration, year, genre.
    Nunca lança exceção — retorna fallback em caso de erro.
    """
    result = _try_mutagen(path)
    fallback = _fallback(path)

    # Garante que todas as keys existem, preenchendo com fallback
    for key, val in fallback.items():
        if key not in result or result[key] is None:
            result[key] = val

    return result
