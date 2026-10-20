"""Add deterministic sample library data to the database."""

from datetime import date, timedelta
from pathlib import Path
import random
import sqlite3
from contextlib import closing

from werkzeug.security import generate_password_hash


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "instance" / "library.db"
RANDOM = random.Random(2026)

CATEGORIES = [
    ("Fiction", "Novels and short stories"),
    ("Science", "Science and technology"),
    ("History", "Historical writing"),
    ("Computing", "Programming and computer science"),
    ("Biography", "Life stories and memoirs"),
    ("Business", "Business and economics"),
    ("Mathematics", "Mathematics and statistics"),
    ("Self-Help", "Personal development"),
]

BOOKS = [
    ("The Quiet River", "A. Morgan", "Fiction"),
    ("Lanterns at Dawn", "M. Patel", "Fiction"),
    ("The Paper Garden", "R. Chen", "Fiction"),
    ("A Map of Small Things", "J. Brooks", "Fiction"),
    ("The Last Station", "S. Rivera", "Fiction"),
    ("North of the Orchard", "L. Wright", "Fiction"),
    ("The Glass Harbor", "D. Kim", "Fiction"),
    ("Letters from Elsewhere", "N. Shah", "Fiction"),
    ("A Season of Blue", "T. Ellis", "Fiction"),
    ("The Open Window", "P. Das", "Fiction"),
    ("Everyday Astronomy", "C. Lewis", "Science"),
    ("The Living Planet", "F. Ahmed", "Science"),
    ("Inside the Cell", "E. Park", "Science"),
    ("Weather and Climate", "B. Taylor", "Science"),
    ("Energy for Tomorrow", "G. Reed", "Science"),
    ("Oceans in Motion", "H. Singh", "Science"),
    ("The Human Brain", "K. Foster", "Science"),
    ("A Short History of Cities", "V. Iyer", "History"),
    ("Trade Routes of the World", "O. Martin", "History"),
    ("The Age of Invention", "W. Clark", "History"),
    ("Stories from the Ancient World", "Y. Rao", "History"),
    ("A History of Modern India", "I. Mehta", "History"),
    ("Introduction to Python", "D. Evans", "Computing"),
    ("Web Development Basics", "M. Johnson", "Computing"),
    ("Data Science in Practice", "A. Gupta", "Computing"),
    ("Networks Explained", "R. Wilson", "Computing"),
    ("Learning Databases", "S. Brown", "Computing"),
    ("Foundations of Machine Learning", "L. Garcia", "Computing"),
    ("The Inventor's Path", "N. Campbell", "Biography"),
    ("A Teacher's Journey", "P. Nair", "Biography"),
    ("Building Better Teams", "C. Adams", "Business"),
    ("The Small Business Handbook", "J. Thomas", "Business"),
    ("Principles of Economics", "F. Khan", "Business"),
    ("Numbers and Patterns", "E. Wright", "Mathematics"),
    ("Practical Statistics", "D. Lopez", "Mathematics"),
    ("Geometry Around Us", "T. Bose", "Mathematics"),
    ("Habits for Learning", "M. Green", "Self-Help"),
    ("Mindful Study", "R. Kapoor", "Self-Help"),
    ("The Confidence Workbook", "A. Scott", "Self-Help"),
    ("Make Time to Read", "K. Murphy", "Self-Help"),
]

FIRST_NAMES = [
    "Aarav", "Aisha", "Amira", "Arjun", "Carlos", "Chloe", "Daniel", "Diya",
    "Ethan", "Fatima", "Grace", "Hana", "Ibrahim", "Isabel", "Jamal", "Jia",
    "Kabir", "Leah", "Liam", "Maya", "Mateo", "Mina", "Noah", "Nora",
    "Omar", "Priya", "Ravi", "Sara", "Sofia", "Zoe",
]
LAST_NAMES = [
    "Adams", "Baker", "Chen", "Das", "Evans", "Foster", "Garcia", "Hall",
    "Iyer", "Jones", "Khan", "Lee", "Martin", "Nair", "Owens", "Patel",
    "Quinn", "Reed", "Shah", "Taylor", "Usman", "Vega", "White", "Xu",
    "Young", "Zaman", "Brooks", "Clark", "Green", "Murphy",
]


def seed_database() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DATABASE_PATH}. Run "
            "'python -m database.setup_db' first."
        )

    with closing(sqlite3.connect(DATABASE_PATH)) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        existing_data = connection.execute(
            "SELECT (SELECT COUNT(*) FROM categories) + "
            "(SELECT COUNT(*) FROM books) + "
            "(SELECT COUNT(*) FROM members) + "
            "(SELECT COUNT(*) FROM users) + "
            "(SELECT COUNT(*) FROM issue_records) + "
            "(SELECT COUNT(*) FROM fines)"
        ).fetchone()[0]
        if existing_data:
            raise RuntimeError(
                "Sample data already exists. Use a new/empty database rather "
                "than deleting existing library data."
            )

        connection.executemany(
            "INSERT INTO categories (name, description) VALUES (?, ?)", CATEGORIES
        )
        category_ids = {
            name: category_id
            for category_id, name in connection.execute(
                "SELECT id, name FROM categories"
            )
        }

        connection.executemany(
            """
            INSERT INTO books
                (title, author, isbn, category_id, total_copies, available_copies)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    title,
                    author,
                    f"978000000{index:04d}",
                    category_ids[category],
                    copies := RANDOM.randint(3, 8),
                    copies,
                )
                for index, (title, author, category) in enumerate(BOOKS, start=1)
            ],
        )

        member_rows = [
            (
                f"{FIRST_NAMES[index]} {LAST_NAMES[index]}",
                f"member{index + 1:02d}@example.edu",
                f"+1-555-{index + 1:04d}",
                (date.today() - timedelta(days=RANDOM.randint(30, 800))).isoformat(),
            )
            for index in range(30)
        ]
        connection.executemany(
            "INSERT INTO members (full_name, email, phone, joined_on) "
            "VALUES (?, ?, ?, ?)",
            member_rows,
        )
        member_ids = [
            row[0] for row in connection.execute("SELECT id FROM members ORDER BY id")
        ]

        # These are demo-only accounts; change the password before real use.
        connection.executemany(
            """
            INSERT INTO users (username, password_hash, full_name, role, member_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    "librarian",
                    generate_password_hash("LibraryDemo123!"),
                    "Demo Librarian",
                    "librarian",
                    None,
                ),
                (
                    "administrator",
                    generate_password_hash("LibraryDemo123!"),
                    "Demo Administrator",
                    "administrator",
                    None,
                ),
                (
                    "student",
                    generate_password_hash("LibraryDemo123!"),
                    member_rows[0][0],
                    "student",
                    member_ids[0],
                ),
            ],
        )

        book_rows = connection.execute(
            "SELECT id, total_copies FROM books ORDER BY id"
        ).fetchall()
        available = {book_id: total for book_id, total in book_rows}
        issue_rows = []
        fine_rows = []
        today = date.today()

        for issue_number in range(500):
            # Some recent books remain out; the rest have been returned.
            is_open = issue_number < 50
            days_ago = RANDOM.randint(0, 30) if is_open else RANDOM.randint(20, 364)
            issue_date = today - timedelta(days=days_ago)
            due_date = issue_date + timedelta(days=14)
            return_date = None

            if not is_open:
                return_delay = RANDOM.randint(1, min(40, days_ago))
                return_date = issue_date + timedelta(days=return_delay)

            book_id = RANDOM.choice(list(available))
            attempts = 0
            while available[book_id] == 0 and attempts < len(available) * 2:
                book_id = RANDOM.choice(list(available))
                attempts += 1
            if available[book_id] == 0:
                raise RuntimeError("Not enough copies to create the sample issues.")
            if is_open:
                available[book_id] -= 1

            issue_rows.append(
                (
                    book_id,
                    RANDOM.choice(member_ids),
                    issue_date.isoformat(),
                    due_date.isoformat(),
                    return_date.isoformat() if return_date else None,
                )
            )
            if return_date and return_date > due_date:
                late_days = (return_date - due_date).days
                fine_rows.append(
                    (
                        issue_number + 1,
                        late_days * 1.0,
                        return_date.isoformat(),
                        return_date.isoformat()
                        if RANDOM.random() < 0.65
                        else None,
                    )
                )

        connection.executemany(
            """
            INSERT INTO issue_records
                (book_id, member_id, issue_date, due_date, return_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            issue_rows,
        )
        # Issue IDs start at 1 in a freshly initialized database.
        connection.executemany(
            "INSERT INTO fines (issue_record_id, amount, assessed_on, paid_on) "
            "VALUES (?, ?, ?, ?)",
            fine_rows,
        )
        connection.executemany(
            "UPDATE books SET available_copies = ? WHERE id = ?",
            [(copies, book_id) for book_id, copies in available.items()],
        )

    print(
        "Seed data created: 40 books, 30 members, 3 users, "
        f"500 issue records, and {len(fine_rows)} late-return fines."
    )


if __name__ == "__main__":
    seed_database()
