# System Diagrams

The Mermaid diagrams can be rendered by compatible Markdown viewers.

## ER diagram

```mermaid
erDiagram
    CATEGORIES ||--o{ BOOKS : groups
    BOOKS ||--o{ ISSUE_RECORDS : borrowed_as
    MEMBERS ||--o{ ISSUE_RECORDS : borrows
    MEMBERS o|--o| USERS : account_for
    ISSUE_RECORDS ||--o| FINES : may_have

    CATEGORIES {
        int id PK
        string name UK
        string description
    }
    BOOKS {
        int id PK
        string title
        string author
        string isbn UK
        int category_id FK
        int total_copies
        int available_copies
    }
    MEMBERS {
        int id PK
        string full_name
        string email UK
        string phone
        date joined_on
    }
    USERS {
        int id PK
        string username UK
        string password_hash
        string full_name
        string role
        int member_id FK
    }
    ISSUE_RECORDS {
        int id PK
        int book_id FK
        int member_id FK
        date issue_date
        date due_date
        date return_date
    }
    FINES {
        int id PK
        int issue_record_id FK
        decimal amount
        date assessed_on
        date paid_on
    }
```

## Class / module diagram

This project uses Flask modules and SQLite rows rather than a large object model.
The diagram shows the main responsibilities.

```mermaid
classDiagram
    class FlaskApp {
      +create_app()
      +load_logged_in_user()
      +protect_form_submissions()
    }
    class AuthRoutes {
      +login()
      +logout()
    }
    class CatalogRoutes {
      +books()
      +members()
      +member_detail()
    }
    class CirculationRoutes {
      +issues()
      +new_issue()
      +return_issue()
      +fines()
    }
    class DatabaseServices {
      +issue_book()
      +return_book()
      +FINE_PER_DAY
    }
    class AdminRoutes {
      +users()
      +create_backup()
    }
    class AnalyticsRoutes {
      +dashboard()
      +predictions()
    }
    class PredictionModels {
      +predict_library_trends()
      +_predict_category_demand()
      +_predict_late_returns()
    }
    FlaskApp --> AuthRoutes
    FlaskApp --> CatalogRoutes
    FlaskApp --> CirculationRoutes
    FlaskApp --> AdminRoutes
    FlaskApp --> AnalyticsRoutes
    CirculationRoutes --> DatabaseServices
    AnalyticsRoutes --> PredictionModels
```

## Data-flow diagram (level 0)

```mermaid
flowchart LR
    L[Librarian] -->|book, member, loan, report requests| APP((Library web app))
    S[Student] -->|search and own-loan request| APP
    A[Administrator] -->|account and backup request| APP
    APP <-->|read/write books, members, users, loans, fines| DB[(SQLite database)]
    APP -->|dashboard, search, reports, predictions| L
    APP -->|catalog and personal loans| S
    APP -->|user management and backup download| A
    DB -->|historical loan data| ML[Analytics and ML]
    ML -->|demand and late-return estimates| APP
```

## Data-flow diagram (circulation detail)

```mermaid
flowchart TD
    LIB[Librarian] --> P1[Validate issue request]
    P1 -->|book and member IDs| D1[(Books and members)]
    D1 -->|valid member and available copies| P2[Save issue transaction]
    P2 -->|decrease available copies| D1
    P2 -->|issue and due dates| D2[(Issue records)]
    LIB --> P3[Record return]
    P3 --> D2
    D2 -->|due date and loan status| P4[Calculate late days]
    P4 -->|return date| D2
    P4 -->|fine at configured daily rate| D3[(Fines)]
    P4 -->|restore one available copy| D1
```
