"""Book and member search and management pages."""

from datetime import date
import sqlite3
import re

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from database.db import get_db
from routes.security import role_required

catalog = Blueprint("catalog", __name__)


def _book_search():
    search = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", "").strip()
    query = """
        SELECT books.*, categories.name AS category_name
        FROM books JOIN categories ON categories.id = books.category_id
        WHERE 1 = 1
    """
    parameters: list[object] = []
    if search:
        pattern = f"%{search}%"
        query += """
            AND (books.title LIKE ? OR books.author LIKE ? OR books.isbn LIKE ?
                 OR categories.name LIKE ? OR CAST(books.id AS TEXT) = ?)
        """
        parameters.extend([pattern, pattern, pattern, pattern, search])
    if category_id:
        if not category_id.isdigit():
            flash("Choose a valid category filter.", "warning")
        else:
            query += " AND books.category_id = ?"
            parameters.append(int(category_id))
    query += " ORDER BY books.title"
    return get_db().execute(query, parameters).fetchall()


@catalog.get("/books")
@role_required("librarian")
def books():
    categories = get_db().execute("SELECT id, name FROM categories ORDER BY name")
    return render_template(
        "books.html",
        books=_book_search(),
        categories=categories,
        query=request.args.get("q", "").strip(),
        selected_category=request.args.get("category_id", ""),
        today=date.today().isoformat(),
    )


@catalog.get("/catalog")
@role_required("student")
def student_catalog():
    categories = get_db().execute("SELECT id, name FROM categories ORDER BY name")
    return render_template(
        "books.html",
        books=_book_search(),
        categories=categories,
        query=request.args.get("q", "").strip(),
        selected_category=request.args.get("category_id", ""),
        student_view=True,
        today=date.today().isoformat(),
    )


def _save_book(book_id: int | None = None):
    database = get_db()
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    isbn = request.form.get("isbn", "").strip()
    category_id = request.form.get("category_id", "").strip()
    copies_text = request.form.get("total_copies", "").strip()
    error = None
    try:
        total_copies = int(copies_text)
        if total_copies < 0:
            raise ValueError
    except ValueError:
        total_copies = -1
        error = "Total copies must be a whole number zero or greater."

    category = database.execute(
        "SELECT id FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    if not title or not author or not isbn:
        error = "Title, author, and ISBN are required."
    elif category is None:
        error = "Choose a valid category."
    if error:
        flash(error, "danger")
        return False

    try:
        if book_id is None:
            database.execute(
                """
                INSERT INTO books
                    (title, author, isbn, category_id, total_copies, available_copies)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (title, author, isbn, category_id, total_copies, total_copies),
            )
        else:
            current = database.execute(
                "SELECT total_copies, available_copies FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
            if current is None:
                abort(404)
            borrowed = current["total_copies"] - current["available_copies"]
            if total_copies < borrowed:
                flash(
                    f"Total copies cannot be less than the {borrowed} currently issued.",
                    "danger",
                )
                return False
            database.execute(
                """
                UPDATE books SET title = ?, author = ?, isbn = ?, category_id = ?,
                    total_copies = ?, available_copies = ?
                WHERE id = ?
                """,
                (
                    title,
                    author,
                    isbn,
                    category_id,
                    total_copies,
                    total_copies - borrowed,
                    book_id,
                ),
            )
        database.commit()
        return True
    except sqlite3.IntegrityError:
        database.rollback()
        flash("That ISBN is already in use. Enter a unique ISBN.", "danger")
        return False


@catalog.route("/books/new", methods=["GET", "POST"])
@role_required("librarian")
def create_book():
    categories = get_db().execute("SELECT id, name FROM categories ORDER BY name")
    if request.method == "POST" and _save_book():
        flash("Book added.", "success")
        return redirect(url_for("catalog.books"))
    return render_template("book_form.html", book=None, categories=categories)


@catalog.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
@role_required("librarian")
def edit_book(book_id: int):
    database = get_db()
    book = database.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        abort(404)
    categories = database.execute("SELECT id, name FROM categories ORDER BY name")
    if request.method == "POST" and _save_book(book_id):
        flash("Book updated.", "success")
        return redirect(url_for("catalog.books"))
    return render_template("book_form.html", book=book, categories=categories)


@catalog.post("/books/<int:book_id>/delete")
@role_required("librarian")
def delete_book(book_id: int):
    database = get_db()
    try:
        cursor = database.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cursor.rowcount == 0:
            abort(404)
        database.commit()
        flash("Book deleted.", "success")
    except sqlite3.IntegrityError:
        database.rollback()
        flash("This book has borrowing history and cannot be deleted.", "danger")
    return redirect(url_for("catalog.books"))


@catalog.get("/members")
@role_required("librarian")
def members():
    search = request.args.get("q", "").strip()
    pattern = f"%{search}%"
    member_rows = get_db().execute(
        """
        SELECT members.*,
            (SELECT COUNT(*) FROM issue_records WHERE member_id = members.id)
                AS borrowing_count
        FROM members
        WHERE ? = '' OR full_name LIKE ? OR email LIKE ?
            OR phone LIKE ? OR CAST(id AS TEXT) = ?
        ORDER BY full_name
        """,
        (search, pattern, pattern, pattern, search),
    ).fetchall()
    return render_template("members.html", members=member_rows, query=search)


def _save_member(member_id: int | None = None) -> bool:
    database = get_db()
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    if not full_name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        flash("Enter a full name and a valid email address.", "danger")
        return False
    try:
        if member_id is None:
            database.execute(
                "INSERT INTO members (full_name, email, phone, joined_on) "
                "VALUES (?, ?, ?, ?)",
                (full_name, email, phone, date.today().isoformat()),
            )
        else:
            database.execute(
                "UPDATE members SET full_name = ?, email = ?, phone = ? WHERE id = ?",
                (full_name, email, phone, member_id),
            )
        database.commit()
        return True
    except sqlite3.IntegrityError:
        database.rollback()
        flash("That email address is already registered.", "danger")
        return False


@catalog.route("/members/new", methods=["GET", "POST"])
@role_required("librarian")
def create_member():
    if request.method == "POST" and _save_member():
        flash("Member added.", "success")
        return redirect(url_for("catalog.members"))
    return render_template("member_form.html", member=None)


@catalog.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
@role_required("librarian")
def edit_member(member_id: int):
    database = get_db()
    member = database.execute(
        "SELECT * FROM members WHERE id = ?", (member_id,)
    ).fetchone()
    if member is None:
        abort(404)
    if request.method == "POST" and _save_member(member_id):
        flash("Member details updated.", "success")
        return redirect(url_for("catalog.member_detail", member_id=member_id))
    return render_template("member_form.html", member=member)


@catalog.post("/members/<int:member_id>/delete")
@role_required("librarian")
def delete_member(member_id: int):
    database = get_db()
    linked_account = database.execute(
        "SELECT id FROM users WHERE member_id = ?", (member_id,)
    ).fetchone()
    if linked_account:
        flash(
            "This member is linked to a student account. Update that account before deleting the member.",
            "danger",
        )
        return redirect(url_for("catalog.members"))
    try:
        cursor = database.execute("DELETE FROM members WHERE id = ?", (member_id,))
        if cursor.rowcount == 0:
            abort(404)
        database.commit()
        flash("Member deleted.", "success")
    except sqlite3.IntegrityError:
        database.rollback()
        flash("This member has borrowing history and cannot be deleted.", "danger")
    return redirect(url_for("catalog.members"))


@catalog.get("/members/<int:member_id>")
@role_required("librarian")
def member_detail(member_id: int):
    database = get_db()
    member = database.execute(
        "SELECT * FROM members WHERE id = ?", (member_id,)
    ).fetchone()
    if member is None:
        abort(404)
    history = database.execute(
        """
        SELECT issue_records.*, books.title,
            fines.amount AS fine_amount, fines.paid_on,
            CASE WHEN issue_records.return_date IS NULL
                      AND issue_records.due_date < date('now')
                 THEN 1 ELSE 0 END AS is_overdue
        FROM issue_records JOIN books ON books.id = issue_records.book_id
        LEFT JOIN fines ON fines.issue_record_id = issue_records.id
        WHERE issue_records.member_id = ?
        ORDER BY issue_records.issue_date DESC, issue_records.id DESC
        """,
        (member_id,),
    ).fetchall()
    return render_template("member_detail.html", member=member, history=history)


@catalog.get("/my-books")
@role_required("student")
def my_books():
    if g.user["member_id"] is None:
        flash("Your account is not linked to a library member.", "danger")
        return redirect(url_for("catalog.student_catalog"))
    books = get_db().execute(
        """
        SELECT issue_records.*, books.title, books.author,
               CASE WHEN issue_records.return_date IS NULL
                         AND issue_records.due_date < date('now')
                    THEN 1 ELSE 0 END AS is_overdue
        FROM issue_records JOIN books ON books.id = issue_records.book_id
        WHERE issue_records.member_id = ?
        ORDER BY issue_records.issue_date DESC
        """,
        (g.user["member_id"],),
    ).fetchall()
    return render_template("my_books.html", books=books)
