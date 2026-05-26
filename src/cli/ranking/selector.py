"""
Recebe lista de faixas com scores e seleciona a próxima.
Implementa exploração controlada: proporção configurável seguras vs. exploratórias.
"""

from __future__ import annotations

import random
import sqlite3
from typing import Optional

from database import queries
from learning import tuning as T
from ranking import scorer as scorer_mod
from ranking.scorer import ScoreExplanation
from ranking.session_state import SessionState


def select_next(
    session: SessionState,
    current_track: Optional[sqlite3.Row] = None,
    verbose: bool = False,
) -> Optional[tuple[int, ScoreExplanation]]:
    """
    Seleciona a próxima faixa a reproduzir.

    Returns:
        (track_id, explanation) ou None se biblioteca estiver vazia.
    """
    candidates = queries.get_all_active_tracks()
    if not candidates:
        return None

    from_track_id = current_track["id"] if current_track else None

    # Determina quantos slots são exploratórios
    total = len(candidates)
    n_exploratory = max(1, int(total * T.EXPLORATION_RATIO))

    # Calcula scores para todos
    scored: list[tuple[ScoreExplanation, sqlite3.Row]] = []
    for cand in candidates:
        # Faixas da sessão recente ficam penalizadas — não excluídas
        exp = scorer_mod.score(
            candidate=cand,
            session=session,
            current_track=current_track,
            from_track_id=from_track_id,
            is_exploratory_slot=False,
        )
        scored.append((exp, cand))

    # Ordena por score
    scored.sort(key=lambda x: x[0].final_score, reverse=True)

    # Separa top seguras do resto (exploratórias)
    n_safe = max(1, total - n_exploratory)
    safe_pool    = scored[:n_safe]
    explore_pool = scored[n_safe:]

    # Decide se este slot é exploratório
    is_explore = random.random() < T.EXPLORATION_RATIO and explore_pool

    if is_explore:
        chosen_exp, chosen_track = random.choice(explore_pool)
        # Recalcula com bônus exploratório para a explicação
        chosen_exp = scorer_mod.score(
            candidate=chosen_track,
            session=session,
            current_track=current_track,
            from_track_id=from_track_id,
            is_exploratory_slot=True,
        )
    else:
        chosen_exp, chosen_track = safe_pool[0]

    if verbose:
        print(f"\n[selector] Próxima faixa:")
        print(chosen_exp.verbose_str())
        if verbose and len(safe_pool) > 1:
            print(f"\n[selector] Top 5 candidatos:")
            for exp, _ in safe_pool[:5]:
                title = _track_label(exp.track_id)
                print(f"  {title:40s} score={exp.final_score:.4f}")

    return chosen_exp.track_id, chosen_exp


def _track_label(track_id: int) -> str:
    row = queries.get_track_by_id(track_id)
    if row is None:
        return f"track#{track_id}"
    artist = row["artist"] or "?"
    title  = row["title"]  or f"track#{track_id}"
    return f"{artist} — {title}"
