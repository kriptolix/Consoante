"""
Gerencia a fila de reprodução atual.
Separa faixas seguras de exploratórias.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QueueEntry:
    track_id: int
    exploratory: bool = False


class PlaybackQueue:
    def __init__(self) -> None:
        self._queue: list[QueueEntry] = []

    # ──────────────────────────────────────────
    # Operações básicas
    # ──────────────────────────────────────────

    def add(self, track_id: int, exploratory: bool = False) -> None:
        self._queue.append(QueueEntry(track_id, exploratory))

    def remove(self, track_id: int) -> bool:
        """Remove a primeira ocorrência do track_id. Retorna True se removeu."""
        for i, entry in enumerate(self._queue):
            if entry.track_id == track_id:
                self._queue.pop(i)
                return True
        return False

    def reorder(self, from_index: int, to_index: int) -> None:
        if 0 <= from_index < len(self._queue) and 0 <= to_index < len(self._queue):
            entry = self._queue.pop(from_index)
            self._queue.insert(to_index, entry)

    def pop_next(self) -> Optional[QueueEntry]:
        return self._queue.pop(0) if self._queue else None

    def peek_next(self) -> Optional[QueueEntry]:
        return self._queue[0] if self._queue else None

    def clear(self) -> None:
        self._queue.clear()

    # ──────────────────────────────────────────
    # Consultas
    # ──────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._queue)

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def track_ids(self) -> list[int]:
        return [e.track_id for e in self._queue]

    def contains(self, track_id: int) -> bool:
        return any(e.track_id == track_id for e in self._queue)
