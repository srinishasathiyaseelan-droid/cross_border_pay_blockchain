"""AI features (P6). Each one calls pipeline.run_task() only; none can change a decision directly.

The only outputs that reach the policy engine are escalate-only codes from the purpose tagger and the
deterministic invoice diff (policy.engine.AI_ESCALATIONS / STRICT_OVERRIDES), which can move a payment to HOLD.
"""
import difflib
import json
import re
from typing import Optional

from flask import current_app

from ...db import utcnow_iso
from .. import context
from ..pipeline import GuardedResult, run_task

PURPOSE_ESCALATE_AT = 0.7


# ---- P6.1 risk explainer ----------------------------------------------------------------------------------
def explain_job(tx_id: str):
    def fn(conn) -> GuardedResult:
        row = conn.execute("SELECT * FROM transactions WHERE transaction_id = ?", (tx_id,)).fetchone()
        if row is None:
            return GuardedResult("FAILED")
        res = run_task("explain", context.explain(conn, dict(row)), None, conn)
        if res.ok:
            conn.execute("INSERT OR REPLACE INTO risk_explanations (tx_id, output_json, provider, model, prompt_version, "
                         "created_at) VALUES (?, ?, ?, ?, ?, ?)",
                         (tx_id, json.dumps(res.data), res.meta.get("provider"), res.meta.get("model"),
                          res.meta.get("prompt_version"), utcnow_iso()))
            from ...realtime import ai_event, publish_safely  # live console one-liner (advisory)

            publish_safely(current_app._get_current_object(),
                           ai_event(tx_id, row["user_id"], res.data.get("summary", "")))
        return res
    return fn


def queue_explanation(conn, tx_id: str) -> str:
    return current_app.extensions["ai_jobs"].submit(conn, "explain", tx_id, explain_job(tx_id))


BACKFILL_LIMIT = 10
BACKFILL_SPACING_S = 60.0  # one large prompt a minute leaves the free tier's tokens/minute for live traffic  # free-tier providers allow only a few large prompts a minute; never starve live traffic


def _spaced(fn, delay: float):
    """Background backfill jobs wait before calling out, so a restart never bursts the provider's rate limit."""
    import time

    def inner(conn):
        if delay > 0:
            time.sleep(delay)
        return fn(conn)
    return inner


def backfill(app, conn, limit: int = BACKFILL_LIMIT) -> dict:
    """Queue explanations (and record-only purpose tags) for recent payments that have none, so pages show AI text
    for payments made before the AI layer was on. Called once at startup; skipped when AI is off or over budget.
    Never touches a decision: explain is advisory and purpose_retry_job only fills the purpose columns."""
    from ..budget import ai_enabled, over_budget

    out = {"explain": 0, "purpose": 0}
    with app.app_context():
        if not ai_enabled(conn) or over_budget(conn):
            return out
        from ..log import spend_today

        if spend_today(conn) >= 0.5 * float(app.config.get("LLM_DAILY_BUDGET_USD") or 0):
            return out  # leave at least half the daily budget for live traffic
        # A separate single-worker runner, so spaced backfill jobs never delay explanations for new payments.
        runner = app.extensions.get("ai_backfill_jobs") or app.extensions["ai_jobs"]
        flags = app.config.get("AI_FLAGS", {})
        delay = 0.0 if app.config.get("AI_RUN_SYNC") else BACKFILL_SPACING_S
        rows = conn.execute(
            "SELECT transaction_id, notes, sender_country, receiver_country, normalized_usd_amount, purpose_category "
            "FROM transactions WHERE decision != 'PENDING_SETTLEMENT' ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        for r in rows:
            tx_id = r["transaction_id"]
            if flags.get("AI_EXPLAIN", True) and not conn.execute(
                    "SELECT 1 FROM ai_jobs WHERE task = 'explain' AND tx_id = ?", (tx_id,)).fetchone():
                runner.submit(conn, "explain", tx_id, _spaced(explain_job(tx_id), delay))
                out["explain"] += 1
            if (flags.get("AI_PURPOSE", True) and (r["notes"] or "").strip() and not r["purpose_category"]
                    and not conn.execute("SELECT 1 FROM ai_jobs WHERE task = 'purpose' AND tx_id = ?", (tx_id,)).fetchone()):
                corridor = f"{r['sender_country']} to {r['receiver_country']}"
                runner.submit(conn, "purpose", tx_id, _spaced(purpose_retry_job(
                    tx_id, r["notes"], corridor, float(r["normalized_usd_amount"] or 0)), delay))
                out["purpose"] += 1
    return out


# ---- P6.2 purpose tagger (escalate-only, G1) ----------------------------------------------------------------
def classify_purpose(conn, notes: str, corridor: str, amount_usd: float, user_id: int) -> dict:
    """Sync, 4 s timeout. -> {"result": dict|None, "escalations": [...], "input_flags": [...], "status": str}"""
    out = {"result": None, "escalations": [], "input_flags": [], "status": "SKIPPED"}
    if not (notes or "").strip():
        return out
    res = run_task("purpose", context.purpose(notes, corridor, amount_usd), user_id, conn)
    out["status"] = res.status
    if res.status == "BLOCKED_INPUT":
        out["input_flags"] = ["NOTES_INSTRUCTION_LIKE_TEXT"] + res.meta.get("input_signals", [])
        if current_app.config.get("INPUT_GUARD_ESCALATES"):  # only if measured FPR <= 2% (docs/AI_GUARDRAIL_MATRIX.md)
            out["escalations"].append("PURPOSE_RED_FLAG")
        return out
    if res.ok:
        out["result"] = res.data
        if res.data["purpose_risk"] >= PURPOSE_ESCALATE_AT or res.data["red_flags"]:
            out["escalations"].append("PURPOSE_RED_FLAG")
    return out


def purpose_retry_job(tx_id: str, notes: str, corridor: str, amount_usd: float):
    """After a timeout the tagger is retried in the background FOR THE RECORD ONLY: the decision is final."""
    def fn(conn):
        res = run_task("purpose", context.purpose(notes, corridor, amount_usd, tx_id), None, conn)
        if res.ok:
            conn.execute("UPDATE transactions SET purpose_category = ?, purpose_risk = ?, purpose_flags = ? "
                         "WHERE transaction_id = ?", (res.data["category"], res.data["purpose_risk"],
                                                       json.dumps(res.data["red_flags"]), tx_id))
        return res
    return fn


# ---- P6.3 HOLD copilot ------------------------------------------------------------------------------------
def copilot(conn, tx: dict, user_id: int) -> GuardedResult:
    return run_task("copilot", context.copilot(conn, tx), user_id, conn)


MIN_OFFICER_REASON = 20
MAX_AI_SIMILARITY = 0.80


def ai_agreement(officer_text: str, ai_draft: Optional[str]) -> Optional[float]:
    if not ai_draft:
        return None
    return round(difflib.SequenceMatcher(None, officer_text.strip().lower(), ai_draft.strip().lower()).ratio(), 3)


def officer_reason_problem(reason: str, ai_draft: Optional[str]) -> Optional[str]:
    """G3: the officer's reason must be their own words."""
    if len((reason or "").strip()) < MIN_OFFICER_REASON:
        return f"Write a reason of at least {MIN_OFFICER_REASON} characters."
    sim = ai_agreement(reason, ai_draft)
    if sim is not None and sim >= MAX_AI_SIMILARITY:
        return "Your reason is too close to the AI draft. Write it in your own words."
    return None


# ---- P6.4 invoice reader + deterministic cross-check (G2) ---------------------------------------------------
_AMOUNT = re.compile(r"(?:total|amount\s+due|grand\s+total|balance\s+due)[^\d]{0,30}([\d][\d,]*(?:\.\d{1,2})?)", re.IGNORECASE)
_CURRENCY = re.compile(r"\b(USD|EUR|GBP|INR|SGD|AED|AUD|CAD|JPY)\b")


def extract_pdf_text(path: str, max_pages: int = 10) -> tuple:
    from pypdf import PdfReader

    reader = PdfReader(path)
    if len(reader.pages) > max_pages:
        raise ValueError(f"PDF has {len(reader.pages)} pages; the limit is {max_pages}.")
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    meta = " ".join(str(v) for v in (reader.metadata or {}).values())
    return text, meta


def deterministic_invoice_parse(text: str) -> dict:
    totals = [float(m.group(1).replace(",", "")) for m in _AMOUNT.finditer(text or "")]
    currencies = _CURRENCY.findall(text or "")
    return {"total_amount": max(totals) if totals else None,
            "currency": max(set(currencies), key=currencies.count) if currencies else None}


def read_invoice(conn, text: str, user_id: int) -> dict:
    res = run_task("invoice", context.invoice(text), user_id, conn)
    det = deterministic_invoice_parse(text)
    fields = res.data if res.ok else None
    verified = {}
    if fields:
        conf = fields.get("confidence") or {}
        for k in ("total_amount", "currency"):
            llm_v, det_v = fields.get(k), det.get(k)
            if llm_v is None:
                verified[k] = "missing"
            elif det_v is None or conf.get(k, 0) < 0.6:
                verified[k] = "unverified"  # low confidence or no deterministic match: never "matched"
            elif (k == "total_amount" and abs(float(llm_v) - float(det_v)) <= 0.01 * max(1.0, float(det_v))) or \
                    (k == "currency" and str(llm_v).upper() == det_v):
                verified[k] = "matched"
            else:
                verified[k] = "conflict"
    return {"status": res.status, "fields": fields, "deterministic": det, "verification": verified}


def invoice_flags(invoice: dict, form: dict, amount_usd: float) -> list:
    """Deterministic diff between the invoice and the form. Mismatch codes can only make the policy stricter."""
    flags = []
    det, fields = invoice.get("deterministic") or {}, invoice.get("fields") or {}
    total = det.get("total_amount")
    try:
        form_amount = float(form.get("amount") or 0)
    except ValueError:
        form_amount = 0
    if total is None:
        if amount_usd > float(current_app.config.get("INVOICE_REQUIRED_ABOVE_USD", 50000)):
            flags.append("INVOICE_UNVERIFIED")
        return flags
    if abs(total - form_amount) > 0.01 * max(1.0, total):
        flags.append("INVOICE_MISMATCH")
    ver = invoice.get("verification") or {}
    if "conflict" in ver.values():
        flags.append("INVOICE_MISMATCH")
    if ver.get("total_amount") in ("unverified", "missing") and amount_usd > float(
            current_app.config.get("INVOICE_REQUIRED_ABOVE_USD", 50000)):
        flags.append("INVOICE_UNVERIFIED")
    cur = det.get("currency")
    if cur and cur != (form.get("sender_currency") or "").upper():
        flags.append("INVOICE_MISMATCH")
    seller = (fields.get("seller") or "") if fields else ""  # the receiver is the invoice's seller
    if seller and form.get("receiver") and difflib.SequenceMatcher(
            None, seller.lower(), form["receiver"].lower()).ratio() < 0.85:
        flags.append("INVOICE_MISMATCH")
    return sorted(set(flags))


# ---- P6.5 natural-language filter -------------------------------------------------------------------------
def nl_filter(conn, query: str, user_id: int) -> GuardedResult:
    return run_task("nl_filter", context.nl_filter(query), user_id, conn)


# ---- P6.6 SME assistant -----------------------------------------------------------------------------------
_REFUSE = re.compile(r"\b(split|structur\w*|smaller\s+payments|under\s+the\s+(limit|threshold)|avoid\w*\s+(the\s+)?"
                     r"(review|detection|reporting|checks?|hold)|thresholds?|other\s+(users?|customers?|smes?|companies)|"
                     r"someone\s+else|system\s+prompt|not\s+(get\s+)?(held|flagged|reviewed))\b", re.IGNORECASE)
# Output side (found by red-team case RT34): an answer that coaches evasion is rejected even if the question looked
# innocent.
_EVASION_OUT = re.compile(r"\b(under|below)\s+the\s+(limit|threshold)|avoid\w*\s+(the\s+)?(review|detection|reporting)|"
                          r"split\w*\s+(it|this|the\s+payment|your\s+payment)?\s*(into|in)\s+(smaller|several|multiple)|"
                          r"\bthresholds?\b", re.IGNORECASE)
REFUSAL = ("I can't help with that. I can explain your own payment, its exchange rate, and which documents can help a "
           "compliance review.")


CHAT_TURNS_PER_TX_PER_DAY = 10


def chat_turns_today(conn, tx_id: str, user_id: int) -> int:
    day = utcnow_iso()[:10] + "T00:00:00Z"
    return conn.execute("SELECT COUNT(*) FROM llm_calls WHERE task = 'assistant' AND tx_id = ? AND user_id = ? "
                        "AND created_at >= ?", (tx_id, user_id, day)).fetchone()[0]


def assistant(conn, tx: dict, message: str, user_id: int) -> dict:
    if chat_turns_today(conn, tx["transaction_id"], user_id) >= CHAT_TURNS_PER_TX_PER_DAY:  # G17
        return {"answer": "You have reached today's limit of 10 questions for this payment.", "refused": True,
                "status": "CHAT_LIMIT"}
    if _REFUSE.search(message or ""):  # deterministic refusal before any model call (G4)
        from ..log import record

        record(conn, task="assistant", prompt_version=None, provider=None, model=None, tx_id=tx["transaction_id"],
               user_id=user_id, input_hash=None, redacted_input=None, status="REFUSED", guard_outcome="REFUSAL_POLICY",
               output_json=None, latency_ms=0, input_tokens=0, output_tokens=0, cost_usd=0)
        return {"answer": REFUSAL, "refused": True, "status": "REFUSED"}
    res = run_task("assistant", context.assistant(conn, tx, message), user_id, conn)
    if not res.ok:
        return {"answer": None, "refused": False, "status": res.status}
    if _EVASION_OUT.search(res.data.get("answer") or ""):
        conn.execute("UPDATE llm_calls SET status = 'REJECTED_GUARD:EVASION_COACHING', guard_outcome = "
                     "'REJECTED_GUARD:EVASION_COACHING', output_json = NULL WHERE id = (SELECT MAX(id) FROM llm_calls "
                     "WHERE task = 'assistant' AND tx_id = ?)", (tx["transaction_id"],))
        return {"answer": None, "refused": True, "status": "REJECTED_GUARD:EVASION_COACHING"}
    return {**res.data, "status": "OK"}


# ---- P6.7 report drafts -----------------------------------------------------------------------------------
def weekly_report(conn, user_id: int) -> GuardedResult:
    return run_task("report", context.weekly_report(conn), user_id, conn)


def sar_draft(conn, tx: dict, user_id: int) -> GuardedResult:
    return run_task("report", context.sar_narrative(conn, tx), user_id, conn)


# ---- AI self-test (/admin/ai) -------------------------------------------------------------------------------
# A fixed synthetic case, never stored as a payment: each feature runs once through the full pipeline (input guard,
# DLP, router, output guard, llm_calls log) so an officer can see in one click which features return real output.
SELFTEST_TX = {
    "transaction_id": "TX-SELFTEST-0001", "user_id": 0, "decision": "HOLD", "risk_level": "MEDIUM", "risk_score": 52.4,
    "p_low": 0.21, "p_med": 0.55, "p_high": 0.24, "scoring_engine": "model", "sender": "Selftest Exports Ltd",
    "receiver": "Selftest Components GmbH", "sender_country": "India", "receiver_country": "Germany",
    "amount": 18500.0, "currency": "USD", "source_currency": "USD", "target_currency": "EUR",
    "exchange_rate": 0.92, "converted_amount": 17020.0, "exchange_rate_provider": "selftest",
    "rate_timestamp": "2026-01-01T00:00:00Z", "normalized_usd_amount": 18500.0, "corridor_risk": 0.22,
    "frequency": 6, "previous_transactions": 14, "suspicious_transactions": 1, "account_age": 9,
    "top_factors": json.dumps([{"feature": "frequency", "label": "Payments in the last 30 days", "value": 6,
                                "contribution": 8.5}]),
    "policy_reasons": json.dumps(["RISK_SCORE_AT_OR_ABOVE_REVIEW_AT"]), "notes": "Invoice 4471 for machine parts",
    "timestamp": "2026-01-01T00:00:00Z", "feature_source": "selftest",
}
SELFTEST_INVOICE = ("COMMERCIAL INVOICE No. 4471\nSeller: Selftest Components GmbH\nBuyer: Selftest Exports Ltd\n"
                    "Description: CNC spindle parts, 40 units\nTotal: 18,500.00 USD\nDate: 2026-01-01")


SELFTEST_SPACING_S = 4.0
SELFTEST_DEADLINE_S = 80.0  # stay well inside gunicorn's 120 s request timeout


def self_test(conn, user_id: int, delay: float = None) -> list:
    """-> [(task, status, detail)]. status is OK, UNAVAILABLE, DISABLED, BLOCKED_INPUT or REJECTED_GUARD:<code>;
    detail names the provider that answered, or every provider's reason when none did."""
    if delay is None:
        delay = 0.0 if current_app.config.get("TESTING") else SELFTEST_SPACING_S
    tx = dict(SELFTEST_TX)
    ctxs = [
        ("explain", context.explain(conn, tx)),
        ("purpose", context.purpose(tx["notes"], "India to Germany", tx["normalized_usd_amount"])),
        ("copilot", context.copilot(conn, tx)),
        ("invoice", context.invoice(SELFTEST_INVOICE)),
        ("nl_filter", context.nl_filter("held payments to Germany over 10000 dollars")),
        ("assistant", context.assistant(conn, tx, "Which documents would help the review of this payment?")),
        ("report", context.weekly_report(conn)),
    ]
    import time

    out = []
    started = time.monotonic()
    for i, (task, ctx) in enumerate(ctxs):
        if time.monotonic() - started > SELFTEST_DEADLINE_S:
            out.append((task, "SKIPPED", "time limit reached; run the self-test again in a minute"))
            continue
        if i and delay > 0:
            time.sleep(delay)  # sequential and spaced: free-tier providers rate-limit bursts
        try:
            res = run_task(task, ctx, user_id, conn)
        except Exception:  # noqa: BLE001 — a self-test never raises to the page
            out.append((task, "ERROR", ""))
            continue
        why = ""
        if res.status == "UNAVAILABLE":
            why = ", ".join(res.meta.get("errors") or []) or res.meta.get("error_code") or "NO_PROVIDER"
        elif res.status == "OK" and res.meta.get("provider"):
            why = res.meta["provider"] + (" (fallback)" if res.meta.get("fallback_used") else "")
        elif res.meta.get("cached"):
            why = "cached"
        out.append((task, res.status, why))
    return out
