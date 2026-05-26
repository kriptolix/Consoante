"""
Aplica decay temporal nos pesos de track_affinity e transitions.
Modelo: weight *= DECAY_RATE por dia sem interação.
Piso mínimo configurável para evitar inacessibilidade total.
"""

from __future__ import annotations

import math
from datetime import datetime

from database import queries
from learning.tuning import DECAY_RATE, WEIGHT_FLOOR


def _days_since(updated_at_str: str) -> float:
    try:
        updated_at = datetime.fromisoformat(updated_at_str)
    except (TypeError, ValueError):
        return 0.0
    delta = datetime.utcnow() - updated_at
    return delta.total_seconds() / 86400.0


def _decayed_weight(weight: float, days: float) -> float:
    if days <= 0:
        return weight
    new_weight = weight * (DECAY_RATE ** days)
    return max(WEIGHT_FLOOR, new_weight)


def run() -> dict:
    """
    Executa o decay em todos os registros de afinidade e transições.
    Retorna contadores de registros atualizados.
    """
    counters = {"affinities": 0, "transitions": 0}

    # Affinities
    affinity_updates: list[tuple[float, int, int]] = []
    for row in queries.get_all_affinities_for_decay():
        days = _days_since(row["updated_at"])
        new_weight = _decayed_weight(row["weight"], days)
        if abs(new_weight - row["weight"]) > 0.01:
            affinity_updates.append((new_weight, row["track_id"], row["context_id"]))

    if affinity_updates:
        queries.bulk_update_affinities(affinity_updates)
        counters["affinities"] = len(affinity_updates)

    # Transitions
    transition_updates: list[tuple[float, int, int, int]] = []
    for row in queries.get_all_transitions_for_decay():
        days = _days_since(row["updated_at"])
        new_weight = _decayed_weight(row["weight"], days)
        if abs(new_weight - row["weight"]) > 0.01:
            transition_updates.append((
                new_weight,
                row["from_track_id"],
                row["to_track_id"],
                row["context_id"],
            ))

    if transition_updates:
        queries.bulk_update_transitions(transition_updates)
        counters["transitions"] = len(transition_updates)

    return counters
