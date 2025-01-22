# Especificação Geral do Projeto

## Visão Geral

O projeto consiste em um player de música heurístico e adaptativo, desenvolvido em Python, cujo objetivo é aprender automaticamente os hábitos e preferências do usuário a partir do comportamento de escuta, sem depender exclusivamente de interações explícitas como “gostei” ou “não gostei”.

O sistema deve interpretar sinais indiretos durante o uso cotidiano — como skips, repetições, volume, ordem das faixas, horários, contexto e padrões de sessão — para construir modelos dinâmicos de preferência.

Ao invés de tratar músicas como itens isolados, o sistema modela relações:

* entre músicas
* entre músicas e contextos
* entre sequências de reprodução
* entre sessões de escuta

Essas relações são armazenadas como pesos ajustáveis, permitindo que o comportamento do player evolua continuamente conforme o uso.

O foco principal não é recomendação baseada em popularidade ou dados externos, mas sim adaptação contextual personalizada.

---

# Conceitos Fundamentais

## 1. Aprendizado Implícito

O sistema prioriza sinais comportamentais indiretos:

* ouvir até o final
* skip precoce
* repetição manual
* alteração de volume
* remoção da fila
* padrões de horário
* padrões de sequência

Interações explícitas ainda podem existir:

* gostei
* não gostei
* favoritar
* excluir

Funcionam como reforço adicional.

---

## 2. Contextos

Toda reprodução acontece dentro de um conjunto de contextos.

Exemplos:

* período do dia
* dia da semana
* humor selecionado
* dispositivo de saída
* volume médio
* tipo de sessão

Os contextos não definem regras fixas.
Eles apenas influenciam pesos de afinidade.

---

## 3. Humores (“Moods”)

O sistema trabalha com o conceito de “humores”, que representam estados subjetivos de escuta.

Inicialmente:

* podem ser definidos manualmente

Posteriormente:

* podem emergir automaticamente a partir de padrões detectados nas sessões.

O objetivo não é classificar músicas em gêneros emocionais absolutos, mas descobrir relações práticas de uso.

Exemplo:
um “mood” pode representar:

* músicas usadas para foco
* músicas noturnas
* sequências energéticas
* sessões introspectivas

Mesmo que o usuário nunca tenha definido isso explicitamente.

---

## 4. Relações ao invés de Histórico Bruto

O sistema evita armazenar logs completos indefinidamente.

Ao invés disso:
eventos são convertidos em relações ponderadas.

Exemplos:

* “essa faixa funciona bem após outra”
* “essa música é frequentemente skipada pela manhã”
* “essa transição mantém sessões longas”
* “essa faixa costuma tocar em volume alto”

O banco armazena principalmente:

* afinidades
* tendências
* pesos de relacionamento

Isso reduz complexidade e mantém o sistema focado em comportamento emergente.

---

# Objetivos do Projeto

## Objetivo Principal

Criar um player que pareça compreender hábitos de escuta sem exigir treinamento manual constante.

---

## Objetivos Secundários

### Reprodução Contextual

Selecionar músicas apropriadas para:

* horário
* sessão
* sequência atual
* comportamento recente

---

### Evolução Contínua

O sistema deve:

* adaptar-se ao longo do tempo
* permitir mudança de gosto
* evitar estagnação

---

### Explicabilidade

As decisões devem ser interpretáveis.

Exemplo:

> “Esta faixa foi escolhida porque:
>
> * combina com o horário atual
> * possui alta afinidade com a música anterior
> * funciona bem em sessões similares”

---

### Arquitetura Modular

O projeto deve separar claramente:

* playback
* análise
* aprendizado
* ranking
* armazenamento

Permitindo evolução independente dos componentes.

---

# Tecnologias

## Núcleo

* Python
* SQLite
* GStreamer

## Análise Musical

* Librosa
* FFmpeg
* Mutagen

## Interface Futura

* GTK4
* Libadwaita
* PyGObject

---

# Estratégia Técnica

O projeto prioriza:

* heurísticas adaptativas
* aprendizado incremental
* sistemas explicáveis
* baixo acoplamento
* processamento local
* simplicidade arquitetural

O objetivo não é construir um sistema de IA pesado, mas um motor heurístico robusto capaz de gerar comportamento inteligente através de relações simples e cumulativas.

---

# Estrutura Geral do Sistema

## Biblioteca

Responsável por:

* escaneamento
* metadata
* análise acústica

---

## Playback

Responsável por:

* reprodução
* fila
* eventos
* volume
* dispositivos

---

## Aprendizado

Responsável por:

* atualização de pesos
* reforços positivos e negativos
* decay
* adaptação contextual

---

## Ranking

Responsável por:

* cálculo de score
* seleção de próximas músicas
* exploração controlada

---

## Banco de Dados

Responsável por:

* persistência
* afinidades
* transições
* contextos

---

# Filosofia do Projeto

O sistema deve agir mais como um “DJ adaptativo pessoal” do que como um recomendador tradicional.

A intenção é criar sensação de continuidade, coerência e adaptação contextual, em vez de apenas prever músicas “prováveis”.

O comportamento ideal do sistema é:

* discreto
* progressivamente inteligente
* contextual
* interpretável
* não intrusivo

# Análise Musical e Processamento Incremental

## Estratégia de Análise

A análise acústica das músicas deve ocorrer de forma:

* assíncrona
* incremental
* em segundo plano
* lazy

O sistema não deve bloquear:

* escaneamento da biblioteca
* reprodução
* uso da interface

durante o processamento de características acústicas.

Ao detectar novas músicas, apenas:

* metadata básica
* duração
* tags

precisam estar disponíveis imediatamente.

As análises mais pesadas devem ocorrer posteriormente através de uma fila interna de processamento.

---

# Campos de Análise Acústica

Os seguintes atributos serão calculados progressivamente:

```sql
bpm REAL,
energy REAL,
valence REAL,
danceability REAL,
loudness REAL,
acousticness REAL,
spectral_centroid REAL
```

Esses dados serão extraídos principalmente utilizando:

* Librosa
* FFmpeg

---

# Objetivo da Análise Acústica

Os atributos acústicos não devem servir apenas como informação descritiva.

Eles serão usados como base para:

* cálculo de similaridade
* compatibilidade entre transições
* agrupamento de sessões
* descoberta de humores
* exploração de músicas pouco conhecidas
* geração de continuidade sonora

---

# Similaridade Musical

O sistema deve conseguir inferir relações entre faixas mesmo sem histórico suficiente do usuário.

Exemplo:

* músicas com BPM parecido
* energia semelhante
* loudness compatível
* características espectrais próximas

podem receber afinidade inicial maior.

Isso permite:

* cold start melhor
* transições mais naturais
* descoberta mais coerente

---

# Similaridade Semântica e Gêneros

Metadados também podem contribuir para similaridade:

* gênero
* artista
* álbum
* ano

Porém:

* tags não devem ser tratadas como verdade absoluta
* comportamento do usuário deve prevalecer sobre metadata

Exemplo:
duas músicas de gêneros diferentes podem acabar fortemente associadas se o usuário frequentemente as escuta na mesma sessão.

---

# Estratégia Inicial de Similaridade

Inicialmente, a similaridade pode ser heurística simples.

Exemplo:

* diferença de BPM
* distância entre energia
* distância entre centroid espectral

gerando um score composto.

Não é necessário usar machine learning avançado na primeira fase.

---

# Evolução Futura

Posteriormente, o sistema pode incorporar:

* embeddings vetoriais
* clustering
* nearest-neighbor search
* análise estatística de sessões

Possíveis bibliotecas futuras:

* numpy
* scipy
* scikit-learn
* annoy
* faiss

Essas bibliotecas podem ajudar em:

* busca vetorial
* agrupamento
* descoberta automática de padrões
* recomendação contextual

Mas inicialmente o sistema deve permanecer simples, explicável e baseado em heurísticas ajustáveis.



Especificação do Projeto

Fase 0 — Fundação

Objetivo:
Construir o núcleo do player como uma ferramenta CLI.

Stack
Python
SQLite
GStreamer
Librosa
FFmpeg
Mutagen

Estrutura Inicial

Módulos separados:

library/
scan
metadata
análise acústica

playback/
gst pipeline
fila
volume
eventos

learning/
atualização de pesos
regras heurísticas
ranking/
seleção de músicas
cálculo de score

database/
schema
queries
migrations simples

cli/
interface inicial
Funcionalidades
Escanear biblioteca
Extrair metadata
Analisar áudio
Inserir no banco
Reprodução básica
Queue simples
Persistência mínima

Eventos mínimos registrados
play
pause
skip
go back
end_of_track
volume_change
manual_select

Fase 1 — Sistema Heurístico Inicial

Objetivo:
Gerar comportamento adaptativo simples.

Contextos suportados
mood
period
weekday
Regras de aprendizado
Reforço positivo

Quando:

faixa toca até o final
faixa é repetida
usuário aumenta volume (peso menor, algumas faixas tem volumes diferentes de outras)

Aumentar:

afinidade contextual
afinidade de transição
Reforço negativo

Quando:

skip precoce
remoção da fila

Reduzir:

peso contextual
peso transicional
Regras importantes
Skip precoce pesa mais
Skip tardio pesa pouco
Repetição recente reduz score temporariamente
Manual play é sinal forte positivo
Seleção de músicas

Score composto por:

afinidade contextual
transição
fadiga
aleatoriedade controlada

Fase 2 — Sessões e Contexto Real

Objetivo:
Entender comportamento contínuo.

Conceito de sessão

Sessão contém:

horário inicial
duração
sequência
interrupções
mood ativo
Novos contextos
device
output
headphone/speaker
volume range
Novas heurísticas
Progressão energética

Detectar:

aumento gradual de energia
redução gradual
alternância extrema
Compatibilidade de sequência

Aprender:

BPM
energia
valence
loudness
Exploração controlada

Separar:

músicas seguras
músicas exploratórias

Exemplo:

80% previsível
20% experimental

Fase 3 — Humores Emergentes

Objetivo:
Descobrir padrões automaticamente.

Conceito

Humores deixam de ser apenas definidos manualmente.

Sistema detecta:

grupos recorrentes
padrões temporais
sequências similares
Implementação simples inicial

Agrupar sessões por:

horário
energia média
skips
repetição
características acústicas
Resultado

Criar automaticamente:

clusters
pseudo-humores

Usuário pode:

aceitar
renomear
ignorar

Fase 4 — Inteligência de Playlist

Objetivo:
Criar sensação de “DJ contextual”.

Recursos
transições suaves
controle de energia
recuperação após skip
adaptação em tempo real
Heurísticas
Recovery Mode

Após múltiplos skips:

aumentar conservadorismo
tocar músicas seguras
Drift Control

Evitar:

repetir mesma energia
repetir mesmo artista
loops comportamentais
Session Intent Detection

Inferir:

foco
descoberta
background
alta energia

Muito importante.

Exemplo:

“Esta faixa foi escolhida porque combina com:

Evening
sequência anterior
histórico recente”

Isso aumenta percepção de inteligência.

Fase 5 — Refinamento Futuro

Opcional.

Possibilidades
embeddings vetoriais
similaridade acústica avançada
recomendação híbrida
sincronização
multi-device
scrobbling
plugins
API local

Fase 6 — UI GNOME

Objetivo:
Transformar backend em aplicação desktop.

Stack
GTK4
Libadwaita
PyGObject
Recursos
gerenciamento da biblioteca
visualização de humores
estatísticas
explicabilidade
Explicabilidade

Regras Arquiteturais Importantes
1. Nunca registrar tudo cru

Sempre transformar eventos em:

relações
pesos
tendências

Não virar sistema de logging gigante.

2. Aprendizado incremental

Evitar:

reprocessamento pesado
batch learning obrigatório

Preferir:

atualização contínua
3. Separar score de decisão

O ranking deve:

calcular score
explicar score

Isso facilita debug absurdamente.

4. Toda heurística deve ser ajustável

Nunca hardcode:

thresholds
decay
bônus
penalidades

Criar camada de tuning desde cedo.

proposta inicial de estrutura de banco (passível de alteração de acordo com a necessidade)

-- Tabela principal de músicas
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    title TEXT,
    artist TEXT,
    album TEXT,
    duration REAL,
    year TEXT,
    genre TEXT,        
    bpm REAL,
    energy REAL,
    valence REAL,
    danceability REAL,
    loudness REAL,
    acousticness REAL,
    spectral_centroid REAL,
    analyzed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela para definição de contextos
CREATE TABLE IF NOT EXISTS contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    type TEXT NOT NULL,
    value TEXT NOT NULL,

    UNIQUE(type, value)
);

-- Tabela geral de afinidade
CREATE TABLE IF NOT EXISTS track_affinity (
    track_id INTEGER NOT NULL,
    context_id INTEGER NOT NULL,

    weight INTEGER NOT NULL DEFAULT 500,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY(track_id, context_id),

    FOREIGN KEY(track_id) REFERENCES tracks(id),
    FOREIGN KEY(context_id) REFERENCES contexts(id)
);

-- Tabela geral de afinidade para transições
CREATE TABLE IF NOT EXISTS transitions (
    from_track_id INTEGER NOT NULL,
    to_track_id INTEGER NOT NULL,

    context_id INTEGER NOT NULL,

    weight INTEGER DEFAULT 500,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (
        from_track_id,
        to_track_id,
        context_id
    ),

    FOREIGN KEY(from_track_id) REFERENCES tracks(id),
    FOREIGN KEY(to_track_id) REFERENCES tracks(id),
    FOREIGN KEY(context_id) REFERENCES contexts(id)
) WITHOUT ROWID;


-- Tabela de configurações para a faixa
CREATE TABLE IF NOT EXISTS track_play_settings (
    track_id INTEGER PRIMARY KEY,

    preferred_volume INTEGER DEFAULT 50,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(track_id) REFERENCES tracks(id)
);

-- Inserção de Moods iniciais
INSERT OR IGNORE INTO contexts (type, value) VALUES
    ('mood', 'Relaxed'),
    ('mood', 'Energetic'),
    ('mood', 'Focus'),
    ('mood', 'Happy'),

    ('period', 'Morning'),
    ('period', 'Afternoon'),
    ('period', 'Evening'),
    ('period', 'Night'),

    ('weekday', 'Sunday'),
    ('weekday', 'Monday'),
    ('weekday', 'Tuesday'),
    ('weekday', 'Wednesday'),
    ('weekday', 'Thursday'),
    ('weekday', 'Friday'),
    ('weekday', 'Saturday');