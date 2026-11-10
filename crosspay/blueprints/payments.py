"""Payments: form, processing pipeline, receipt, history, dashboard, ledger explorer.

P0: behaviour moved unchanged from app.py (findings C4, H1, H2, H3 are fixed in later phases).
"""
import json

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for

from ..db import get_db, utcnow_iso
from ..security.decorators import current_user_row, login_required
from ..security.idempotency import new_key
from ..services.settlement import DuplicateSubmission, settle_payment
from ..services.features import (
    ALLOWED_COUNTRIES,
    DEMO_VECTORS,
    FeatureError,
    apply_demo_vector,
    build_features,
)
from ..services.currency import (
    COUNTRY_TO_DEFAULT_CURRENCY,
    SUPPORTED_CURRENCIES,
    ExchangeRateAPIError,
    InvalidAmountError,
    UnsupportedCurrencyError,
)

bp = Blueprint("payments", __name__)

def tenant_scope():
    """H3: SMEs only ever see their own rows; compliance admins see everything."""
    row = current_user_row()
    if row["role"] == "admin":
        return "", []
    return " AND user_id = ?", [row["id"]]


def get_visible_tx(tx_id):
    where, params = tenant_scope()
    tx = get_db().execute(f"SELECT * FROM transactions WHERE transaction_id = ?{where}", [tx_id, *params]).fetchone()
    if tx is None:
        abort(404)  # another tenant's receipt is indistinguishable from a missing one
    return tx


class PaymentInputError(ValueError):
    pass


def read_payment_form(form, kyc_record):
    """L1: validate the parts of the form the sender legitimately controls."""
    receiver = (form.get("receiver") or "").strip()
    if not 2 <= len(receiver) <= 120:
        raise PaymentInputError("Receiver name is required (2-120 characters).")
    sender_country = (form.get("sender_country") or kyc_record["country"]).strip()
    receiver_country = (form.get("receiver_country") or "").strip()
    for c in (sender_country, receiver_country):
        if c not in ALLOWED_COUNTRIES:
            raise PaymentInputError("Choose sender and receiver countries from the supported list.")
    notes = (form.get("notes") or "").strip()[:500]
    return {
        "sender": kyc_record["business_name"],
        "receiver": receiver,
        "sender_country": sender_country,
        "receiver_country": receiver_country,
        "sender_currency": (form.get("sender_currency") or "USD").strip().upper(),
        "receiver_currency": (form.get("receiver_currency") or "USD").strip().upper(),
        "amount": (form.get("amount") or "").strip(),
        "notes": notes,
        "scenario": (form.get("scenario") or "").strip().lower(),
    }


def assess(conn, user_id, data, conversion):
    """Feature building + scoring shared by the payment route and /api/risk_preview (M5)."""
    features = build_features(conn, user_id, conversion["normalized_usd_amount"], data["sender_country"],
                              data["receiver_country"])
    source = "db"
    if current_app.config.get("DEMO_MODE") and data.get("scenario") in DEMO_VECTORS:
        features = apply_demo_vector(features, data["scenario"])
        source = "demo_vector"
    scored = current_app.extensions["scorer"].score(features)
    return features, scored, source


@bp.route("/payment")
@login_required
def payment():
    kyc_record = get_db().execute(
        "SELECT * FROM kyc WHERE user_id = ? ORDER BY id DESC LIMIT 1", (session["user_id"],)
    ).fetchone()
    return render_template(
        "payment.html",
        kyc=dict(kyc_record) if kyc_record else None,
        is_verified=bool(kyc_record and kyc_record["status"] == "VERIFIED"),
        countries=ALLOWED_COUNTRIES,
        idempotency_key=new_key(),
        supported_currencies=SUPPORTED_CURRENCIES,
        country_currencies=COUNTRY_TO_DEFAULT_CURRENCY,
    )


@bp.route("/process_payment", methods=["POST"])
@login_required
def process_payment():
    user_id = session["user_id"]
    conn = get_db()
    kyc_record = conn.execute("SELECT * FROM kyc WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    if not kyc_record or kyc_record["status"] != "VERIFIED":
        flash("Access Denied: Only KYC-VERIFIED SMEs can submit cross-border settlements.", "danger")
        return redirect(url_for("kyc.kyc"))

    try:
        data = read_payment_form(request.form, kyc_record)
        conversion = current_app.extensions["currency"].convert(
            amount=data["amount"], source_currency=data["sender_currency"], target_currency=data["receiver_currency"]
        )
        features, scored, feature_source = assess(conn, user_id, data, conversion)
    except (PaymentInputError, FeatureError, InvalidAmountError, UnsupportedCurrencyError) as e:
        flash(f"Payment not submitted: {e}", "danger")
        return redirect(url_for("payments.payment"))
    except ExchangeRateAPIError as e:
        flash(f"Exchange rate service unavailable, nothing was stored: {e}", "danger")
        return redirect(url_for("payments.payment"))

    # P6.2 purpose tagger: advisory and escalate-only (G1). It never enters the model; its only effect on the
    # decision is the PURPOSE_RED_FLAG code, which the policy engine can use to move APPROVED to HOLD.
    from ..ai import tasks as ai_tasks

    corridor = f"{data['sender_country']} to {data['receiver_country']}"
    purpose = ai_tasks.classify_purpose(conn, data["notes"], corridor, conversion["normalized_usd_amount"], user_id)
    pres = purpose["result"] or {}
    extra = {
        "purpose_category": pres.get("category"), "purpose_risk": pres.get("purpose_risk"),
        "purpose_flags": json.dumps(pres.get("red_flags", [])) if pres else None,
        "ai_escalations": json.dumps(purpose["escalations"]), "input_guard_flags": json.dumps(purpose["input_flags"]),
    }
    try:
        outcome = settle_payment(
            conn, user_id=user_id, kyc_status=kyc_record["status"], data=data, conversion=conversion,
            features=features, scored=scored, feature_source=feature_source,
            idempotency_key=(request.form.get("idempotency_key") or "").strip()[:64] or None,
            ai_escalations=purpose["escalations"], extra_columns=extra,
        )
    except DuplicateSubmission as dup:
        flash("This form was already submitted; showing the original payment.", "info")
        if dup.tx_id == "IN_PROGRESS":
            return redirect(url_for("payments.transactions"))
        return redirect(url_for("payments.result", tx_id=dup.tx_id))

    jobs = current_app.extensions["ai_jobs"]
    if purpose["status"] == "UNAVAILABLE" and data["notes"]:  # timed out: retry for the record only
        jobs.submit(conn, "purpose", outcome["tx_id"], ai_tasks.purpose_retry_job(
            outcome["tx_id"], data["notes"], corridor, conversion["normalized_usd_amount"]))
    if current_app.config.get("LLM_ENABLED"):
        ai_tasks.queue_explanation(conn, outcome["tx_id"])  # P6.1, background
    return redirect(url_for("payments.result", tx_id=outcome["tx_id"]))


@bp.route("/result/<tx_id>")
@login_required
def result(tx_id):
    tx = dict(get_visible_tx(tx_id))
    tx["top_factors_list"] = json.loads(tx.get("top_factors") or "[]")
    tx["policy_reasons_list"] = json.loads(tx.get("policy_reasons") or "[]")
    reviews = get_db().execute(
        "SELECT r.*, u.name AS admin_name FROM hold_reviews r JOIN users u ON u.id = r.admin_id "
        "WHERE r.tx_id = ? ORDER BY r.id", (tx_id,)).fetchall()
    contract = current_app.extensions["contract"]
    return render_template(
        "result.html", tx=tx, reviews=[dict(r) for r in reviews], contract_address=contract.CONTRACT_ADDRESS,
        contract_label=contract.CONTRACT_LABEL, supported_currencies=SUPPORTED_CURRENCIES,
    )


@bp.route("/transactions")
@login_required
def transactions():
    status_filter = request.args.get("status", "ALL")
    search_query = request.args.get("q", "").strip()
    where, scope_params = tenant_scope()
    sql, params = "SELECT * FROM transactions WHERE 1=1" + where, list(scope_params)
    if status_filter in ["APPROVED", "HOLD", "BLOCKED", "REJECTED"]:  # L3
        sql += " AND decision = ?"
        params.append(status_filter)
    if search_query:
        sql += " AND (transaction_id LIKE ? OR sender LIKE ? OR receiver LIKE ?)"
        params.extend([f"%{search_query}%"] * 3)
    rows = get_db().execute(sql + " ORDER BY id DESC", params).fetchall()
    return render_template("transactions.html", transactions=[dict(r) for r in rows], status_filter=status_filter,
                           query=search_query)


@bp.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    where, params = tenant_scope()

    def count(cond="1=1"):
        return conn.execute(f"SELECT COUNT(*) FROM transactions WHERE {cond}{where}", params).fetchone()[0]

    stats = {
        "total_txs": count(),
        "approved_txs": count("decision = 'APPROVED'"),
        "held_txs": count("decision = 'HOLD'"),
        "blocked_txs": count("decision = 'BLOCKED'"),
        "rejected_txs": count("decision = 'REJECTED'"),
        "low_risk_count": count("risk_level = 'LOW'"),
        "med_risk_count": count("risk_level = 'MEDIUM'"),
        "high_risk_count": count("risk_level = 'HIGH'"),
        "verified_kyc_count": (conn.execute("SELECT COUNT(*) FROM kyc WHERE status = 'VERIFIED'").fetchone()[0]
                               if not where else None),
        "total_volume_approved": round(conn.execute(
            "SELECT COALESCE(SUM(COALESCE(normalized_usd_amount, amount)), 0) FROM transactions "
            f"WHERE decision = 'APPROVED'{where}", params).fetchone()[0], 2),
    }
    recent = conn.execute(f"SELECT * FROM transactions WHERE 1=1{where} ORDER BY id DESC LIMIT 6", params).fetchall()
    scorer = current_app.extensions["scorer"]
    return render_template("dashboard.html", stats=stats, recent_transactions=[dict(r) for r in recent],
                           metrics=current_app.extensions["metrics"], scoring_engine=scorer.engine,
                           fallback_reason=scorer.fallback_reason)


@bp.route("/blockchain")
@login_required
def blockchain_explorer():
    conn = get_db()
    ledger = current_app.extensions["ledger"]
    check = ledger.verify(conn)
    blocks = [b.to_dict() for b in ledger.blocks(conn)]
    where, params = tenant_scope()
    if where:  # SMEs see every block hash but transaction details only for their own payments
        own = {r[0] for r in conn.execute(f"SELECT transaction_id FROM transactions WHERE 1=1{where}", params)}
        for b in blocks:
            b["transactions"] = [
                t if (t.get("transaction_id") in own or b["index"] == 0)
                else {"transaction_id": "(another SME)", "sender": "—", "receiver": "—", "amount": 0.0,
                      "source_currency": "", "redacted": True}
                for t in b["transactions"]
            ]
    contract = current_app.extensions["contract"]
    return render_template(
        "blockchain.html", chain=blocks, is_valid=check["valid"], validation_msg=check["message"],
        audit_records=check["audit_records"], difficulty=ledger.difficulty,
        contract_address=contract.CONTRACT_ADDRESS, contract_label=contract.CONTRACT_LABEL,
    )
