"""
Interface de linha de comando.
Comandos básicos do player adaptativo.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ──────────────────────────────────────────────
# Bootstrap
# ──────────────────────────────────────────────

def _bootstrap(db_path: str) -> None:
    from database import connection, schema
    from learning import decay
    from library import acoustic_analyzer

    connection.init(db_path)
    schema.migrate()
    decay.run()
    acoustic_analyzer.start()


# ──────────────────────────────────────────────
# Comandos
# ──────────────────────────────────────────────

def cmd_scan(args: argparse.Namespace) -> None:
    from library import acoustic_analyzer, scanner

    _bootstrap(args.db)

    def on_new(track_id: int, path: Path) -> None:
        acoustic_analyzer.enqueue(track_id, path)

    print(f"[scan] Escaneando: {args.dirs}")
    counts = scanner.scan(args.dirs, on_new_track=on_new)
    print(
        f"[scan] Concluído — adicionadas: {counts['added']}, "
        f"atualizadas: {counts['updated']}, "
        f"desativadas: {counts['deactivated']}"
    )

    if args.wait_analysis:
        import time
        while acoustic_analyzer.queue_size() > 0:
            print(f"[scan] Análise acústica: {acoustic_analyzer.queue_size()} pendentes…")
            time.sleep(2)
        print("[scan] Análise acústica concluída.")


def cmd_list(args: argparse.Namespace) -> None:
    from database import queries

    _bootstrap(args.db)
    tracks = queries.get_all_active_tracks()
    if not tracks:
        print("Biblioteca vazia. Use 'scan' para indexar músicas.")
        return

    print(f"{'ID':>5}  {'Artista':<25} {'Título':<35} {'BPM':>5}  Analisada")
    print("-" * 80)
    for t in tracks:
        bpm = f"{t['bpm']:.2f}" if t["bpm"] is not None else "—"
        analyzed = "✓" if t["analyzed"] else "·"
        artist = (t["artist"] or "?")[:24]
        title  = (t["title"]  or "?")[:34]
        print(f"{t['id']:>5}  {artist:<25} {title:<35} {bpm:>5}  {analyzed}")


def cmd_next(args: argparse.Namespace) -> None:
    from database import queries
    from ranking import selector
    from ranking.session_state import SessionState

    _bootstrap(args.db)
    session = SessionState()
    if args.mood:
        session.set_mood(args.mood)

    result = selector.select_next(session=session, verbose=True)
    if result is None:
        print("Biblioteca vazia.")
        return

    track_id, explanation = result
    row = queries.get_track_by_id(track_id)
    artist = row["artist"] or "?"
    title  = row["title"]  or f"track#{track_id}"
    print(f"\n→ Selecionada: {artist} — {title}")

    if args.verbose:
        import json
        print(json.dumps(explanation.to_dict(), indent=2, ensure_ascii=False))


def cmd_decay(args: argparse.Namespace) -> None:
    from learning import decay

    _bootstrap(args.db)
    counts = decay.run()
    print(
        f"[decay] Afinidades atualizadas: {counts['affinities']}, "
        f"Transições: {counts['transitions']}"
    )


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="adaptive-player",
        description="Player de música heurístico e adaptativo.",
    )
    parser.add_argument("--db", default="data/player.db", help="Caminho do banco SQLite")

    sub = parser.add_subparsers(dest="command", required=True)

    # scan
    p_scan = sub.add_parser("scan", help="Escaneia diretórios e indexa músicas")
    p_scan.add_argument("dirs", nargs="+", help="Diretórios de música")
    p_scan.add_argument("--wait-analysis", action="store_true",
                        help="Aguarda análise acústica concluir")
    p_scan.set_defaults(func=cmd_scan)

    # list
    p_list = sub.add_parser("list", help="Lista faixas indexadas")
    p_list.set_defaults(func=cmd_list)

    # next
    p_next = sub.add_parser("next", help="Seleciona e exibe próxima faixa (dry-run)")
    p_next.add_argument("--mood", default=None,
                        help="Mood ativo: Relaxed, Energetic, Focus, Happy")
    p_next.add_argument("--verbose", "-v", action="store_true",
                        help="Exibe decomposição completa do score")
    p_next.set_defaults(func=cmd_next)

    # decay
    p_decay = sub.add_parser("decay", help="Executa decay temporal manualmente")
    p_decay.set_defaults(func=cmd_decay)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
