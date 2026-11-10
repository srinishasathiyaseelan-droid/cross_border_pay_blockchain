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
