"""
Encapsula pipeline GStreamer (play, pause, stop, seek).
Emite eventos internos para o módulo learning.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional, Callable


class Pipeline:
    """
    Abstração sobre GStreamer. Se GStreamer não estiver disponível,
    opera em modo simulado (útil para testes e CLI sem áudio).
    """

    def __init__(self, on_track_end: Optional[Callable[[], None]] = None) -> None:
        self._on_track_end = on_track_end
        self._track_id: Optional[int] = None
        self._track_path: Optional[str] = None
        self._duration: float = 0.0
        self._position: float = 0.0
        self._start_time: float = 0.0
        self._volume: float = 0.5
        self._playing: bool = False
        self._gst_player = None
        self._gst_available = self._init_gst()

    def _init_gst(self) -> bool:
        try:
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst, GLib
            Gst.init(None)

            self._Gst = Gst
            self._GLib = GLib

            self._pipeline = Gst.ElementFactory.make("playbin", "player")
            bus = self._pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message::eos", self._on_eos)
            bus.connect("message::error", self._on_error)

            return True
        except Exception:
            return False

    # ──────────────────────────────────────────
    # GStreamer callbacks
    # ──────────────────────────────────────────

    def _on_eos(self, _bus, _msg) -> None:
        self._playing = False
        if self._on_track_end:
            self._on_track_end()

    def _on_error(self, _bus, msg) -> None:
        err, debug = msg.parse_error()
        print(f"[pipeline] GStreamer error: {err}, {debug}")
        self._playing = False

    # ──────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────

    def load(self, track_id: int, path: str, duration: float) -> None:
        self._track_id = track_id
        self._track_path = path
        self._duration = duration
        self._position = 0.0

        if self._gst_available:
            self._pipeline.set_state(self._Gst.State.NULL)
            self._pipeline.set_property("uri", Path(path).as_uri())
            self._pipeline.set_property("volume", self._volume)

    def play(self) -> None:
        self._playing = True
        self._start_time = time.time()
        if self._gst_available:
            self._pipeline.set_state(self._Gst.State.PLAYING)

    def pause(self) -> None:
        self._playing = False
        if self._gst_available:
            self._pipeline.set_state(self._Gst.State.PAUSED)
        else:
            self._position = self.position_relative()

    def stop(self) -> None:
        self._playing = False
        self._position = 0.0
        if self._gst_available:
            self._pipeline.set_state(self._Gst.State.NULL)

    def seek(self, position_seconds: float) -> None:
        if self._gst_available:
            ns = int(position_seconds * 1e9)
            self._pipeline.seek_simple(
                self._Gst.Format.TIME,
                self._Gst.SeekFlags.FLUSH | self._Gst.SeekFlags.KEY_UNIT,
                ns,
            )
        else:
            self._position = position_seconds / self._duration if self._duration else 0.0

    def set_volume(self, volume: float) -> None:
        """volume: 0.0–1.0"""
        self._volume = max(0.0, min(1.0, volume))
        if self._gst_available:
            self._pipeline.set_property("volume", self._volume)

    # ──────────────────────────────────────────
    # Consultas de estado
    # ──────────────────────────────────────────

    def position_relative(self) -> float:
        """Retorna posição relativa na faixa (0.0–1.0)."""
        if self._gst_available and self._duration > 0:
            ok, pos_ns = self._pipeline.query_position(self._Gst.Format.TIME)
            if ok:
                return min(1.0, (pos_ns / 1e9) / self._duration)
        # Simulado
        if self._playing and self._duration > 0:
            elapsed = time.time() - self._start_time
            return min(1.0, elapsed / self._duration)
        return self._position

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def volume(self) -> float:
        return self._volume

    @property
    def current_track_id(self) -> Optional[int]:
        return self._track_id
