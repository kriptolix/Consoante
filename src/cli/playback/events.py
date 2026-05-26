"""
Define e despacha o conjunto canônico de eventos de reprodução.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class EventType(Enum):
    PLAY         = "play"
    PAUSE        = "pause"
    SKIP         = "skip"
    GO_BACK      = "go_back"
    END_OF_TRACK = "end_of_track"
    VOLUME_CHANGE = "volume_change"
    MANUAL_SELECT = "manual_select"
    QUEUE_REMOVE  = "queue_remove"


@dataclass
class PlaybackEvent:
    type: EventType
    track_id: int
    timestamp: float = field(default_factory=time.time)

    # Posição relativa na faixa no momento do evento (0.0–1.0)
    position: float = 0.0

    # Contextos ativos no momento do evento
    active_mood:    Optional[str] = None
    active_period:  Optional[str] = None
    active_weekday: Optional[str] = None

    # Extras por tipo de evento
    volume_before: Optional[float] = None   # para VOLUME_CHANGE
    volume_after:  Optional[float] = None   # para VOLUME_CHANGE
    from_track_id: Optional[int]   = None   # para transições


# ──────────────────────────────────────────────
# Dispatcher simples (pub/sub)
# ──────────────────────────────────────────────

_listeners: list[Callable[[PlaybackEvent], None]] = []


def subscribe(listener: Callable[[PlaybackEvent], None]) -> None:
    _listeners.append(listener)


def unsubscribe(listener: Callable[[PlaybackEvent], None]) -> None:
    if listener in _listeners:
        _listeners.remove(listener)


def dispatch(event: PlaybackEvent) -> None:
    for listener in list(_listeners):
        try:
            listener(event)
        except Exception as exc:
            print(f"[events] Listener error: {exc}")
