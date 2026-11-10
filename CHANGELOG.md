# Changelog — branch `hardening-llm`

Finding IDs (C1–C6, H1–H7, M1–M9, L1–L7) and phase IDs (P0–P7) refer to
"Cross-Border Pay Blockchain — Audit, LLM Integration Plan & Cowork Instructions" (10 Nov 2026).

## P0 — Baseline and test harness (M6, M7, L7)

**Baseline (before any change).** `docs/baseline_test_run.txt`: the original 12 unittest cases and the
12 `test_flow.py` checks all passed on commit d12451c, but the run rewrote the tracked
`blockchain/blockchain_ledger.json` (23 → 26 blocks) and called the live FX API.
`docs/baseline_findings_probe.txt` (FX mocked) reproduced C1, C2, C3, C4, C5, C6, H2, H3, H4, H5, L1, M8 at runtime.

**Findings fixed:** M6 (per-request connection on `flask.g` + `teardown_appcontext`), M7 (tests use temp DB/ledger,
FX mocked, pytest discovers everything), L7 (pinned requirements, `.env.example`, `Procfile`).
C6 is also closed here as a side effect: `app.py` only enables debug when `FLASK_DEBUG=1`.

**Files changed**
- New package `crosspay/`: `create_app()` in `__init__.py`, `config.py` (Dev/Test/Prod/Demo), `db.py`,
  blueprints `auth`, `kyc`, `payments`, `admin`, `api`. Routes moved without behaviour changes.
- Moved with history: `currency_service.py` → `crosspay/services/currency.py`,
  `blockchain/blockchain.py` → `crosspay/ledger/chain.py` (ledger path now a constructor argument),
  `database/db.py` → `crosspay/db.py`.
- Import-time `init_db()` and `load_ml_model()` removed; the model is loaded once per app (cached per file).
- `app.py` is now a launcher. Timestamps written by new code are ISO-8601 UTC.
- Templates: `url_for()` endpoints renamed to blueprint names.
- `requirements.txt` pinned exactly (scikit-learn 1.9.1 = the version that pickled the committed model; it loads
  without an InconsistentVersionWarning), `requirements-dev.txt`, `pytest.ini`, `.env.example`, `Procfile`, `.gitignore`.

**Tests added:** `tests/conftest.py` (fixtures `app`, `client`, `sme_client`, `admin_client`, `fx_mock`, `db`),
`tests/test_currency.py` (unittest suite converted), `tests/test_flow.py` (script converted to test functions).

**How verified:** `pytest -q` → 26 passed; `git status` unchanged after the run (DB and ledger live in `tmp_path`).

## P0.5 — Reuse inventory

**Files:** `docs/REUSE_INVENTORY.md` (module map for Netvrio @98bbc09 and Aegis Node @4e64429, secret-scan summary).

**How verified:** `gitleaks dir --redact` over both reference folders (hits listed by file only; the `.env` files were
never opened); `gitleaks git` over CrossPay history confirms H6 (Hardhat #0 key in `_legacy_archive/scripts/deploy*.js`).
Approval to port: the user's chat request of 2026-11-10. Open item: Netvrio has no LICENSE file.

## P1 — Security lock-down (C1, C2, C3, C6, H3, H4, H6, L4, L6)

**Findings fixed**
- **C1** `resolve_hold` is `@admin_required`; the role is read from the `users` table, so a forged `user_role` cookie
  value is ignored. Release/Reject controls render only for admins.
- **C2** `/quick_login/<role>` is `@demo_only` (404 unless `DEMO_MODE=1`). Seed passwords come from
  `DEMO_SME_PASSWORD` / `DEMO_ADMIN_PASSWORD`, random when unset; the login page no longer pre-fills `sme123`.
- **C3** No hard-coded key. `SECRET_KEY` (and `LEDGER_SIGNING_KEY`) are required when `CROSSPAY_ENV=prod`; dev/demo
  generate a random key under `instance/` (gitignored).
- **C6** (closed in P0) debug only when `FLASK_DEBUG=1`; `Procfile` runs gunicorn.
- **H3** `/result`, `/transactions`, `/dashboard`, `/blockchain`, `/payment`, `/api/validate_chain` need login.
  SMEs see only their own rows (another tenant's receipt is a 404); the explorer redacts other tenants' block payloads;
  the dashboard shows SME-scoped numbers. Admins see everything.
- **H4** `CSRFProtect` with `{{ csrf_token() }}` in the login, register, KYC, payment, resolve (×2) and logout forms.
  The JSON API is exempt from token CSRF but unsafe methods must pass a same-origin (Origin/Referer) check.
  Logout is POST-only.
- **H6 / L4** `_legacy_archive/` (8.3 MB) removed; README warns that its keys are compromised. History not rewritten (ask).
- **L6** government IDs are Fernet-encrypted at rest (legacy rows encrypted on startup) and shown masked (last 4);
  passwords need ≥ 10 characters; email format validated.

**Files:** `crosspay/security/decorators.py`, `crosspay/security/pii.py`, blueprints, templates, `templates/error.html`,
`README.md`, `requirements.txt` (+ cryptography).

**Tests added:** `tests/test_security_p1.py` — anonymous resolve → 302 with HOLD unchanged; SME resolve → 403; forged
role cookie → 403; cross-tenant receipt → 404; POST without CSRF token → 400; cross-origin API POST → 403;
`/quick_login` → 404 when `DEMO_MODE=0`; prod without SECRET_KEY refuses to start; registration rules; encrypted and
masked government ID; logout needs POST.

**How verified:** `pytest -q` → 45 passed, working tree unchanged after the run.

## P2 — Honest risk pipeline (C4, C5, H1, H5, M5, L1)

**Findings fixed**
- **C4** `crosspay/services/features.py::build_features()` derives all seven model features on the server:
  frequency = this SME's payments in the last 30 days, previous_transactions = total, suspicious_transactions =
  HOLD + BLOCKED + REJECTED (+ any payment that went through hold review), account_age = whole months since
  `users.created_at` (min 1), corridor_risk from the country table, amount_to_age_ratio. The four behavioural form
  fields are gone and are ignored if posted. In DEMO_MODE the scenario buttons send `scenario=low|medium|high`, which
  loads a fixed server-side vector; the receipt shows a **DEMO VECTOR** badge. Outside DEMO_MODE `scenario` is ignored.
- **C5** a KYC submission goes to PENDING. Only an admin (`/admin/kyc`, reason ≥ 10 characters, reviewer recorded)
  sets VERIFIED. The "simulated provider" buttons exist only in DEMO_MODE and are labelled DEMO SIMULATION.
- **H1** `crosspay/services/scoring.py::Scorer.score()` stores p_low/p_med/p_high, the engine and
  score = round((p_med·0.5 + p_high)·100, 1). No `random` anywhere in scoring; the fallback engine uses transparent
  rule points and never invents probabilities.
- **H5** the target rate and the USD reference rate come from the same base response (one API call); a missing USD
  rate raises `ExchangeRateAPIError`, the user sees "nothing was stored".
- **M5** the payment page's live preview calls `POST /api/risk_preview`, which runs the same `build_features` +
  `Scorer` path and writes nothing.
- **L1** receiver 2–120 characters; both countries must be in the corridor table (no silent 0.45 default).

**Files:** `crosspay/services/features.py`, `crosspay/services/scoring.py`, `crosspay/services/currency.py`,
`crosspay/blueprints/{payments,kyc,admin,api}.py`, `templates/{payment,kyc,result,base,admin_kyc}.html`,
`static/js/script.js` (rewritten), `crosspay/db.py` (new columns; demo SME opened 26 months ago, history dated
45/20/9 days back).

**Tests added:** `tests/test_risk_pipeline_p2.py` — posted `suspicious_transactions=0` ignored; same input → same
score ×10; INR→EUR with USD missing → clear error and no row; USD amount from one response; new user stays PENDING
for every `simulate_action` when DEMO_MODE=0; admin queue verifies with a reason; SME gets 403 on the queue; receiver
and country validation; preview equals the stored score and writes nothing; demo vector badge; scenario ignored
outside DEMO_MODE.

**How verified:** `pytest -q` → 60 passed.
