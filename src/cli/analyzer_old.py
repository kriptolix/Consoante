import essentia.standard as es
import numpy as np
import os
import time
from multiprocessing import Process
from db_manager import DatabaseManager

def extract_features(file_path):
    """Extração de features usando Essentia (substituindo Librosa)."""
    try:
        # O MusicExtractor calcula centenas de features de uma vez
        features, frames = es.MusicExtractor(
            lowlevelStats=['mean'],
            rhythmStats=['mean'],
            tonalStats=['mean']
        )(file_path)
        
        return {
            'bpm': float(features['rhythm.bpm']),
            'energy': float(features['lowlevel.average_loudness']), # Simplificado para exemplo
            'valence': float(features['tonal.valence']) if 'tonal.valence' in features else 0.5,
            'danceability': float(features['rhythm.danceability']),
            'loudness': float(features['lowlevel.loudness_ebu128.integrated']),
            'spectral_centroid': float(features['lowlevel.spectral_centroid.mean'])
        }
    except Exception as e:
        print(f"Erro Essentia em {file_path}: {e}")
        return None

def analysis_worker_process(db_path):
    """Worker que roda em um processo separado para não afetar a reprodução."""
    # Baixa a prioridade do processo para não competir com o áudio (Linux/macOS)
    if hasattr(os, 'nice'):
        os.nice(15)

    db = DatabaseManager(db_path)
    pending = db.get_pending_analysis()
    
    if not pending:
        return

    for track_id, file_path in pending:
        try:
            features = extract_features(file_path)
            if features:
                db.update_audio_features(track_id, features)

            time.sleep(0.5)
        except Exception:
            continue

def start_background_analysis(db_path):
    p = Process(target=analysis_worker_process, args=(db_path,))
    # Define como daemon para que o processo morra quando o player fechar
    p.daemon = True
    p.start()
    return p