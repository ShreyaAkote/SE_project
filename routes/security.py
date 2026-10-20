"""Authentication and role-checking helpers."""

from functools import wraps

from flask import flash, g, redirect, url_for


def role_required(*roles: str):
    """Restrict a route to signed-in users with one of the given roles."""
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.get("user") is None:
                flash("Please sign in to continue.", "warning")
                return redirect(url_for("auth.login"))
            if g.user["role"] not in roles:
                flash("You do not have permission to open that page.", "danger")
                return redirect(url_for("index"))
            return view(*args, **kwargs)

        return wrapped

    return decorate
