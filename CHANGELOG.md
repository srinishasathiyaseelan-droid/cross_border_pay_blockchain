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

## P3 — Ledger and database consistency (H2, H7, M3, M4, M8, M9, L2, L3)

**Findings fixed**
- **H2** Transaction IDs are `TX-` + ULID (48-bit ms time + 80 random bits). `crosspay/services/settlement.py` runs,
  inside one `BEGIN IMMEDIATE` transaction: claim idempotency key → INSERT as `PENDING_SETTLEMENT` → policy decision →
  build the PoW block in memory → UPDATE the row → append the HMAC audit record carrying the block → COMMIT. The
  explorer JSON is written only after COMMIT; any exception rolls back row, audit record and block together.
  A hidden `idempotency_key` + UNIQUE `(user_id, key)` row stops a double-submit (ported from Netvrio, SQLite not Redis).
- **H7** Solidity: `onlyOracle` on `processSettlement` (risk comes from the oracle, not the sender), `bytes32
  governmentIdHash` instead of the raw ID, header states it is a reference design. The UI labels the contract address
  "simulated (reference design, not deployed)".
- **M3** The audit chain in SQLite is the source of truth. `blockchain/blockchain_ledger.json` is untracked; the
  explorer view lives at `LEDGER_PATH` (default `instance/`), is rebuilt from the audit chain, and is written via temp
  file + `os.replace` under a cross-process file lock. Fixture rows get the same signed history at startup, so block #1
  is TX-2026-8801 in both the DB and the ledger.
- **M4** `crosspay/ledger/audit.py` (ported from Netvrio `audit_log.py`): HMAC-SHA256 with `LEDGER_SIGNING_KEY`,
  UNIQUE(previous_hash) fork guard, `verify()` and `verify_incremental()`. `Ledger.verify()` checks the genesis block,
  PoW hash/link/difficulty/numbering, the HMAC chain, and that every transaction row matches its signed audit record.
  Transaction hashes are SHA-256 over a canonical record (no `time.time()`). PoW difficulty defaults to 3 (config).
- **M8** Stale-rate policy: on an API failure the last good rates are served for up to
  `EXCHANGE_RATE_MAX_STALE_HOURS` (24) and flagged `stale=true` (stored as `rate_stale`); `is_cached` now means a real
  cache hit.
- **M9** `hold_reviews` table (tx, admin, action, reason ≥ 20 chars, KYC status at review, time); KYC is re-checked
  before a release; officer actions are signed into the audit chain.
- **L2** New timestamps are ISO-8601 UTC (`2026-11-10T12:00:00Z`), provider rate times are normalised.
- **L3** `REJECTED` is a first-class decision: KYC gate and officer rejections, with its own filter and badge.
- `crosspay/policy/engine.py` (ported from Netvrio): thresholds `REVIEW_AT=40`, `BLOCK_AT=80` from config; the model's
  class can only tighten the outcome; deterministic overrides and the AI escalation hook are stricter-only.

**Files:** `crosspay/ledger/{audit,chain,filelock}.py`, `crosspay/policy/engine.py`, `crosspay/security/idempotency.py`,
`crosspay/services/{settlement,currency}.py`, `crosspay/util.py`, `crosspay/db.py`, blueprints, templates,
`blockchain/smart_contract.sol`; `blockchain/blockchain_ledger.json` removed from git.

**Tests added:** `tests/test_ledger_p3.py` — forced IntegrityError after the decision → no row, no audit record, no
block, view unchanged; edited audit payload → HMAC failure; edited transaction row → mismatch reported; re-signing
without the key detected; double-submit → one transaction; 10 concurrent submits → 10 rows, contiguous blocks, valid
chain, view in sync; release needs a ≥ 20-char reason and records a review; release re-checks KYC; REJECTED filter;
stale-rate window; ISO timestamps; policy thresholds, KYC gate, AI escalations never lower and never block,
no LLM parameter in the policy signature; Solidity hardening present.

**How verified:** `pytest -q` → 98 passed.

## P4 — Honest ML (M1, M2)

**Findings fixed**
- **M1** `model/train_model.py::generate_sme_dataset()` draws one SME population: log-normal amounts that overlap
  across classes, Poisson counts, corridor risk from the real country table, labels from a noisy latent rule plus
  7% label noise, and a `created_at` per row. Split by time 70/15/15. Seed stays 42.
  `purpose_risk` is not a model feature (G1); the RF keeps its 7 features.
- **M2** The artefact stores `sklearn_version` and `feature_names`; `model/model_card.json` stores its sha256,
  version, features and `trained_at`. The app checks the checksum **before** unpickling, then version and feature
  names; any failure logs the reason, uses the fallback engine, and records `scoring_engine='fallback'` per payment
  (the dashboard shows the reason).
- `Scorer.top_factors()` returns the 3 largest per-feature contributions to the 0-100 score using a tree-path
  decomposition (treeinterpreter method, no new dependency); bias + contributions equals `predict_proba` exactly.
- The medium demo vector was re-chosen (28,500 USD to India, 5 payments/30 d, 12 previous, 0 flags, 10 months)
  because the old one scores HIGH under the honest model.
- Every 98.67% claim (README, PROJECT_INTELLIGENCE_DOCUMENTATION.md, dashboard, landing page) replaced with measured
  values; the 28 `file:///C:/Users/NISHA/...` links in PROJECT_INTELLIGENCE_DOCUMENTATION.md are relative now (**L5**).

**Measured (seed 42, test = newest 900 rows):** accuracy 0.7289, macro F1 0.7002,
Brier (3-class) 0.3832. Per class P/R/F1/PR-AUC: LOW 0.864/0.790/0.825/0.889,
MEDIUM 0.525/0.548/0.536/0.507, HIGH 0.660/0.840/0.739/0.801.
5-fold CV (training period) accuracy 0.6969 ± 0.0132, macro F1 0.6614 ± 0.0154.
Policy at REVIEW_AT=40 / BLOCK_AT=80 on test: 84.0% of HIGH blocked, 0.0% of HIGH approved,
78.2% of LOW approved, 29.8% of payments held for review.

**Files:** `model/train_model.py` (rewritten), `model/random_forest_model.pkl`, `model/model_card.json`,
`model/metrics.json`, `model/evaluation/` (train/validation/test CSVs, `threshold_results.csv`,
`false_negatives.jsonl`, `final_evaluation_report.json`); `model/dataset.csv` removed;
`crosspay/services/scoring.py`, `crosspay/__init__.py`, templates, docs.

**Tests added:** `tests/test_ml_p4.py`: retraining twice gives identical metrics; committed metrics equal a fresh
run; class amounts overlap; version or checksum mismatch → fallback, logged, stored per payment, shown on the
dashboard; a swapped pickle is never unpickled; top factors present and the decomposition is exact; the three demo
scenarios still give LOW→APPROVED, MEDIUM→HOLD, HIGH→BLOCKED; no 98.67/98.66 left in docs, templates or code.

**How verified:** `pytest -q` → 109 passed.

## P5 — AI foundation (advisory LLM layer)

Everything below is advisory. `policy.engine.evaluate()` takes no LLM argument; the only path from AI into a
decision is the escalate-only `ai_escalations` hook added in P3.

- **Providers** `crosspay/ai/providers/` (ported from Netvrio): `base.py` (`complete()` → raw text + usage,
  `complete_json()` → schema-validated model), `openai_compat.py` (Groq, NVIDIA NIM), `cloudflare.py`, `fake.py`
  (`FakeLLMClient`, scripted, used by every test). Keys and model names come only from env. Live check on
  2026-11-10: Groq `openai/gpt-oss-120b` answered in 0.8 s; NVIDIA `openai/gpt-oss-20b` timed out at 25 s;
  the supplied Cloudflare token returned HTTP 401 "Authentication error". Fallback order `groq,nvidia,cloudflare`.
- **Router** `crosspay/ai/router.py` (ported from Netvrio, Aegis error classifier in `crosspay/ai/errors.py`):
  priority fallback, per-call timeout, one retry on a schema failure, circuit breaker (3 failures → skip 60 s), stores
  error codes only, never raises.
- **Schemas** `crosspay/ai/schemas.py`: one response model per task, `extra="forbid"`, no verdict field anywhere
  (G11); FORBIDDEN_KEYS extended with CrossPay PII and threshold names.
- **DLP** `crosspay/security/dlp.py` (ported from Netvrio + EIN, PAN/GSTIN, IBAN, SWIFT, email, phone, provider key
  shapes); a hit on the request blocks the call (`BLOCKED_DLP`), any DLP exception fails closed.
- **Evidence** `crosspay/ai/evidence.py`: deterministic `ev_<hash6>_<n>` items from features, top factors, corridor,
  90-day median, history, FX snapshot and policy reasons; no thresholds.
- **Guard** `crosspay/ai/guard.py` (Netvrio citation check made null-safe + Aegis parser/sanitiser): first-JSON
  extraction, citation check, number/ID faithfulness, decision-word check, URL/Markdown-image/HTML stripping,
  tripwire, output DLP redaction.
- **Pipeline** `crosspay/ai/pipeline.py::run_task()` is the single entry point (kill switch → budget → input guard →
  forbidden keys → DLP → cache → router → output guard → log → cache). Prompts in `crosspay/ai/prompts/*.md` with
  version tags; user text is wrapped in `<user_data>`.
- **Tables** `llm_calls` (redacted input + hash only), `ai_cache`, `ai_jobs`, `ai_settings`, `risk_explanations`;
  transaction columns for purpose results, `ai_escalations` and `input_guard_flags`.
- **Budget / kill switch** `crosspay/ai/budget.py`: `LLM_DAILY_BUDGET_USD` (estimated cost per provider, configurable),
  runtime kill switch on `/admin/ai`.
- **Background jobs** `crosspay/ai/jobs.py`: `ThreadPoolExecutor(max_workers=2)` + `ai_jobs`, queue cap 50
  (`QUEUE_FULL`); `GET /api/ai/<task>/<tx_id>` for polling (tenant-scoped).
- **/admin/ai**: provider circuit state, calls today, rejections by guard code, spend vs budget, kill switch, flags,
  officer agreement with AI drafts.
- The purpose tagger is already called on payment submit (it is needed for the injection acceptance test); its UI
  and the other features land in P6.

**Tests added:** `tests/ai/test_ai_foundation_p5.py` (23): LLM_ENABLED=0 → no outbound call and no `llm_calls` row;
kill switch; DLP blocks EIN, email, card, IBAN before any call and the log holds only redacted text; forbidden keys;
invented evidence ID / number / decision claim → `REJECTED_GUARD`; valid output logged and cached; Markdown image and
URL stripped; first-JSON extractor; null-safe guard; injection in the notes of a HIGH payment → input guard skips the
call, decision stays BLOCKED; router timeout → fallback, all fail → None + meta, schema retry, circuit breaker,
no raw exception text; budget exhausted → UNAVAILABLE; /admin/ai access; no verdict field in any schema.

**How verified:** `pytest -q` → 132 passed.

## P5.5 — Guardrails (G1–G18, OWASP LLM Top 10 2026)

- **Input guard** `crosspay/ai/input_guard.py` (ported from Aegis Node `guardrails.py`, MIT): NFKC, zero-width / bidi /
  Unicode-tag stripping (G13), `<user_data>` wrapping with `<`/`>` escaped and closing-tag detection (G14), size caps,
  8 signal families with payment phrasing, Hindi and Telugu (G15), base64, ROT13, homoglyph folding and spaced-text
  collapsing. Aegis's "override … rules anywhere" false positive is removed.
- **Holdout** `tests/fixtures/guardrails/` (200 benign incl. 40 hard negatives, 25 Hindi, 25 Telugu; 100 adversarial;
  template-generated) and `model/evaluation/guardrail_holdout.py`: **83 % of attacks blocked, 100 % flagged, 0/200
  benign blocked** (first run before the tag/homoglyph/spacing detectors: 71 % / 88 % / 0 %). The fixtures were visible
  while tuning, so the numbers are optimistic. FPR ≤ 2 %, so `INPUT_GUARD_ESCALATES=1`: a BLOCK skips the AI call, adds
  `NOTES_INSTRUCTION_LIKE_TEXT` as evidence, and can move an otherwise-approved payment to HOLD (never lower).
- **Escalate-only hook** (G1, G2): the P3 policy engine's `ai_escalations` is now fed by the purpose tagger
  (`PURPOSE_RED_FLAG` when purpose_risk ≥ 0.7 or any red flag) and the invoice diff; `purpose_risk` never enters the RF.
- **Evasion coaching** (G4): deterministic refusal on the question, plus an output check on the assistant's answer,
  added after red-team case RT34 found that an innocent-looking question could get a coaching answer past the guard.
- **Chat cap** (G17): 10 assistant turns per payment per user per day (`CHAT_LIMIT`).
- **Red-team suite** `tests/ai/redteam/cases.yaml` (45 cases, 10 categories) + `test_redteam.py`: the fake provider
  obeys every attack; every case ends with the expected guard code, a decision never less strict than the baseline,
  no other tenant's data and no URL. `tests/ai/redteam/live.py` (`pytest -m live_redteam`) ran the same cases against
  Groq `openai/gpt-oss-120b` → `docs/AI_REDTEAM_REPORT.md`: **45/45 safe**; several cases ended `UNAVAILABLE`
  (provider timeouts/rate limits) and the decision-word check rejected one honest assistant answer (false positive,
  documented). The prompts now tell the model to avoid outcome words other than the stored decision.
- **Docs** `docs/AI_GUARDRAIL_MATRIX.md` (Aegis format, 24 rows with tests and remaining gaps).
- **Supply chain** `.github/CODEOWNERS` on prompts, guards and the policy engine.

**How verified:** `pytest -q -m "not live_redteam"` → 178 passed; live red-team 45/45 safe.

## UI redesign + P6 — AI features (partial: feature tests and P6.8 still to do)

- **UI:** token-based theme (dark default, light via system or toggle), original inline SVG icon sprite (works
  offline), glossy 3D icon tiles, pressable 3D buttons, cursor-glow cards, CSS 3D block-chain hero with a particle
  canvas, risk gauge, Chart.js pinned to 4.4.6 and re-themed on toggle, mobile nav; motion off under
  `prefers-reduced-motion`. Every page was rewritten (`templates/*.html`, `_macros.html`, `_icons.html`, `static/css/style.css`,
  `static/js/script.js`).
- **P6.1** "Why this decision" card on the receipt (polls the background job; falls back to the model's top factors).
- **P6.2** purpose tagger on submit (escalate-only).
- **P6.3** `/admin/review/<tx>`: facts on the left, a collapsed AI copilot on the right, the officer's own reason
  (≥ 20 chars, < 80 % similar to the AI draft), and the agreement stored per review.
- **P6.4** PDF invoice reader (`/api/ai/invoice`, ≤ 5 MB, magic-byte check, stored outside `static/`) with an exact
  text cross-check; mismatches can only make the policy stricter.
- **P6.5** natural-language filter → validated chips → parameterised, tenant-scoped query.
- **P6.6** SME assistant chat on the receipt (own record + FAQ, refusals, 10 turns per payment per day).
- **P6.7** `/admin/reports`: weekly summary and blocked-payment narrative, DRAFT until signed, Markdown export.
- Live check: a demo MEDIUM payment ended HOLD; Groq purpose tagger (1.6 s) and explanation (2.1 s) passed the guards.

**Not done yet:** dedicated P6 tests (`tests/ai/test_ai_features_p6.py`), P6.8 (optional), P7 (CI, docs, README).
**How verified:** `pytest -q -m "not live_redteam"` → 178 passed; manual run in the browser.
