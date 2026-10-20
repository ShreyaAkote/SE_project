# Project Walkthrough and Viva Preparation

## Project files in simple words

| File/folder | What it does |
|---|---|
| `app.py` | Starts Flask, applies session/CSRF checks, and connects all page groups. |
| `requirements.txt` | Names Python packages required to install the app. |
| `database/schema.sql` | Describes the six SQLite tables, their rules, and indexes. |
| `database/db.py` | Creates the schema and provides the database connection for a request. |
| `database/services.py` | Holds issue and return rules; the fine rate is set here once. |
| `database/setup_db.py` | Creates an empty database structure. |
| `database/seed_db.py` | Creates safe, reproducible sample books, members, users, and loans. |
| `database/backup_db.py` | Makes a consistent local copy of the SQLite database. |
| `database/__init__.py` | Marks the database folder as a Python package. |
| `routes/__init__.py` | Collects the route groups and defines the librarian dashboard. |
| `routes/auth.py` | Contains the sign-in and sign-out pages. |
| `routes/security.py` | Checks whether a signed-in user has permission for a page. |
| `routes/catalog.py` | Searches and manages books and members, and shows student loans. |
| `routes/circulation.py` | Creates issues and returns and handles fines. |
| `routes/reports.py` | Builds the six print-friendly report pages. |
| `routes/analytics.py` | Calculates library summaries and opens prediction results. |
| `routes/admin.py` | Lets administrators manage accounts and backups. |
| `ml/predictions.py` | Builds the demand regressor and late-return classifier. |
| `ml/__init__.py` | Marks the ML folder as a Python package. |
| `templates/base.html` | Shared navigation, page layout, and flash messages. |
| `templates/login.html` | Sign-in form. |
| `templates/dashboard.html` | Librarian's main counts and shortcuts. |
| `templates/books.html`, `templates/book_form.html` | Book search/list and add/edit form. |
| `templates/members.html`, `templates/member_form.html` | Member search/list and add/edit form. |
| `templates/member_detail.html`, `templates/my_books.html` | Member history and student's personal borrowing list. |
| `templates/partials/history_table.html` | Shared borrowing-history table. |
| `templates/issues.html`, `templates/issue_form.html` | Current issue/return list and issue form. |
| `templates/fines.html` | Assessed fine list and payment action. |
| `templates/reports.html`, `templates/report_detail.html` | Report menu and printable report table. |
| `templates/analytics.html` | Chart.js dashboard. |
| `templates/predictions.html` | Model forecasts, accuracy scores, and explanations. |
| `templates/users.html`, `templates/user_form.html` | Administrator account list and account form. |
| `templates/backups.html` | Administrator backup list and download links. |
| `static/style.css` | Small layout adjustments and print rules. |
| `tests/test_library.py` | Automated checks for database, circulation, auth, roles, and pages. |
| `static/.gitkeep` | Keeps the static folder present before static assets are added. |
| `docs/` | Requirements, diagrams, use cases, test cases, and traceability. |

## 15 likely viva questions and answers

1. **What problem does this project solve?**  
   It keeps a library's books, members, borrowing transactions, returns, and
   fines in one web application, with reports and simple analytics.

2. **Why did you choose Flask?**  
   Flask is a small Python web framework. Its routes and templates are easy to
   understand in a college project.

3. **Why is SQLite used?**  
   SQLite stores the whole database in one file and needs no separate database
   server, so it is simple for a local demonstration.

4. **What are the main database tables?**  
   `categories`, `books`, `members`, `users`, `issue_records`, and `fines`.
   Their relationships are shown in the ER diagram.

5. **How do you know which copies are available?**  
   `books` stores total and available copies. Issuing decrements availability;
   returning increments it. The database also checks that availability is
   between zero and total copies.

6. **What happens if the last copy is already out?**  
   The issue service updates only a book whose `available_copies` is above
   zero. If no row changes, it reports that no copies are available.

7. **How is a fine calculated?**  
   The service compares the return date with the due date and multiplies late
   days by `FINE_PER_DAY`, currently ₹2.

8. **How are passwords protected?**  
   Werkzeug's password-hashing utilities store a salted hash. Login checks a
   submitted password against the hash; the database does not store the
   readable password.

9. **How do roles restrict pages?**  
   The `role_required` decorator checks the signed-in user's database role
   before the route runs. Hiding a link alone is not treated as security.

10. **What does CSRF protection do here?**  
    Each session gets a random token. Every POST form includes it, and the app
    rejects a missing or incorrect token before changing data.

11. **What is a foreign key?**  
    It connects a row to a row in another table. For example, an issue record
    refers to an existing book and member, preventing orphaned loan records.

12. **What is the difference between analytics and prediction?**  
    Analytics summarizes past/current data. Prediction uses a learned model to
    estimate future demand or a possible late return.

13. **How is demand prediction evaluated?**  
    A random-forest regressor is trained on earlier category/month counts. The
    page reports mean absolute error and the percentage of forecasts within
    two issues on held-out months.

14. **How is the late-return classifier evaluated?**  
    It trains on earlier returned loans and tests on a later chronological
    portion. Accuracy is the share of those held-out loans whose late/on-time
    label it predicts correctly.

15. **How do you make a backup and test the app?**  
    An administrator uses the backup page, or runs
    `python -m database.backup_db`. Automated checks run with
    `python -m unittest discover -s tests -v`.
