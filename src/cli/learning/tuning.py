"""
Centraliza todos os parâmetros ajustáveis do sistema.
Nenhum threshold, delta ou fator deve ser hardcoded fora deste módulo.
"""

# ──────────────────────────────────────────────
# Heurísticas de reforço
# ──────────────────────────────────────────────

# Posição relativa (0–1) que define skip precoce
SKIP_EARLY_THRESHOLD: float = 0.30

# Deltas de afinidade contextual
SKIP_EARLY_PENALTY: float = -80.0    # skip antes do threshold
SKIP_LATE_PENALTY: float = -20.0     # skip após o threshold
COMPLETE_BONUS: float = 40.0         # faixa ouvida até o final
REPEAT_BONUS: float = 60.0           # repetição manual
MANUAL_SELECT_BONUS: float = 100.0   # seleção manual (sinal mais forte)
VOLUME_UP_BONUS: float = 15.0        # aumento de volume ≥ 15%
QUEUE_REMOVE_PENALTY: float = -50.0  # remoção da fila

# Limiares complementares
VOLUME_CHANGE_THRESHOLD: float = 0.15   # variação mínima de volume para gerar sinal

# ──────────────────────────────────────────────
# Decay temporal
# ──────────────────────────────────────────────

DECAY_RATE: float = 0.995        # fator multiplicativo por dia sem interação
WEIGHT_FLOOR: float = 100.0      # piso mínimo (escala 0–1000)
WEIGHT_CEILING: float = 1000.0   # teto máximo
WEIGHT_NEUTRAL: float = 500.0    # peso inicial de faixas novas

# ──────────────────────────────────────────────
# Cold start
# ──────────────────────────────────────────────

COLD_START_WINDOW: int = 5       # reproduções na janela de apresentação
COLD_START_BONUS: float = 80.0   # bônus exploratório durante a janela

# ──────────────────────────────────────────────
# Pesos relativos de contexto na agregação
# ──────────────────────────────────────────────

CONTEXT_WEIGHT_MOOD: float = 1.5
CONTEXT_WEIGHT_PERIOD: float = 1.0
CONTEXT_WEIGHT_WEEKDAY: float = 0.5

# ──────────────────────────────────────────────
# Seleção e exploração
# ──────────────────────────────────────────────

EXPLORATION_RATIO: float = 0.20    # proporção de faixas exploratórias na seleção

# Penalidade de fadiga (redução temporária por reprodução recente)
FATIGUE_PENALTY: float = -150.0
FATIGUE_WINDOW: int = 10           # últimas N faixas da sessão que sofrem fadiga

# ──────────────────────────────────────────────
# Similaridade acústica
# ──────────────────────────────────────────────

SIMILARITY_WEIGHTS: dict = {
    "bpm_normalized":     0.25,
    "energy":             0.25,
    "brightness":         0.20,
    "rhythmic_regularity": 0.20,
    "acousticness":       0.10,
}

# Bônus máximo de similaridade acústica aplicado ao score
SIMILARITY_BONUS_MAX: float = 50.0
