"""Deterministic evidence items for a transaction.

Adapted from Netvrio (sandysunny99/razorpay-ai-risk-manager @98bbc09) backend/evidence/builder.py — items come from
CrossPay's own features, top factors, corridor, FX snapshot and history; IDs are deterministic
(ev_<sha256(tx_id + feature_json)[:6]>_<n>) instead of a random UUID per call, so cached explanations still match.
No thresholds, secrets or other tenants' data are ever included (LLM08).
"""
import hashlib
import json
import statistics


def _prefix(tx: dict) -> str:
    feats = {k: tx.get(k) for k in ("amount", "normalized_usd_amount", "frequency", "previous_transactions",
                                    "suspicious_transactions", "account_age", "corridor_risk", "risk_score")}
    digest = hashlib.sha256((tx["transaction_id"] + json.dumps(feats, sort_keys=True, default=str)).encode()).hexdigest()
    return f"ev_{digest[:6]}"


def usd_median_90d(conn, user_id: int, exclude_tx: str, now_iso: str):
    from datetime import datetime, timedelta

    try:
        now = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    since = (now - timedelta(days=90)).isoformat().replace("+00:00", "Z")
    vals = [r[0] for r in conn.execute(
        "SELECT normalized_usd_amount FROM transactions WHERE user_id = ? AND transaction_id != ? AND timestamp >= ? "
        "AND normalized_usd_amount IS NOT NULL", (user_id, exclude_tx, since))]
    return round(statistics.median(vals), 2) if vals else None


def build(conn, tx: dict, purpose: dict = None, invoice_flags: list = None, input_flags: list = None) -> list:
    p = _prefix(tx)
    items = []

    def add(kind, text):
        items.append({"id": f"{p}_{len(items) + 1}", "kind": kind, "text": text})

    if tx.get("p_low") is not None:
        add("score", f"Model risk score {tx['risk_score']} of 100 (level {tx['risk_level']}); class probabilities "
                     f"LOW {tx['p_low']}, MEDIUM {tx['p_med']}, HIGH {tx['p_high']}.")
    else:
        add("score", f"Risk score {tx['risk_score']} of 100 (level {tx['risk_level']}), engine "
                     f"{tx.get('scoring_engine') or 'seed record'}.")
    for f in json.loads(tx.get("top_factors") or "[]")[:3]:
        direction = "raised" if (f.get("contribution") or 0) > 0 else "lowered"
        add("factor", f"{f.get('label') or f.get('feature')} = {f.get('value')} {direction} the score by "
                      f"{abs(float(f.get('contribution') or 0)):.1f} points.")
    add("corridor", f"Corridor {tx['sender_country']} to {tx['receiver_country']} has corridor risk "
                    f"{tx['corridor_risk']} on a 0 to 1 scale.")
    median = usd_median_90d(conn, tx["user_id"], tx["transaction_id"], tx.get("timestamp") or "")
    usd = tx.get("normalized_usd_amount") or tx.get("amount")
    if median:
        add("amount", f"Amount {usd} USD versus this SME's 90-day median of {median} USD "
                      f"({round(float(usd) / median, 1)} times the median).")
    else:
        add("amount", f"Amount {usd} USD; this SME has no other payments in the last 90 days.")
    add("history", f"{tx['frequency']} payments in the last 30 days, {tx['previous_transactions']} payments before "
                   f"this one, {tx['suspicious_transactions']} earlier payments held, blocked or rejected; account age "
                   f"{tx['account_age']} months.")
    add("fx", f"Exchange rate 1 {tx.get('source_currency')} = {tx.get('exchange_rate')} {tx.get('target_currency')} "
              f"from {tx.get('exchange_rate_provider')}" + ("; the rate was STALE (served from cache)." if tx.get("rate_stale") else "."))
    reasons = json.loads(tx.get("policy_reasons") or "[]")
    add("policy", f"Policy outcome {tx['decision']}" + (f" with reason codes {', '.join(reasons)}." if reasons else "."))
    if tx.get("feature_source") == "demo_vector":
        add("demo", "This payment used a fixed DEMO VECTOR for its behaviour features.")
    if purpose:
        flags = ", ".join(purpose.get("red_flags") or []) or "none"
        add("purpose", f"Purpose tagger (AI, advisory): category {purpose.get('category')}, red flags {flags}.")
    for code in invoice_flags or []:
        add("invoice", f"Invoice check flag: {code}.")
    for code in input_flags or []:
        add("input_guard", f"Input guard flag on the payment notes: {code} (AI call skipped for that text).")
    return items


def as_text(items: list) -> str:
    return "\n".join(f"[{i['id']}] {i['text']}" for i in items)
