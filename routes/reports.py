"""Print-friendly librarian reports."""

from datetime import date

from flask import Blueprint, abort, render_template, request

from database.db import get_db
from routes.security import role_required

reports = Blueprint("reports", __name__, url_prefix="/reports")

REPORTS = {
    "available": ("Available books", "Books with at least one available copy"),
    "issued": ("Issued books", "Books currently borrowed"),
    "overdue": ("Overdue books", "Unreturned books past their due date"),
    "members": ("Member details", "Library member contact and borrowing totals"),
    "fines": ("Fine details", "Assessed fines and payment status"),
    "history": ("Borrowing history", "All completed and active borrowing records"),
}


@reports.get("/")
@role_required("librarian")
def index():
    return render_template("reports.html", reports=REPORTS)


@reports.get("/<report_type>")
@role_required("librarian")
def show_report(report_type: str):
    if report_type not in REPORTS:
        abort(404)

    database = get_db()
    member_filter = request.args.get("member_id", "").strip()
    today = date.today().isoformat()
    if report_type == "available":
        headers = ["ID", "Title", "Author", "ISBN", "Category", "Available", "Total"]
        rows = database.execute(
            """
            SELECT books.id, books.title, books.author, books.isbn,
                   categories.name, books.available_copies, books.total_copies
            FROM books JOIN categories ON categories.id = books.category_id
            WHERE books.available_copies > 0 ORDER BY books.title
            """
        ).fetchall()
    elif report_type == "issued":
        headers = ["Issue ID", "Book", "Member", "Issue date", "Due date"]
        rows = database.execute(
            """
            SELECT issue_records.id, books.title, members.full_name,
                   issue_records.issue_date, issue_records.due_date
            FROM issue_records JOIN books ON books.id = issue_records.book_id
            JOIN members ON members.id = issue_records.member_id
            WHERE issue_records.return_date IS NULL
            ORDER BY issue_records.due_date
            """
        ).fetchall()
    elif report_type == "overdue":
        headers = ["Issue ID", "Book", "Member", "Due date", "Days overdue"]
        rows = database.execute(
            """
            SELECT issue_records.id, books.title, members.full_name,
                   issue_records.due_date,
                   CAST(julianday(?) - julianday(issue_records.due_date) AS INTEGER)
            FROM issue_records JOIN books ON books.id = issue_records.book_id
            JOIN members ON members.id = issue_records.member_id
            WHERE issue_records.return_date IS NULL AND issue_records.due_date < ?
            ORDER BY issue_records.due_date
            """,
            (today, today),
        ).fetchall()
    elif report_type == "members":
        headers = ["Member ID", "Name", "Email", "Phone", "Joined", "Borrowings"]
        rows = database.execute(
            """
            SELECT members.id, members.full_name, members.email, members.phone,
                   members.joined_on, COUNT(issue_records.id)
            FROM members LEFT JOIN issue_records ON issue_records.member_id = members.id
            GROUP BY members.id ORDER BY members.full_name
            """
        ).fetchall()
    elif report_type == "fines":
        headers = ["Fine ID", "Member", "Book", "Amount", "Assessed", "Paid on", "Status"]
        rows = database.execute(
            """
            SELECT fines.id, members.full_name, books.title, fines.amount,
                   fines.assessed_on, COALESCE(fines.paid_on, '—'),
                   CASE WHEN fines.paid_on IS NULL THEN 'Unpaid' ELSE 'Paid' END
            FROM fines JOIN issue_records ON issue_records.id = fines.issue_record_id
            JOIN members ON members.id = issue_records.member_id
            JOIN books ON books.id = issue_records.book_id
            ORDER BY fines.assessed_on DESC
            """
        ).fetchall()
    else:
        headers = ["Issue ID", "Member", "Book", "Issue date", "Due date", "Return date", "Fine"]
        query = """
            SELECT issue_records.id, members.full_name, books.title,
                   issue_records.issue_date, issue_records.due_date,
                   COALESCE(issue_records.return_date, 'Not returned'),
                   COALESCE(fines.amount, 0)
            FROM issue_records JOIN members ON members.id = issue_records.member_id
            JOIN books ON books.id = issue_records.book_id
            LEFT JOIN fines ON fines.issue_record_id = issue_records.id
        """
        parameters: tuple[object, ...] = ()
        if member_filter:
            if not member_filter.isdigit():
                abort(400, description="Member ID must be a number.")
            query += " WHERE members.id = ?"
            parameters = (int(member_filter),)
        query += " ORDER BY issue_records.issue_date DESC, issue_records.id DESC"
        rows = database.execute(query, parameters).fetchall()

    return render_template(
        "report_detail.html",
        title=REPORTS[report_type][0],
        description=REPORTS[report_type][1],
        headers=headers,
        rows=rows,
        members=database.execute("SELECT id, full_name FROM members ORDER BY full_name"),
        selected_member=member_filter,
    )
