"""
Controlador central do player.
Orquestra pipeline, fila, events, learning e ranking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from database import queries
from learning import decay, reinforcement
from playback.events import EventType, PlaybackEvent, dispatch, subscribe
from playback.pipeline import Pipeline
from playback.queue import PlaybackQueue
from ranking.selector import select_next
from ranking.session_state import SessionState


class Player:
    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self.session = SessionState()
        self.queue = PlaybackQueue()
        self._current_track_id: Optional[int] = None
        self._pipeline = Pipeline(on_track_end=self._handle_track_end)

        # Registra listener de eventos no dispatcher
        subscribe(reinforcement.process)

    # ──────────────────────────────────────────
    # Controles de reprodução
    # ──────────────────────────────────────────

    def play_track(self, track_id: int, from_manual: bool = False) -> None:
        row = queries.get_track_by_id(track_id)
        if row is None:
            print(f"[player] Faixa {track_id} não encontrada.")
            return

        prev_id = self._current_track_id
        self._current_track_id = track_id
        self.session.record_play(track_id)

        self._pipeline.load(
            track_id=track_id,
            path=row["file_path"],
            duration=row["duration"] or 0.0,
        )
        self._pipeline.play()

        event_type = EventType.MANUAL_SELECT if from_manual else EventType.PLAY
        dispatch(PlaybackEvent(
            type=event_type,
            track_id=track_id,
            position=0.0,
            from_track_id=prev_id,
            **self._ctx_kwargs(),
        ))

        if self.verbose:
            artist = row["artist"] or "?"
            title  = row["title"] or f"track#{track_id}"
            print(f"[player] ▶  {artist} — {title}")

    def pause(self) -> None:
        if not self._pipeline.is_playing:
            return
        pos = self._pipeline.position_relative()
        self._pipeline.pause()
        dispatch(PlaybackEvent(
            type=EventType.PAUSE,
            track_id=self._current_track_id,
            position=pos,
            **self._ctx_kwargs(),
        ))

    def resume(self) -> None:
        self._pipeline.play()

    def skip(self) -> None:
        if self._current_track_id is None:
            return
        pos = self._pipeline.position_relative()
        self._pipeline.stop()
        self.session.record_skip()

        dispatch(PlaybackEvent(
            type=EventType.SKIP,
            track_id=self._current_track_id,
            position=pos,
            from_track_id=None,
            **self._ctx_kwargs(),
        ))

        if self.verbose:
            print(f"[player] ⏭  skip @ {pos:.0%}")

        self._advance()

    def go_back(self) -> None:
        """Repete a faixa atual ou volta para a anterior."""
        if self._current_track_id is None:
            return
        pos = self._pipeline.position_relative()
        dispatch(PlaybackEvent(
            type=EventType.GO_BACK,
            track_id=self._current_track_id,
            position=pos,
            **self._ctx_kwargs(),
        ))
        self.play_track(self._current_track_id)

    def set_volume(self, volume: float) -> None:
        before = self._pipeline.volume
        self._pipeline.set_volume(volume)
        after = self._pipeline.volume

        if self._current_track_id is not None:
            dispatch(PlaybackEvent(
                type=EventType.VOLUME_CHANGE,
                track_id=self._current_track_id,
                position=self._pipeline.position_relative(),
                volume_before=before,
                volume_after=after,
                **self._ctx_kwargs(),
            ))

    def set_mood(self, mood: str) -> None:
        self.session.set_mood(mood)
        if self.verbose:
            print(f"[player] Mood → {mood}")

    def remove_from_queue(self, track_id: int) -> None:
        removed = self.queue.remove(track_id)
        if removed:
            dispatch(PlaybackEvent(
                type=EventType.QUEUE_REMOVE,
                track_id=track_id,
                position=0.0,
                **self._ctx_kwargs(),
            ))

    # ──────────────────────────────────────────
    # Avanço automático
    # ──────────────────────────────────────────

    def _handle_track_end(self) -> None:
        if self._current_track_id is not None:
            dispatch(PlaybackEvent(
                type=EventType.END_OF_TRACK,
                track_id=self._current_track_id,
                position=1.0,
                **self._ctx_kwargs(),
            ))
        self._advance()

    def _advance(self) -> None:
        # Primeiro tenta a fila manual
        if not self.queue.is_empty():
            entry = self.queue.pop_next()
            self.play_track(entry.track_id)
            return

        # Senão usa o ranking para selecionar
        current_row = (
            queries.get_track_by_id(self._current_track_id)
            if self._current_track_id else None
        )
        result = select_next(
            session=self.session,
            current_track=current_row,
            verbose=self.verbose,
        )
        if result:
            track_id, _ = result
            self.play_track(track_id)

    # ──────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────

    def _ctx_kwargs(self) -> dict:
        return {
            "active_mood":    self.session.active_mood,
            "active_period":  self.session.active_period,
            "active_weekday": self.session.active_weekday,
        }

    @property
    def current_track_id(self) -> Optional[int]:
        return self._current_track_id

    @property
    def is_playing(self) -> bool:
        return self._pipeline.is_playing
