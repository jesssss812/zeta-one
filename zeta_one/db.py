"""The gateway's SQLite file. Each module creates and owns its own tables in it."""

import sqlite3
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "zeta.db"


def connect(path: Path | str = DEFAULT_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
