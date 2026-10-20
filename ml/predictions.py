"""Train small, explainable models from historical library loans."""

from collections import defaultdict
from datetime import date

import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error

from database.db import get_db

LATE_FEATURES = [
    "category_id",
    "issue_month",
    "issue_weekday",
    "prior_loans",
    "prior_late_rate",
]


def predict_library_trends() -> dict:
    """Return next-month category demand and late-return model results."""
    database = get_db()
    issue_rows = database.execute(
        """
        SELECT issue_records.id, issue_records.book_id, issue_records.member_id,
               issue_records.issue_date, issue_records.due_date,
               issue_records.return_date, books.title, books.category_id,
               categories.name AS category_name
        FROM issue_records JOIN books ON books.id = issue_records.book_id
        JOIN categories ON categories.id = books.category_id
        ORDER BY issue_records.issue_date, issue_records.id
        """
    ).fetchall()
    categories = database.execute(
        "SELECT id, name FROM categories ORDER BY name"
    ).fetchall()

    demand = _predict_category_demand(issue_rows, categories)
    lateness = _predict_late_returns(issue_rows)
    return {"demand": demand, "lateness": lateness}


def _predict_category_demand(issue_rows, categories) -> dict:
    if not issue_rows or not categories:
        return {
            "forecasts": [],
            "mae": None,
            "within_two_accuracy": None,
            "explanation": "Add borrowing history across several months before forecasting demand.",
        }

    frame = pd.DataFrame(
        [
            {
                "category_id": row["category_id"],
                "category": row["category_name"],
                "month": date.fromisoformat(row["issue_date"]).replace(day=1),
            }
            for row in issue_rows
        ]
    )
    current_month = date.today().replace(day=1)
    first_month = (pd.Timestamp(current_month) - pd.DateOffset(months=11)).date()
    month_starts = [
        (pd.Timestamp(first_month) + pd.DateOffset(months=index)).date()
        for index in range(12)
    ]
    monthly = frame.groupby(["category_id", "category", "month"]).size()
    rows = []
    for category in categories:
        previous_count = 0
        for month_index, month in enumerate(month_starts):
            count = int(monthly.get((category["id"], category["name"], month), 0))
            rows.append(
                {
                    "category_id": category["id"],
                    "month_index": month_index,
                    "previous_count": previous_count,
                    "issue_count": count,
                    "category": category["name"],
                }
            )
            previous_count = count

    training = pd.DataFrame(rows)
    train_rows = training[training["month_index"] < 9]
    test_rows = training[training["month_index"] >= 9]
    if train_rows.empty or test_rows.empty:
        return {
            "forecasts": [],
            "mae": None,
            "within_two_accuracy": None,
            "explanation": "At least nine months of borrowing history are needed to evaluate demand forecasts.",
        }

    feature_names = ["category_id", "month_index", "previous_count"]
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(train_rows[feature_names], train_rows["issue_count"])
    test_predictions = model.predict(test_rows[feature_names])
    mae = float(mean_absolute_error(test_rows["issue_count"], test_predictions))
    within_two = float(
        (abs(test_rows["issue_count"].to_numpy() - test_predictions) <= 2).mean() * 100
    )

    forecasts = []
    for category in categories:
        category_history = training[training["category_id"] == category["id"]]
        previous_count = int(category_history.iloc[-1]["issue_count"])
        estimate = float(
            model.predict(
                pd.DataFrame(
                    [
                        {
                            "category_id": category["id"],
                            "month_index": 12,
                            "previous_count": previous_count,
                        }
                    ]
                )[feature_names]
            )[0]
        )
        forecasts.append(
            {"category": category["name"], "expected_issues": max(0, round(estimate))}
        )

    return {
        "forecasts": forecasts,
        "mae": round(mae, 2),
        "within_two_accuracy": round(within_two, 1),
        "explanation": (
            "A random-forest regression model looks at category, month, and the "
            "previous month's issue count. It estimates next month's borrowing. "
            "The holdout score is the share of predictions within two issues of "
            "the actual count; MAE is the average absolute error in issues."
        ),
    }


def _late_features(issue_rows):
    completed_loans: dict[int, list[tuple[date, int]]] = defaultdict(list)
    training_rows = []
    open_rows = []
    for row in issue_rows:
        issue_date = date.fromisoformat(row["issue_date"])
        known_history = [
            late
            for return_date, late in completed_loans[row["member_id"]]
            if return_date < issue_date
        ]
        count = len(known_history)
        feature = {
            "category_id": row["category_id"],
            "issue_month": issue_date.year * 12 + issue_date.month,
            "issue_weekday": issue_date.weekday(),
            "prior_loans": count,
            "prior_late_rate": sum(known_history) / count if count else 0.0,
        }
        if row["return_date"] is None:
            open_rows.append((row, feature))
        else:
            late = date.fromisoformat(row["return_date"]) > date.fromisoformat(
                row["due_date"]
            )
            training_rows.append((feature, int(late)))
            completed_loans[row["member_id"]].append(
                (date.fromisoformat(row["return_date"]), int(late))
            )
    return training_rows, open_rows


def _predict_late_returns(issue_rows) -> dict:
    training_rows, open_rows = _late_features(issue_rows)
    labels = [label for _, label in training_rows]
    if len(training_rows) < 20 or len(set(labels)) < 2:
        return {
            "accuracy": None,
            "predictions": [],
            "explanation": (
                "The late-return model needs at least 20 returned loans and examples "
                "of both on-time and late returns. It does not make predictions until "
                "that history is available."
            ),
        }

    # Use the most recent quarter as a simple chronological holdout.
    split_at = max(1, int(len(training_rows) * 0.75))
    train_data = training_rows[:split_at]
    test_data = training_rows[split_at:]
    if not test_data or len({label for _, label in train_data}) < 2:
        return {
            "accuracy": None,
            "predictions": [],
            "explanation": "More varied returned-loan history is needed to evaluate this model.",
        }

    model = RandomForestClassifier(
        n_estimators=100, class_weight="balanced", random_state=42
    )
    model.fit(
        pd.DataFrame([features for features, _ in train_data])[LATE_FEATURES],
        [label for _, label in train_data],
    )
    accuracy = float(
        accuracy_score(
            [label for _, label in test_data],
            model.predict(
                pd.DataFrame([features for features, _ in test_data])[LATE_FEATURES]
            ),
        )
    )
    predictions = []
    for row, features in open_rows:
        probability = model.predict_proba(
            pd.DataFrame([features])[LATE_FEATURES]
        )[0]
        late_class = list(model.classes_).index(1)
        risk = float(probability[late_class])
        predictions.append(
            {
                "book": row["title"],
                "issue_id": row["id"],
                "risk": round(risk * 100),
                "label": "Higher risk" if risk >= 0.5 else "Lower risk",
            }
        )
    return {
        "accuracy": round(accuracy * 100, 1),
        "predictions": predictions,
        "explanation": (
            "A random-forest classifier learns from past returned loans. It uses "
            "the book category, issue month and weekday, and the member's earlier "
            "borrowing and late-return history. Accuracy is measured on the newest "
            "quarter of returned loans, which was held aside during training. This "
            "is a planning aid, not a guarantee about an individual borrower."
        ),
    }
