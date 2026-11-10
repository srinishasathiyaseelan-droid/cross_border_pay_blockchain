# Reuse inventory (P0.5)

Read-only survey of the two reference folders, done 2026-11-10. Nothing was copied wholesale; each row
below was re-written as an adapted module with the header `Adapted from <source> — <what changed>`.

| Reference | Path | Commit | Licence | Stack |
|---|---|---|---|---|
| Netvrio | `C:\Users\sunny\Downloads\projects\RAZAORPAY AI` (github.com/sandysunny99/razorpay-ai-risk-manager) | **98bbc09** (the plan names 1d41992; the local clone has moved on) | **No LICENSE file** | FastAPI + SQLAlchemy + httpx |
| Aegis Node | `C:\Users\sunny\Downloads\projects\AI FULL STACK PROJECT\Aegis-Node` (github.com/sandysunny99/aegis-node) | 4e64429 | MIT | FastAPI + SQLite |

**Approval.** The user asked in chat on 2026-11-10 to use the RAZAORPAY AI folder to fix the audit issues and
supplied the plan that names Aegis Node as the P5.5 source. The rows below are ported on that basis.

**Open item (licence).** Netvrio has no LICENSE file and CrossPay belongs to another account. Before this branch
is pushed or merged, add an MIT LICENSE to Netvrio (or get written agreement from the CrossPay owner). The
reference folders are read-only here, so this was not done automatically.

## Module map

| Source path | What it does | CrossPay target | How adapted | Risks / flaw fixed while porting |
|---|---|---|---|---|
| Netvrio `backend/llm/interfaces.py`, `router.py`, `errors.py`, `health.py` | Provider ABC + priority fallback router | `crosspay/ai/providers/base.py`, `crosspay/ai/router.py` | Synchronous; `complete_json(system, user, schema, timeout)`; circuit breaker (3 failures → skip 60 s); one retry on schema failure; never raises | Dead "Test 1" try/pass removed; raw exception text no longer stored (error codes only) |
| Netvrio `backend/llm/providers/openai_compat.py`, `groq.py`, `nvidia.py`, `cloudflare.py` | HTTP adapters | `crosspay/ai/providers/openai_compat.py`, `cloudflare.py` | Model name always from env; returns raw text to the guard | Hard-coded default models removed |
| Netvrio `backend/llm/schemas.py` | Request/response models with forbidden-key scan | `crosspay/ai/schemas.py` | One response model per task, `extra="forbid"`, **no `recommended_action`/verdict field (G11)** | `"41112222"` literal check replaced by the DLP engine (G12); FORBIDDEN_KEYS extended with government_id, email, address, phone, account_number, iban, swift |
| Netvrio `backend/llm/policy.py` | Evidence-citation check | `crosspay/ai/guard.py` | Null-safe, length caps, HTML stripping, case-insensitive tripwire over all text fields, decision-word check | Crashed when `explanation` was None |
| Netvrio `backend/evidence/builder.py` | Evidence package | `crosspay/ai/evidence.py` | Items built from CrossPay features | Random UUID IDs replaced by deterministic `ev_<tx>_<n>` + content hash |
| Netvrio `backend/policy/engine.py` | Deterministic decision, stricter-only overrides | `crosspay/policy/engine.py` | REVIEW_AT/BLOCK_AT from config; `ai_escalations` can only raise to HOLD; no LLM argument | None (core of the "LLM never decides" claim) |
| Netvrio `backend/audit/audit_log.py` | Hash-chained audit log, fork guard, incremental verify | `crosspay/ledger/audit.py` | sqlite3 instead of SQLAlchemy; UNIQUE(previous_hash) fork guard kept | Unkeyed SHA-256 replaced by HMAC-SHA256 with `LEDGER_SIGNING_KEY` |
| Netvrio `backend/security/idempotency.py` | Double-submit guard | `crosspay/security/idempotency.py` | SQLite UNIQUE row instead of Redis | — |
| Netvrio `backend/app/security/dlp.py` | Luhn PAN, JWT, API key, DB URI, private key detectors | `crosspay/security/dlp.py` | Added US EIN, India PAN/GSTIN, IBAN, email, phone, SWIFT/BIC, Groq/NVIDIA/Cloudflare key shapes | — |
| Netvrio `backend/realtime/velocity.py` | Sliding velocity counter | Idea only | 30-day features come from SQL over `transactions` | Clears all keys when full (exploitable); not ported |
| Netvrio `backend/tests/llm/*` | Boundary, payload, router, schema tests | `tests/ai/` | Rewritten against CrossPay classes + an end-to-end "fake LLM says APPROVE on HIGH" test | — |
| Netvrio `evaluation/` layout | Threshold sweep, false-negative review | `model/evaluation/` | Same file layout for the CrossPay RF | — |
| Netvrio `.github/workflows/ci.yml`, `codeql.yml`, `render.yaml` | CI and deploy | same paths | Commands changed for Flask/pytest | Netvrio's committed scratch files (`pytest_output.txt`, `*_list.txt`, `audit_report.json`) not copied |
| Aegis `backend/services/guardrails.py` | Input guardrail: canonicalise, bounded base64 decode, 7 signal families | `crosspay/ai/input_guard.py` | Added payment signals ("mark as low risk", "approve this payment", "skip review", "split into smaller payments") and Hindi/Telugu phrasings; "override … rules" no longer fires on its own | English-only regex; Aegis's own holdout: 80 % detection / 20 % FPR, so it is **not** an escalation trigger unless CrossPay's measured FPR ≤ 2 % |
| Aegis `backend/services/llm_service.py` (`_extract_first_json_object`, `_validate_and_parse`, `_sanitize_llm_output`, `_DANGEROUS_PATTERNS`) | Output parsing and sanitising | `crosspay/ai/guard.py` | Stack-based first-object extractor, 4,000-char cap, dangerous-pattern rejection, per-field HTML/control-char stripping, list caps | Its schema has a `verdict` field; CrossPay schemas do not. Added number/ID faithfulness check (its documented gap) |
| Aegis `backend/services/llm_error_classifier.py` | Error categories, Retry-After clamp | `crosspay/ai/errors.py` | Used by the router | — |
| Aegis `backend/limiter.py` | Trusted-proxy-aware client IP | `crosspay/security/limiter.py` | Flask-Limiter; per user, per IP for anonymous routes | — |
| Aegis `tests/benchmark_holdout.py`, `test_llm_security.py` | Holdout harness | `tests/ai/redteam/`, `model/evaluation/guardrail_holdout.py` | New CrossPay fixtures (benign + adversarial payment notes) | — |
| Aegis `docs/AI_GUARDRAIL_MATRIX.md` | Matrix format | `docs/AI_GUARDRAIL_MATRIX.md` | Same columns, CrossPay rows | — |

Not ported: Netvrio `hmac.py`/`replay.py` (CrossPay has no inbound webhooks), Aegis `turnstile.py` (needs a site key;
off by default in the plan), the Grok/Hugging Face/Gemini adapters (no keys supplied).

## Secret scan of the reference folders

`gitleaks dir <folder> --redact` (gitleaks 8.30.1), files >5 MB skipped. **Values were never printed.**

| Folder | Hits | Where (file only) | Assessment |
|---|---|---|---|
| Netvrio | 273 | 247 + 3 in `.venv/Lib/**` | Third-party package test data; not copied |
| | 11 | `.env` | Real local secrets; gitignored there; **never opened or copied** |
| | 2 | `backend/app/api/routes_security.py:141`, `backend/app/security/masking.py:53` (+ its `.pyc`) | Test/example strings in source; neither file was ported |
| | 7 | `dev/context-mode/tests/fixtures/github-issues.json`, `dev/context-mode/tests/session/session-extract.test.ts`, `dev/token-savior/tests/test_config_integration.py` | Vendored tool fixtures; not ported |
| | 1 | `docs/IMPLEMENTATION_AUDIT.md:13` | Not ported |
| Aegis Node | 146 | 132 in `.venv/Lib/**` | Third-party packages; not copied |
| | 10 | `.env` | Gitignored; **never opened or copied** (plan rule) |
| | 4 | `RENDER_GROQ_TURNSTILE.env` | Gitignored; **never opened or copied** (plan rule) |

CrossPay itself (`gitleaks git`, history of d12451c): 10 hits, all under `_legacy_archive/` — the public Hardhat #0
key in `scripts/deploy*.js` and `docker-compose.yml`, and credentials in `application.properties` (+ copies under
`target/`). This confirms **H6**; the folder is removed in P1 and the keys must be treated as compromised.
