"""Authentication: landing page, login, demo quick login, registration, logout."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import get_db, utcnow_iso

bp = Blueprint("auth", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


def _start_session(user) -> None:
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_role"] = user["role"]


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password"], password):
            _start_session(user)
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("payments.dashboard"))
        flash("Invalid email or password. Please try again.", "danger")
    return render_template("login.html")


@bp.route("/quick_login/<role>")
def quick_login(role):
    conn = get_db()
    wanted = "sme" if role == "sme" else "admin"
    user = conn.execute("SELECT * FROM users WHERE role = ? ORDER BY id LIMIT 1", (wanted,)).fetchone()
    if user:
        _start_session(user)
        flash(f"Quick Demo Access granted as {user['name']}.", "info")
    return redirect(url_for("payments.dashboard"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        business_type = request.form.get("business_type", "SME Trader")
        country = request.form.get("country", "United States")

        if not name or not email or not password:
            flash("All fields are required.", "warning")
            return redirect(url_for("auth.register"))

        conn = get_db()
        if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            flash("An account with this email already exists.", "danger")
            return redirect(url_for("auth.register"))

        now = utcnow_iso()
        cur = conn.execute(
            "INSERT INTO users (name, email, password, role, created_at) VALUES (?, ?, ?, 'sme', ?)",
            (name, email, generate_password_hash(password), now),
        )
        user_id = cur.lastrowid
        conn.execute(
            """INSERT INTO kyc (user_id, business_name, country, business_type, government_id, address, status,
                   submitted_at)
               VALUES (?, ?, ?, ?, 'NOT_PROVIDED', 'Pending SME submission', 'PENDING', ?)""",
            (user_id, name, country, business_type, now),
        )
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        _start_session(user)
        flash("Registration successful! Please complete your KYC verification to initiate payments.", "success")
        return redirect(url_for("kyc.kyc"))

    return render_template("register.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("auth.login"))
