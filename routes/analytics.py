"""Analytics and machine-learning pages."""

from flask import Blueprint, render_template

from database.db import get_db
from routes.security import role_required

analytics = Blueprint("analytics", __name__)


@analytics.get("/analytics")
@role_required("librarian")
def dashboard():
    database = get_db()
    most_borrowed = database.execute(
        """
        SELECT books.title, COUNT(issue_records.id) AS total
        FROM issue_records JOIN books ON books.id = issue_records.book_id
        GROUP BY books.id ORDER BY total DESC, books.title LIMIT 8
        """
    ).fetchall()
    category_borrowing = database.execute(
        """
        SELECT categories.name, COUNT(issue_records.id) AS total
        FROM categories
        LEFT JOIN books ON books.category_id = categories.id
        LEFT JOIN issue_records ON issue_records.book_id = books.id
        GROUP BY categories.id ORDER BY total DESC, categories.name
        """
    ).fetchall()
    monthly = database.execute(
        """
        WITH RECURSIVE months(month_start, step) AS (
            SELECT date('now', 'start of month', '-11 months'), 0
            UNION ALL
            SELECT date(month_start, '+1 month'), step + 1 FROM months WHERE step < 11
        )
        SELECT strftime('%Y-%m', months.month_start) AS month,
               COUNT(issue_records.id) AS total
        FROM months LEFT JOIN issue_records
          ON strftime('%Y-%m', issue_records.issue_date) = strftime('%Y-%m', months.month_start)
        GROUP BY months.month_start ORDER BY months.month_start
        """
    ).fetchall()
    overdue_count = database.execute(
        "SELECT COUNT(*) FROM issue_records "
        "WHERE return_date IS NULL AND due_date < date('now')"
    ).fetchone()[0]
    collected = database.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM fines WHERE paid_on IS NOT NULL"
    ).fetchone()[0]
    active_members = database.execute(
        """
        SELECT members.full_name, COUNT(issue_records.id) AS total
        FROM members JOIN issue_records ON issue_records.member_id = members.id
        GROUP BY members.id ORDER BY total DESC, members.full_name LIMIT 8
        """
    ).fetchall()

    charts = {
        "mostBorrowed": {
            "labels": [row["title"] for row in most_borrowed],
            "values": [row["total"] for row in most_borrowed],
        },
        "categories": {
            "labels": [row["name"] for row in category_borrowing],
            "values": [row["total"] for row in category_borrowing],
        },
        "monthly": {
            "labels": [row["month"] for row in monthly],
            "values": [row["total"] for row in monthly],
        },
        "activeMembers": {
            "labels": [row["full_name"] for row in active_members],
            "values": [row["total"] for row in active_members],
        },
    }
    return render_template(
        "analytics.html",
        charts=charts,
        overdue_count=overdue_count,
        fines_collected=collected,
    )


@analytics.get("/predictions")
@role_required("librarian")
def predictions():
    from ml.predictions import predict_library_trends

    results = predict_library_trends()
    return render_template("predictions.html", results=results)
