# CrossPay: risk-adaptive cross-border settlement for SMEs

> **Security note (Nov 2026).** The removed `_legacy_archive/` folder contained the public Hardhat account #0
> private key and Ganache keys in `scripts/deploy*.js` and `docker-compose.yml`, plus credentials in
> `application.properties`. Treat every one of those keys and passwords as compromised and never fund or reuse them.
> They are still in git history (commit d12451c); purging them needs a history rewrite, which has not been done.

Academic prototype. A KYC-verified SME submits a cross-border payment. CrossPay converts it at a live exchange rate,
scores it with a Random Forest built from the SME's own payment history, and a deterministic policy either approves it
onto a signed ledger, holds it for a compliance officer, or blocks it. An optional LLM layer explains decisions and
helps officers, but **never makes a decision**.

## The problem

SMEs pay suppliers across borders with little room for manual compliance. A rule set that is too loose lets risky
payments through; one that is too strict buries officers in reviews. CrossPay adapts settlement to risk and keeps every
decision explainable and verifiable.

## Architecture

```mermaid
flowchart LR
    F[Payment form] --> FB[Feature builder<br/>from DB history]
    FB --> RF[Random Forest<br/>LOW / MED / HIGH]
    RF --> P[Policy engine<br/>REVIEW_AT 40 · BLOCK_AT 80]
    P -->|APPROVED| L[(SQLite + HMAC audit chain<br/>+ PoW block)]
    P -->|HOLD| O[Compliance officer]
    O --> L
    P -->|BLOCKED| L
    subgraph Advisory AI (guarded, optional)
      PT[Purpose tagger] -. escalate-only .-> P
      IV[Invoice diff] -. stricter-only .-> P
      EX[Explainer] -.-> R[Receipt]
      CP[HOLD copilot] -.-> O
    end
```

- `crosspay/services/features.py` builds all seven model features on the server; nothing the sender types reaches the
  model except the amount and corridor.
- `crosspay/policy/engine.py` is the only place a decision is made. AI signals can only move APPROVED to HOLD.
- `crosspay/services/settlement.py` inserts, decides, mines and signs in **one** database transaction.
- `crosspay/ledger/audit.py` is an HMAC-SHA256 chain with a fork guard; the explorer view is rebuilt from it.
- `crosspay/ai/pipeline.py::run_task()` is the single guarded path for every AI call.

## Run it

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt        # Windows (use .venv/bin/pip elsewhere)
copy .env.example .env                                   # then fill in SECRET_KEY, LEDGER_SIGNING_KEY, keys
.venv\Scripts\python app.py                              # http://localhost:5000
```

Production: `gunicorn "crosspay:create_app('prod')"` (see `Procfile`, `render.yaml`). Tests: `pytest -q` (no network;
FX mocked, AI faked). Retrain the model: `python model/train_model.py`.

### Key environment variables (full list in `.env.example`)

| Variable | Default | Purpose |
|---|---|---|
| `CROSSPAY_ENV` | `dev` | `dev`, `demo` or `prod` (`prod` refuses to start without `SECRET_KEY` and `LEDGER_SIGNING_KEY`) |
| `DEMO_MODE` | `0` | quick logins, KYC simulation and fixed demo scenarios, all labelled |
| `REVIEW_AT` / `BLOCK_AT` | `40` / `80` | policy thresholds on the 0–100 risk score |
| `LLM_ENABLED` | `0` | the app is fully usable with AI off |
| `LLM_PROVIDERS` | `groq,nvidia,cloudflare` | fallback order; providers without keys are skipped |
| `LLM_DAILY_BUDGET_USD` | `1.00` | AI calls stop for the day once reached |
| `EXCHANGE_RATE_MAX_STALE_HOURS` | `24` | serve cached rates (flagged STALE) when the API is down |

## Demo mode

`DEMO_MODE=1` adds one-click SME and officer logins, a labelled "demo provider" KYC simulation, and three scenario
buttons that load fixed server-side behaviour vectors (badged **DEMO VECTOR** on the receipt). See `docs/VIVA_DEMO.md`
for a 7-minute script.

## Measured model performance

Synthetic data (6,000 rows, overlapping classes, 7% label noise), split by time 70/15/15, seed 42 — `model/metrics.json`:

| Metric (test set, newest 900 rows) | Value |
|---|---|
| Accuracy | 72.9% |
| Macro F1 | 0.700 |
| HIGH-class recall / PR-AUC | 0.840 / 0.801 |
| Brier score (3-class) | 0.383 |
| 5-fold CV accuracy (training period) | 69.7% ± 1.3% |
| HIGH payments auto-approved at 40/80 | 0.0% |

These describe how well the model recovers the generator's rule, not real-world fraud detection. The earlier
near-perfect accuracy figure came from non-overlapping synthetic classes and has been withdrawn.

## AI features and their limits

| Feature | Where | Limit |
|---|---|---|
| Risk explainer | receipt, "Why this decision" | rejected if it cites unknown evidence, invents a number or claims another outcome |
| Purpose tagger | on submit | escalate-only (to HOLD); never a model feature |
| HOLD copilot | `/admin/review/<tx>` | collapsed by default, no verdict field; the officer's reason must be their own words |
| Invoice reader | payment page (PDF) | an exact text check cross-checks the AI; mismatches only tighten the policy |
| Natural-language filter | transactions | becomes validated filter chips, never SQL; always tenant-scoped |
| SME assistant | receipt | own record + FAQ only; refuses evasion and other customers; 10 questions per payment per day |
| Report drafts | `/admin/reports` | numbers must come from the database; DRAFT until an officer signs |

Measured on a live golden set: explainer 17/20 passed every guard, purpose tagger escalation precision 1.00 / recall
0.90 (`docs/AI_EVALUATION.md`). Red-team suite: 45/45 cases safe with a model scripted to obey every attack, and 45/45
live (`docs/AI_GUARDRAIL_MATRIX.md`, `docs/AI_REDTEAM_REPORT.md`).

## Security

Admin-only hold release, tenant isolation, CSRF protection, encrypted government IDs, a checksum-verified model file,
DLP on every AI payload, rate limits, and an HMAC-signed audit chain whose verification also detects edited
transaction rows. Threats, fixes and residual risks: `docs/THREAT_MODEL.md`. Full change history by finding ID:
`CHANGELOG.md`.

The Solidity contract in `blockchain/smart_contract.sol` is a **reference design, never deployed**; the address shown in
the UI is labelled "simulated".

## Project documentation

`docs/THREAT_MODEL.md` · `docs/AI_GUARDRAIL_MATRIX.md` · `docs/AI_EVALUATION.md` · `docs/AI_REDTEAM_REPORT.md` ·
`docs/VIVA_DEMO.md` · `docs/REUSE_INVENTORY.md` · `PROJECT_INTELLIGENCE_DOCUMENTATION.md` (original write-up, metrics updated).
