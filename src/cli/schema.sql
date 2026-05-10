-- Tabela principal de músicas
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    title TEXT,
    artist TEXT,
    album TEXT,
    genre TEXT,
    year TEXT,
    duration REAL,
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