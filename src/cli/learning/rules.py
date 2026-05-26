"""
Define as regras heurísticas de forma declarativa.
Facilita adição de novas regras sem alterar reinforcement.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from playback.events import EventType, PlaybackEvent
import learning.tuning as T


@dataclass
class Rule:
    name: str
    matches: Callable[[PlaybackEvent], bool]
    affinity_delta: Callable[[PlaybackEvent], float]
    transition_delta: Optional[Callable[[PlaybackEvent], float]] = None
    volume_delta: Optional[Callable[[PlaybackEvent], int]] = None
    description: str = ""


def _volume_increased_significantly(event: PlaybackEvent) -> bool:
    if event.volume_before is None or event.volume_after is None:
        return False
    if event.volume_before <= 0:
        return False
    ratio = (event.volume_after - event.volume_before) / event.volume_before
    return ratio >= T.VOLUME_CHANGE_THRESHOLD


RULES: list[Rule] = [
    Rule(
        name="end_of_track",
        description="Faixa ouvida até o final — reforço positivo.",
        matches=lambda e: e.type == EventType.END_OF_TRACK,
        affinity_delta=lambda e: T.COMPLETE_BONUS,
        transition_delta=lambda e: T.COMPLETE_BONUS,
    ),
    Rule(
        name="skip_early",
        description="Skip precoce — penalidade forte.",
        matches=lambda e: (
            e.type == EventType.SKIP and e.position < T.SKIP_EARLY_THRESHOLD
        ),
        affinity_delta=lambda e: T.SKIP_EARLY_PENALTY,
        transition_delta=lambda e: T.SKIP_EARLY_PENALTY,
    ),
    Rule(
        name="skip_late",
        description="Skip tardio — penalidade leve.",
        matches=lambda e: (
            e.type == EventType.SKIP and e.position >= T.SKIP_EARLY_THRESHOLD
        ),
        affinity_delta=lambda e: T.SKIP_LATE_PENALTY,
        transition_delta=None,
    ),
    Rule(
        name="manual_select",
        description="Seleção manual — sinal mais forte do sistema.",
        matches=lambda e: e.type == EventType.MANUAL_SELECT,
        affinity_delta=lambda e: T.MANUAL_SELECT_BONUS,
        transition_delta=lambda e: T.MANUAL_SELECT_BONUS * 0.5,
    ),
    Rule(
        name="repeat",
        description="Repetição manual — reforço positivo.",
        matches=lambda e: e.type == EventType.GO_BACK,
        affinity_delta=lambda e: T.REPEAT_BONUS,
        transition_delta=lambda e: T.REPEAT_BONUS,
    ),
    Rule(
        name="volume_up",
        description="Aumento de volume significativo — reforço leve.",
        matches=_volume_increased_significantly,
        affinity_delta=lambda e: T.VOLUME_UP_BONUS,
        transition_delta=None,
    ),
    Rule(
        name="queue_remove",
        description="Remoção da fila — penalidade.",
        matches=lambda e: e.type == EventType.QUEUE_REMOVE,
        affinity_delta=lambda e: T.QUEUE_REMOVE_PENALTY,
        transition_delta=lambda e: T.QUEUE_REMOVE_PENALTY,
    ),
]
