import os
import pygame
import random
import sqlite3
from scanner import LibraryScanner
from analyzer import start_background_analysis
from db_manager import DatabaseManager # Assumindo que o arquivo db_manager.py existe conforme o spec

CONFIG_FILE = "musicli-config.txt"
DB_FILE = "heuristic_player.db"

class AudioEngine:
    def __init__(self):
        pygame.mixer.init()
        self.current_track = None
        self.last_track_id = None
        self.paused = False

    def load_track(self, track_tuple):
        """track_tuple: (id, file_path, title, artist, duration)"""
        self.current_track = track_tuple
        if os.path.exists(track_tuple[1]):
            pygame.mixer.music.load(track_tuple[1])
            self.paused = False
        else:
            print(f"Erro: Arquivo não encontrado {track_tuple[1]}")

    def play(self):
        if self.paused:
            pygame.mixer.music.unpause()
            self.paused = False
        else:
            pygame.mixer.music.play()

    def pause(self):
        if not self.paused:
            pygame.mixer.music.pause()
            self.paused = True
        else:
            pygame.mixer.music.unpause()
            self.paused = False

    def stop(self):
        pygame.mixer.music.stop()
        self.paused = False

    def get_position(self):
        pos_ms = pygame.mixer.music.get_pos()
        return max(0, pos_ms / 1000.0)

    def is_playing(self):
        return pygame.mixer.music.get_busy()

    def get_duration(self):
        return self.current_track[4] if self.current_track and len(self.current_track) > 4 else 0

def setup():
    path = input("Enter the path to your music folder: ")
    with open(CONFIG_FILE, "w") as config_file:
        config_file.write(path)
    return path

def main():
    db = DatabaseManager(DB_FILE)
    engine = AudioEngine()
    scanner = LibraryScanner(db)

    if not os.path.exists(CONFIG_FILE):
        path = setup()
    else:
        with open(CONFIG_FILE, "r") as config_file:
            path = config_file.read().strip()
    
    # Sincroniza o banco com o diretório
    print("Scanning library...")
    scanner.scan_directory(path)
    print("Initial scan complete. Deep analysis running in background.")
    
    # Inicia análise profunda (BPM, Energy) em segundo plano (Processo separado)
    analysis_process = start_background_analysis(DB_FILE)

    moods = db.get_moods()
    print("\nSelect a Mood (Enter for default):")
    for mid, name in moods.items():
        print(f"{mid}: {name}")
    m_choice = input("> ")
    current_mood_id = int(m_choice) if m_choice.isdigit() else 1

    while True:
        print("\n" + "="*40)
        print("MusiCLi - Heuristic Player")
        print("="*40)
        print("1. Search Tracks")
        print("2. Play Random")
        print("3. List All")
        print("9. Exit")
        opt = input("Choice: ")

        selected_track = None
        prev_track_id = engine.current_track[0] if engine.current_track else None

        if opt == "1":
            query = input("Search term: ")
            cursor = db.conn.cursor()
            cursor.execute("SELECT id, file_path, title, artist, duration FROM tracks WHERE title LIKE ? OR artist LIKE ?", 
                           (f'%{query}%', f'%{query}%'))
            results = cursor.fetchall()
            
            if results:
                for idx, r in enumerate(results):
                    print(f"{idx}: {r[2]} - {r[3]}")
                c = int(input("Track number: "))
                selected_track = results[c]
            else:
                print("No results.")

        elif opt == "2":
            tracks = db.get_all_tracks() # Retorna (id, path, title, artist)
            if tracks:
                # Adicionamos a duração para o player
                track = random.choice(tracks)
                cursor = db.conn.cursor()
                cursor.execute("SELECT duration FROM tracks WHERE id = ?", (track[0],))
                dur = cursor.fetchone()[0]
                selected_track = (*track, dur)

        elif opt == "3":
            tracks = db.get_all_tracks()
            for idx, r in enumerate(tracks):
                print(f"{idx}: {r[2]} - {r[3]}")
            c = int(input("Track number: "))
            cursor = db.conn.cursor()
            cursor.execute("SELECT duration FROM tracks WHERE id = ?", (tracks[c][0],))
            selected_track = (*tracks[c], cursor.fetchone()[0])

        if selected_track:
            # Registrar transição no banco antes de carregar a nova
            if prev_track_id:
                # Aqui chamamos o DB para registrar a transição entre prev_track_id e selected_track[0]
                db.register_transition(prev_track_id, selected_track[0])
            
            engine.load_track(selected_track)
            engine.play()
            print(f"Playing: {selected_track[2]}")
            
            while True:
                p_opt = input("[P]ause [S]top [N]ext: ").lower()
                if p_opt == 'p':
                    engine.pause()
                elif p_opt == 's':
                    engine.stop()
                    break
                elif p_opt == 'n':
                    # Lógica de interação seria chamada aqui antes do stop
                    engine.stop()
                    break

        if opt == "9":
            # Garante que o processo de análise pare imediatamente ao sair
            if analysis_process and analysis_process.is_alive():
                analysis_process.terminate()
            break

if __name__ == "__main__":
    main()
