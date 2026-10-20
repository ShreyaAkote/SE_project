"""Rules for issuing, returning, and fine calculation."""

from datetime import date
import sqlite3

from database.db import get_db

FINE_PER_DAY = 2.0


class LibraryOperationError(ValueError):
    """A library transaction could not be completed safely."""


def issue_book(book_id: int, member_id: int, issue_date: date, due_date: date) -> int:
    """Issue one available copy and return the new issue record ID."""
    if due_date < issue_date:
        raise LibraryOperationError("The due date cannot be before the issue date.")
    if issue_date > date.today():
        raise LibraryOperationError("The issue date cannot be in the future.")

    database = get_db()
    try:
        database.execute("BEGIN IMMEDIATE")
        member = database.execute(
            "SELECT id FROM members WHERE id = ?", (member_id,)
        ).fetchone()
        if member is None:
            raise LibraryOperationError("Select a valid member.")

        updated = database.execute(
            """
            UPDATE books
            SET available_copies = available_copies - 1
            WHERE id = ? AND available_copies > 0
            """,
            (book_id,),
        )
        if updated.rowcount == 0:
            book = database.execute(
                "SELECT id FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            if book is None:
                raise LibraryOperationError("Select a valid book.")
            raise LibraryOperationError("No copies of this book are available.")

        cursor = database.execute(
            """
            INSERT INTO issue_records (book_id, member_id, issue_date, due_date)
            VALUES (?, ?, ?, ?)
            """,
            (book_id, member_id, issue_date.isoformat(), due_date.isoformat()),
        )
        database.commit()
        return int(cursor.lastrowid)
    except (LibraryOperationError, sqlite3.Error):
        database.rollback()
        raise


def return_book(issue_id: int, return_date: date) -> float:
    """Record a book return, restore availability, and add any late fine."""
    database = get_db()
    try:
        database.execute("BEGIN IMMEDIATE")
        issue = database.execute(
            """
            SELECT id, book_id, issue_date, due_date, return_date
            FROM issue_records WHERE id = ?
            """,
            (issue_id,),
        ).fetchone()
        if issue is None:
            raise LibraryOperationError("That issue record does not exist.")
        if issue["return_date"] is not None:
            raise LibraryOperationError("This book has already been returned.")
        issue_date = date.fromisoformat(issue["issue_date"])
        if return_date < issue_date:
            raise LibraryOperationError("The return date cannot be before the issue date.")
        if return_date > date.today():
            raise LibraryOperationError("The return date cannot be in the future.")

        due_date = date.fromisoformat(issue["due_date"])
        late_days = max(0, (return_date - due_date).days)
        database.execute(
            "UPDATE issue_records SET return_date = ? WHERE id = ?",
            (return_date.isoformat(), issue_id),
        )
        updated = database.execute(
            """
            UPDATE books
            SET available_copies = available_copies + 1
            WHERE id = ? AND available_copies < total_copies
            """,
            (issue["book_id"],),
        )
        if updated.rowcount == 0:
            raise LibraryOperationError(
                "The book availability is inconsistent; the return was not saved."
            )

        fine = late_days * FINE_PER_DAY
        if fine > 0:
            database.execute(
                """
                INSERT INTO fines (issue_record_id, amount, assessed_on)
                VALUES (?, ?, ?)
                """,
                (issue_id, fine, return_date.isoformat()),
            )
        database.commit()
        return fine
    except (LibraryOperationError, sqlite3.Error):
        database.rollback()
        raise
