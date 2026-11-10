# Viva demo script (about 7 minutes)

Setup: `.env` with `CROSSPAY_ENV=demo`, `DEMO_MODE=1`, `LLM_ENABLED=1` and a Groq key. Start with
`.venv\Scripts\python app.py` and open http://localhost:5000. Everything also works with `LLM_ENABLED=0`.

| Min | Step | What to say |
|---|---|---|
| 0:00 | Landing page → **Try as demo SME** | Quick logins exist only in DEMO_MODE; outside it `/quick_login` is a 404. |
| 0:30 | **Send payment → Low risk** scenario, submit | The four behaviour features come from the SME's history (here a fixed DEMO VECTOR, badged on the receipt). Live preview = same model, nothing saved. |
| 1:15 | Receipt: APPROVED, block number, probabilities, top factors, "Why this decision" | Explanation is AI-generated and advisory; it is rejected if it cites evidence or numbers it was not given, or claims another outcome. |
| 2:00 | **Medium risk** scenario → HOLD | Policy: score ≥ REVIEW_AT (40) → HOLD. Nothing mined yet. |
| 2:30 | Sign out → **Compliance officer** → Transactions → Review → **Generate copilot draft** | The copilot is collapsed by default, never pre-selects a button, and a reason copied from its draft is refused. |
| 3:30 | Release with your own reason | One DB transaction: update row, mine block, sign audit record, store the review. Dashboard live feed shows it. |
| 4:00 | SME again → **High risk** scenario → BLOCKED; officer → Reports → draft narrative | Report numbers must appear in the input; it stays DRAFT until signed. |
| 5:00 | Tamper: `sqlite3 instance\crosspay.db "UPDATE transactions SET amount=1 WHERE transaction_id='TX-2026-8801'"`, then Ledger → **Verify integrity now** | Verification fails and names the edited row: the row no longer matches its HMAC-signed audit record. |
| 6:00 | Officer → AI ops → **Kill switch** → submit another payment | The app keeps working; AI panels fall back to the model's own top factors. |
| 6:30 | Close: show `docs/AI_GUARDRAIL_MATRIX.md` and the measured model metrics on the dashboard | No inflated accuracy claim: test accuracy 72.9% on honest synthetic data, HIGH recall 84%, 0% of HIGH auto-approved. |

Reset the demo data by deleting `instance\crosspay.db` and `instance\blockchain_ledger.json` (both are recreated on start).
