"""KYC submission. P1: login required, government ID encrypted at rest and masked in the UI (L6)."""
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

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
        simulate_action = request.form.get("simulate_action", "")
        if not government_id and kyc_record:  # blank = keep the stored (encrypted) value
            government_id = decrypt_value(kyc_record["government_id"])
            if government_id in ("NOT_PROVIDED", "[unreadable]"):
                government_id = ""

        complete = bool(business_name and country and address and len(government_id) >= 6)
        demo = current_app.config.get("DEMO_MODE")
        verified_at = None
        if not complete:
            status, notes = "REJECTED", "Incomplete submission: business name, country, address and ID are required."
        elif demo and simulate_action == "demo_verify":
            # DEMO_MODE only: stands in for a KYC provider called on the server. Clearly labelled, never in prod.
            status, notes, verified_at = "VERIFIED", "DEMO SIMULATION: simulated registry check passed.", utcnow_iso()
        elif demo and simulate_action == "demo_reject":
            status, notes = "REJECTED", "DEMO SIMULATION: simulated registry check failed."
        else:
            # C5: a submission never verifies itself. A compliance officer decides in /admin/kyc.
            status, notes = "PENDING", "Submitted. Awaiting compliance review."

        enc_id = encrypt_value(government_id) if government_id else "NOT_PROVIDED"
        if kyc_record:
            conn.execute(
                """UPDATE kyc SET business_name = ?, country = ?, business_type = ?, government_id = ?,
                       address = ?, status = ?, verification_notes = ?, verified_at = ?, submitted_at = ?,
                       reviewed_by = NULL, review_reason = NULL, reviewed_at = NULL WHERE id = ?""",
                (business_name[:120], country, business_type[:80], enc_id, address[:200], status, notes,
                 verified_at, utcnow_iso(), kyc_record["id"]),
            )
        else:
            conn.execute(
                """INSERT INTO kyc (user_id, business_name, country, business_type, government_id, address, status,
                       verification_notes, submitted_at, verified_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, business_name, country, business_type, enc_id, address, status, notes,
                 utcnow_iso(), verified_at),
            )

        if status == "VERIFIED":
            flash("KYC verified (demo simulation). You can now submit payments.", "success")
        elif status == "PENDING":
            flash("KYC submitted. A compliance officer will review it before you can send payments.", "info")
        else:
            flash("KYC Status: REJECTED. Please review the submitted details and retry.", "danger")
        return redirect(url_for("kyc.kyc"))

    return render_template("kyc.html", kyc=kyc_view_model(kyc_record), user=user)
