"""Create the library database tables."""

from pathlib import Path
import sqlite3
from contextlib import closing

from database.db import init_db


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "instance" / "library.db"


class DatabaseApp:
    """Small config object used by the shared database initializer."""

    config = {"DATABASE": str(DATABASE_PATH)}


def main() -> None:
    init_db(DatabaseApp())
    # Confirm that the setup script created a usable database.
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        connection.execute("SELECT 1 FROM categories LIMIT 1")
    print(f"Database tables are ready: {DATABASE_PATH}")


if __name__ == "__main__":
    main()
