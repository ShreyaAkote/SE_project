# Software Requirements Specification

## Project

**Smart Library Management System with Analytics and Prediction**

## Scope and source

This is the project's agreed requirements baseline, written from the features
requested for the college project. The starting workspace did not contain the
referenced `docs/SRS.md`, so this is not a transcription or review of an
original supplied SRS. Update it if your course has an authoritative SRS.

The application is a local web app for librarians, students, and
administrators. It manages books, members, circulation, and fines, provides
reports and analytics, and demonstrates two small machine-learning models.

## Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | The system shall authenticate users with hashed passwords and assign one of three roles: librarian, student, or administrator. |
| FR-02 | Librarians shall add, edit, delete, and search books by title, author, ISBN, category, and book ID. |
| FR-03 | Librarians shall add, edit, delete, and search members and view each member's borrowing history. |
| FR-04 | Students shall search books, see their availability, and view their own borrowing records and due dates. |
| FR-05 | Librarians shall issue an available copy, recording member, book, issue date, and due date. Issuing shall fail when no copy is available. |
| FR-06 | Librarians shall record a return date; the system shall restore availability and clearly identify overdue loans. |
| FR-07 | The system shall assess late-return fines at a configurable rate of ₹2 per late day and show fine/payment details. |
| FR-08 | The system shall provide available-book, issued-book, overdue-book, member-detail, fine-detail, and borrowing-history reports in print-friendly form. |
| FR-09 | Librarians shall view most-borrowed books, category borrowing, monthly issue trend, overdue count, fines collected, and most active members. |
| FR-10 | The system shall forecast next-month issue demand by category and estimate late-return risk for current loans, with evaluation scores and plain-language explanations. |
| FR-11 | Administrators shall create, edit, and delete user accounts and create/download SQLite database backups. |
| FR-12 | The user interface shall be responsive, use Bootstrap, and display clear success and error messages. |

## Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | **Security:** Hash passwords; enforce role checks on the server; use parameterized SQL, CSRF checks for form submissions, and secure session-cookie defaults. |
| NFR-02 | **Speed:** Use indexes for common category, member, book, and due-date lookups; keep dashboard queries aggregated in SQLite. |
| NFR-03 | **Ease of use:** Use a consistent responsive layout, labels, validation feedback, role-specific navigation, and print-friendly reports. |
| NFR-04 | **Reliability:** Enforce foreign keys and database constraints; make issue/return updates atomic; use SQLite's online backup API; test key workflows. |
| NFR-05 | **Maintainability:** Separate routes, database services/schema, templates, machine-learning code, and tests. Keep the fine rate in one configuration constant. |
| NFR-06 | **Prediction transparency:** Show holdout evaluation metrics and explain model inputs and limitations in everyday language. |

## Assumptions and limitations

- This is a learning/demo app, not a production library service.
- Seeded demo passwords must be changed before real accounts are used.
- Bootstrap and Chart.js are loaded from public CDNs; internet access is needed
  to display their styling and charts.
- The ML examples need enough returned-loan history. When training examples
  are insufficient, the page explains why it cannot score predictions.
- A single SQLite database is suitable for a local college demo. A deployed
  multi-user service may need a server database and operational monitoring.

## Non-functional requirement review

| Area | Implementation reviewed | Outcome and remaining limit |
|---|---|---|
| Speed | Category/member/book/due-date indexes; aggregate SQL for the dashboards; compact sample ML dataset | Appropriate for the 500-record college demo. No numeric response-time target was supplied, so no latency claim is made. Benchmark with the expected production-sized data if the scope grows. |
| Security | Werkzeug password hashes; server-side role decorator; parameterized SQL; per-session CSRF tokens on POST; Jinja autoescaping; random default secret; HttpOnly/SameSite cookies; debug disabled | Core web protections are implemented. The local HTTP setup leaves `SESSION_COOKIE_SECURE` off so it runs locally; set `SESSION_COOKIE_SECURE=1`, configure a stable secret, and use HTTPS when deployed. Replace demo accounts. |
| Ease of use | Shared responsive Bootstrap navigation; role-specific links; labeled forms; validation and flash messages; overdue highlighting; browser print view | Pages are smoke-tested for HTTP success and key workflows. Bootstrap and Chart.js use CDNs, so their styling/charts need internet access. |
| Reliability | Foreign keys and check constraints; atomic `BEGIN IMMEDIATE` issue/return updates; unique fine per issue; SQLite online backup; unit and route tests | 22 tests pass, including zero-copy issue, duplicate return, late fine, login, role restrictions, backup, and page smoke checks. For multi-process/high-volume deployment, consider a server database and scheduled off-site backups. |

The review uses this project baseline, derived from the requested features,
because the original SRS file was not present in the starting workspace.
