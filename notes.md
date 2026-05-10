Modelo de dados
Tabela tracks
track_id
artist_id
genre
bpm
energy
danceability
valence
acousticness

Tabela interactions
track_id
started_at
played_seconds
skipped
replayed
mood

Tabela transitions
from_track
to_track
skip_rate
success_rate

Aqui nasce a magia.

Sistema de score

Você NÃO precisa de ML pesado inicialmente.

Um scoring heurístico já funciona absurdamente bem:

score =
+ full_plays * 5
+ replay * 8
- early_skip * 10
+ mood_affinity * 6
+ recentness

| Comportamento                | Sinal provável          |
| ---------------------------- | ----------------------- |
| ouviu até o fim várias vezes | gosta                   |
| pulou em <15s                | rejeição forte          |
| pulou depois de 80%          | talvez goste mas cansou |
| replay imediato              | afinidade alta          |
| ouve sempre à noite          | contexto emocional      |
| escuta após certas músicas   | associação/transição    |


Depois você evolui para:

collaborative filtering local
embeddings
reinforcement learning


| Dimensão      | Significado              |
| ------------- | ------------------------ |
| energia       | intensidade              |
| valência      | feliz ↔ triste           |
| densidade     | cheio ↔ minimalista      |
| agressividade | suave ↔ agressivo        |
| organicidade  | acústico ↔ eletrônico    |
| foco          | distração ↔ concentração |


O que registrar

Evento de play
track_id
timestamp
source
queue_position
mood

Evento de stop/skip
played_seconds
track_duration
skip_position_percent
Evento de replay

Detectar:

replay imediato
replay frequente
Evento de contexto

Opcional inicialmente:

hora do dia
dia da semana
dispositivo
volume
O que isso permite

Você começa a inferir:

Comportamento	Interpretação
3 skips rápidos	rejeição
replay	afinidade
escuta noturna	contexto
nunca termina	fadiga
Implementação técnica
Banco

SQLite basta.

Tabela:

interactions

com:

id
track_id
started_at
ended_at
played_ratio
skipped
mood_id
Regras iniciais
Exemplo
played_ratio < 0.15
→ strong dislike

played_ratio > 0.85
→ positive affinity

replayed within 10 min
→ strong affinity

3. Smart Shuffle
Objetivo

Substituir shuffle aleatório por seleção contextual.

Cada música recebe atributos

Inicialmente:

tags ID3
gênero
artista
play count
skip rate

Depois:

BPM
energia
embeddings

MOOD SESSIONS
4. Mood Sessions

Essa é provavelmente sua feature principal.

Objetivo

Transformar a sessão atual num contexto emocional.

Fluxo

Usuário abre:

Mood: "foco"

Tudo que ocorre nessa sessão:

aumenta/decrementa afinidade naquele mood
Estrutura
Tabela moods
moods
Tabela mood_affinity
track_id
mood_id
score

TRANSITIONS

O que são transitions

Você aprende:
não apenas “o que o usuário gosta”,
mas:
“o que combina depois do quê”.

Exemplo

Usuário frequentemente:

sai de ambient
entra em techno leve

O sistema aprende:

ambient → techno suave = boa transição
Estrutura
transitions
from_track
to_track
success_score
Como medir sucesso

Boa transição:

próxima música não levou skip

Ruim:

skip imediato

EMBEDDINGS
O que são embeddings

Representações numéricas compactas.

Cada música vira:

[0.22, 0.91, 0.13, ...]
O vetor representa

Mistura de:

mood
energia
comportamento
contexto
Benefício

Você consegue:

calcular similaridade
interpolar moods
descobrir relações ocultas
Como começar simples

Use:

tags
BPM
gênero
artista

Depois:

Essentia

CLUSTERING
Objetivo

Descobrir grupos automaticamente.

Exemplo

Sistema percebe:

Cluster A:
- ambient
- piano
- chuva
- madrugada

Mesmo sem nome.

Você pode sugerir
"Você parece ter um novo mood emergente"

Isso seria MUITO legal.

Técnicas

Depois:

KMeans
HDBSCAN
UMAP/t-SNE visual

MOODS AUTOMÁTICOS
Objetivo

Eliminar necessidade de criar moods manualmente.

Como funciona

Sistema detecta:

sessão atual ≈ cluster noturno introspectivo

dia
mes
dia da semana
hora do dia


e adapta automaticamente.


Você pode inferir energia sem IA

Exemplo simples:

energia =
+ loudness
+ spectral centroid
+ BPM
+ dynamic range

Já funciona surpreendentemente bem.

Pipeline recomendado
Importação
scan biblioteca
→ ler metadata
→ gerar waveform leve
→ salvar DB
Análise assíncrona
worker:
- BPM
- loudness
- key
- energy


FASE 1:
mutagen + librosa + ffmpeg
1. mutagen

Mutagen

Para:

tags
metadata
ReplayGain
capa
duração

É obrigatório praticamente.

2. librosa

librosa

Para:

BPM
onset
spectral features
chroma
energia

Ler metadata

mutagen:

artista
álbum
gênero
duração
bitrate
replaygain
Salvar imediatamente

Sem análise pesada.

ETAPA 2 — Queue de análise

Tabela:

analysis_queue

com:

track_id
status
priority
last_attempt
ETAPA 3 — Worker assíncrono

Thread/process separado:

pega música pendente
→ analisa
→ salva features
ETAPA 4 — Feature store

Tabela:

audio_features
Estrutura recomendada
track_id
bpm
energy
loudness
danceability
valence
spectral_centroid
acousticness
instrumentalness

Como calcular “energy”

Você pode criar sua própria definição.

Exemplo:

energy =
0.4 * normalized_rms +
0.3 * normalized_bpm +
0.3 * spectral_centroid

Isso já funciona MUITO bem.


O primeiro fluxo que eu implementaria
1. Scan de pasta
encontrar arquivos
salvar no DB
2. Metadata extraction

mutagen.

3. Playback funcional

GStreamer.

4. Interaction logging

plays/skips.

5. Analysis queue

background.


Uma recomendação MUITO importante
NÃO deixe librosa tocar diretamente nos arquivos da biblioteca

Faça pipeline explícito.

Exemplo:

audio_loader.py
feature_extractor.py
waveform_generator.py

Porque depois:

você pode trocar librosa
adicionar Essentia
adicionar cache binário

sem quebrar tudo.

Outra recomendação importante
Use multiprocessing para análise

NÃO threads.

Porque:

análise de áudio é CPU-bound
Python tem GIL

Então:

ProcessPoolExecutor

é ideal.