"""
Aplica reforço positivo e negativo nos pesos de track_affinity e transitions.
Recebe eventos do playback e aplica as regras heurísticas correspondentes.
"""

from __future__ import annotations

from typing import Optional

from database import queries
from learning.rules import RULES
from learning.tuning import WEIGHT_FLOOR, WEIGHT_CEILING
from playback.events import PlaybackEvent


def _clamp(value: float) -> float:
    return max(WEIGHT_FLOOR, min(WEIGHT_CEILING, value))


def _apply_affinity_delta(
    track_id: int,
    context_ids: list[int],
    delta: float,
) -> None:
    for ctx_id in context_ids:
        current = queries.get_affinity(track_id, ctx_id)
        new_weight = _clamp(current + delta)
        queries.upsert_affinity(track_id, ctx_id, new_weight)


def _apply_transition_delta(
    from_track_id: Optional[int],
    to_track_id: int,
    context_ids: list[int],
    delta: float,
) -> None:
    if from_track_id is None:
        return
    for ctx_id in context_ids:
        current = queries.get_transition_weight(from_track_id, to_track_id, ctx_id)
        new_weight = _clamp(current + delta)
        queries.upsert_transition(from_track_id, to_track_id, ctx_id, new_weight)


def _resolve_context_ids(event: PlaybackEvent) -> list[int]:
    """Resolve os IDs dos contextos ativos no evento."""
    ids: list[int] = []
    for ctx_type, ctx_value in [
        ("mood",    event.active_mood),
        ("period",  event.active_period),
        ("weekday", event.active_weekday),
    ]:
        if ctx_value is None:
            continue
        ctx_id = queries.get_context_id(ctx_type, ctx_value)
        if ctx_id is not None:
            ids.append(ctx_id)
    return ids


def process(event: PlaybackEvent) -> None:
    """
    Ponto de entrada principal.
    Recebe um PlaybackEvent e aplica todas as regras que correspondem.
    """
    context_ids = _resolve_context_ids(event)

    for rule in RULES:
        if not rule.matches(event):
            continue

        affinity_delta = rule.affinity_delta(event)
        _apply_affinity_delta(event.track_id, context_ids, affinity_delta)

        if rule.transition_delta is not None:
            transition_delta = rule.transition_delta(event)
            _apply_transition_delta(
                event.from_track_id,
                event.track_id,
                context_ids,
                transition_delta,
            )
