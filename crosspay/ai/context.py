"""Server-side context builders, one per task (G4, G5, LLM02, LLM08).

Callers pass a transaction row they already fetched with tenant scoping (payments.get_visible_tx); nothing here
looks records up by IDs found in user text. Each builder sends an allow-list of fields only: never thresholds,
secrets, government IDs, emails, addresses, other tenants' rows or other tasks' prompts.
"""
import json
from datetime import date, datetime, timedelta, timezone

from ..services.features import ALLOWED_COUNTRIES
from . import evidence as ev
from .pipeline import TaskContext

FAQ = """Q: Why is my payment on hold? A: The risk policy sends some payments to a compliance officer. An officer
reviews the evidence and releases or rejects it; you may be asked for documents such as an invoice or bill of lading.
Q: How was the exchange rate applied? A: The converted amount is the payment amount multiplied by the rate shown on
your receipt, from the provider and time shown there.
Q: What documents help a review? A: A commercial invoice, a purchase order or contract, shipping documents and proof
of the receiver's business registration.
Q: Can the assistant change a decision? A: No. Decisions come from the risk policy and from compliance officers."""


def _tx_facts(tx: dict) -> dict:
    return {
        "transaction": tx["transaction_id"],
        "decision": tx["decision"],
        "risk_level": tx["risk_level"],
        "risk_score": tx["risk_score"],
        "scoring_engine": tx.get("scoring_engine") or "seed",
        "corridor": f"{tx['sender_country']} to {tx['receiver_country']}",
        "amount": f"{tx['amount']} {tx.get('source_currency') or tx.get('currency')}",
        "amount_usd": tx.get("normalized_usd_amount"),
        "converted": f"{tx.get('converted_amount')} {tx.get('target_currency')}",
    }


def _purpose_of(conn, tx_id):
    row = conn.execute("SELECT result_json FROM ai_jobs WHERE task = 'purpose' AND tx_id = ? AND status = 'DONE'",
                       (tx_id,)).fetchone()
    return json.loads(row[0]) if row and row[0] else None


def explain(conn, tx: dict) -> TaskContext:
    items = ev.build(conn, tx, purpose=_purpose_of(conn, tx["transaction_id"]))
    return TaskContext(facts=_tx_facts(tx), evidence=items, tx_id=tx["transaction_id"], stored_decision=tx["decision"])


def purpose(notes: str, corridor: str, amount_usd: float, tx_id: str = None) -> TaskContext:
    band = "under 10,000 USD" if amount_usd < 10000 else "10,000 to 50,000 USD" if amount_usd < 50000 else "over 50,000 USD"
    return TaskContext(facts={"corridor": corridor, "amount_band": band}, user_fields=[("notes", notes or "", "notes")],
                       tx_id=tx_id)


def copilot(conn, tx: dict) -> TaskContext:
    items = ev.build(conn, tx, purpose=_purpose_of(conn, tx["transaction_id"]))
    hist = conn.execute(
        "SELECT decision, COUNT(*) FROM transactions WHERE user_id = ? AND transaction_id != ? GROUP BY decision",
        (tx["user_id"], tx["transaction_id"])).fetchall()
    reviews = conn.execute("SELECT COUNT(*) FROM hold_reviews r JOIN transactions t ON t.transaction_id = r.tx_id "
                           "WHERE t.user_id = ?", (tx["user_id"],)).fetchone()[0]
    kyc = conn.execute("SELECT status FROM kyc WHERE user_id = ? ORDER BY id DESC LIMIT 1", (tx["user_id"],)).fetchone()
    facts = {**_tx_facts(tx), "sme_history_by_decision": {r[0]: r[1] for r in hist}, "prior_officer_reviews": reviews,
             "kyc_status": kyc[0] if kyc else "MISSING"}
    return TaskContext(facts=facts, evidence=items, tx_id=tx["transaction_id"], stored_decision=tx["decision"],
                       user_fields=[("notes", tx.get("notes") or "", "notes"), ("receiver", tx["receiver"], "receiver")])


def invoice(text: str) -> TaskContext:
    return TaskContext(facts={"document": "commercial invoice (text extracted from the uploaded PDF)"},
                       user_fields=[("invoice_text", text, "invoice_text")])


def nl_filter(query: str, today: date = None) -> TaskContext:
    today = today or datetime.now(timezone.utc).date()
    first = today.replace(day=1)
    last_month_first = (first - timedelta(days=1)).replace(day=1)
    ref = (f"today {today.isoformat()}; first day of this month {first.isoformat()}; first day of last month "
           f"{last_month_first.isoformat()}; last day of last month {(first - timedelta(days=1)).isoformat()}; "
           f"7 days ago {(today - timedelta(days=7)).isoformat()}; 30 days ago {(today - timedelta(days=30)).isoformat()}; "
           f"90 days ago {(today - timedelta(days=90)).isoformat()}.\nCountries: {', '.join(ALLOWED_COUNTRIES)}.\n"
           "Currencies: USD, EUR, GBP, INR, SGD, AED, AUD, CAD, JPY.")
    return TaskContext(facts={"search_scope": "the officer's or SME's own visible payments"}, reference_text=ref,
                       user_fields=[("query", query, "query")])


def assistant(conn, tx: dict, message: str) -> TaskContext:
    items = ev.build(conn, tx)
    facts = {**_tx_facts(tx), "rate": f"1 {tx.get('source_currency')} = {tx.get('exchange_rate')} {tx.get('target_currency')}",
             "rate_provider": tx.get("exchange_rate_provider"), "rate_time": tx.get("rate_timestamp")}
    return TaskContext(facts=facts, evidence=items, reference_text=FAQ, tx_id=tx["transaction_id"],
                       stored_decision=tx["decision"], user_fields=[("message", message, "chat")])


def weekly_report(conn, days: int = 7) -> TaskContext:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows = conn.execute("SELECT decision, COUNT(*), ROUND(COALESCE(SUM(normalized_usd_amount), 0), 2) FROM transactions "
                        "WHERE timestamp >= ? GROUP BY decision", (since,)).fetchall()
    corridors = conn.execute("SELECT receiver_country, COUNT(*) FROM transactions WHERE timestamp >= ? "
                             "GROUP BY receiver_country ORDER BY COUNT(*) DESC LIMIT 5", (since,)).fetchall()
    reviews = conn.execute("SELECT action, COUNT(*) FROM hold_reviews WHERE created_at >= ? GROUP BY action",
                           (since,)).fetchall()
    facts = {"period_days": days, "period_start": since[:10],
             "payments_by_decision": {r[0]: {"count": r[1], "usd_volume": r[2]} for r in rows},
             "top_receiver_countries": {r[0]: r[1] for r in corridors},
             "officer_reviews": {r[0]: r[1] for r in reviews}}
    return TaskContext(facts=facts)


def sar_narrative(conn, tx: dict) -> TaskContext:
    return TaskContext(facts=_tx_facts(tx), evidence=ev.build(conn, tx), tx_id=tx["transaction_id"],
                       stored_decision=tx["decision"], user_fields=[("notes", tx.get("notes") or "", "notes")])
