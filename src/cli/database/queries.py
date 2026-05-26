"""
Centraliza todas as queries SQL como funções nomeadas.
Nenhum SQL deve aparecer fora deste módulo.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from database import connection


# ──────────────────────────────────────────────
# Tracks
# ──────────────────────────────────────────────

def upsert_track(
    file_path: str,
    file_hash: str,
    title: Optional[str],
    artist: Optional[str],
    album: Optional[str],
    duration: Optional[float],
    year: Optional[str],
    genre: Optional[str],
) -> int:
    """Insere ou atualiza metadata básica. Retorna o id da faixa."""
    with connection.get() as conn:
        conn.execute(
            """
            INSERT INTO tracks (file_path, file_hash, title, artist, album, duration, year, genre)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                file_hash = excluded.file_hash,
                title     = excluded.title,
                artist    = excluded.artist,
                album     = excluded.album,
                duration  = excluded.duration,
                year      = excluded.year,
                genre     = excluded.genre,
                active    = 1
            """,
            (file_path, file_hash, title, artist, album, duration, year, genre),
        )
        row = conn.execute(
            "SELECT id FROM tracks WHERE file_path = ?", (file_path,)
        ).fetchone()
        return row["id"]


def reconcile_moved_track(file_hash: str, new_path: str) -> Optional[int]:
    """
    Se o hash já existe com outro caminho, atualiza o path e retorna o id.
    Retorna None se não encontrar.
    """
    with connection.get() as conn:
        row = conn.execute(
            "SELECT id FROM tracks WHERE file_hash = ? AND file_path != ?",
            (file_hash, new_path),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE tracks SET file_path = ?, active = 1 WHERE id = ?",
            (new_path, row["id"]),
        )
        return row["id"]


def mark_track_inactive(file_path: str) -> None:
    with connection.get() as conn:
        conn.execute(
            "UPDATE tracks SET active = 0 WHERE file_path = ?", (file_path,)
        )


def update_acoustic_features(
    track_id: int,
    bpm: float,
    energy: float,
    loudness: float,
    acousticness: float,
    brightness: float,
    rhythmic_regularity: float,
    spectral_centroid: float,
) -> None:
    with connection.get() as conn:
        conn.execute(
            """
            UPDATE tracks SET
                bpm = ?, energy = ?, loudness = ?, acousticness = ?,
                brightness = ?, rhythmic_regularity = ?, spectral_centroid = ?,
                analyzed = 1
            WHERE id = ?
            """,
            (
                bpm, energy, loudness, acousticness,
                brightness, rhythmic_regularity, spectral_centroid,
                track_id,
            ),
        )


def get_track_by_id(track_id: int) -> Optional[sqlite3.Row]:
    with connection.get() as conn:
        return conn.execute(
            "SELECT * FROM tracks WHERE id = ?", (track_id,)
        ).fetchone()


def get_all_active_tracks() -> list[sqlite3.Row]:
    with connection.get() as conn:
        return conn.execute(
            "SELECT * FROM tracks WHERE active = 1"
        ).fetchall()


def get_active_file_paths() -> set[str]:
    with connection.get() as conn:
        rows = conn.execute(
            "SELECT file_path FROM tracks WHERE active = 1"
        ).fetchall()
        return {r["file_path"] for r in rows}


def get_play_count_proxy(track_id: int) -> int:
    """
    Conta quantas entradas de afinidade a faixa possui — proxy para
    determinar se ainda está na janela de cold start.
    """
    with connection.get() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM track_affinity WHERE track_id = ?",
            (track_id,),
        ).fetchone()
        return row["cnt"] if row else 0


# ──────────────────────────────────────────────
# Contexts
# ──────────────────────────────────────────────

def get_context_id(ctx_type: str, ctx_value: str) -> Optional[int]:
    with connection.get() as conn:
        row = conn.execute(
            "SELECT id FROM contexts WHERE type = ? AND value = ?",
            (ctx_type, ctx_value),
        ).fetchone()
        return row["id"] if row else None


def get_all_contexts() -> list[sqlite3.Row]:
    with connection.get() as conn:
        return conn.execute("SELECT * FROM contexts").fetchall()


# ──────────────────────────────────────────────
# Track affinity
# ──────────────────────────────────────────────

def get_affinity(track_id: int, context_id: int) -> float:
    with connection.get() as conn:
        row = conn.execute(
            "SELECT weight FROM track_affinity WHERE track_id = ? AND context_id = ?",
            (track_id, context_id),
        ).fetchone()
        return row["weight"] if row else 500.0


def upsert_affinity(track_id: int, context_id: int, weight: float) -> None:
    with connection.get() as conn:
        conn.execute(
            """
            INSERT INTO track_affinity (track_id, context_id, weight, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(track_id, context_id) DO UPDATE SET
                weight     = excluded.weight,
                updated_at = CURRENT_TIMESTAMP
            """,
            (track_id, context_id, weight),
        )


def get_all_affinities_for_decay() -> list[sqlite3.Row]:
    """Retorna todos os registros de afinidade com data de atualização."""
    with connection.get() as conn:
        return conn.execute(
            "SELECT track_id, context_id, weight, updated_at FROM track_affinity"
        ).fetchall()


def bulk_update_affinities(updates: list[tuple[float, int, int]]) -> None:
    """updates: list of (new_weight, track_id, context_id)"""
    with connection.get() as conn:
        conn.executemany(
            """
            UPDATE track_affinity SET weight = ?, updated_at = CURRENT_TIMESTAMP
            WHERE track_id = ? AND context_id = ?
            """,
            updates,
        )


# ──────────────────────────────────────────────
# Transitions
# ──────────────────────────────────────────────

def get_transition_weight(
    from_track_id: int, to_track_id: int, context_id: int
) -> float:
    with connection.get() as conn:
        row = conn.execute(
            """
            SELECT weight FROM transitions
            WHERE from_track_id = ? AND to_track_id = ? AND context_id = ?
            """,
            (from_track_id, to_track_id, context_id),
        ).fetchone()
        return row["weight"] if row else 500.0


def upsert_transition(
    from_track_id: int, to_track_id: int, context_id: int, weight: float
) -> None:
    with connection.get() as conn:
        conn.execute(
            """
            INSERT INTO transitions (from_track_id, to_track_id, context_id, weight, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(from_track_id, to_track_id, context_id) DO UPDATE SET
                weight     = excluded.weight,
                updated_at = CURRENT_TIMESTAMP
            """,
            (from_track_id, to_track_id, context_id, weight),
        )


def get_all_transitions_for_decay() -> list[sqlite3.Row]:
    with connection.get() as conn:
        return conn.execute(
            "SELECT from_track_id, to_track_id, context_id, weight, updated_at FROM transitions"
        ).fetchall()


def bulk_update_transitions(
    updates: list[tuple[float, int, int, int]]
) -> None:
    """updates: list of (new_weight, from_track_id, to_track_id, context_id)"""
    with connection.get() as conn:
        conn.executemany(
            """
            UPDATE transitions SET weight = ?, updated_at = CURRENT_TIMESTAMP
            WHERE from_track_id = ? AND to_track_id = ? AND context_id = ?
            """,
            updates,
        )


# ──────────────────────────────────────────────
# Track play settings
# ──────────────────────────────────────────────

def get_preferred_volume(track_id: int) -> int:
    with connection.get() as conn:
        row = conn.execute(
            "SELECT preferred_volume FROM track_play_settings WHERE track_id = ?",
            (track_id,),
        ).fetchone()
        return row["preferred_volume"] if row else 50


def upsert_preferred_volume(track_id: int, volume: int) -> None:
    with connection.get() as conn:
        conn.execute(
            """
            INSERT INTO track_play_settings (track_id, preferred_volume, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(track_id) DO UPDATE SET
                preferred_volume = excluded.preferred_volume,
                updated_at       = CURRENT_TIMESTAMP
            """,
            (track_id, volume),
        )
