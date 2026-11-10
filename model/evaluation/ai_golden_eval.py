"""Live evaluation of the AI tasks on a small golden set (P7). Needs provider keys; never runs in CI.

    python model/evaluation/ai_golden_eval.py

Golden set: 20 explain cases (synthetic payments across the three demo scenarios and the corridor table) and 20
purpose notes (10 benign trade notes, 10 with a clear red flag, labels written by the fixture author). Reports, per
task: guard-passed rate (schema + citations + numbers + decision words), evidence faithfulness (cited IDs within the
given IDs), latency p50/p95, estimated cost per 100 payments, and for purpose the escalation precision/recall against
the author labels. Writes model/evaluation/ai_golden_eval.json. Outputs are NOT hand-reviewed by a compliance officer.
"""
import json
import os
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

PURPOSE_NOTES = [
    ("Invoice 4471 - HS 8471 laptops, 30-day terms", False),
    ("PO-2026-118 second instalment for steel coils", False),
    ("Freight charges for container MSKU1234567, CIF Rotterdam", False),
    ("Software licence renewal, annual subscription", False),
    ("Royalty for Q3 per licence agreement", False),
    ("Sample batch of cotton T-shirts, invoice 5521", False),
    ("Customs brokerage and port handling, B/L 7781", False),
    ("Advance for green coffee beans, LC at sight", False),
    ("Consulting services for ERP rollout, milestone 2 of 4", False),
    ("Split shipment: second half of brake assemblies under PO-2026-77", False),
    ("Offshore consulting fee, no invoice available", True),
    ("Urgent transfer, keep this confidential from our auditors", True),
    ("Payment to a third party on behalf of our customer, they will repay us in cash", True),
    ("Convert to crypto for our partner's wallet", True),
    ("First of five transfers, kept small so nothing is flagged", True),
    ("Gift to the customs officer for faster clearance", True),
    ("Consultancy fee to a shell company registered last week", True),
    ("Loan repayment to director's personal account offshore", True),
    ("Dual-use night vision equipment, export licence pending", True),
    ("No invoice, pay the beneficiary's cousin instead", True),
]
EXPLAIN_CASES = [(sc, rc, amt) for sc, rc, amt in [
    ("low", "Germany", "4500"), ("low", "Singapore", "1200"), ("low", "Japan", "8000"), ("low", "Canada", "2500"),
    ("low", "United Kingdom", "3000"), ("low", "France", "6000"), ("low", "Australia", "900"),
    ("medium", "India", "28500"), ("medium", "United Arab Emirates", "22000"), ("medium", "Brazil", "18000"),
    ("medium", "Mexico", "15000"), ("medium", "India", "35000"), ("medium", "South Africa", "12000"),
    ("high", "Nigeria", "145000"), ("high", "Russia", "90000"), ("high", "Pakistan", "120000"),
    ("high", "Nigeria", "60000"), ("high", "Brazil", "200000"), ("low", "Germany", "15000"), ("medium", "India", "9000")]]
CUR = {"Germany": "EUR", "France": "EUR", "Singapore": "SGD", "Japan": "JPY", "Canada": "CAD", "United Kingdom": "GBP",
       "Australia": "AUD", "India": "INR", "United Arab Emirates": "AED"}


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))] if xs else None


def run():
    from dotenv import load_dotenv

    load_dotenv(os.path.join(ROOT, ".env"), override=False)
    from crosspay import create_app
    from crosspay.ai import context, tasks
    from crosspay.ai.pipeline import run_task
    from crosspay.db import connect
    from tests.conftest import FakeFX

    tmp = tempfile.mkdtemp()
    app = create_app("test", {"DB_PATH": os.path.join(tmp, "eval.db"), "LEDGER_PATH": os.path.join(tmp, "l.json"),
                              "WTF_CSRF_ENABLED": False, "LLM_ENABLED": True, "AI_RUN_SYNC": True,
                              "LLM_DAILY_BUDGET_USD": 1.0})
    conn = connect(app.config["DB_PATH"])
    client = app.test_client()
    client.get("/quick_login/sme")
    with patch("crosspay.services.currency.requests.get", side_effect=FakeFX()):
        tx_ids = []
        for sc, rc, amt in EXPLAIN_CASES:
            client.post("/process_payment", data={"receiver": "Golden Case Ltd", "sender_country": "United States",
                                                  "receiver_country": rc, "sender_currency": "USD",
                                                  "receiver_currency": CUR.get(rc, "USD"), "amount": amt, "scenario": sc,
                                                  "notes": ""})
            tx_ids.append(conn.execute("SELECT transaction_id FROM transactions ORDER BY id DESC LIMIT 1").fetchone()[0])
    app.config["LLM_ENABLED"] = True
    results = {"explain": [], "purpose": []}
    with app.app_context():
        conn.execute("DELETE FROM ai_cache")
        for tx_id in tx_ids:
            tx = dict(conn.execute("SELECT * FROM transactions WHERE transaction_id = ?", (tx_id,)).fetchone())
            ctx = context.explain(conn, tx)
            t = time.time()
            res = run_task("explain", ctx, None, conn)
            cited = [f["evidence_id"] for f in (res.data or {}).get("factors", [])]
            results["explain"].append({"tx": tx_id, "status": res.status, "latency_s": round(time.time() - t, 2),
                                       "faithful": all(c in {e["id"] for e in ctx.evidence} for c in cited),
                                       "provider": res.meta.get("provider")})
        for note, label in PURPOSE_NOTES:
            t = time.time()
            out = tasks.classify_purpose(conn, note, "United States to India", 20000.0, None)
            results["purpose"].append({"note": note, "label_escalate": label, "status": out["status"],
                                       "escalated": bool(out["escalations"]), "latency_s": round(time.time() - t, 2)})
    cost = conn.execute("SELECT task, COUNT(*), SUM(cost_usd), SUM(input_tokens), SUM(output_tokens) FROM llm_calls "
                        "GROUP BY task").fetchall()
    summary = {}
    for task, rows in results.items():
        ok = [r for r in rows if r["status"] in ("OK", "BLOCKED_INPUT")]
        lat = [r["latency_s"] for r in rows if r["status"] == "OK"]
        summary[task] = {"cases": len(rows), "guard_passed": sum(r["status"] == "OK" for r in rows),
                         "statuses": {s: sum(r["status"] == s for r in rows) for s in {r["status"] for r in rows}},
                         "latency_p50_s": pct(lat, 0.5), "latency_p95_s": pct(lat, 0.95)}
        if task == "explain":
            summary[task]["evidence_faithful"] = sum(r.get("faithful", False) for r in ok)
        if task == "purpose":
            tp = sum(r["escalated"] and r["label_escalate"] for r in rows)
            fp = sum(r["escalated"] and not r["label_escalate"] for r in rows)
            fn = sum((not r["escalated"]) and r["label_escalate"] for r in rows)
            summary[task].update({"escalation_precision": round(tp / (tp + fp), 3) if tp + fp else None,
                                  "escalation_recall": round(tp / (tp + fn), 3) if tp + fn else None,
                                  "tp": tp, "fp": fp, "fn": fn})
    for task, n, usd, tin, tout in cost:
        if task in summary:
            summary[task]["est_cost_usd_total"] = round(usd or 0, 6)
            summary[task]["est_cost_per_100_payments_usd"] = round((usd or 0) / max(1, n) * 100, 4)
    report = {"run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "provider_chain": os.getenv("LLM_PROVIDERS"),
              "summary": summary, "cases": results,
              "note": "Labels written by the fixture author; outputs not hand-reviewed by a compliance officer."}
    with open(os.path.join(ROOT, "model", "evaluation", "ai_golden_eval.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    conn.close()
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
