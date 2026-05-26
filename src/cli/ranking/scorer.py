"""
Calcula o score composto de cada faixa candidata.
Retorna score + estrutura de explicação completa.

Componentes (Fase 1):
  - Afinidade contextual (média ponderada mood + period + weekday)
  - Afinidade de transição (peso from → to no contexto atual)
  - Penalidade de fadiga (faixas tocadas recentemente na sessão)
  - Bônus de similaridade acústica (compatibilidade com faixa atual)
  - Bônus cold start (faixas novas recebem bônus exploratório)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from database import queries
from learning import tuning as T
from library.similarity import acoustic_similarity
from ranking.session_state import SessionState


# ──────────────────────────────────────────────
# Estrutura de explicação
# ──────────────────────────────────────────────

@dataclass
class ScoreExplanation:
    track_id: int
    final_score: float
    context_affinity: float = 0.0
    transition_affinity: float = 0.0
    fatigue_penalty: float = 0.0
    similarity_bonus: float = 0.0
    exploration_factor: float = 0.0
    active_contexts: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "track_id":   self.track_id,
            "final_score": round(self.final_score, 4),
            "components": {
                "context_affinity":    round(self.context_affinity, 4),
                "transition_affinity": round(self.transition_affinity, 4),
                "fatigue_penalty":     round(self.fatigue_penalty, 4),
                "similarity_bonus":    round(self.similarity_bonus, 4),
                "exploration_factor":  round(self.exploration_factor, 4),
            },
            "active_contexts": self.active_contexts,
            "reason": self.reason,
        }

    def verbose_str(self) -> str:
        d = self.to_dict()
        lines = [
            f"  track_id       : {d['track_id']}",
            f"  final_score    : {d['final_score']}",
            f"  context_affinity  : {d['components']['context_affinity']}",
            f"  transition_affinity: {d['components']['transition_affinity']}",
            f"  fatigue_penalty: {d['components']['fatigue_penalty']}",
            f"  similarity_bonus: {d['components']['similarity_bonus']}",
            f"  exploration_factor: {d['components']['exploration_factor']}",
            f"  contexts       : {', '.join(d['active_contexts'])}",
            f"  reason         : {d['reason']}",
        ]
        return "\n".join(lines)


# ──────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────

def _normalize_weight(weight: float) -> float:
    """Converte peso (0–1000) para score normalizado (0–1)."""
    return weight / 1000.0


def _context_affinity(
    track_id: int,
    mood: Optional[str],
    period: Optional[str],
    weekday: Optional[str],
) -> tuple[float, list[str]]:
    """
    Calcula média ponderada da afinidade contextual.
    Retorna (score_normalizado, lista_de_contextos_ativos).
    """
    weighted_sum = 0.0
    weight_total = 0.0
    active_labels: list[str] = []

    pairs = [
        ("mood",    mood,    T.CONTEXT_WEIGHT_MOOD),
        ("period",  period,  T.CONTEXT_WEIGHT_PERIOD),
        ("weekday", weekday, T.CONTEXT_WEIGHT_WEEKDAY),
    ]

    for ctx_type, ctx_value, ctx_factor in pairs:
        if ctx_value is None:
            continue
        ctx_id = queries.get_context_id(ctx_type, ctx_value)
        if ctx_id is None:
            continue
        raw_weight = queries.get_affinity(track_id, ctx_id)
        norm = _normalize_weight(raw_weight)
        weighted_sum += norm * ctx_factor
        weight_total += ctx_factor
        active_labels.append(ctx_value)

    if weight_total == 0:
        return 0.5, active_labels

    return weighted_sum / weight_total, active_labels


def _transition_affinity(
    from_track_id: Optional[int],
    to_track_id: int,
    mood: Optional[str],
    period: Optional[str],
    weekday: Optional[str],
) -> float:
    """Score de transição, média ponderada pelos contextos ativos."""
    if from_track_id is None:
        return 0.5  # neutro quando não há faixa anterior

    weighted_sum = 0.0
    weight_total = 0.0

    pairs = [
        ("mood",    mood,    T.CONTEXT_WEIGHT_MOOD),
        ("period",  period,  T.CONTEXT_WEIGHT_PERIOD),
        ("weekday", weekday, T.CONTEXT_WEIGHT_WEEKDAY),
    ]

    for ctx_type, ctx_value, ctx_factor in pairs:
        if ctx_value is None:
            continue
        ctx_id = queries.get_context_id(ctx_type, ctx_value)
        if ctx_id is None:
            continue
        raw_weight = queries.get_transition_weight(from_track_id, to_track_id, ctx_id)
        norm = _normalize_weight(raw_weight)
        weighted_sum += norm * ctx_factor
        weight_total += ctx_factor

    if weight_total == 0:
        return 0.5

    return weighted_sum / weight_total


def _fatigue_penalty(track_id: int, session: SessionState) -> float:
    """Penalidade temporária para faixas tocadas recentemente na sessão."""
    recent = session.recent_track_ids(T.FATIGUE_WINDOW)
    if track_id in recent:
        return _normalize_weight(T.FATIGUE_PENALTY)
    return 0.0


def _similarity_bonus(
    candidate: sqlite3.Row,
    current_track: Optional[sqlite3.Row],
) -> float:
    """Bônus de compatibilidade acústica com a faixa atual."""
    if current_track is None:
        return 0.0
    sim = acoustic_similarity(candidate, current_track)
    # Sim já é 0–1; escalonamos pelo bônus máximo configurado
    max_bonus = T.SIMILARITY_BONUS_MAX / 1000.0
    return sim * max_bonus


def _cold_start_bonus(track_id: int) -> float:
    """
    Bônus exploratório para faixas na janela de cold start.
    Usa contagem de entradas de afinidade como proxy de exposição.
    """
    play_proxy = queries.get_play_count_proxy(track_id)
    if play_proxy < T.COLD_START_WINDOW:
        return _normalize_weight(T.COLD_START_BONUS)
    return 0.0


# ──────────────────────────────────────────────
# Função principal
# ──────────────────────────────────────────────

def score(
    candidate: sqlite3.Row,
    session: SessionState,
    current_track: Optional[sqlite3.Row] = None,
    from_track_id: Optional[int] = None,
    is_exploratory_slot: bool = False,
) -> ScoreExplanation:
    """
    Calcula o score composto para um candidato.

    Args:
        candidate:           Linha da tabela tracks do candidato.
        session:             Estado da sessão atual.
        current_track:       Linha da faixa sendo reproduzida agora (para similaridade).
        from_track_id:       ID da faixa atual (para transições).
        is_exploratory_slot: Se True, aplica bônus de exploração.
    """
    track_id = candidate["id"]
    mood    = session.active_mood
    period  = session.active_period
    weekday = session.active_weekday

    ctx_aff, active_labels = _context_affinity(track_id, mood, period, weekday)
    trans_aff = _transition_affinity(from_track_id, track_id, mood, period, weekday)
    fatigue   = _fatigue_penalty(track_id, session)
    sim_bonus = _similarity_bonus(candidate, current_track)

    cold_bonus = _cold_start_bonus(track_id)
    exploration_factor = cold_bonus if is_exploratory_slot else 0.0

    final = ctx_aff + (trans_aff * 0.3) + fatigue + sim_bonus + exploration_factor

    # Gera razão textual
    reason = _build_reason(ctx_aff, trans_aff, fatigue, sim_bonus, exploration_factor)

    return ScoreExplanation(
        track_id=track_id,
        final_score=final,
        context_affinity=ctx_aff,
        transition_affinity=trans_aff,
        fatigue_penalty=fatigue,
        similarity_bonus=sim_bonus,
        exploration_factor=exploration_factor,
        active_contexts=active_labels,
        reason=reason,
    )


def _build_reason(
    ctx: float,
    trans: float,
    fatigue: float,
    sim: float,
    exploration: float,
) -> str:
    parts: list[str] = []
    if ctx >= 0.7:
        parts.append("alta afinidade contextual")
    elif ctx >= 0.5:
        parts.append("afinidade contextual moderada")
    else:
        parts.append("baixa afinidade contextual")

    if trans >= 0.6:
        parts.append("boa transição da faixa anterior")

    if fatigue < 0:
        parts.append("penalidade de fadiga aplicada")

    if sim > 0.05:
        parts.append("compatibilidade acústica com faixa atual")

    if exploration > 0:
        parts.append("bônus exploratório (faixa nova)")

    return "; ".join(parts) if parts else "score neutro"
