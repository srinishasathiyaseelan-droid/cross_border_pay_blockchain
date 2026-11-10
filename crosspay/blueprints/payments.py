"""Payments: form, processing pipeline, receipt, history, dashboard, ledger explorer.

P0: behaviour moved unchanged from app.py (findings C4, H1, H2, H3 are fixed in later phases).
"""
import json
import random

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for

from ..db import get_db, utcnow_iso
from ..security.decorators import current_user_row, login_required
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

    sender, receiver, notes = data["sender"], data["receiver"], data["notes"]
    sender_country, receiver_country = data["sender_country"], data["receiver_country"]
    normalized_usd = conversion["normalized_usd_amount"]
    risk_level, risk_score = scored["level"], scored["score"]

    tx_id = f"TX-2026-{random.randint(1000, 9999)}"
    tx_data = {
        "transaction_id": tx_id, "sender": sender, "receiver": receiver, "sender_country": sender_country,
        "receiver_country": receiver_country, "amount": conversion["original_amount"],
        "currency": conversion["source_currency"], "source_currency": conversion["source_currency"],
        "target_currency": conversion["target_currency"], "exchange_rate": conversion["exchange_rate"],
        "converted_amount": conversion["converted_amount"], "exchange_rate_provider": conversion["provider"],
        "rate_timestamp": conversion["last_updated"], "normalized_usd_amount": normalized_usd, "notes": notes,
    }
    sc_result = current_app.extensions["contract"].evaluate_settlement(
        kyc_status=kyc_record["status"], tx_data=tx_data, risk_level=risk_level, risk_score=risk_score
    )
    conn.execute(
        """INSERT INTO transactions (
            transaction_id, user_id, sender, receiver, sender_country, receiver_country,
            currency, amount, source_currency, target_currency, exchange_rate, converted_amount,
            exchange_rate_provider, rate_timestamp, normalized_usd_amount,
            frequency, previous_transactions, suspicious_transactions,
            account_age, corridor_risk, risk_level, risk_score, decision, blockchain_hash,
            smart_contract_status, block_number, notes, timestamp,
            amount_to_age_ratio, p_low, p_med, p_high, scoring_engine, top_factors, feature_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?, ?)""",
        (tx_id, user_id, sender, receiver, sender_country, receiver_country,
         conversion["source_currency"], conversion["original_amount"], conversion["source_currency"],
         conversion["target_currency"], conversion["exchange_rate"], conversion["converted_amount"],
         conversion["provider"], conversion["last_updated"], normalized_usd,
         features["frequency"], features["previous_transactions"], features["suspicious_transactions"],
         features["account_age"], features["corridor_risk"], risk_level,
         risk_score, sc_result["decision"], sc_result["blockchain_hash"], sc_result["smart_contract_status"],
         sc_result["block_number"], notes, utcnow_iso(),
         features["amount_to_age_ratio"], scored["p_low"], scored["p_med"], scored["p_high"], scored["engine"],
         json.dumps(scored["top_factors"]), feature_source),
    )
    return redirect(url_for("payments.result", tx_id=tx_id))


@bp.route("/result/<tx_id>")
@login_required
def result(tx_id):
    tx = dict(get_visible_tx(tx_id))
    tx["top_factors_list"] = json.loads(tx.get("top_factors") or "[]")
    return render_template(
        "result.html", tx=tx, contract_address=current_app.extensions["contract"].CONTRACT_ADDRESS,
        supported_currencies=SUPPORTED_CURRENCIES,
    )


@bp.route("/transactions")
@login_required
def transactions():
    status_filter = request.args.get("status", "ALL")
    search_query = request.args.get("q", "").strip()
    where, scope_params = tenant_scope()
    sql, params = "SELECT * FROM transactions WHERE 1=1" + where, list(scope_params)
    if status_filter in ["APPROVED", "HOLD", "BLOCKED"]:
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
    return render_template("dashboard.html", stats=stats, recent_transactions=[dict(r) for r in recent],
                           metrics=current_app.extensions["metrics"])


@bp.route("/blockchain")
@login_required
def blockchain_explorer():
    chain = current_app.extensions["blockchain"]
    is_valid, validation_msg = chain.is_chain_valid()
    blocks = [b.to_dict() for b in chain.chain]
    where, params = tenant_scope()
    if where:  # SMEs see block hashes for every block but transaction details only for their own payments
        own = {r[0] for r in get_db().execute(f"SELECT transaction_id FROM transactions WHERE 1=1{where}", params)}
        for b in blocks:
            b["transactions"] = [
                t if (t.get("transaction_id") in own or b["index"] == 0)
                else {"transaction_id": "(another SME)", "sender": "—", "receiver": "—", "amount": 0.0,
                      "currency": "", "redacted": True}
                for t in b["transactions"]
            ]
    return render_template(
        "blockchain.html", chain=blocks, is_valid=is_valid,
        validation_msg=validation_msg, contract_address=current_app.extensions["contract"].CONTRACT_ADDRESS,
    )
