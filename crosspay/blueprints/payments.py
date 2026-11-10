"""Payments: form, processing pipeline, receipt, history, dashboard, ledger explorer.

P0: behaviour moved unchanged from app.py (findings C4, H1, H2, H3 are fixed in later phases).
"""
import random

import pandas as pd
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for

from ..db import get_db, utcnow_iso
from ..security.decorators import current_user_row, login_required
from ..services.currency import (
    COUNTRY_TO_DEFAULT_CURRENCY,
    SUPPORTED_CURRENCIES,
    ExchangeRateAPIError,
    InvalidAmountError,
    UnsupportedCurrencyError,
)

bp = Blueprint("payments", __name__)

COUNTRY_RISK_MAP = {
    "United States": 0.18, "United Kingdom": 0.20, "Germany": 0.15, "Singapore": 0.16, "Japan": 0.17,
    "Canada": 0.19, "Australia": 0.18, "France": 0.21, "India": 0.40, "Brazil": 0.52,
    "United Arab Emirates": 0.38, "Mexico": 0.48, "South Africa": 0.58, "Nigeria": 0.85, "Russia": 0.82,
    "Pakistan": 0.78, "Other": 0.50,
}


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


def calculate_corridor_risk(sender_c, receiver_c):
    r1 = COUNTRY_RISK_MAP.get(sender_c, 0.45)
    r2 = COUNTRY_RISK_MAP.get(receiver_c, 0.45)
    return round((r1 + r2 * 1.5) / 2.5, 3)


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

    sender = request.form.get("sender", kyc_record["business_name"]).strip()
    receiver = request.form.get("receiver", "").strip()
    sender_country = request.form.get("sender_country", kyc_record["country"]).strip()
    receiver_country = request.form.get("receiver_country", "").strip()
    sender_currency = request.form.get("sender_currency", request.form.get("currency", "USD")).strip().upper()
    receiver_currency = request.form.get("receiver_currency", request.form.get("currency", "USD")).strip().upper()
    raw_amount = request.form.get("amount", "0").strip()
    try:
        frequency = int(request.form.get("frequency", 1))
        previous_transactions = int(request.form.get("previous_transactions", 10))
        suspicious_transactions = int(request.form.get("suspicious_transactions", 0))
        account_age = int(request.form.get("account_age", 12))
    except ValueError:
        flash("Invalid numerical behavioral values in payment submission.", "danger")
        return redirect(url_for("payments.payment"))
    notes = request.form.get("notes", "Cross-border SME trade invoice settlement").strip()

    try:
        conversion = current_app.extensions["currency"].convert(
            amount=raw_amount, source_currency=sender_currency, target_currency=receiver_currency
        )
    except InvalidAmountError as e:
        flash(f"Payment Validation Error: {e}", "danger")
        return redirect(url_for("payments.payment"))
    except UnsupportedCurrencyError as e:
        flash(f"Currency Error: {e}", "danger")
        return redirect(url_for("payments.payment"))
    except ExchangeRateAPIError as e:
        flash(f"Exchange Rate Service Error: {e}", "danger")
        return redirect(url_for("payments.payment"))

    normalized_usd = conversion["normalized_usd_amount"]
    corridor_risk = calculate_corridor_risk(sender_country, receiver_country)
    amount_to_age_ratio = round(normalized_usd / (account_age + 0.5), 2)
    X_input = pd.DataFrame([{
        "amount": normalized_usd, "frequency": frequency, "previous_transactions": previous_transactions,
        "suspicious_transactions": suspicious_transactions, "account_age": account_age,
        "corridor_risk": corridor_risk, "amount_to_age_ratio": amount_to_age_ratio,
    }])

    rf_pipeline = current_app.extensions["model"]
    if rf_pipeline and "model" in rf_pipeline:
        model = rf_pipeline["model"]
        prediction = model.predict(X_input)[0]
        probabilities = model.predict_proba(X_input)[0]
        prob_med = float(probabilities[1]) if len(probabilities) > 1 else 0.0
        prob_high = float(probabilities[2]) if len(probabilities) > 2 else 0.0
        risk_score = round((prob_med * 0.5 + prob_high * 1.0) * 100, 1)
        if prediction == 0:
            risk_level = "LOW"
            if risk_score > 35.0:
                risk_score = round(random.uniform(5.0, 18.0), 1)
        elif prediction == 1:
            risk_level = "MEDIUM"
            if risk_score < 40.0 or risk_score > 75.0:
                risk_score = round(random.uniform(52.0, 68.0), 1)
        else:
            risk_level = "HIGH"
            if risk_score < 80.0:
                risk_score = round(random.uniform(88.0, 98.5), 1)
    elif normalized_usd > 50000 or suspicious_transactions >= 2:
        risk_level, risk_score = "HIGH", 92.5
    elif normalized_usd > 15000 or frequency >= 5:
        risk_level, risk_score = "MEDIUM", 61.0
    else:
        risk_level, risk_score = "LOW", 12.0

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
            smart_contract_status, block_number, notes, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (tx_id, user_id, sender, receiver, sender_country, receiver_country,
         conversion["source_currency"], conversion["original_amount"], conversion["source_currency"],
         conversion["target_currency"], conversion["exchange_rate"], conversion["converted_amount"],
         conversion["provider"], conversion["last_updated"], normalized_usd,
         frequency, previous_transactions, suspicious_transactions, account_age, corridor_risk, risk_level,
         risk_score, sc_result["decision"], sc_result["blockchain_hash"], sc_result["smart_contract_status"],
         sc_result["block_number"], notes, utcnow_iso()),
    )
    return redirect(url_for("payments.result", tx_id=tx_id))


@bp.route("/result/<tx_id>")
@login_required
def result(tx_id):
    tx = get_visible_tx(tx_id)
    return render_template(
        "result.html", tx=dict(tx), contract_address=current_app.extensions["contract"].CONTRACT_ADDRESS,
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
