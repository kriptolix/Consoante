import os
from mutagen import File


class LibraryScanner:
    def __init__(self, db_manager):
        self.db = db_manager

    def scan_directory(self, path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith((".mp3", ".flac", ".ogg")):
                    file_path = os.path.join(root, file)

                    # Lazy Scan: Pula se já existir no DB
                    if self.db.track_exists(file_path):
                        continue

                    try:
                        # Usa o File de forma genérica para suportar MP3, FLAC e OGG
                        audio = File(file_path, easy=True)
                        if audio is None or audio.info is None:
                            continue

                        metadata = {
                            'file_path': file_path,
                            'title': audio.get('title', [file])[0],
                            'artist': audio.get('artist', ['Unknown'])[0],
                            'album': audio.get('album', ['Unknown'])[0],
                            'genre': audio.get('genre', ['Unknown'])[0],
                            'year': audio.get('date', ['Unknown'])[0],
                            'duration': getattr(audio.info, 'length', 0)
                        }
                        self.db.add_track(metadata)
                    except Exception as e:
                        print(f"Erro ao processar {file}: {e}")
