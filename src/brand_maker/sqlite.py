"""Shared SQLite initialization and connection policy."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def initialize_database(path: Path, schema: str) -> None:
    """Install one schema and enable settings suited to concurrent local tabs."""

    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5.0)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.executescript(schema)
        connection.commit()
    finally:
        connection.close()


def connect_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=5.0)
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


@contextmanager
def database_connection(path: Path) -> Iterator[sqlite3.Connection]:
    """Yield a configured transaction and always close its connection."""

    connection = connect_database(path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
