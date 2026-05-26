"""
Mantém o estado da sessão atual em memória.
Descartado ao fechar o player — sem persistência.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SessionState:
    # Contextos ativos
    active_mood: str = "Relaxed"  # mood neutro inicial
    active_period: str = field(default_factory=lambda: _current_period())
    active_weekday: str = field(default_factory=lambda: _current_weekday())

    # Histórico da sessão (track_ids em ordem de reprodução)
    played_track_ids: list[int] = field(default_factory=list)

    # Skips consecutivos recentes (para Recovery Mode — Fase 2)
    consecutive_skips: int = 0

    # Timestamp de início da sessão
    started_at: float = field(default_factory=time.time)

    def record_play(self, track_id: int) -> None:
        self.played_track_ids.append(track_id)
        self.consecutive_skips = 0

    def record_skip(self) -> None:
        self.consecutive_skips += 1

    def recent_track_ids(self, n: int) -> list[int]:
        """Retorna os últimos N track_ids reproduzidos."""
        return self.played_track_ids[-n:]

    def set_mood(self, mood: str) -> None:
        self.active_mood = mood

    def session_length(self) -> float:
        return time.time() - self.started_at


# ──────────────────────────────────────────────
# Helpers de período e dia
# ──────────────────────────────────────────────

def _current_period() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 18:
        return "Afternoon"
    elif 18 <= hour < 22:
        return "Evening"
    else:
        return "Night"


def _current_weekday() -> str:
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return days[datetime.now().weekday()]
