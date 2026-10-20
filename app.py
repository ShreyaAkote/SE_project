"""Start the Smart Library Management System web application."""

import os
import hmac
import secrets
from datetime import timedelta

from flask import Flask, abort, g, redirect, request, session, url_for

from database.db import get_db, init_db
from routes import admin, analytics, auth, catalog, circulation, main, reports


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure the Flask application."""
    instance_path = test_config.get("INSTANCE_PATH") if test_config else None
    app = Flask(
        __name__,
        instance_relative_config=True,
        instance_path=instance_path,
    )
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", secrets.token_hex(32)),
        DATABASE=os.path.join(app.instance_path, "library.db"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    init_db(app)

    @app.before_request
    def load_logged_in_user() -> None:
        user_id = session.get("user_id")
        g.user = None
        if user_id is not None:
            g.user = get_db().execute(
                "SELECT id, username, full_name, role, member_id "
                "FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if g.user is None:
                session.clear()

    @app.before_request
    def protect_form_submissions() -> None:
        if request.method == "POST":
            submitted = request.form.get("csrf_token", "")
            expected = session.get("_csrf_token", "")
            if not submitted or not expected or not hmac.compare_digest(
                submitted, expected
            ):
                abort(400, description="The form expired or was invalid. Please try again.")

    @app.context_processor
    def inject_user():
        return {"current_user": g.get("user")}

    @app.teardown_appcontext
    def close_db(_error: BaseException | None = None) -> None:
        database = g.pop("database", None)
        if database is not None:
            database.close()

    @app.get("/")
    def index():
        if g.get("user") is None:
            return redirect(url_for("auth.login"))
        if g.user["role"] == "student":
            return redirect(url_for("catalog.student_catalog"))
        if g.user["role"] == "administrator":
            return redirect(url_for("admin.users"))
        return redirect(url_for("main.dashboard"))

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(catalog)
    app.register_blueprint(circulation)
    app.register_blueprint(reports)
    app.register_blueprint(analytics)
    app.register_blueprint(admin)
    return app


app = create_app()


if __name__ == "__main__":
    app.run()
