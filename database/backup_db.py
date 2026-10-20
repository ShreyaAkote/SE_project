"""Create a timestamped SQLite backup from the command line."""

from datetime import datetime
from pathlib import Path
import sqlite3
from contextlib import closing

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "instance" / "library.db"
BACKUP_DIRECTORY = PROJECT_ROOT / "instance" / "backups"


def create_backup() -> Path:
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(
            f"Database not found at {DATABASE_PATH}. Set up the database first."
        )
    BACKUP_DIRECTORY.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIRECTORY / (
        "library-backup-"
        + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        + ".sqlite3"
    )
    with closing(sqlite3.connect(DATABASE_PATH)) as source:
        with closing(sqlite3.connect(backup_path)) as destination:
            source.backup(destination)
    return backup_path


if __name__ == "__main__":
    print(f"Backup created: {create_backup()}")
