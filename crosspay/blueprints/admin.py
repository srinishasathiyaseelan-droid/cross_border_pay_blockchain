"""Compliance administration. Every route here requires an admin account (C1)."""
from flask import Blueprint, flash, redirect, request, url_for

from ..db import get_db
from ..security.decorators import admin_required

bp = Blueprint("admin", __name__)


MIN_REASON_LEN = 20


@bp.route("/resolve_hold/<tx_id>", methods=["POST"])
@admin_required
def resolve_hold(tx_id):
    from flask import session

    from ..services.settlement import SettlementError, resolve_hold as do_resolve

    action = request.form.get("action", "")
    reason = (request.form.get("reason") or "").strip()
    back = request.form.get("next") or url_for("payments.result", tx_id=tx_id)
    if not back.startswith("/") or back.startswith("//"):
        back = url_for("payments.result", tx_id=tx_id)
    if action not in ("approve", "reject"):
        flash("Choose Approve or Reject.", "warning")
        return redirect(back)
    if len(reason) < MIN_REASON_LEN:  # M9: every officer decision carries a reason
        flash(f"Write a reason of at least {MIN_REASON_LEN} characters in your own words.", "warning")
        return redirect(back)
    try:
        out = do_resolve(get_db(), tx_id=tx_id, admin_id=session["user_id"], action=action, reason=reason[:2000])
    except SettlementError as e:
        flash(str(e), "warning")
        return redirect(back)
    if out["decision"] == "APPROVED":
        flash(f"{tx_id} released after compliance review and recorded in block #{out['block']}.", "success")
    else:
        flash(f"{tx_id} rejected by compliance. Nothing was recorded on the ledger.", "info")
    return redirect(back)


# ----------------- KYC review queue (C5) -----------------
@bp.route("/admin/kyc")
@admin_required
def kyc_queue():
    from flask import render_template

    from ..security.pii import decrypt_value

    conn = get_db()
    rows = conn.execute(
        """SELECT k.*, u.email, u.name AS user_name FROM kyc k JOIN users u ON u.id = k.user_id
           WHERE k.id IN (SELECT MAX(id) FROM kyc GROUP BY user_id)
           ORDER BY CASE k.status WHEN 'PENDING' THEN 0 ELSE 1 END, k.submitted_at DESC"""
    ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["government_id_plain"] = decrypt_value(d.pop("government_id"))  # officers need the full ID to verify
        items.append(d)
    return render_template("admin_kyc.html", items=items)


@bp.route("/admin/kyc/<int:kyc_id>", methods=["POST"])
@admin_required
def kyc_decide(kyc_id):
    from flask import session

    from ..db import utcnow_iso

    action = request.form.get("action")
    reason = (request.form.get("reason") or "").strip()
    if action not in ("approve", "reject"):
        flash("Unknown action.", "warning")
        return redirect(url_for("admin.kyc_queue"))
    if len(reason) < 10:
        flash("Give a reason of at least 10 characters.", "warning")
        return redirect(url_for("admin.kyc_queue"))
    conn = get_db()
    row = conn.execute("SELECT id, status FROM kyc WHERE id = ?", (kyc_id,)).fetchone()
    if row is None:
        flash("KYC record not found.", "warning")
        return redirect(url_for("admin.kyc_queue"))
    now = utcnow_iso()
    status = "VERIFIED" if action == "approve" else "REJECTED"
    conn.execute(
        """UPDATE kyc SET status = ?, verification_notes = ?, verified_at = ?, reviewed_by = ?, review_reason = ?,
               reviewed_at = ? WHERE id = ?""",
        (status, f"Compliance review: {reason[:300]}", now if status == "VERIFIED" else None, session["user_id"],
         reason[:500], now, kyc_id),
    )
    flash(f"KYC #{kyc_id} set to {status}.", "success" if status == "VERIFIED" else "info")
    return redirect(url_for("admin.kyc_queue"))
