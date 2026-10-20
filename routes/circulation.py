"""Librarian circulation pages and student loan list."""

from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from database.db import get_db
from database.services import LibraryOperationError, issue_book, return_book
from routes.security import role_required

circulation = Blueprint("circulation", __name__)


@circulation.get("/issues")
@role_required("librarian")
def issues():
    rows = get_db().execute(
        """
        SELECT issue_records.*, books.title, books.isbn,
               members.full_name AS member_name,
               CASE WHEN issue_records.return_date IS NULL
                         AND issue_records.due_date < date('now')
                    THEN 1 ELSE 0 END AS is_overdue,
               fines.amount AS fine_amount, fines.paid_on
        FROM issue_records
        JOIN books ON books.id = issue_records.book_id
        JOIN members ON members.id = issue_records.member_id
        LEFT JOIN fines ON fines.issue_record_id = issue_records.id
        ORDER BY issue_records.return_date IS NULL DESC,
                 issue_records.due_date ASC, issue_records.id DESC
        """
    ).fetchall()
    return render_template("issues.html", issues=rows, today=date.today().isoformat())


@circulation.get("/fines")
@role_required("librarian")
def fines():
    rows = get_db().execute(
        """
        SELECT fines.id, fines.amount, fines.assessed_on, fines.paid_on,
               issue_records.id AS issue_id, members.full_name, books.title
        FROM fines JOIN issue_records ON issue_records.id = fines.issue_record_id
        JOIN members ON members.id = issue_records.member_id
        JOIN books ON books.id = issue_records.book_id
        ORDER BY fines.paid_on IS NOT NULL, fines.assessed_on DESC
        """
    ).fetchall()
    return render_template("fines.html", fines=rows)


@circulation.post("/fines/<int:fine_id>/pay")
@role_required("librarian")
def mark_fine_paid(fine_id: int):
    database = get_db()
    cursor = database.execute(
        "UPDATE fines SET paid_on = ? WHERE id = ? AND paid_on IS NULL",
        (date.today().isoformat(), fine_id),
    )
    database.commit()
    if cursor.rowcount:
        flash("Fine marked as paid.", "success")
    else:
        flash("That fine does not exist or has already been paid.", "warning")
    return redirect(url_for("circulation.fines"))


@circulation.route("/issues/new", methods=["GET", "POST"])
@role_required("librarian")
def new_issue():
    database = get_db()
    books = database.execute(
        "SELECT id, title, available_copies FROM books "
        "WHERE available_copies > 0 ORDER BY title"
    )
    members = database.execute("SELECT id, full_name FROM members ORDER BY full_name")
    if request.method == "POST":
        try:
            book_id = int(request.form.get("book_id", ""))
            member_id = int(request.form.get("member_id", ""))
            issue_date = date.fromisoformat(request.form.get("issue_date", ""))
            due_date = date.fromisoformat(request.form.get("due_date", ""))
            issue_book(book_id, member_id, issue_date, due_date)
            flash("Book issued successfully.", "success")
            return redirect(url_for("circulation.issues"))
        except LibraryOperationError as error:
            flash(str(error) or "Enter valid issue and due dates.", "danger")
        except (ValueError, TypeError):
            flash("Choose a book and member, then enter valid issue and due dates.", "danger")
    return render_template(
        "issue_form.html",
        books=books,
        members=members,
        today=date.today().isoformat(),
        default_due=(date.today() + timedelta(days=14)).isoformat(),
    )


@circulation.post("/issues/<int:issue_id>/return")
@role_required("librarian")
def return_issue(issue_id: int):
    try:
        return_date = date.fromisoformat(
            request.form.get("return_date", date.today().isoformat())
        )
        fine = return_book(issue_id, return_date)
        if fine:
            flash(f"Return recorded. Late fine: ₹{fine:.2f}.", "warning")
        else:
            flash("Return recorded. No fine is due.", "success")
    except LibraryOperationError as error:
        flash(str(error), "danger")
    except ValueError:
        flash("Enter a valid return date.", "danger")
    return redirect(url_for("circulation.issues"))
