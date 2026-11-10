"""Route guards (C1, C2, H3).

login_required  -> anonymous users are redirected to /login (302)
admin_required  -> anonymous: 302 to /login; logged-in non-admins: 403
demo_only       -> 404 unless DEMO_MODE is on
"""
from functools import wraps

from flask import abort, current_app, flash, redirect, request, session, url_for

from ..db import get_db


def current_user_row():
    uid = session.get("user_id")
    if not uid:
        return None
    return get_db().execute("SELECT id, name, email, role FROM users WHERE id = ?", (uid,)).fetchone()


def is_admin() -> bool:
    row = current_user_row()
    return bool(row and row["role"] == "admin")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user_row() is None:
            session.clear()
            if request.path.startswith("/api/"):
                return {"success": False, "error": "login required"}, 401
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        row = current_user_row()
        if row is None:
            session.clear()
            if request.path.startswith("/api/"):
                return {"success": False, "error": "login required"}, 401
            flash("Please sign in as a compliance officer.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if row["role"] != "admin":  # role is read from the DB, not trusted from the session cookie
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def demo_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_app.config.get("DEMO_MODE"):
            abort(404)
        return view(*args, **kwargs)

    return wrapped
