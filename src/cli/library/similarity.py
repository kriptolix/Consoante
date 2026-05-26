"""
Calcula score de similaridade acústica entre duas faixas.
Todos os atributos já estão normalizados no banco — sem conversão adicional aqui.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from learning.tuning import SIMILARITY_WEIGHTS


def acoustic_similarity(a: sqlite3.Row, b: sqlite3.Row) -> float:
    """
    Retorna similaridade entre 0.0 e 1.0.
    Faixas sem análise retornam 0.5 (neutral).
    """
    if not a["analyzed"] or not b["analyzed"]:
        return 0.5

    diff_sq = 0.0
    for attr, weight in SIMILARITY_WEIGHTS.items():
        val_a: Optional[float] = a[attr] if attr != "bpm_normalized" else _normalize_bpm(a)
        val_b: Optional[float] = b[attr] if attr != "bpm_normalized" else _normalize_bpm(b)

        if val_a is None or val_b is None:
            continue

        diff_sq += weight * (val_a - val_b) ** 2

    return max(0.0, 1.0 - diff_sq ** 0.5)


def _normalize_bpm(row: sqlite3.Row) -> Optional[float]:
    """BPM já está normalizado 0–1 no banco (normalizado durante análise)."""
    return row["bpm"]
