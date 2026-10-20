"""Unit and basic page tests for the library starter."""

from datetime import date, timedelta
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

from app import create_app
from database.db import get_db
from database.services import (
    FINE_PER_DAY,
    LibraryOperationError,
    issue_book,
    return_book,
)


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.temporary_directory.name) / "test.db")
        self.instance_path = str(Path(self.temporary_directory.name) / "instance")
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": self.database_path,
                "INSTANCE_PATH": self.instance_path,
                "SECRET_KEY": "test-only-secret",
            }
        )
        self.client = self.app.test_client()
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "INSERT INTO categories (name) VALUES ('Fiction')"
            )
            connection.execute(
                """
                INSERT INTO members (full_name, email, phone, joined_on)
                VALUES ('Test Member', 'member@example.edu', '', ?)
                """,
                (date.today().isoformat(),),
            )
            connection.executemany(
                """
                INSERT INTO users (username, password_hash, full_name, role, member_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        "librarian",
                        generate_password_hash(
                            "LibraryPass123!", method="pbkdf2:sha256:1000"
                        ),
                        "Test Librarian",
                        "librarian",
                        None,
                    ),
                    (
                        "student",
                        generate_password_hash(
                            "StudentPass123!", method="pbkdf2:sha256:1000"
                        ),
                        "Test Member",
                        "student",
                        1,
                    ),
                    (
                        "admin",
                        generate_password_hash(
                            "AdminPass123!", method="pbkdf2:sha256:1000"
                        ),
                        "Test Admin",
                        "administrator",
                        None,
                    ),
                ],
            )
            connection.execute(
                """
                INSERT INTO books
                    (title, author, isbn, category_id, total_copies, available_copies)
                VALUES ('Test Book', 'Test Author', '1234567890123', 1, 1, 1)
                """
            )
            connection.execute(
                """
                INSERT INTO books
                    (title, author, isbn, category_id, total_copies, available_copies)
                VALUES ('Unavailable Book', 'Test Author', '1234567890124', 1, 0, 0)
                """
            )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _csrf(self) -> str:
        self.client.get("/login")
        with self.client.session_transaction() as session:
            return session["_csrf_token"]

    def _login(self, username: str, password: str) -> None:
        token = self._csrf()
        response = self.client.post(
            "/login",
            data={"csrf_token": token, "username": username, "password": password},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

    def test_empty_database_initializes_and_login_page_loads(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            empty_database = str(Path(temporary_directory) / "empty.db")
            empty_app = create_app(
                {
                    "TESTING": True,
                    "DATABASE": empty_database,
                    "SECRET_KEY": "empty-test-secret",
                }
            )
            response = empty_app.test_client().get("/login")
            self.assertEqual(response.status_code, 200)
            with closing(sqlite3.connect(empty_database)) as connection:
                count = connection.execute("SELECT COUNT(*) FROM books").fetchone()[0]
            self.assertEqual(count, 0)

    def test_schema_creates_tables_and_enforces_foreign_keys_and_roles(self):
        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertTrue(
                {
                    "books",
                    "categories",
                    "fines",
                    "issue_records",
                    "members",
                    "users",
                }.issubset(tables)
            )
            connection.execute("PRAGMA foreign_keys = ON")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO users (username, password_hash, full_name, role) "
                    "VALUES ('bad-role', 'hash', 'Test User', 'visitor')"
                )

    def test_issue_blocks_when_no_copies_remain(self):
        with self.app.app_context():
            with self.assertRaisesRegex(
                LibraryOperationError, "No copies of this book are available"
            ):
                issue_book(2, 1, date.today(), date.today() + timedelta(days=14))
            count = get_db().execute(
                "SELECT COUNT(*) FROM issue_records"
            ).fetchone()[0]
            self.assertEqual(count, 0)

    def test_issue_return_availability_and_fine_calculation(self):
        issued_on = date.today() - timedelta(days=20)
        due_on = date.today() - timedelta(days=10)
        returned_on = date.today()
        with self.app.app_context():
            issue_id = issue_book(1, 1, issued_on, due_on)
            available = get_db().execute(
                "SELECT available_copies FROM books WHERE id = 1"
            ).fetchone()[0]
            self.assertEqual(available, 0)

            fine = return_book(issue_id, returned_on)
            self.assertEqual(fine, 10 * FINE_PER_DAY)
            available = get_db().execute(
                "SELECT available_copies FROM books WHERE id = 1"
            ).fetchone()[0]
            self.assertEqual(available, 1)
            fine_row = get_db().execute(
                "SELECT amount, paid_on FROM fines WHERE issue_record_id = ?",
                (issue_id,),
            ).fetchone()
            self.assertEqual(fine_row["amount"], 20)
            self.assertIsNone(fine_row["paid_on"])

    def test_librarian_issue_and_return_routes_apply_the_fine(self):
        self._login("librarian", "LibraryPass123!")
        with self.client.session_transaction() as session:
            token = session["_csrf_token"]
        today = date.today()
        response = self.client.post(
            "/issues/new",
            data={
                "csrf_token": token,
                "book_id": "1",
                "member_id": "1",
                "issue_date": (today - timedelta(days=20)).isoformat(),
                "due_date": (today - timedelta(days=10)).isoformat(),
            },
            follow_redirects=True,
        )
        self.assertIn(b"Book issued successfully.", response.data)
        with self.app.app_context():
            issue_id = get_db().execute(
                "SELECT id FROM issue_records ORDER BY id DESC LIMIT 1"
            ).fetchone()["id"]
        response = self.client.post(
            f"/issues/{issue_id}/return",
            data={"csrf_token": token, "return_date": today.isoformat()},
            follow_redirects=True,
        )
        self.assertIn(b"Late fine: \xe2\x82\xb920.00", response.data)

    def test_returning_same_book_twice_is_rejected(self):
        with self.app.app_context():
            issue_id = issue_book(
                1,
                1,
                date.today() - timedelta(days=2),
                date.today() + timedelta(days=5),
            )
            return_book(issue_id, date.today())
            with self.assertRaisesRegex(LibraryOperationError, "already been returned"):
                return_book(issue_id, date.today())
            copies = get_db().execute(
                "SELECT available_copies FROM books WHERE id = 1"
            ).fetchone()[0]
            self.assertEqual(copies, 1)

    def test_login_uses_password_hash_and_role_restricts_librarian_pages(self):
        self._login("student", "StudentPass123!")
        response = self.client.get("/books", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Search books", response.data)
        self.assertNotIn(b"Book management", response.data)

        bad_client = self.app.test_client()
        bad_token = self._csrf_for(bad_client)
        response = bad_client.post(
            "/login",
            data={
                "csrf_token": bad_token,
                "username": "student",
                "password": "wrong-password",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Username or password is incorrect.", response.data)

    def _csrf_for(self, client) -> str:
        client.get("/login")
        with client.session_transaction() as session:
            return session["_csrf_token"]

    def test_librarian_dashboard_pages_render(self):
        self._login("librarian", "LibraryPass123!")
        paths = [
            "/dashboard",
            "/books",
            "/books/1/edit",
            "/members",
            "/members/1",
            "/members/1/edit",
            "/issues",
            "/issues/new",
            "/fines",
            "/reports/",
            "/reports/available",
            "/reports/issued",
            "/reports/overdue",
            "/reports/members",
            "/reports/fines",
            "/reports/history",
            "/analytics",
            "/predictions",
        ]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, response.get_data(as_text=True))

    def test_administrator_can_manage_accounts_but_student_cannot(self):
        self._login("student", "StudentPass123!")
        response = self.client.get("/admin/users", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Search books", response.data)

        self.client.post(
            "/logout",
            data={"csrf_token": self._csrf()},
            follow_redirects=True,
        )
        self._login("admin", "AdminPass123!")
        response = self.client.get("/admin/users")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"User accounts", response.data)
        for path in ["/admin/users/new", "/admin/users/2/edit", "/admin/backups"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_book_search_matches_all_supported_fields(self):
        self._login("librarian", "LibraryPass123!")
        for query in ["Test Book", "Test Author", "1234567890123", "Fiction", "1"]:
            with self.subTest(query=query):
                response = self.client.get("/books", query_string={"q": query})
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Test Book", response.data)

    def test_book_crud_and_validation(self):
        token = self._csrf()
        self._login("librarian", "LibraryPass123!")
        with self.client.session_transaction() as session:
            token = session["_csrf_token"]
        response = self.client.post(
            "/books/new",
            data={
                "csrf_token": token,
                "title": "New Book",
                "author": "New Author",
                "isbn": "9781234567890",
                "category_id": "1",
                "total_copies": "2",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Book added.", response.data)
        with self.app.app_context():
            book = get_db().execute(
                "SELECT id FROM books WHERE title = 'New Book'"
            ).fetchone()
            self.assertIsNotNone(book)
            book_id = book["id"]

        response = self.client.post(
            f"/books/{book_id}/edit",
            data={
                "csrf_token": token,
                "title": "Changed Book",
                "author": "New Author",
                "isbn": "9781234567890",
                "category_id": "1",
                "total_copies": "2",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Book updated.", response.data)
        response = self.client.post(
            "/books/new",
            data={
                "csrf_token": token,
                "title": "Invalid",
                "author": "Author",
                "isbn": "9781234567890",
                "category_id": "1",
                "total_copies": "1",
            },
            follow_redirects=True,
        )
        self.assertIn(b"unique ISBN", response.data)
        response = self.client.post(
            "/books/new",
            data={
                "csrf_token": token,
                "title": "Invalid",
                "author": "Author",
                "isbn": "9781234567891",
                "category_id": "1",
                "total_copies": "not-a-number",
            },
            follow_redirects=True,
        )
        self.assertIn(b"whole number", response.data)
        response = self.client.post(
            f"/books/{book_id}/delete",
            data={"csrf_token": token},
            follow_redirects=True,
        )
        self.assertIn(b"Book deleted.", response.data)

    def test_member_crud_search_and_history(self):
        self._login("librarian", "LibraryPass123!")
        with self.client.session_transaction() as session:
            token = session["_csrf_token"]
        response = self.client.post(
            "/members/new",
            data={
                "csrf_token": token,
                "full_name": "New Member",
                "email": "new@example.edu",
                "phone": "555-0100",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Member added.", response.data)
        response = self.client.get("/members", query_string={"q": "New Member"})
        self.assertIn(b"New Member", response.data)
        with self.app.app_context():
            member_id = get_db().execute(
                "SELECT id FROM members WHERE email = 'new@example.edu'"
            ).fetchone()["id"]
            issue_book(
                1,
                member_id,
                date.today() - timedelta(days=1),
                date.today() + timedelta(days=10),
            )
        response = self.client.get(f"/members/{member_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Book", response.data)
        response = self.client.post(
            f"/members/{member_id}/edit",
            data={
                "csrf_token": token,
                "full_name": "Updated Member",
                "email": "updated@example.edu",
                "phone": "555-0101",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Member details updated.", response.data)

    def test_member_can_be_deleted_without_borrowing_history(self):
        self._login("librarian", "LibraryPass123!")
        with self.client.session_transaction() as session:
            token = session["_csrf_token"]
        response = self.client.post(
            "/members/new",
            data={
                "csrf_token": token,
                "full_name": "Temporary Member",
                "email": "temporary@example.edu",
                "phone": "",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Member added.", response.data)
        with self.app.app_context():
            member_id = get_db().execute(
                "SELECT id FROM members WHERE email = 'temporary@example.edu'"
            ).fetchone()["id"]
        response = self.client.post(
            f"/members/{member_id}/delete",
            data={"csrf_token": token},
            follow_redirects=True,
        )
        self.assertIn(b"Member deleted.", response.data)

    def test_student_sees_own_borrowing_records(self):
        with self.app.app_context():
            issue_book(
                1,
                1,
                date.today(),
                date.today() + timedelta(days=14),
            )
        self._login("student", "StudentPass123!")
        response = self.client.get("/my-books")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Book", response.data)

    def test_overdue_issue_is_highlighted_for_librarian(self):
        with self.app.app_context():
            issue_book(
                1,
                1,
                date.today() - timedelta(days=15),
                date.today() - timedelta(days=1),
            )
        self._login("librarian", "LibraryPass123!")
        response = self.client.get("/issues")
        self.assertIn(b"OVERDUE", response.data)

    def test_administrator_can_create_hashed_user_account(self):
        self._login("admin", "AdminPass123!")
        with self.client.session_transaction() as session:
            token = session["_csrf_token"]
        response = self.client.post(
            "/admin/users/new",
            data={
                "csrf_token": token,
                "username": "new-librarian",
                "full_name": "New Librarian",
                "password": "NewPassword123!",
                "role": "librarian",
                "member_id": "",
            },
            follow_redirects=True,
        )
        self.assertIn(b"User account created.", response.data)
        with self.app.app_context():
            account = get_db().execute(
                "SELECT password_hash FROM users WHERE username = 'new-librarian'"
            ).fetchone()
            self.assertTrue(check_password_hash(account["password_hash"], "NewPassword123!"))
            self.assertNotEqual(account["password_hash"], "NewPassword123!")
        response = self.client.post(
            "/admin/users/4/edit",
            data={
                "csrf_token": token,
                "full_name": "Renamed Librarian",
                "password": "",
                "role": "librarian",
                "member_id": "",
            },
            follow_redirects=True,
        )
        self.assertIn(b"User account updated.", response.data)
        response = self.client.post(
            "/admin/users/4/delete",
            data={"csrf_token": token},
            follow_redirects=True,
        )
        self.assertIn(b"User account deleted.", response.data)

    def test_fine_can_be_marked_paid_once(self):
        with self.app.app_context():
            issue_id = issue_book(
                1,
                1,
                date.today() - timedelta(days=20),
                date.today() - timedelta(days=10),
            )
            return_book(issue_id, date.today())
        self._login("librarian", "LibraryPass123!")
        with self.app.app_context():
            fine_id = get_db().execute("SELECT id FROM fines").fetchone()["id"]
        with self.client.session_transaction() as session:
            token = session["_csrf_token"]
        response = self.client.post(
            f"/fines/{fine_id}/pay",
            data={"csrf_token": token},
            follow_redirects=True,
        )
        self.assertIn(b"Fine marked as paid.", response.data)

    def test_admin_can_create_and_download_backup(self):
        self._login("admin", "AdminPass123!")
        with self.client.session_transaction() as session:
            token = session["_csrf_token"]
        response = self.client.post(
            "/admin/backup", data={"csrf_token": token}, follow_redirects=True
        )
        self.assertIn(b"Database backup created", response.data)
        response = self.client.get("/admin/backups")
        self.assertEqual(response.status_code, 200)
        backup_path = next((Path(self.instance_path) / "backups").glob("*.sqlite3"))
        with closing(sqlite3.connect(backup_path)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM books").fetchone()[0], 2
            )
        download = self.client.get(f"/admin/backups/{backup_path.name}")
        self.assertEqual(download.status_code, 200)
        self.assertGreater(len(download.data), 0)
        download.close()

    def test_report_has_print_action(self):
        self._login("librarian", "LibraryPass123!")
        response = self.client.get("/reports/available")
        self.assertIn(b"window.print()", response.data)

    def test_predictions_page_explains_metrics(self):
        self._login("librarian", "LibraryPass123!")
        response = self.client.get("/predictions")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"planning estimates", response.data)
        self.assertIn(b"late-return model", response.data)

    def test_analytics_displays_requested_measures(self):
        with self.app.app_context():
            issue_book(
                1,
                1,
                date.today() - timedelta(days=20),
                date.today() - timedelta(days=10),
            )
        self._login("librarian", "LibraryPass123!")
        response = self.client.get("/analytics")
        self.assertEqual(response.status_code, 200)
        for label in [
            b"Most borrowed books",
            b"Borrowing by category",
            b"Monthly issue trend",
            b"Currently overdue",
            b"Fines collected",
            b"Most active members",
        ]:
            self.assertIn(label, response.data)

    def test_post_without_csrf_token_is_rejected(self):
        response = self.client.post(
            "/login", data={"username": "student", "password": "StudentPass123!"}
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
