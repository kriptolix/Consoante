import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_name="music_library.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self._setup_db()

    def _setup_db(self):
        """Carrega o esquema SQL a partir de um arquivo externo."""
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                sql_script = f.read()
            self.conn.executescript(sql_script)
        self.conn.commit()

    def add_track(self, metadata):
        """Insere metadados básicos de uma faixa (Mutagen stage)."""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT OR IGNORE INTO tracks (
                file_path,
                title,
                artist,
                album,
                genre,
                year,
                duration
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata['file_path'],
            metadata['title'],
            metadata['artist'],
            metadata['album'],
            metadata.get('genre', 'Unknown'),
            metadata.get('year', 'Unknown'),
            metadata['duration']
        ))

        self.conn.commit()

    def track_exists(self, file_path):
        """Verifica se a música já está no banco para evitar re-scan."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM tracks WHERE file_path = ?", (file_path,))
        return cursor.fetchone() is not None

    def get_pending_analysis(self):
        """Busca músicas que ainda não passaram pelo scanner de áudio pesado."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, file_path FROM tracks WHERE analyzed = 0")
        return cursor.fetchall()

    def update_audio_features(self, track_id, features):
        """Atualiza os dados heurísticos após análise profunda."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE tracks
            SET bpm = ?, energy = ?, valence = ?, danceability = ?, loudness = ?, spectral_centroid = ?, analyzed = 1
            WHERE id = ?
        ''', (
            features.get('bpm'),
            features.get('energy'),
            features.get('valence'),
            features.get('danceability'),
            features.get('loudness'),
            features.get('spectral_centroid'),
            track_id
        ))
        self.conn.commit()

    def register_transition(self, from_id, to_id, context_ids):
        cursor = self.conn.cursor()

        for context_id in context_ids:
            cursor.execute('''
                INSERT INTO transitions (
                    from_track_id,
                    to_track_id,
                    context_id,
                    weight
                )
                VALUES (?, ?, ?, 500)
                ON CONFLICT(from_track_id, to_track_id, context_id) DO UPDATE SET
                    weight = MIN(1000, weight + 10),
                    last_transition_at = CURRENT_TIMESTAMP
            ''', (from_id, to_id, context_id))

        self.conn.commit()

    def get_all_tracks(self):
        """Recupera as faixas básicas (id, file_path, title, artist)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, file_path, title, artist FROM tracks")
        return cursor.fetchall()

    def get_moods(self):
        """Retorna um dicionário de moods {id: value}."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, value
            FROM contexts
            WHERE type = 'mood'
        """)
        return {row[0]: row[1] for row in cursor.fetchall()}