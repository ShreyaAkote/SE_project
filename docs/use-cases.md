# Use Case Descriptions

## Actors

- **Librarian:** Maintains the collection, members, circulation, fines, reports,
  and library analytics.
- **Student:** Searches the catalog and checks their own loans and due dates.
- **Administrator:** Manages user accounts and database backups.

## Use cases

| ID | Use case | Primary actor | Result |
|---|---|---|---|
| UC-01 | Sign in | Librarian, student, administrator | A valid account opens the pages allowed for its role. |
| UC-02 | Search catalog | Student, librarian | Matching books show category and available/total copies. |
| UC-03 | Maintain books | Librarian | A validated book is created, edited, or removed if it has no history. |
| UC-04 | Maintain members | Librarian | A member is created, edited, searched, or viewed with borrowing history. |
| UC-05 | Issue a copy | Librarian | An issue record is created and one available copy is reserved. |
| UC-06 | Return a copy | Librarian | The return date is recorded, availability is restored, and a late fine is assessed. |
| UC-07 | View personal loans | Student | The student sees their current and prior loans and due/overdue status. |
| UC-08 | Manage fines | Librarian | The librarian reviews assessed fines and records payment. |
| UC-09 | View/print reports | Librarian | A selected library report is displayed in a print-friendly layout. |
| UC-10 | View analytics/predictions | Librarian | Charts and model estimates are shown with evaluation and explanations. |
| UC-11 | Manage accounts | Administrator | A user is created, edited, or deleted with an assigned role. |
| UC-12 | Back up database | Administrator | A consistent SQLite backup is created and can be downloaded. |

## Use-case flow: issue a book

1. The librarian opens **Issue/return** and chooses **Issue a book**.
2. The page lists members and books with available copies.
3. The librarian selects a member and book, then confirms issue and due dates.
4. The server validates the dates and membership, then atomically decrements
   availability and inserts an issue record.
5. If a copy is unavailable or input is invalid, the page shows a clear error
   and no partial issue is saved.
