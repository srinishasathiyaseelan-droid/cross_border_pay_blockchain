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


# ----------------- AI operations page (P5) -----------------
@bp.route("/admin/ai", methods=["GET", "POST"])
@admin_required
def ai_ops():
    from datetime import datetime, timezone

    from flask import current_app, render_template

    from ..ai import budget
    from ..ai import log as ailog

    conn = get_db()
    if request.method == "POST":
        on = request.form.get("kill_switch") == "on"
        budget.set_kill_switch(conn, on)
        flash("AI kill switch is ON: every AI call is off." if on else "AI kill switch is OFF.", "info")
        return redirect(url_for("admin.ai_ops"))
    ailog.purge(conn, int(current_app.config["LLM_LOG_RETENTION_DAYS"]))
    day = datetime.now(timezone.utc).date().isoformat() + "T00:00:00Z"
    by_status = conn.execute("SELECT task, status, COUNT(*) FROM llm_calls WHERE created_at >= ? GROUP BY task, status "
                             "ORDER BY task, status", (day,)).fetchall()
    by_guard = conn.execute("SELECT guard_outcome, COUNT(*) FROM llm_calls WHERE guard_outcome IS NOT NULL AND "
                            "guard_outcome != 'OK' GROUP BY guard_outcome ORDER BY COUNT(*) DESC").fetchall()
    agreement = conn.execute(
        "SELECT u.name, COUNT(r.id), ROUND(AVG(r.ai_agreement), 3) FROM hold_reviews r JOIN users u ON u.id = r.admin_id "
        "WHERE r.ai_agreement IS NOT NULL GROUP BY u.name").fetchall()
    kill = conn.execute("SELECT value FROM ai_settings WHERE key = 'kill_switch'").fetchone()
    return render_template(
        "admin_ai.html",
        llm_enabled=current_app.config.get("LLM_ENABLED"), kill_switch=bool(kill and kill[0] == "1"),
        providers=current_app.extensions["ai_router"].circuit_state(),
        calls_today=sum(r[2] for r in by_status), by_status=[tuple(r) for r in by_status],
        by_guard=[tuple(r) for r in by_guard], agreement=[tuple(r) for r in agreement],
        spend=round(ailog.spend_today(conn), 4), budget=current_app.config.get("LLM_DAILY_BUDGET_USD"),
        flags=current_app.config.get("AI_FLAGS", {}),
    )
