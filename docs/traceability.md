# SRS Requirements Traceability

The source workspace did not include an original SRS. The requirement IDs below
refer to the project baseline in [SRS.md](./SRS.md), created from the requested
features. Each row points to code and an automated check in
[test_library.py](../tests/test_library.py).

| Requirement | Implementing feature / files | Test that checks it |
|---|---|---|
| FR-01 Login, password hashing, and roles | `routes/auth.py`, `routes/security.py`, `app.py`, `database/schema.sql` | `test_login_uses_password_hash_and_role_restricts_librarian_pages`; `test_administrator_can_manage_accounts_but_student_cannot` |
| FR-02 Book add/edit/delete/search by title, author, ISBN, category, and ID | `routes/catalog.py`, `templates/books.html`, `templates/book_form.html` | `test_book_search_matches_all_supported_fields`; `test_book_crud_and_validation` |
| FR-03 Member CRUD, search, and borrowing history | `routes/catalog.py`, `templates/members.html`, `templates/member_detail.html` | `test_member_crud_search_and_history` |
| FR-04 Student catalog and own borrowing list | `routes/catalog.py`, `templates/my_books.html` | `test_login_uses_password_hash_and_role_restricts_librarian_pages`; `test_student_sees_own_borrowing_records` |
| FR-05 Issue copy and block zero availability | `database/services.py`, `routes/circulation.py` | `test_issue_blocks_when_no_copies_remain`; `test_librarian_issue_and_return_routes_apply_the_fine` |
| FR-06 Return copy and overdue display | `database/services.py`, `routes/circulation.py`, `templates/issues.html` | `test_issue_return_availability_and_fine_calculation`; `test_overdue_issue_is_highlighted_for_librarian` |
| FR-07 Fine rate, assessment, and payment | `database/services.py`, `routes/circulation.py`, `templates/fines.html` | `test_issue_return_availability_and_fine_calculation`; `test_fine_can_be_marked_paid_once` |
| FR-08 Six reports and print styles | `routes/reports.py`, `templates/report_detail.html`, `static/style.css` | `test_librarian_dashboard_pages_render`; `test_report_has_print_action` |
| FR-09 Analytics metrics and charts | `routes/analytics.py`, `templates/analytics.html` | `test_analytics_displays_requested_measures` |
| FR-10 Demand and late-return ML with evaluation | `ml/predictions.py`, `routes/analytics.py`, `templates/predictions.html` | `test_predictions_page_explains_metrics` |
| FR-11 User admin and backups | `routes/admin.py`, `database/backup_db.py`, `templates/backups.html` | `test_administrator_can_manage_accounts_but_student_cannot`; `test_admin_can_create_and_download_backup` |
| FR-12 Responsive Bootstrap UI and flash feedback | `templates/base.html`, `static/style.css`, route validation messages | `test_librarian_dashboard_pages_render`; `test_book_crud_and_validation` |
| NFR-01 Security controls | `app.py`, `routes/security.py`, `routes/auth.py`, SQL parameters | `test_post_without_csrf_token_is_rejected`; role and login tests above |
| NFR-02 Indexed, aggregate database access | `database/schema.sql`, route query modules | `test_schema_creates_tables_and_enforces_foreign_keys_and_roles`; page-render/analytics test |
| NFR-03 Usable, responsive, printable pages | `templates/base.html`, `static/style.css` | `test_report_has_print_action`; page-render tests |
| NFR-04 Integrity, atomic circulation, and backup | `database/services.py`, `database/schema.sql`, backup routes | circulation and backup tests above |
| NFR-05 Separated modules and centralized fine rate | `database/`, `routes/`, `ml/`, `templates/`, `tests/` | `test_issue_return_availability_and_fine_calculation` |
| NFR-06 Explainable evaluated predictions | `ml/predictions.py`, `templates/predictions.html` | `test_predictions_page_explains_metrics` |
