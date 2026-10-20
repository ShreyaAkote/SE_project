"""SQLite connection and initialization helpers."""

import sqlite3
from contextlib import closing
from pathlib import Path

from flask import current_app, g


def get_db() -> sqlite3.Connection:
    """Return one SQLite connection for the current Flask request."""
    if "database" not in g:
        database_path = current_app.config["DATABASE"]
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        g.database = sqlite3.connect(database_path)
        g.database.row_factory = sqlite3.Row
        g.database.execute("PRAGMA foreign_keys = ON")
    return g.database


def init_db(app) -> None:
    """Create the tables if they have not been created yet."""
    schema_path = Path(__file__).with_name("schema.sql")
    schema = schema_path.read_text(encoding="utf-8")
    database_path = Path(app.config["DATABASE"])
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema)
