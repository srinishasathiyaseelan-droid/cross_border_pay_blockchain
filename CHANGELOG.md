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
