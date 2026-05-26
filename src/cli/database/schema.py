"""
Define e cria todas as tabelas via SQL.
Gerencia migrations com tabela de versão interna.
"""

from database import connection

SCHEMA_VERSION = 1

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

-- Faixas da biblioteca
CREATE TABLE IF NOT EXISTS tracks (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path             TEXT UNIQUE NOT NULL,
    file_hash             TEXT,
    title                 TEXT,
    artist                TEXT,
    album                 TEXT,
    duration              REAL,
    year                  TEXT,
    genre                 TEXT,
    bpm                   REAL,
    energy                REAL,
    loudness              REAL,
    acousticness          REAL,
    brightness            REAL,
    rhythmic_regularity   REAL,
    spectral_centroid     REAL,
    analyzed              INTEGER DEFAULT 0,
    active                INTEGER DEFAULT 1,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
"""

_SEED_CONTEXTS_SQL = """
INSERT OR IGNORE INTO contexts (type, value) VALUES
    ('mood', 'Relaxed'),   ('mood', 'Energetic'),
    ('mood', 'Focus'),     ('mood', 'Happy'),
    ('period', 'Morning'), ('period', 'Afternoon'),
    ('period', 'Evening'), ('period', 'Night'),
    ('weekday', 'Sunday'),    ('weekday', 'Monday'),
    ('weekday', 'Tuesday'),   ('weekday', 'Wednesday'),
    ('weekday', 'Thursday'),  ('weekday', 'Friday'),
    ('weekday', 'Saturday');
"""


def migrate() -> None:
    """Aplica o schema e seeds caso ainda não existam."""
    with connection.get() as conn:
        # Executa criação de tabelas
        conn.executescript(_CREATE_SQL)

        # Verifica versão atual
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        current = row["version"] if row else 0

        if current < SCHEMA_VERSION:
            conn.executescript(_SEED_CONTEXTS_SQL)
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
