# Test Case Table

| ID | Test case | Input / action | Expected result | Automated check |
|---|---|---|---|---|
| TC-01 | Empty database startup | Create app with a new SQLite file; open sign-in page | Schema exists and page responds successfully with zero book rows | `test_empty_database_initializes_and_login_page_loads` |
| TC-02 | Issue with available copy | Issue a book to an existing member | New record is saved and available count decreases by one | `test_issue_return_availability_and_fine_calculation`; `test_librarian_issue_and_return_routes_apply_the_fine` |
| TC-03 | Issue with no copies | Request a zero-copy book | Clear error; no issue record created | `test_issue_blocks_when_no_copies_remain` |
| TC-04 | Return an overdue loan | Return ten days after due date | Availability increases and fine equals ten times the configured daily rate | `test_issue_return_availability_and_fine_calculation`; `test_librarian_issue_and_return_routes_apply_the_fine` |
| TC-05 | Return twice | Return one issue record two times | Second attempt is rejected and availability does not increase again | `test_returning_same_book_twice_is_rejected` |
| TC-06 | Sign in as student | Submit valid student credentials | User signs in and can open student catalog | `test_login_uses_password_hash_and_role_restricts_librarian_pages` |
| TC-07 | Student opens librarian page | Request `/books` while signed in as student | Redirects to the student's allowed page; librarian controls are absent | `test_login_uses_password_hash_and_role_restricts_librarian_pages` |
| TC-08 | Invalid credentials | Submit incorrect password | Login stays unsuccessful and displays an error | `test_login_uses_password_hash_and_role_restricts_librarian_pages` |
| TC-09 | CSRF rejection | POST without the session token | Request is rejected with HTTP 400 | `test_post_without_csrf_token_is_rejected` |
| TC-10 | Librarian navigation smoke test | Open dashboard, books, members, issues, fines, reports, analytics, predictions | Each page responds with HTTP 200 | `test_librarian_dashboard_pages_render` |
| TC-11 | Admin role restriction | Student opens user accounts; administrator opens user accounts | Student is redirected; administrator page loads | `test_administrator_can_manage_accounts_but_student_cannot` |
| TC-12 | Schema role constraint | Insert an unsupported role | SQLite rejects the row | `test_schema_creates_tables_and_enforces_foreign_keys_and_roles` |
| TC-13 | Book search and CRUD | Search by title, author, ISBN, category, and ID; add, edit, and delete a book | Matching book appears; valid changes save; duplicate ISBN and invalid copy count show errors | `test_book_search_matches_all_supported_fields`; `test_book_crud_and_validation` |
| TC-14 | Member CRUD and history | Add/search/edit a member and open their history | Member changes save; prior loan appears in history; an unused member can be removed | `test_member_crud_search_and_history`; `test_member_can_be_deleted_without_borrowing_history` |
| TC-15 | Student personal loans | Sign in as student with a linked member and open personal loans | Only that member's loans are displayed | `test_student_sees_own_borrowing_records` |
| TC-16 | Overdue visibility | Create an unreturned loan with a past due date | Librarian issue table highlights it and shows the overdue badge | `test_overdue_issue_is_highlighted_for_librarian` |
| TC-17 | Fine payment | Mark an assessed fine as paid | Payment date is stored and status changes to paid | `test_fine_can_be_marked_paid_once` |
| TC-18 | Analytics and model outputs | Open analytics and predictions pages | Requested metrics render; prediction page includes plain-language guidance | `test_analytics_displays_requested_measures`; `test_predictions_page_explains_metrics` |
| TC-19 | Admin accounts and backup | Create a user, create a backup, and download it | User password is hashed; backup is readable and accessible only to admin | `test_administrator_can_create_hashed_user_account`; `test_admin_can_create_and_download_backup` |
| TC-20 | Print-friendly reports | Open a report and inspect print action | Browser print action is available; print CSS hides navigation and controls | `test_report_has_print_action` |

Run the table's automated checks with:

```bash
python -m unittest discover -s tests -v
```
