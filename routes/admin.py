"""Administrator-only user and backup management."""

from datetime import datetime
from pathlib import Path
import re
import sqlite3
from contextlib import closing

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from werkzeug.security import generate_password_hash

from database.db import get_db
from routes.security import role_required

admin = Blueprint("admin", __name__, url_prefix="/admin")
ROLES = ("librarian", "student", "administrator")


def _backup_directory() -> Path:
    path = Path(current_app.instance_path) / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


@admin.get("/users")
@role_required("administrator")
def users():
    users_list = get_db().execute(
        """
        SELECT users.id, users.username, users.full_name, users.role,
               members.full_name AS member_name
        FROM users LEFT JOIN members ON users.member_id = members.id
        ORDER BY users.username
        """
    ).fetchall()
    return render_template("users.html", users=users_list)


@admin.route("/users/new", methods=["GET", "POST"])
@role_required("administrator")
def create_user():
    database = get_db()
    members = database.execute("SELECT id, full_name FROM members ORDER BY full_name")
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        member_id = request.form.get("member_id", "").strip() or None
        error = None
        if not username or not full_name or len(password) < 8:
            error = "Enter a username and full name; passwords must be at least 8 characters."
        elif role not in ROLES:
            error = "Choose a valid account role."
        elif role == "student" and member_id is None:
            error = "Link student accounts to a library member."
        if error:
            flash(error, "danger")
        else:
            try:
                database.execute(
                    """
                    INSERT INTO users (username, password_hash, full_name, role, member_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        generate_password_hash(password),
                        full_name,
                        role,
                        member_id,
                    ),
                )
                database.commit()
                flash("User account created.", "success")
                return redirect(url_for("admin.users"))
            except sqlite3.IntegrityError as error:
                database.rollback()
                flash(f"Could not create account: {error}.", "danger")
    return render_template("user_form.html", account=None, roles=ROLES, members=members)


@admin.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@role_required("administrator")
def edit_user(user_id: int):
    database = get_db()
    account = database.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if account is None:
        abort(404)
    members = database.execute("SELECT id, full_name FROM members ORDER BY full_name")

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "")
        password = request.form.get("password", "")
        member_id = request.form.get("member_id", "").strip() or None
        if not full_name or role not in ROLES:
            flash("Enter a name and choose a valid role.", "danger")
        elif role == "student" and member_id is None:
            flash("Link student accounts to a library member.", "danger")
        elif account["id"] == g.user["id"] and role != "administrator":
            flash("You cannot remove your own administrator role.", "danger")
        elif password and len(password) < 8:
            flash("Passwords must be at least 8 characters.", "danger")
        else:
            try:
                if password:
                    database.execute(
                        """
                        UPDATE users SET full_name = ?, role = ?, member_id = ?,
                            password_hash = ? WHERE id = ?
                        """,
                        (
                            full_name,
                            role,
                            member_id,
                            generate_password_hash(password),
                            user_id,
                        ),
                    )
                else:
                    database.execute(
                        "UPDATE users SET full_name = ?, role = ?, member_id = ? "
                        "WHERE id = ?",
                        (full_name, role, member_id, user_id),
                    )
                database.commit()
                flash("User account updated.", "success")
                return redirect(url_for("admin.users"))
            except sqlite3.IntegrityError as error:
                database.rollback()
                flash(f"Could not update account: {error}.", "danger")
    return render_template("user_form.html", account=account, roles=ROLES, members=members)


@admin.post("/users/<int:user_id>/delete")
@role_required("administrator")
def delete_user(user_id: int):
    if user_id == g.user["id"]:
        flash("You cannot delete your own administrator account.", "danger")
    else:
        database = get_db()
        database.execute("DELETE FROM users WHERE id = ?", (user_id,))
        database.commit()
        flash("User account deleted.", "success")
    return redirect(url_for("admin.users"))


@admin.post("/backup")
@role_required("administrator")
def create_backup():
    backup_path = _backup_directory() / (
        "library-backup-"
        + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        + ".sqlite3"
    )
    with closing(sqlite3.connect(backup_path)) as destination:
        get_db().backup(destination)
    flash(f"Database backup created: {backup_path.name}", "success")
    return redirect(url_for("admin.users"))


@admin.get("/backups/<filename>")
@role_required("administrator")
def download_backup(filename: str):
    if not re.fullmatch(
        r"library-backup-\d{8}-\d{6}(?:-\d{6})?\.sqlite3", filename
    ):
        abort(404)
    backup_path = _backup_directory() / filename
    if not backup_path.is_file():
        abort(404)
    return send_file(backup_path, as_attachment=True)


@admin.get("/backups")
@role_required("administrator")
def backups():
    backup_files = sorted(
        _backup_directory().glob("library-backup-*.sqlite3"), reverse=True
    )
    return render_template("backups.html", backups=backup_files)
