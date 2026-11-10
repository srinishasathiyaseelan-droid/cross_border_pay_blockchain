"""KYC submission (P0: behaviour moved unchanged from app.py)."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..db import get_db, utcnow_iso

bp = Blueprint("kyc", __name__)


@bp.route("/kyc", methods=["GET", "POST"])
def kyc():
    if "user_id" not in session:
        flash("Please log in to view or complete KYC verification.", "warning")
        return redirect(url_for("auth.login"))

    conn = get_db()
    user_id = session["user_id"]
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    kyc_record = conn.execute("SELECT * FROM kyc WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()

    if request.method == "POST":
        business_name = request.form.get("business_name", "").strip()
        country = request.form.get("country", "").strip()
        business_type = request.form.get("business_type", "").strip()
        government_id = request.form.get("government_id", "").strip()
        address = request.form.get("address", "").strip()
        simulate_action = request.form.get("simulate_action", "auto_validate")

        if simulate_action == "reject":
            status, notes, verified_at = "REJECTED", "Simulated Compliance Rejection.", None
        elif simulate_action == "pending":
            status, notes, verified_at = "PENDING", "Manual compliance review pending.", None
        elif business_name and country and government_id and len(government_id) >= 6 and address:
            status, notes, verified_at = "VERIFIED", f"Autonomous Verification Passed ({country}).", utcnow_iso()
        else:
            status, notes, verified_at = "REJECTED", "Verification Failed: Incomplete credentials.", None

        if kyc_record:
            conn.execute(
                """UPDATE kyc SET business_name = ?, country = ?, business_type = ?, government_id = ?,
                       address = ?, status = ?, verification_notes = ?, verified_at = ? WHERE id = ?""",
                (business_name, country, business_type, government_id, address, status, notes, verified_at,
                 kyc_record["id"]),
            )
        else:
            conn.execute(
                """INSERT INTO kyc (user_id, business_name, country, business_type, government_id, address, status,
                       verification_notes, submitted_at, verified_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, business_name, country, business_type, government_id, address, status, notes,
                 utcnow_iso(), verified_at),
            )

        if status == "VERIFIED":
            flash("KYC Verification Successful! You are now authorized to initiate cross-border payments.", "success")
        elif status == "PENDING":
            flash("KYC Status: PENDING. Verification documents are under review.", "warning")
        else:
            flash("KYC Status: REJECTED. Please review the submitted details and retry.", "danger")
        return redirect(url_for("kyc.kyc"))

    return render_template("kyc.html", kyc=dict(kyc_record) if kyc_record else None, user=user)
