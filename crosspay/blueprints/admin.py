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


# ----------------- Live operations console -----------------
@bp.route("/admin/live")
@admin_required
def live_console():
    """Officer console: KPIs, the HOLD queue (with the stored AI one-liner, advisory) and the live event table."""
    import json

    from flask import current_app, render_template

    from ..realtime import REASON_LABELS

    rows = get_db().execute(
        """SELECT t.transaction_id, t.normalized_usd_amount, t.amount, t.source_currency, t.currency, t.sender_country,
                  t.receiver_country, t.risk_score, t.risk_level, t.policy_reasons, t.timestamp, e.output_json
           FROM transactions t LEFT JOIN risk_explanations e ON e.tx_id = t.transaction_id
           WHERE t.decision = 'HOLD' ORDER BY t.id DESC LIMIT 25""").fetchall()
    queue = []
    for r in rows:
        reasons = json.loads(r["policy_reasons"] or "[]")
        try:
            summary = json.loads(r["output_json"]).get("summary") if r["output_json"] else None
        except (TypeError, ValueError):
            summary = None
        queue.append({**dict(r), "why": REASON_LABELS.get(reasons[-1], reasons[-1]) if reasons else "On hold",
                      "ai_summary": summary})
    return render_template("admin_live.html", queue=queue, demo=bool(current_app.config.get("DEMO_MODE")))


# ----------------- AI operations page (P5) -----------------
@bp.route("/admin/ai", methods=["GET", "POST"])
@admin_required
def ai_ops():
    from datetime import datetime, timezone

    from flask import current_app, render_template

    from ..ai import budget
    from ..ai import log as ailog

    conn = get_db()
    selftest = None
    if request.method == "POST" and request.form.get("action") == "selftest":
        from flask import session

        from ..ai import tasks as ai_tasks

        selftest = ai_tasks.self_test(conn, session["user_id"])
    elif request.method == "POST":
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
        flags=current_app.config.get("AI_FLAGS", {}), selftest=selftest,
    )


# ----------------- P6.3 HOLD review with AI copilot -----------------
@bp.route("/admin/review/<tx_id>", methods=["GET", "POST"])
@admin_required
def review(tx_id):
    import json

    from flask import current_app, render_template, session

    from ..ai import tasks as ai_tasks
    from ..ai.budget import ai_enabled
    from ..db import utcnow_iso
    from ..services.settlement import SettlementError, resolve_hold as do_resolve

    conn = get_db()
    row = conn.execute("SELECT * FROM transactions WHERE transaction_id = ?", (tx_id,)).fetchone()
    if row is None:
        from flask import abort

        abort(404)
    tx = dict(row)
    draft_row = conn.execute("SELECT result_json FROM ai_jobs WHERE task = 'copilot' AND tx_id = ? AND status = 'DONE'",
                             (tx_id,)).fetchone()
    copilot = json.loads(draft_row[0]) if draft_row and draft_row[0] else None

    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "generate":  # explicit officer request; the panel never auto-selects a decision
            res = ai_tasks.copilot(conn, tx, session["user_id"])
            now = utcnow_iso()
            conn.execute("INSERT INTO ai_jobs (task, tx_id, status, result_json, error_code, created_at, updated_at) "
                         "VALUES ('copilot', ?, ?, ?, ?, ?, ?) ON CONFLICT(task, tx_id) DO UPDATE SET status = "
                         "excluded.status, result_json = excluded.result_json, error_code = excluded.error_code, "
                         "updated_at = excluded.updated_at",
                         (tx_id, "DONE" if res.ok else "FAILED", json.dumps(res.data) if res.ok else None,
                          None if res.ok else res.status, now, now))
            if not res.ok:
                flash(f"The copilot could not produce a safe draft ({res.status}). Review the facts directly.", "warning")
            return redirect(url_for("admin.review", tx_id=tx_id))
        if action not in ("approve", "reject"):
            flash("Choose Release or Reject.", "warning")
            return redirect(url_for("admin.review", tx_id=tx_id))
        reason = (request.form.get("reason") or "").strip()
        memo = (request.form.get("memo") or "").strip()[:4000]
        ai_draft = copilot.get("draft_memo") if copilot else None
        problem = ai_tasks.officer_reason_problem(reason, ai_draft)  # G3: own words, >= 20 chars, < 80% similar
        if problem:
            flash(problem, "warning")
            return redirect(url_for("admin.review", tx_id=tx_id))
        try:
            out = do_resolve(conn, tx_id=tx_id, admin_id=session["user_id"], action=action, reason=reason[:2000],
                             copilot_memo=memo or None, ai_draft=ai_draft,
                             ai_agreement=ai_tasks.ai_agreement(memo or reason, ai_draft))
        except SettlementError as e:
            flash(str(e), "warning")
            return redirect(url_for("admin.review", tx_id=tx_id))
        flash(f"{tx_id}: {'released and recorded in block #' + str(out['block']) if out['decision'] == 'APPROVED' else 'rejected'}.",
              "success" if out["decision"] == "APPROVED" else "info")
        return redirect(url_for("payments.result", tx_id=tx_id))

    from ..ai import evidence as ev

    hist = conn.execute("SELECT transaction_id, timestamp, receiver_country, normalized_usd_amount, risk_level, decision "
                        "FROM transactions WHERE user_id = ? AND transaction_id != ? ORDER BY id DESC LIMIT 8",
                        (tx["user_id"], tx_id)).fetchall()
    kyc = conn.execute("SELECT status, country, business_name FROM kyc WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                       (tx["user_id"],)).fetchone()
    reviews = conn.execute("SELECT r.*, u.name AS admin_name FROM hold_reviews r JOIN users u ON u.id = r.admin_id "
                           "WHERE r.tx_id = ? ORDER BY r.id", (tx_id,)).fetchall()
    tx["top_factors_list"] = json.loads(tx.get("top_factors") or "[]")
    tx["policy_reasons_list"] = json.loads(tx.get("policy_reasons") or "[]")
    return render_template("admin_review.html", tx=tx, history=[dict(h) for h in hist], kyc=dict(kyc) if kyc else None,
                           reviews=[dict(r) for r in reviews], copilot=copilot, evidence=ev.build(conn, tx),
                           ai_on=ai_enabled(conn) and current_app.config["AI_FLAGS"].get("AI_COPILOT", True),
                           input_flags=json.loads(tx.get("input_guard_flags") or "[]"))


# ----------------- P6.7 compliance report drafts -----------------
@bp.route("/admin/reports", methods=["GET", "POST"])
@admin_required
def reports():
    import json

    from flask import current_app, render_template, session

    from ..ai import tasks as ai_tasks
    from ..ai.budget import ai_enabled
    from ..db import utcnow_iso

    conn = get_db()
    if request.method == "POST":
        kind = request.form.get("kind")
        if kind == "sign":
            rid = request.form.get("report_id", type=int)
            conn.execute("UPDATE report_drafts SET status = 'SIGNED', signed_by = ?, signed_at = ? WHERE id = ? AND "
                         "status = 'DRAFT'", (session["user_id"], utcnow_iso(), rid))
            flash("Report signed off. It is no longer a draft.", "success")
            return redirect(url_for("admin.reports"))
        if kind == "weekly":
            res, tx_id = ai_tasks.weekly_report(conn, session["user_id"]), None
        elif kind == "sar":
            tx_id = request.form.get("tx_id", "")
            row = conn.execute("SELECT * FROM transactions WHERE transaction_id = ? AND decision = 'BLOCKED'",
                               (tx_id,)).fetchone()
            if row is None:
                flash("Choose a BLOCKED transaction.", "warning")
                return redirect(url_for("admin.reports"))
            res = ai_tasks.sar_draft(conn, dict(row), session["user_id"])
        else:
            flash("Unknown report type.", "warning")
            return redirect(url_for("admin.reports"))
        if not res.ok:
            flash(f"No draft produced ({res.status}). Nothing unverified is shown.", "warning")
            return redirect(url_for("admin.reports"))
        conn.execute("INSERT INTO report_drafts (kind, tx_id, title, body, key_points, status, created_by, created_at) "
                     "VALUES (?, ?, ?, ?, ?, 'DRAFT', ?, ?)", (kind, tx_id, res.data["title"], res.data["body"],
                                                                json.dumps(res.data["key_points"]), session["user_id"],
                                                                utcnow_iso()))
        flash("Draft created. Review every sentence before signing.", "info")
        return redirect(url_for("admin.reports"))
    drafts = conn.execute("SELECT d.*, u.name AS signer FROM report_drafts d LEFT JOIN users u ON u.id = d.signed_by "
                          "ORDER BY d.id DESC LIMIT 20").fetchall()
    blocked = conn.execute("SELECT transaction_id, receiver, receiver_country, normalized_usd_amount FROM transactions "
                           "WHERE decision = 'BLOCKED' ORDER BY id DESC LIMIT 30").fetchall()
    items = []
    for d in drafts:
        x = dict(d)
        x["key_points_list"] = json.loads(x.get("key_points") or "[]")
        items.append(x)
    return render_template("admin_reports.html", drafts=items, blocked=[dict(b) for b in blocked],
                           ai_on=ai_enabled(conn) and current_app.config["AI_FLAGS"].get("AI_REPORTS", True))


@bp.route("/admin/reports/<int:report_id>.md")
@admin_required
def report_markdown(report_id):
    import json

    from flask import Response

    r = get_db().execute("SELECT * FROM report_drafts WHERE id = ?", (report_id,)).fetchone()
    if r is None:
        from flask import abort

        abort(404)
    status = "SIGNED" if r["status"] == "SIGNED" else "DRAFT - not reviewed"
    md = (f"# {r['title']}\n\n**Status:** {status}  \n**Generated:** {r['created_at']} (AI-generated, advisory)\n\n"
          f"{r['body']}\n\n" + "\n".join(f"- {p}" for p in json.loads(r["key_points"] or "[]")) + "\n")
    return Response(md, mimetype="text/markdown",
                    headers={"Content-Disposition": f"attachment; filename=crosspay-report-{report_id}.md"})
