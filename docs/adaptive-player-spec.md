# Adaptive Music Player — Especificação Técnica

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Conceitos Fundamentais](#2-conceitos-fundamentais)
3. [Estrutura de Módulos](#3-estrutura-de-módulos)
4. [Sistema de Aprendizado](#4-sistema-de-aprendizado)
5. [Banco de Dados](#5-banco-de-dados)
6. [Análise Acústica](#6-análise-acústica)
7. [Roadmap de Fases](#7-roadmap-de-fases)
8. [Regras Arquiteturais](#8-regras-arquiteturais)

---

## 1. Visão Geral

O projeto é um player de música heurístico e adaptativo desenvolvido em Python. Seu objetivo central é aprender automaticamente os hábitos do usuário a partir do comportamento de escuta, sem depender de interações explícitas como "gostei" ou "não gostei".

O sistema interpreta sinais comportamentais indiretos — skips, repetições, variações de volume, ordem das faixas, horários e padrões de sessão — para construir modelos dinâmicos de preferência. Em vez de tratar músicas como itens isolados, o sistema modela relações entre músicas, entre músicas e contextos, e entre sequências de reprodução.

Essas relações são armazenadas como pesos ajustáveis que evoluem continuamente com o uso. O foco não é recomendação por popularidade ou dados externos, mas adaptação contextual personalizada rodando inteiramente de forma local.

### 1.1 Filosofia do Projeto

O sistema deve se comportar como um DJ adaptativo pessoal, não como um recomendador tradicional. A experiência pretendida é de continuidade, coerência e adaptação contextual progressiva.

Comportamento esperado:

- **Discreto** — não exige configuração constante
- **Progressivamente inteligente** — melhora com o uso
- **Contextual** — responde ao momento atual da sessão
- **Interpretável** — decisões podem ser explicadas
- **Não intrusivo** — não interrompe nem reclama atenção

> O objetivo não é construir IA pesada. É construir um motor heurístico robusto que gere comportamento inteligente através de relações simples e cumulativas.

### 1.2 Stack Tecnológica

| Camada | Tecnologias |
|---|---|
| Núcleo | Python, SQLite, GStreamer |
| Análise musical | Librosa, FFmpeg, Mutagen |
| Interface (futuro) | GTK4, Libadwaita, PyGObject |

---

## 2. Conceitos Fundamentais

### 2.1 Aprendizado Implícito

O sistema prioriza sinais comportamentais indiretos. Interações explícitas existem, mas funcionam como reforço secundário.

| Tipo de sinal | Exemplos |
|---|---|
| Implícito (primário) | Ouvir até o final, skip precoce, repetição manual, variação de volume, remoção da fila, padrões de horário, padrões de sequência |
| Explícito (secundário) | Gostei, não gostei, favoritar, excluir |

### 2.2 Contextos

Toda reprodução acontece dentro de um conjunto de contextos ativos simultaneamente. Contextos não definem regras fixas — eles influenciam os pesos de afinidade das faixas.

Contextos suportados inicialmente:

- `mood` — estado de escuta ativo (Relaxed, Energetic, Focus, Happy)
- `period` — período do dia (Morning, Afternoon, Evening, Night)
- `weekday` — dia da semana (Monday … Sunday)

Contextos planejados para fases posteriores:

- `device` — dispositivo de saída (headphone, speaker)
- `volume_range` — faixa de volume médio da sessão

#### Agregação de múltiplos contextos

Quando múltiplos contextos estão ativos, o score final de uma faixa é calculado pela média ponderada dos pesos de afinidade de cada contexto ativo. Os pesos relativos de cada tipo de contexto são configuráveis em `tuning.py`.

> Exemplo: mood com fator 1.5, period com 1.0 e weekday com 0.5 — o mood influencia mais o ranking final, mas todos contribuem.

### 2.3 Humores (Moods)

Moods representam estados subjetivos de escuta. O sistema trabalha com dois tipos:

- **Manuais** — definidos pelo usuário (Fases 0–2)
- **Emergentes** — detectados automaticamente a partir dos pesos acumulados em `track_affinity` e `transitions` (Fase 3)

O objetivo não é classificar músicas em gêneros emocionais absolutos, mas descobrir relações práticas de uso. Um mood pode representar "músicas para foco", "sequências noturnas" ou "sessões de alta energia", mesmo sem que o usuário tenha definido isso explicitamente.

### 2.4 Sessões

Uma sessão corresponde a um ciclo de uso do player: começa quando o player é aberto e termina quando ele é fechado. Não há persistência de estado entre sessões — cada abertura inicia uma sessão nova.

Ao iniciar, o sistema parte do mood neutro e organiza o ranking com base no `weekday` e `period` atuais. O mood pode ser alterado manualmente a qualquer momento durante a sessão.

O estado da sessão atual é mantido inteiramente em memória por `ranking/session_state.py` e descartado ao fechar. Não há tabela de sessões no banco — os padrões de longo prazo emergem naturalmente dos pesos acumulados em `track_affinity` e `transitions`.

### 2.5 Relações em vez de Histórico Bruto

O sistema não armazena logs de eventos. Eventos são imediatamente convertidos em relações ponderadas. O banco armazena apenas:

- **Afinidades** — peso de uma faixa em determinado contexto
- **Transições** — peso de uma faixa após outra em determinado contexto
- **Configurações por faixa** — volume preferido

> Isso elimina necessidade de rotinas de manutenção e mantém o sistema focado em comportamento emergente, não em auditoria de eventos passados.

---

## 3. Estrutura de Módulos

O projeto é dividido em módulos independentes com responsabilidades bem delimitadas. Cada módulo pode evoluir sem forçar reescrita dos demais.

| Módulo | Responsabilidade principal |
|---|---|
| `library/` | Escaneamento, metadata, análise acústica |
| `playback/` | Pipeline GStreamer, fila, volume, eventos |
| `learning/` | Atualização de pesos, decay, heurísticas |
| `ranking/` | Cálculo de score, seleção de faixas, explicabilidade |
| `database/` | Schema, queries, migrations |
| `cli/` | Interface de linha de comando (Fase 0) |
| `ui/` | Interface GTK4 (Fase 6) |

### 3.1 library/

#### `library/scanner.py`

- Percorre recursivamente diretórios configurados
- Detecta arquivos de áudio por extensão e MIME type
- Insere registros novos em `tracks` com metadata básica
- Marca faixas removidas como inativas (sem deleção, para preservar histórico de pesos)
- Enfileira novas faixas para análise acústica
- Ao encontrar caminho desconhecido, calcula `file_hash` e tenta reconciliar com entrada existente antes de inserir como novo registro (ver seção 5.3)

#### `library/metadata.py`

- Extrai `title`, `artist`, `album`, `year`, `genre`, `duration` via Mutagen
- Normaliza tags inconsistentes (encoding, campos vazios)
- Atualiza a tabela `tracks`

#### `library/acoustic_analyzer.py`

- Processa a fila de análise de forma assíncrona, em segundo plano
- Extrai e deriva os atributos acústicos via Librosa/FFmpeg (ver seção 6)
- Normaliza todos os atributos para escala 0–1 antes de persistir
- Atualiza o campo `analyzed = 1` ao concluir
- Nunca bloqueia reprodução ou interface

#### `library/similarity.py`

- Calcula score de similaridade acústica entre duas faixas
- Todos os atributos já estão normalizados no banco — sem conversão adicional aqui
- Usado pelo ranking para cold start, bônus de transição e descoberta
- Evolui para busca vetorial em fase posterior (ver seção 6.3)

### 3.2 playback/

#### `playback/pipeline.py`

- Encapsula pipeline GStreamer (play, pause, stop, seek)
- Controla volume com normalização por faixa via `track_play_settings`
- Emite eventos internos para o módulo `learning`

#### `playback/queue.py`

- Gerencia a fila de reprodução atual
- Expõe operações: `add`, `remove`, `reorder`, `peek_next`
- Separa faixas seguras de exploratórias (usado pelo ranking na Fase 2)

#### `playback/events.py`

- Define e despacha o conjunto canônico de eventos de reprodução
- Eventos registrados: `play`, `pause`, `skip`, `go_back`, `end_of_track`, `volume_change`, `manual_select`, `queue_remove`
- Cada evento carrega: `track_id`, `timestamp`, contexto ativo, posição relativa na faixa no momento do evento

> `volume_change` só gera sinal de aprendizado quando a variação é ≥ 75% do volume atual, para ignorar ajustes finos.

### 3.3 learning/

#### `learning/reinforcement.py`

- Aplica reforço positivo e negativo nos pesos de `track_affinity` e `transitions`
- Recebe eventos do playback e aplica as regras heurísticas correspondentes
- Consulta `tuning.py` para todos os deltas e thresholds — nenhum valor hardcoded aqui

#### `learning/rules.py`

- Define as regras heurísticas de forma declarativa, separada da lógica de aplicação
- Facilita adição de novas regras sem alterar `reinforcement.py`

#### `learning/decay.py`

- Aplica decay temporal nos pesos de `track_affinity` e `transitions`
- Modelo: `weight *= DECAY_RATE` por dia sem interação (padrão: 0.995)
- Piso mínimo configurável (padrão: 100, escala 0–1000) para evitar inacessibilidade total
- Executado ao abrir o player ou em thread background periódica

> O piso garante que músicas antigas nunca se tornem completamente inacessíveis — apenas improváveis. Uma nova interação pode reativar uma faixa adormecida.

#### `learning/tuning.py`

- Centraliza todos os parâmetros ajustáveis do sistema
- Nenhum threshold, delta ou fator deve ser hardcoded fora deste módulo

Parâmetros de referência:

| Parâmetro | Descrição |
|---|---|
| `SKIP_EARLY_THRESHOLD` | Posição relativa (0–1) que define skip precoce |
| `SKIP_EARLY_PENALTY` | Delta negativo para skip precoce |
| `SKIP_LATE_PENALTY` | Delta negativo para skip tardio |
| `COMPLETE_BONUS` | Delta positivo para faixa completa |
| `REPEAT_BONUS` | Delta positivo para repetição manual |
| `MANUAL_SELECT_BONUS` | Delta positivo para seleção manual (sinal mais forte) |
| `VOLUME_UP_BONUS` | Delta positivo para aumento de volume ≥ 15% |
| `DECAY_RATE` | Fator de decay diário (ex: 0.995) |
| `WEIGHT_FLOOR` | Piso mínimo de peso (ex: 100) |
| `CONTEXT_WEIGHT_MOOD` | Peso relativo do contexto mood na agregação |
| `CONTEXT_WEIGHT_PERIOD` | Peso relativo do contexto period |
| `CONTEXT_WEIGHT_WEEKDAY` | Peso relativo do contexto weekday |
| `EXPLORATION_RATIO` | Proporção de faixas exploratórias na seleção (ex: 0.20) |
| `COLD_START_WINDOW` | Número de reproduções na janela de apresentação |
| `COLD_START_BONUS` | Bônus exploratório durante a janela de apresentação |

### 3.4 ranking/

#### `ranking/scorer.py`

- Calcula o score composto de cada faixa candidata
- Componentes do score:
  - Afinidade contextual (média ponderada dos contextos ativos)
  - Afinidade de transição (peso da faixa atual → candidata)
  - Penalidade de fadiga (redução temporária para faixas tocadas recentemente)
  - Bônus de similaridade acústica (compatibilidade com a faixa atual)
  - Fator de exploração (bônus para faixas exploratórias no ciclo atual)
- Retorna junto com o score uma estrutura de explicação (ver seção 4.4)

#### `ranking/selector.py`

- Recebe lista de faixas com scores e seleciona a próxima
- Implementa exploração controlada: proporção configurável de faixas seguras vs. exploratórias
- Faixas exploratórias bem recebidas migram naturalmente para o grupo seguro via reforço positivo acumulado — não há mecanismo separado para essa transição
- Em Recovery Mode (múltiplos skips consecutivos): aumenta proporção segura temporariamente

#### `ranking/session_state.py`

- Mantém o estado da sessão atual em memória
- Rastreia: sequência de faixas tocadas, skips recentes, energia média acumulada
- Alimenta as heurísticas de progressão energética e Drift Control (Fase 2)
- Descartado ao fechar o player — sem persistência

### 3.5 database/

#### `database/schema.py`

- Define e cria todas as tabelas via SQL
- Gerencia migrations com tabela de versão interna

#### `database/queries.py`

- Centraliza todas as queries SQL como funções nomeadas
- Nenhum SQL deve aparecer fora deste módulo

#### `database/connection.py`

- Gerencia conexão SQLite com WAL mode habilitado
- Expõe context manager para transações

---

## 4. Sistema de Aprendizado

### 4.1 Heurísticas de Reforço

Todos os deltas são parâmetros configuráveis em `tuning.py`.

| Evento | Efeito nos pesos |
|---|---|
| Faixa completa (`end_of_track`) | `+` afinidade contextual, `+` transição |
| Skip precoce (< `SKIP_EARLY_THRESHOLD`) | `−` afinidade contextual forte, `−` transição |
| Skip tardio (≥ threshold) | `−` afinidade contextual leve |
| Repetição manual | `+` afinidade contextual, `+` transição |
| Seleção manual (`manual_select`) | `+` afinidade contextual forte (sinal mais forte do sistema) |
| Aumento de volume (≥ 15%) | `+` afinidade contextual leve |
| Remoção da fila (`queue_remove`) | `−` afinidade contextual, `−` transição |

> Repetição recente da mesma faixa reduz o score temporariamente via penalidade de fadiga, mas não altera os pesos permanentes.

### 4.2 Decay Temporal

Sem decay, o sistema estagnaria nas preferências antigas. O mecanismo adotado:

- **Tipo:** exponencial por tempo
- **Taxa padrão:** `weight *= DECAY_RATE` por dia sem interação (ex: 0.995)
- **Piso mínimo:** configurável, padrão 100 (escala 0–1000)
- **Execução:** ao abrir o player, ou em thread background periódica

### 4.3 Cold Start de Faixas Novas

Faixas recém-adicionadas iniciam com peso neutro (500 em escala 0–1000) e passam por uma janela de apresentação controlada:

- Nas primeiras `COLD_START_WINDOW` reproduções, a faixa recebe um bônus exploratório temporário
- Após a janela, entra no ranking normal com os pesos acumulados
- Faixas sem análise acústica ainda recebem score por afinidade contextual e metadata
- A similaridade acústica com faixas de alta afinidade serve como estimativa inicial de compatibilidade quando disponível

### 4.4 Explicabilidade do Score

Toda decisão de seleção é acompanhada de uma estrutura de explicação. Isso facilita debug e aumenta a percepção de inteligência do sistema.

```json
{
  "track_id": 42,
  "final_score": 0.74,
  "components": {
    "context_affinity": 0.81,
    "transition_affinity": 0.68,
    "fatigue_penalty": -0.10,
    "similarity_bonus": 0.05,
    "exploration_factor": 0.00
  },
  "active_contexts": ["Evening", "Focus", "Wednesday"],
  "reason": "Alta afinidade com o período atual e boa transição da faixa anterior"
}
```

A razão textual é exibida no modo verbose da CLI e no painel de explicabilidade da UI (Fase 6).

---

## 5. Banco de Dados

### 5.1 Schema Completo

```sql
-- Faixas da biblioteca
CREATE TABLE IF NOT EXISTS tracks (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path         TEXT UNIQUE NOT NULL,
    file_hash         TEXT,           -- hash dos primeiros 64KB + duração
    title             TEXT,
    artist            TEXT,
    album             TEXT,
    duration          REAL,
    year              TEXT,
    genre             TEXT,
    bpm               REAL,           -- batidas por minuto
    energy            REAL,           -- 0.0–1.0
    loudness          REAL,           -- 0.0–1.0 (normalizado de dBFS)
    acousticness      REAL,           -- 0.0–1.0
    brightness        REAL,           -- 0.0–1.0 (centroid espectral normalizado)
    rhythmic_regularity REAL,         -- 0.0–1.0 (1 = ritmo muito regular)
    spectral_centroid REAL,           -- valor bruto em Hz (usado em cálculos internos)
    analyzed          INTEGER DEFAULT 0,
    active            INTEGER DEFAULT 1,  -- 0 se arquivo removido da biblioteca
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Definição de contextos
CREATE TABLE IF NOT EXISTS contexts (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    type  TEXT NOT NULL,
    value TEXT NOT NULL,
    UNIQUE(type, value)
);

-- Afinidade faixa × contexto
CREATE TABLE IF NOT EXISTS track_affinity (
    track_id   INTEGER NOT NULL,
    context_id INTEGER NOT NULL,
    weight     REAL NOT NULL DEFAULT 500.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (track_id, context_id),
    FOREIGN KEY (track_id)   REFERENCES tracks(id),
    FOREIGN KEY (context_id) REFERENCES contexts(id)
);

-- Afinidade de transição entre faixas
CREATE TABLE IF NOT EXISTS transitions (
    from_track_id INTEGER NOT NULL,
    to_track_id   INTEGER NOT NULL,
    context_id    INTEGER NOT NULL,
    weight        REAL DEFAULT 500.0,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (from_track_id, to_track_id, context_id),
    FOREIGN KEY (from_track_id) REFERENCES tracks(id),
    FOREIGN KEY (to_track_id)   REFERENCES tracks(id),
    FOREIGN KEY (context_id)    REFERENCES contexts(id)
) WITHOUT ROWID;

-- Configurações de reprodução por faixa
CREATE TABLE IF NOT EXISTS track_play_settings (
    track_id         INTEGER PRIMARY KEY,
    preferred_volume INTEGER DEFAULT 50,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);

-- Contextos iniciais
INSERT OR IGNORE INTO contexts (type, value) VALUES
    ('mood', 'Relaxed'),   ('mood', 'Energetic'),
    ('mood', 'Focus'),     ('mood', 'Happy'),
    ('period', 'Morning'), ('period', 'Afternoon'),
    ('period', 'Evening'), ('period', 'Night'),
    ('weekday', 'Sunday'),    ('weekday', 'Monday'),
    ('weekday', 'Tuesday'),   ('weekday', 'Wednesday'),
    ('weekday', 'Thursday'),  ('weekday', 'Friday'),
    ('weekday', 'Saturday');
```

### 5.2 Decisões de Design

| Decisão | Justificativa |
|---|---|
| `weight` como `REAL` | Operações de decay acumulam erro em `INTEGER`; `REAL` evita arredondamentos progressivos |
| `active` em `tracks` | Preserva histórico de pesos quando o arquivo é removido do disco |
| `file_hash` em `tracks` | Permite reconciliar faixas renomeadas ou movidas sem perder histórico |
| Sem tabela de sessões | Estado de sessão vive em memória; padrões de longo prazo emergem dos pesos acumulados |
| `track_play_settings` separado | Volume preferido é ortogonal à afinidade contextual |

### 5.3 Gerenciamento de Arquivos Movidos

O campo `file_hash` armazena um hash derivado dos primeiros 64KB do arquivo combinado com a duração. Quando um rescan detecta um caminho desconhecido, o sistema tenta reconciliar antes de inserir como novo registro:

1. Rescan encontra arquivo em caminho desconhecido
2. Calcula `file_hash` do arquivo
3. Busca em `tracks` por `file_hash` correspondente
4. Se encontrado: `UPDATE file_path`, mantém `id` e todos os pesos
5. Se não encontrado: `INSERT` como faixa nova

> Antes de assumir que é a mesma faixa, o sistema confirma também duração e tamanho do arquivo para reduzir risco de colisão de hash.

---

## 6. Análise Acústica

### 6.1 Estratégia de Processamento

A análise acústica é assíncrona, incremental e lazy. O sistema nunca bloqueia reprodução ou interface aguardando análise. Ao detectar novas faixas, apenas metadata básica e duração precisam estar disponíveis imediatamente.

**Importante:** todos os atributos são normalizados para a escala 0–1 antes de serem persistidos no banco. Isso elimina a necessidade de normalização em runtime durante os cálculos de similaridade.

### 6.2 Atributos e Método de Extração

| Atributo | Método |
|---|---|
| `bpm` | `librosa.beat.beat_track` — extração direta |
| `energy` | RMS médio via `librosa.feature.rms`, normalizado pelo valor máximo da faixa |
| `loudness` | dBFS médio via FFmpeg, normalizado de [−60, 0] para [0, 1] |
| `acousticness` | Razão entre energia harmônica e percussiva via `librosa.effects.hpss` |
| `brightness` | `librosa.feature.spectral_centroid` médio, normalizado pelo Nyquist (sr/2) |
| `rhythmic_regularity` | `1 − coeficiente_de_variação(intervalos_entre_beats)`, calculado a partir de `librosa.beat.beat_track` |
| `spectral_centroid` | Valor bruto em Hz — mantido para uso em cálculos internos de similaridade antes da normalização |

> `brightness` e `rhythmic_regularity` substituem `valence` e `danceability`. Esses dois atributos eram derivados de forma indireta e com baixa confiabilidade acústica. `brightness` e `rhythmic_regularity` são métricas honestas sobre o que a análise realmente mede, e cobrem dimensões complementares úteis para similaridade.

### 6.3 Similaridade Acústica

A similaridade entre duas faixas é calculada como distância euclidiana normalizada sobre o vetor de atributos. Como todos os atributos estão na mesma escala (0–1) no banco, não há risco de um atributo dominar o cálculo por diferença de escala.

```python
SIMILARITY_WEIGHTS = {
    "bpm_normalized": 0.25,   # bpm / 250.0 para comparação
    "energy":         0.25,
    "brightness":     0.20,
    "rhythmic_regularity": 0.20,
    "acousticness":   0.10,
}

def acoustic_similarity(a: Track, b: Track) -> float:
    diff = sum(
        w * (getattr(a, attr) - getattr(b, attr)) ** 2
        for attr, w in SIMILARITY_WEIGHTS.items()
    )
    return max(0.0, 1.0 - diff ** 0.5)
```

Os pesos da função de similaridade são configuráveis em `tuning.py`.

Esta similaridade é usada para:

- Estimativa de afinidade inicial em cold start
- Bônus de compatibilidade de transição no scorer
- Descoberta de faixas pouco conhecidas similares a favoritas

Metadata (gênero, artista, álbum, ano) contribui como sinal secundário de similaridade, mas o comportamento observado do usuário sempre prevalece sobre metadados.

### 6.4 Evolução Futura da Similaridade

Após a Fase 2, a similaridade pode evoluir para:

- Embeddings vetoriais dos atributos acústicos
- Clustering de sessões para descoberta automática de padrões
- Nearest-neighbor search com `annoy` ou `faiss`

Bibliotecas candidatas: `numpy`, `scipy`, `scikit-learn`, `annoy`, `faiss`. Não são necessárias nas fases iniciais.

---

## 7. Roadmap de Fases

### Fase 0 — Fundação (CLI)

Objetivo: player funcional com persistência mínima e infraestrutura completa de módulos.

- Escaneamento e indexação de biblioteca
- Extração de metadata e análise acústica assíncrona
- Reprodução básica via GStreamer (play, pause, skip, volume)
- Fila simples com seleção aleatória
- Registro de eventos e atualização de pesos (sem ranking ainda)
- CLI com comandos básicos
- Schema completo criado e seedado

### Fase 1 — Heurísticas Básicas

Objetivo: seleção de próximas músicas guiada por afinidade contextual.

- Scorer com afinidade contextual (mood + period + weekday)
- Regras de reforço positivo e negativo completas
- Decay temporal implementado
- Exploração controlada (proporção configurável)
- Output de explicação do score na CLI (modo verbose)

### Fase 2 — Contexto Avançado

Objetivo: comportamento sensível à progressão e ao arco da sessão.

- Progressão energética (detectar tendência crescente/decrescente)
- Compatibilidade de transição por atributos acústicos
- Recovery Mode após múltiplos skips consecutivos
- Drift Control (evitar loops de artista ou energia)
- Contextos de dispositivo e `volume_range`

### Fase 3 — Humores Emergentes

Objetivo: detectar padrões automaticamente a partir dos pesos acumulados.

- Análise de clusters nos pesos de `track_affinity` e `transitions`
- Geração de pseudo-moods a partir dos clusters detectados
- Interface para o usuário aceitar, renomear ou ignorar moods sugeridos

### Fase 4 — Inteligência de Playlist

Objetivo: experiência de "DJ contextual" com adaptação em tempo real.

- Session Intent Detection (inferir foco, descoberta, background, alta energia)
- Transições suaves por compatibilidade acústica
- Controle de arco energético da sessão
- Adaptação dinâmica após eventos (skip, repetição, manual select)

### Fase 5 — Refinamentos Opcionais

- Embeddings vetoriais e busca por similaridade avançada
- Sincronização e suporte multi-device
- Scrobbling (Last.fm ou local)
- API local para integrações externas
- Sistema de plugins

### Fase 6 — Interface GNOME

Objetivo: transformar o backend em aplicação desktop completa.

- GTK4 + Libadwaita + PyGObject
- Gerenciamento de biblioteca com visualização de análise acústica
- Visualização de moods e mapa de afinidades
- Painel de explicabilidade: por que esta faixa foi escolhida?
- Estatísticas de uso e evolução de preferências

---

## 8. Regras Arquiteturais

| Regra | Descrição |
|---|---|
| Sem logging bruto | Eventos são convertidos em pesos imediatamente. O sistema não é um log de auditoria. |
| Aprendizado incremental | Sem reprocessamento batch. Pesos são atualizados a cada evento. |
| Score separado de decisão | `scorer.py` calcula e explica. `selector.py` decide. Debug é trivial. |
| Tudo configurável | Nenhum threshold ou delta é hardcoded. Tudo passa por `tuning.py`. |
| SQL centralizado | Nenhuma query SQL fora de `database/queries.py`. |
| Análise nunca bloqueia | `acoustic_analyzer.py` é sempre assíncrono. |
| Atributos normalizados no banco | A normalização acontece uma vez, na análise. Cálculos de runtime operam sempre em 0–1. |

### 8.1 Estratégia de Testes

Para um sistema de pesos evolutivos, regressões silenciosas são o principal risco — uma mudança no scorer começa a favorecer sempre o mesmo artista e só é percebida semanas depois.

Cobertura mínima necessária:

- Testes unitários para `scorer.py` e `reinforcement.py` com estados de banco fixos
- Testes de decay: verificar que pesos chegam ao piso após N dias sem interação
- Testes de cold start: faixa nova deve aparecer nos primeiros resultados com bônus exploratório
- **Modo de simulação/replay:** rodar sequência histórica de eventos e inspecionar evolução dos pesos

> O modo de simulação é especialmente útil para calibrar os parâmetros de `tuning.py` sem precisar usar o player por semanas. Uma sequência de eventos pré-gravada deve ser suficiente para validar que o comportamento do sistema é o esperado após ajustes.