"""
Testes unitários para scorer.py com estados de banco fixos.
Cobre: context_affinity, transition_affinity, fatigue, cold start.
"""

import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch, MagicMock

from ranking.session_state import SessionState
from ranking import scorer as scorer_mod
from ranking.scorer import ScoreExplanation


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

def make_track(track_id=1, analyzed=0, bpm=0.5, energy=0.5,
               brightness=0.5, rhythmic_regularity=0.5, acousticness=0.5):
    row = {
        "id": track_id, "analyzed": analyzed,
        "bpm": bpm, "energy": energy, "brightness": brightness,
        "rhythmic_regularity": rhythmic_regularity, "acousticness": acousticness,
        "artist": "Artista Teste", "title": "Faixa Teste",
        "file_path": f"/music/track{track_id}.mp3", "duration": 240.0,
        "active": 1,
    }
    # sqlite3.Row é difícil de mockar — usamos um dict-like
    return _DictRow(row)


class _DictRow(dict):
    """Simula sqlite3.Row com acesso por chave."""
    def __getitem__(self, key):
        return super().__getitem__(key)


def make_session(mood="Relaxed", period="Evening", weekday="Wednesday"):
    s = SessionState.__new__(SessionState)
    s.active_mood = mood
    s.active_period = period
    s.active_weekday = weekday
    s.played_track_ids = []
    s.consecutive_skips = 0
    import time
    s.started_at = time.time()
    return s


# ──────────────────────────────────────────────
# Testes de context_affinity
# ──────────────────────────────────────────────

class TestContextAffinity:
    def test_neutral_weight_returns_05(self):
        """Peso neutro (500) deve retornar score ~0.5."""
        with (
            patch("ranking.scorer.queries.get_context_id", return_value=1),
            patch("ranking.scorer.queries.get_affinity", return_value=500.0),
        ):
            score, labels = scorer_mod._context_affinity(1, "Relaxed", "Evening", "Wednesday")
        assert abs(score - 0.5) < 0.01

    def test_high_affinity_returns_high_score(self):
        with (
            patch("ranking.scorer.queries.get_context_id", return_value=1),
            patch("ranking.scorer.queries.get_affinity", return_value=900.0),
        ):
            score, _ = scorer_mod._context_affinity(1, "Relaxed", "Evening", "Wednesday")
        assert score > 0.8

    def test_low_affinity_returns_low_score(self):
        with (
            patch("ranking.scorer.queries.get_context_id", return_value=1),
            patch("ranking.scorer.queries.get_affinity", return_value=150.0),
        ):
            score, _ = scorer_mod._context_affinity(1, "Relaxed", "Evening", "Wednesday")
        assert score < 0.25

    def test_missing_context_returns_neutral(self):
        """Contexto não encontrado no banco deve retornar 0.5."""
        with patch("ranking.scorer.queries.get_context_id", return_value=None):
            score, labels = scorer_mod._context_affinity(1, "Relaxed", None, None)
        assert score == 0.5

    def test_active_labels_populated(self):
        with (
            patch("ranking.scorer.queries.get_context_id", return_value=1),
            patch("ranking.scorer.queries.get_affinity", return_value=500.0),
        ):
            _, labels = scorer_mod._context_affinity(1, "Focus", "Morning", "Monday")
        assert "Focus" in labels
        assert "Morning" in labels
        assert "Monday" in labels


# ──────────────────────────────────────────────
# Testes de transition_affinity
# ──────────────────────────────────────────────

class TestTransitionAffinity:
    def test_no_previous_track_returns_neutral(self):
        score = scorer_mod._transition_affinity(None, 2, "Relaxed", "Evening", "Wednesday")
        assert score == 0.5

    def test_high_transition_weight(self):
        with (
            patch("ranking.scorer.queries.get_context_id", return_value=1),
            patch("ranking.scorer.queries.get_transition_weight", return_value=850.0),
        ):
            score = scorer_mod._transition_affinity(1, 2, "Relaxed", "Evening", "Wednesday")
        assert score > 0.75


# ──────────────────────────────────────────────
# Testes de fatigue
# ──────────────────────────────────────────────

class TestFatigue:
    def test_no_fatigue_when_not_played_recently(self):
        session = make_session()
        session.played_track_ids = [10, 11, 12]
        penalty = scorer_mod._fatigue_penalty(99, session)
        assert penalty == 0.0

    def test_fatigue_applied_when_played_recently(self):
        session = make_session()
        session.played_track_ids = [1, 2, 3]
        penalty = scorer_mod._fatigue_penalty(2, session)
        assert penalty < 0.0

    def test_fatigue_outside_window_no_penalty(self):
        from learning.tuning import FATIGUE_WINDOW
        session = make_session()
        # Faixa 1 tocada há mais de FATIGUE_WINDOW faixas atrás
        session.played_track_ids = [1] + [10 + i for i in range(FATIGUE_WINDOW)]
        penalty = scorer_mod._fatigue_penalty(1, session)
        assert penalty == 0.0


# ──────────────────────────────────────────────
# Testes de cold start
# ──────────────────────────────────────────────

class TestColdStart:
    def test_new_track_gets_bonus(self):
        """Faixa nova (0 entradas de afinidade) deve receber bônus."""
        with patch("ranking.scorer.queries.get_play_count_proxy", return_value=0):
            bonus = scorer_mod._cold_start_bonus(99)
        assert bonus > 0.0

    def test_established_track_no_bonus(self):
        """Faixa já estabelecida não deve receber bônus cold start."""
        from learning.tuning import COLD_START_WINDOW
        with patch("ranking.scorer.queries.get_play_count_proxy",
                   return_value=COLD_START_WINDOW + 1):
            bonus = scorer_mod._cold_start_bonus(1)
        assert bonus == 0.0


# ──────────────────────────────────────────────
# Teste integrado do score()
# ──────────────────────────────────────────────

class TestScoreIntegration:
    def test_score_returns_explanation(self):
        session = make_session()
        track = make_track(track_id=1)

        with (
            patch("ranking.scorer.queries.get_context_id", return_value=1),
            patch("ranking.scorer.queries.get_affinity", return_value=500.0),
            patch("ranking.scorer.queries.get_transition_weight", return_value=500.0),
            patch("ranking.scorer.queries.get_play_count_proxy", return_value=10),
        ):
            exp = scorer_mod.score(
                candidate=track,
                session=session,
                current_track=None,
                from_track_id=None,
            )

        assert isinstance(exp, ScoreExplanation)
        assert exp.track_id == 1
        assert isinstance(exp.final_score, float)
        assert exp.reason != ""

    def test_high_affinity_track_beats_low_affinity(self):
        """Faixa com alta afinidade deve ter score maior que faixa com baixa afinidade."""
        session = make_session()
        track_high = make_track(track_id=1)
        track_low  = make_track(track_id=2)

        with (
            patch("ranking.scorer.queries.get_context_id", return_value=1),
            patch("ranking.scorer.queries.get_play_count_proxy", return_value=10),
            patch("ranking.scorer.queries.get_transition_weight", return_value=500.0),
        ):
            with patch("ranking.scorer.queries.get_affinity", return_value=900.0):
                exp_high = scorer_mod.score(track_high, session)
            with patch("ranking.scorer.queries.get_affinity", return_value=150.0):
                exp_low = scorer_mod.score(track_low, session)

        assert exp_high.final_score > exp_low.final_score

    def test_score_dict_structure(self):
        session = make_session()
        track = make_track()

        with (
            patch("ranking.scorer.queries.get_context_id", return_value=1),
            patch("ranking.scorer.queries.get_affinity", return_value=500.0),
            patch("ranking.scorer.queries.get_transition_weight", return_value=500.0),
            patch("ranking.scorer.queries.get_play_count_proxy", return_value=10),
        ):
            exp = scorer_mod.score(track, session)

        d = exp.to_dict()
        assert "track_id" in d
        assert "final_score" in d
        assert "components" in d
        assert "active_contexts" in d
        assert "reason" in d
        assert all(k in d["components"] for k in [
            "context_affinity", "transition_affinity",
            "fatigue_penalty", "similarity_bonus", "exploration_factor"
        ])


# ──────────────────────────────────────────────
# Testes de decay
# ──────────────────────────────────────────────

class TestDecay:
    def test_weight_decreases_with_time(self):
        from learning.decay import _decayed_weight
        original = 800.0
        decayed = _decayed_weight(original, days=30)
        assert decayed < original

    def test_weight_never_below_floor(self):
        from learning.decay import _decayed_weight
        from learning.tuning import WEIGHT_FLOOR
        result = _decayed_weight(WEIGHT_FLOOR + 1, days=10000)
        assert result >= WEIGHT_FLOOR

    def test_zero_days_no_change(self):
        from learning.decay import _decayed_weight
        original = 700.0
        result = _decayed_weight(original, days=0)
        assert abs(result - original) < 0.001


# ──────────────────────────────────────────────
# Testes de reinforcement
# ──────────────────────────────────────────────

class TestReinforcement:
    def _make_event(self, event_type, position=0.0, from_id=None,
                    vol_before=None, vol_after=None):
        from playback.events import PlaybackEvent
        return PlaybackEvent(
            type=event_type,
            track_id=1,
            position=position,
            from_track_id=from_id,
            active_mood="Relaxed",
            active_period="Evening",
            active_weekday="Wednesday",
            volume_before=vol_before,
            volume_after=vol_after,
        )

    def test_complete_track_increases_affinity(self):
        from playback.events import EventType
        from learning import reinforcement
        from learning.tuning import COMPLETE_BONUS

        event = self._make_event(EventType.END_OF_TRACK, position=1.0, from_id=None)

        calls = []
        with (
            patch("learning.reinforcement.queries.get_context_id", return_value=1),
            patch("learning.reinforcement.queries.get_affinity", return_value=500.0),
            patch("learning.reinforcement.queries.upsert_affinity",
                  side_effect=lambda tid, cid, w: calls.append(w)),
            patch("learning.reinforcement.queries.get_transition_weight", return_value=500.0),
            patch("learning.reinforcement.queries.upsert_transition"),
        ):
            reinforcement.process(event)

        # Deve ter chamado upsert_affinity com valor > 500
        assert any(w > 500.0 for w in calls)

    def test_early_skip_decreases_affinity(self):
        from playback.events import EventType
        from learning import reinforcement
        from learning.tuning import SKIP_EARLY_THRESHOLD

        event = self._make_event(
            EventType.SKIP,
            position=SKIP_EARLY_THRESHOLD - 0.01,
        )

        calls = []
        with (
            patch("learning.reinforcement.queries.get_context_id", return_value=1),
            patch("learning.reinforcement.queries.get_affinity", return_value=500.0),
            patch("learning.reinforcement.queries.upsert_affinity",
                  side_effect=lambda tid, cid, w: calls.append(w)),
            patch("learning.reinforcement.queries.get_transition_weight", return_value=500.0),
            patch("learning.reinforcement.queries.upsert_transition"),
        ):
            reinforcement.process(event)

        assert any(w < 500.0 for w in calls)

    def test_volume_up_ignored_below_threshold(self):
        """Aumento de volume menor que o threshold não deve gerar sinal."""
        from playback.events import EventType
        from learning import reinforcement

        event = self._make_event(
            EventType.VOLUME_CHANGE,
            vol_before=0.5,
            vol_after=0.55,   # +10% — abaixo do threshold de 15%
        )

        calls = []
        with (
            patch("learning.reinforcement.queries.get_context_id", return_value=1),
            patch("learning.reinforcement.queries.get_affinity", return_value=500.0),
            patch("learning.reinforcement.queries.upsert_affinity",
                  side_effect=lambda tid, cid, w: calls.append(w)),
            patch("learning.reinforcement.queries.upsert_transition"),
        ):
            reinforcement.process(event)

        # Nenhuma chamada de upsert deve ter ocorrido
        assert len(calls) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
