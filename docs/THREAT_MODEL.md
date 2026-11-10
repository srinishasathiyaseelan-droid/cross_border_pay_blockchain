# CrossPay threat model (P7)

Scope: the Flask app, its SQLite database, the derived ledger view, the Random Forest, and the advisory LLM layer.
The Solidity contract is a reference design that is never deployed.

## Actors

| Actor | Can do | Wants to |
|---|---|---|
| SME user | register, submit KYC, submit payments, read own receipts, chat about own payments | get a payment approved, see others' data, avoid review |
| Compliance officer (admin) | verify KYC, release or reject holds, run AI copilot and reports, kill switch | decide quickly (risk: rubber-stamping AI drafts) |
| External attacker | anonymous HTTP, CSRF via a victim's browser, hostile PDF/notes | act as admin, release holds, forge sessions, steal PII or keys |
| Malicious notes / invoices / receiver names | text that reaches an LLM | inject instructions, exfiltrate data, lower risk |
| Operator with DB file access | edit SQLite rows | rewrite history without detection |

## Trust boundaries

1. Browser → Flask: sessions (signed with `SECRET_KEY`), CSRF tokens on forms, same-origin check on JSON APIs, rate limits.
2. Flask → SQLite: per-request connection, one `BEGIN IMMEDIATE` transaction per settlement.
3. Flask → exchange-rate API: response trusted for rates only; a missing USD rate fails closed; stale rates are flagged.
4. Flask → LLM provider: everything sent is DLP-scanned, allow-listed and delimited; everything returned is untrusted.
5. Model file → app: checksum verified before unpickling.

## Findings and how they were fixed

| ID | Threat | Fix | Evidence |
|---|---|---|---|
| C1 | Anyone releases a HOLD | `@admin_required`, role read from DB | `tests/test_security_p1.py` |
| C2 | Password-less admin login | `/quick_login` 404 outside DEMO_MODE; random seed passwords | same |
| C3 | Forged sessions via public key | `SECRET_KEY` from env, required in prod | same |
| C4 | Sender chooses own risk features | features built from DB history | `tests/test_risk_pipeline_p2.py` |
| C5 | Self-verified KYC | PENDING until an officer decides | same |
| C6 | Werkzeug debugger RCE | debug only with `FLASK_DEBUG=1`; gunicorn | P0 |
| H1 | Fabricated scores | deterministic score; no `random` | P2 tests |
| H2 | Block mined before insert; ID collisions | ULID IDs; atomic insert→decide→block→audit→commit | `tests/test_ledger_p3.py` |
| H3 | Cross-tenant reads | tenant scope on every query; 404 for others' receipts | P1 tests, live-feed tests |
| H4 | CSRF | Flask-WTF on forms; same-origin on JSON | P1 tests |
| H5 | Foreign amount scored as USD | USD from the same rate response or fail | P2 tests |
| H6 | Committed private keys | folder removed; keys treated as compromised | README; history not rewritten |
| H7 | Contract trusts caller's risk | `onlyOracle`; hashed government ID | `smart_contract.sol` |
| M1/M2 | Inflated ML claims; swapped pickle | honest data and metrics; checksum before load | `tests/test_ml_p4.py` |
| M3/M4 | Ledger/DB drift; re-mineable chain | HMAC audit chain is the source of truth; consistency check | P3 tests |
| M5–M9, L1–L7 | see CHANGELOG | | |
| LLM01–LLM10, G1–G18 | prompt injection, leakage, over-reliance, unbounded use | see `docs/AI_GUARDRAIL_MATRIX.md` | `tests/ai/` (45-case red-team suite) |

## Residual risks

- **Operator with DB and key access.** The HMAC chain detects edits by someone without `LEDGER_SIGNING_KEY`; someone with
  both the DB and the key can re-sign history. Anchoring the chain head to a public testnet would close this.
- **Legacy keys in git history** (commit d12451c). Purging needs a history rewrite and a force-push (not done).
- **Input-guard numbers are optimistic.** Fixtures are template-generated and were visible while tuning.
- **Decision-word check is strict.** It can reject an honest assistant answer ("will be released or rejected").
- **Single-node SQLite and an in-memory rate limiter.** Fine for a demo, not for multi-instance production.
- **SSE live feed** holds a worker thread per open dashboard.
- **Netvrio code licence.** Netvrio has no LICENSE file; settle it before publishing this branch.
- **DEMO_MODE** deliberately keeps quick logins and the KYC simulation; never enable it on a public deployment with real users.
