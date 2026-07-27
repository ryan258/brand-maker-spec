from pathlib import Path

from brand_maker.sqlite import connect_database, initialize_database

SCHEMA = "CREATE TABLE IF NOT EXISTS probe (id INTEGER PRIMARY KEY)"

NORMAL = 1
FULL = 2


def synchronous(path: Path) -> int:
    connection = connect_database(path)
    try:
        return int(connection.execute("PRAGMA synchronous").fetchone()[0])
    finally:
        connection.close()


def test_wal_database_relaxes_synchronous_to_normal(tmp_path: Path) -> None:
    path = tmp_path / "probe.db"
    initialize_database(path, SCHEMA)

    assert synchronous(path) == NORMAL


def test_database_that_lost_wal_keeps_full_synchronous(tmp_path: Path) -> None:
    path = tmp_path / "probe.db"
    initialize_database(path, SCHEMA)
    reverted = connect_database(path)
    reverted.execute("PRAGMA journal_mode=DELETE")
    reverted.close()

    assert synchronous(path) == FULL
