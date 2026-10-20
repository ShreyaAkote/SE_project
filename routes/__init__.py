"""Blueprints for the library application."""

from flask import Blueprint, render_template

from database.db import get_db
from routes.admin import admin
from routes.analytics import analytics
from routes.auth import auth
from routes.catalog import catalog
from routes.circulation import circulation
from routes.reports import reports

main = Blueprint("main", __name__)


@main.get("/dashboard")
def dashboard():
    """Show summary counts for librarians."""
    database = get_db()
    stats = {
        "books": database.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        "members": database.execute("SELECT COUNT(*) FROM members").fetchone()[0],
        "issues": database.execute(
            "SELECT COUNT(*) FROM issue_records"
        ).fetchone()[0],
        "open_issues": database.execute(
            "SELECT COUNT(*) FROM issue_records WHERE return_date IS NULL"
        ).fetchone()[0],
        "overdue": database.execute(
            "SELECT COUNT(*) FROM issue_records "
            "WHERE return_date IS NULL AND due_date < date('now')"
        ).fetchone()[0],
    }
    return render_template("dashboard.html", stats=stats)


@main.app_template_global()
def csrf_token() -> str:
    """Return a per-session token used to protect form submissions."""
    from secrets import token_urlsafe
    from flask import session

    if "_csrf_token" not in session:
        session["_csrf_token"] = token_urlsafe(32)
    return session["_csrf_token"]
