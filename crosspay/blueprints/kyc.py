"""KYC submission. P1: login required, government ID encrypted at rest and masked in the UI (L6)."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..db import get_db, utcnow_iso
from ..security.decorators import login_required
from ..security.pii import decrypt_value, encrypt_value, mask

bp = Blueprint("kyc", __name__)


def kyc_view_model(row):
    if not row:
        return None
    d = dict(row)
    d["government_id_masked"] = mask(decrypt_value(d.get("government_id")))
    d.pop("government_id", None)
    return d


@bp.route("/kyc", methods=["GET", "POST"])
@login_required
def kyc():
    conn = get_db()
    user_id = session["user_id"]
    user = conn.execute("SELECT id, name, email, role FROM users WHERE id = ?", (user_id,)).fetchone()
    kyc_record = conn.execute("SELECT * FROM kyc WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()

    if request.method == "POST":
        business_name = request.form.get("business_name", "").strip()
        country = request.form.get("country", "").strip()
        business_type = request.form.get("business_type", "").strip()
        government_id = request.form.get("government_id", "").strip()
        address = request.form.get("address", "").strip()
        simulate_action = request.form.get("simulate_action", "auto_validate")
        if not government_id and kyc_record:  # blank = keep the stored (encrypted) value
            government_id = decrypt_value(kyc_record["government_id"])
            if government_id in ("NOT_PROVIDED", "[unreadable]"):
                government_id = ""

        if simulate_action == "reject":
            status, notes, verified_at = "REJECTED", "Simulated Compliance Rejection.", None
        elif simulate_action == "pending":
            status, notes, verified_at = "PENDING", "Manual compliance review pending.", None
        elif business_name and country and government_id and len(government_id) >= 6 and address:
            status, notes, verified_at = "VERIFIED", f"Autonomous Verification Passed ({country}).", utcnow_iso()
        else:
            status, notes, verified_at = "REJECTED", "Verification Failed: Incomplete credentials.", None

        enc_id = encrypt_value(government_id) if government_id else "NOT_PROVIDED"
        if kyc_record:
            conn.execute(
                """UPDATE kyc SET business_name = ?, country = ?, business_type = ?, government_id = ?,
                       address = ?, status = ?, verification_notes = ?, verified_at = ? WHERE id = ?""",
                (business_name, country, business_type, enc_id, address, status, notes, verified_at,
                 kyc_record["id"]),
            )
        else:
            conn.execute(
                """INSERT INTO kyc (user_id, business_name, country, business_type, government_id, address, status,
                       verification_notes, submitted_at, verified_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, business_name, country, business_type, enc_id, address, status, notes,
                 utcnow_iso(), verified_at),
            )

        if status == "VERIFIED":
            flash("KYC Verification Successful! You are now authorized to initiate cross-border payments.", "success")
        elif status == "PENDING":
            flash("KYC Status: PENDING. Verification documents are under review.", "warning")
        else:
            flash("KYC Status: REJECTED. Please review the submitted details and retry.", "danger")
        return redirect(url_for("kyc.kyc"))

    return render_template("kyc.html", kyc=kyc_view_model(kyc_record), user=user)
