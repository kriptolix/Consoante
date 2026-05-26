"""
Gerencia a conexão SQLite com WAL mode habilitado.
Expõe context manager para transações.
"""

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

_local = threading.local()
_db_path: Path | None = None


def init(path: str | Path) -> None:
    """Configura o caminho do banco. Deve ser chamado antes de qualquer uso."""
    global _db_path
    _db_path = Path(path)
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    # Garante que o banco existe e o WAL está ativo
    with get() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")


def _connect() -> sqlite3.Connection:
    if _db_path is None:
        raise RuntimeError("database.connection.init() não foi chamado.")
    conn = sqlite3.connect(str(_db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager que entrega uma conexão SQLite.
    Faz commit ao sair normalmente e rollback em exceção.
    """
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = _connect()

    conn: sqlite3.Connection = _local.conn
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def close() -> None:
    """Fecha a conexão da thread atual, se existir."""
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None
