# AI guardrail matrix (P5.5)

Format reused from Aegis Node's `docs/AI_GUARDRAIL_MATRIX.md`. One row per guardrail. "Fail behaviour" is what
happens when the guardrail trips or errors; in every case the deterministic payment pipeline carries on.

**Design premise (OWASP LLM01):** prompt injection cannot be reliably filtered, so the defence is architectural.
The LLM has no tools and no write access, and its signals can only escalate a payment to HOLD. The filters below are
tripwires layered on top of that.

| # | Guardrail | Implementation | Location | Enforcement point | Fail behaviour | Tests | Remaining gap |
|---|---|---|---|---|---|---|---|
| 1 | LLM never decides (G1, G11) | `evaluate()` has no LLM parameter; AI codes only raise APPROVED→HOLD; no verdict field in any schema | `crosspay/policy/engine.py`, `crosspay/ai/schemas.py` | every payment | n/a (structural) | `test_ledger_p3.py::test_ai_escalations_never_lower`, `::test_policy_signature_has_no_llm_argument`, `test_ai_foundation_p5.py::test_explain_schema_has_no_verdict_field`, red-team RT39–RT43 | — |
| 2 | Kill switch / LLM_ENABLED | config flag + `ai_settings.kill_switch` | `crosspay/ai/budget.py` | first step of `run_task` | `DISABLED`, nothing calls out | `test_disabled_layer_never_calls_out`, `test_kill_switch_disables_at_runtime` | — |
| 3 | Daily budget (LLM06) | estimated cost per call summed per UTC day | `crosspay/ai/budget.py`, `log.py` | before the call | `UNAVAILABLE` until midnight UTC | `test_budget_exhausted_returns_unavailable` | prices are estimates (`LLM_PRICE_*` env to correct) |
| 4 | Input normalisation (G13) | NFKC, strip zero-width, bidi and Unicode-tag characters | `crosspay/ai/input_guard.py::canonicalize` | every user field | hidden text never reaches the model | RT19, RT20 | ZWJ/ZWNJ are also stripped from Hindi/Telugu (rendering only) |
| 5 | Delimiting and escaping (G14) | `<user_data name=…>` wrapper, `<`/`>` escaped, closing tag inside content = BLOCK | `input_guard.prepare` | every user field | `BLOCKED_INPUT` | RT10–RT12 | — |
| 6 | Size caps (LLM06) | notes 500, chat 1,000, receiver 120, query 300, invoice text 12,000 chars; PDF ≤ 5 MB, ≤ 10 pages | `input_guard.CAPS`, `tasks.extract_pdf_text` | before the call | truncated / `TOO_MANY_PAGES` | RT36, RT37 | — |
| 7 | Injection tripwire on input (G10, G15) | 8 signal families incl. payment phrasing, Hindi/Telugu, base64, ROT13, homoglyph folding, spaced text | `input_guard.evaluate` | every user field | `BLOCKED_INPUT`; call skipped; evidence item `NOTES_INSTRUCTION_LIKE_TEXT` for the officer; escalate-only HOLD (see holdout) | `tests/ai/redteam/` RT01–RT26, holdout below | English/Hindi/Telugu only; new phrasings will get through (by design the architecture still holds) |
| 8 | Forbidden keys (LLM02) | allow-listed facts; recursive key check incl. PII and threshold names | `crosspay/ai/schemas.py::check_forbidden_keys`, `crosspay/ai/context.py` | before the call | `BLOCKED_DLP` | `test_forbidden_keys_never_reach_a_provider` | — |
| 9 | DLP on the request (LLM02, G16) | Luhn PAN, JWT, bearer, provider keys, DB URI, private keys, EIN, PAN/GSTIN, IBAN, SWIFT, email, phone | `crosspay/security/dlp.py` | serialised request | `BLOCKED_DLP`, no call; DLP exception = fail closed | `test_dlp_blocks_before_any_call` | regex-based; unusual formats may pass |
| 10 | Least context, tenant scope (G4, G5, LLM08) | context built only from the session user's tenant-checked row; NL filter schema has no tenant field and the server applies `user_id` scope | `crosspay/ai/context.py`, `blueprints/api.py` | context building | n/a | RT29–RT31, `test_ai_features_p6.py::test_nl_filter_is_tenant_scoped` | — |
| 11 | System prompt rules (LLM01, LLM08) | data-not-instructions, no decisions, cite given IDs only, plain text, JSON only; written assuming users read it | `crosspay/ai/prompts/_base_v1.md` | every call | n/a | — | a prompt is not a control; rows 1, 12–16 are |
| 12 | Schema validation (LLM05) | Pydantic, `extra="forbid"`, enums, length and list caps; first-JSON extraction; one retry | `crosspay/ai/schemas.py`, `guard.extract_first_json_object`, `router.py` | response | retry once, then next provider, then `UNAVAILABLE` | `test_router_retries_schema_failure_once_then_falls_back`, RT31 | — |
| 13 | Citation check | every cited `ev_…` must be in the given evidence | `guard.check` | response | `REJECTED_GUARD:UNKNOWN_EVIDENCE_ID` | `test_invented_evidence_id_rejected`, RT40 | — |
| 14 | Number/ID faithfulness (G6, LLM07) | every number, amount, `TX-…` and `ev_…` in the output must appear in the input (rounding allowed) | `guard.unsupported_numbers/ids` | response | `REJECTED_GUARD:UNSUPPORTED_NUMBER/ID` | `test_invented_number_rejected`, RT30, RT41 | numbers written as words ("three") are not checked |
| 15 | Decision-word check (LLM07, G11) | output may not use an outcome word other than the stored decision | `guard.DECISION_WORDS` | explain, copilot, assistant | `REJECTED_GUARD:DECISION_CLAIM` | `test_decision_claim_rejected`, RT39, RT43 | strict: an honest "will be released or rejected" is rejected (seen live on RT30) |
| 16 | Markup and URL stripping (G7, LLM10) | Markdown images/links, URLs, data:/javascript:, HTML removed; rendered with Jinja autoescape / `textContent`, never `|safe` | `guard.clean_text`, templates, `static/js/script.js` | response + rendering | stripped, event logged | `test_markdown_image_and_url_are_stripped`, RT27 | — |
| 17 | Output tripwire (G10) | injection phrases, shell/SQL fragments in any text field | `guard._TRIPWIRE` | response | `REJECTED_GUARD:INJECTION_TRIPWIRE` | RT32, RT44 | — |
| 18 | DLP on the response (G8) | same detectors, redact before storing or showing | `guard.check` step 6 | response | redacted, event `OUTPUT_REDACTED` | — | — |
| 19 | Evasion coaching (G4) | deterministic refusal on the question; output check on the answer (added after red-team RT34 found a gap) | `crosspay/ai/tasks/__init__.py::_REFUSE/_EVASION_OUT` | assistant | `REFUSED` / `REJECTED_GUARD:EVASION_COACHING` | RT33–RT35, RT45 | English only |
| 20 | Rate limits (G17, LLM06) | Flask-Limiter 30/hour/user on AI endpoints, chat and upload; 10 chat turns per payment per day; job queue cap 50 | `crosspay/security/limiter.py`, `tasks.chat_turns_today`, `jobs.QUEUE_CAP` | routes | HTTP 429 / `CHAT_LIMIT` / `QUEUE_FULL` | RT38, `test_ai_features_p6.py` | in-memory limiter storage resets on restart |
| 21 | Logging and retention (G9) | `llm_calls` holds redacted input + hash, prompt version, model, guard outcome, tokens, cost; purge after 30 days | `crosspay/ai/log.py` | every call | logging errors never break the request | `test_dlp_blocks_before_any_call`, `test_valid_explanation_passes_and_is_logged_and_cached` | — |
| 22 | Human in the loop (G3) | copilot panel collapsed; officer reason ≥ 20 chars and < 80 % similar to the AI draft; agreement stored per review and shown per officer | `tasks.officer_reason_problem`, `blueprints/admin.py`, `/admin/ai` | officer review | form refused with a message | `test_ai_features_p6.py::test_officer_reason_must_be_own_words` | similarity is lexical; paraphrased rubber-stamping is not caught |
| 23 | Provider errors (LLM04) | error codes only (no raw exception text), circuit breaker, model name from env and logged | `crosspay/ai/router.py`, `errors.py` | every call | next provider / `UNAVAILABLE` | router tests | — |
| 24 | Supply chain (LLM04, LLM05) | pinned httpx/pydantic; prompts under CODEOWNERS; model trained only on generator labels (`label_source` column), LLM-labelled share 0 % | `requirements.txt`, `.github/CODEOWNERS`, `model/train_model.py` | review / training | — | — | — |

## Input-guard holdout

`python model/evaluation/guardrail_holdout.py` → `model/evaluation/guardrail_holdout.json`.
Fixtures: `tests/fixtures/guardrails/benign_notes.json` (200 notes: 150 English incl. 40 hard negatives such as
"override shipping rules per contract", "please ignore previous invoice", "approve the sample batch", "split
shipment"; 25 Hindi; 25 Telugu) and `adversarial_notes.json` (100 attacks).

| Measure | Value |
|---|---|
| Adversarial notes blocked (BLOCK) | 83 / 100 (83 %) |
| Adversarial notes flagged (BLOCK or RESTRICT) | 100 / 100 |
| Benign notes blocked (false-positive rate) | 0 / 200 (0 %) |

By category (BLOCK): override 9/9, role spoofing 9/9, delimiter 9/9, decision manipulation 9/9, extraction 9/9,
multilingual 8/8, base64 5/5, ROT13 5/5, zero-width 5/5, Unicode tags 5/5, homoglyphs 5/5, spaced 5/5. Evasion
phrasing (0/9) and exfiltration markup (0/8) are scored RESTRICT on purpose: they are not instructions to the model,
and they are handled downstream (the purpose tagger red-flags structuring, the assistant refuses evasion, the output
guard strips markup).

**Caveats.** Both fixture files are template-generated (not real customer notes), and they were visible while the
guard was tuned (unicode-tag, homoglyph and spaced-text detectors were added after the first run, which measured
71 % BLOCK / 88 % flagged). Treat these numbers as optimistic; a blind set of real notes is needed before production.

**Escalation decision.** The plan allows the input guard to escalate a payment to HOLD only if its measured FPR on
CrossPay's benign notes is ≤ 2 %. Measured: 0 %. So `INPUT_GUARD_ESCALATES=1` by default: a BLOCK skips the AI call,
adds the evidence item `NOTES_INSTRUCTION_LIKE_TEXT`, and sends an otherwise-approved payment to an officer. It can
never lower a decision. Set `INPUT_GUARD_ESCALATES=0` to make it evidence-only.

## Red-team suite

`tests/ai/redteam/cases.yaml` — 45 cases across direct override, role spoofing, delimiter breakout, indirect (invoice
text), encodings, Hindi/Telugu, exfiltration, evasion coaching, consumption and decision tampering. In CI the fake
provider is scripted to obey every attack; all 45 end with the expected guard code, an unchanged-or-stricter decision,
no other tenant's data and no URL. `docs/AI_REDTEAM_REPORT.md` holds the live run against the real provider chain.
