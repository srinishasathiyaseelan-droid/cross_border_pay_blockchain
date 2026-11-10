# CrossPay hand-off (2026-11-11)

## Current state

- Repo: <https://github.com/srinishasathiyaseelan-droid/cross_border_pay_blockchain>.
- Live: <https://crosspay-i4gl.onrender.com> (Render, auto-deploys from `main`).
- `main` = `a2ae3a2` (PR #9). Everything through PR #9 is merged and live: hardening, the advisory AI layer and its
  guards, the redesigned UI, the live console (`/admin/live`), the VELOCITY_BURST rule, the simulator scenarios, the
  AI self-test, the rate-limit pacing, the report-figures fix, the README, `docs/DEPLOY_RENDER.md`, the demo dataset
  (PR #8) and its startup fix (PR #9).
- Checked on the live site on 2026-11-11, after the PR #9 deploy went Live:
  - `/healthz`, `/` and `/login` return 200.
  - All 10 "Demo …" SMEs are listed on `/admin/kyc`.
  - `/api/live/stats`: 143 payments (112 approved / 11 hold / 20 blocked).
  - `/api/validate_chain`: valid; genesis plus 112 settlement blocks, 143 HMAC-signed audit records, no mismatches.
- No open branches. Merged branches that can be deleted: `fix/report-figures` (reached `main` via PR #7),
  `feat/demo-dataset` and `fix/demo-seed-startup`.

## PR #9: `fix/demo-seed-startup` (merged, live as `a2ae3a2`)

The PR #8 deploy (`6821f18`) failed on Render; PR #9 fixed it.

- Cause: PR #8 started the seed thread in the middle of `create_app`. The seed holds the SQLite write lock for tens of
  seconds (locally 12.7 s, then 9.0 s for mining), so the startup writes after it (LLM log purge, `ai_jobs` reset)
  waited for the lock. Locally `create_app` went from 10.1 s to 31.9 s; on Render's smaller CPU the wait passes the
  30 s `busy_timeout`, "database is locked" is raised and the gunicorn worker fails to boot. (Inferred from the local
  reproduction; the Render deploy log itself was not read.)
- Fix: the seed starts as the last step of `create_app`, after every startup write, and waits `DEMO_DATASET_DELAY`
  seconds (default 20) in a daemon timer, so the worker is serving and the health check passes first. Locally
  `create_app` is back to 9.2 s. Two regression tests cover the order and the timer.
- While the seed runs, other DB *writes* wait for the lock; reads are unaffected (WAL). It has already run on
  Render's disk (marker `demo_dataset_v1`), so later deploys skip it unless the database is reset.

## PR #8: `feat/demo-dataset` (merged)

- In DEMO_MODE only, it adds once (marker `demo_dataset_v1` in `ai_settings`; `DEMO_DATASET=0` turns it off):
  - 10 "Demo …" SMEs with verified KYC
  - 140 payments: clean history 5–12 months back, plus 80 payments over the last 4 months
- Every payment is decided by the real feature builder, model and policy engine (including VELOCITY_BURST), then
  signed and mined by `bootstrap_ledger`, so `Ledger.verify` stays valid.
- No FX or AI calls (fixed, labelled demo rates) and no officer reviews.
- It runs in a background thread `DEMO_DATASET_DELAY` seconds (default 20) after startup. There is also
  `flask seed-demo`; run it with `AI_BACKFILL=0`, or the process waits for the spaced AI jobs before it exits.
- Local result: 2 → 12 users, 5 → 145 payments (112 approved / 13 hold / 20 blocked); the ledger verifies.

Re-check commands (Windows, from the repo folder):

```bash
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check crosspay tests model app.py --select E,F,W --ignore E501,E402
gitleaks git --log-opts="origin/main..HEAD" --redact
```

## Render environment (set in the dashboard, never in the repo)

- `GROQ_MODEL=openai/gpt-oss-120b`. This key has no access to `llama-3.1-8b-instant`.
- `LLM_PROVIDERS=groq,cloudflare,nvidia`. NVIDIA's free endpoint times out, so it stays last.
- `AI_BACKFILL=0` until after the demo.
- Cloudflare keys come from the new account (verified working). Its free quota resets at 00:00 UTC.

## Before the demo

1. About 10 minutes before, open `/admin/ai` and click **Run AI self-test** once (each run costs about 7 large
   prompts).
2. Open `/admin/live` and click **Start simulated traffic** (dry run). Clicking a row shows the trace.
3. Use the AI features one at a time with short gaps.

## Known limitations

- Free tiers allow about 2 large AI answers a minute (Groq: 8,000 tokens per minute, 1,000 requests per day).
- A large payment with no invoice uploaded never gets INVOICE_UNVERIFIED. The flag only appears when an uploaded
  invoice's total can't be read.
- The p95 KPI value can wrap onto two lines at about 1366 px (cosmetic).
- The legacy Hardhat/Ganache keys remain in git history (commit d12451c); never reuse them.
  - The Groq and NVIDIA keys have been used throughout this work; rotate them after the demo as a precaution.
- Not done: P6.8, and an accessibility pass (screen reader, Lighthouse).
- The landing-page "clipping" Sandeep saw could not be reproduced at 1100–1440 px. It is most likely the browser window
  being wider than the screen.

## Rules for whoever continues

- Never read or print `.env` or `CROSSPAY env.txt`, and never commit any secret. gitleaks runs before every push.
- Push to a branch; Sandeep opens and merges the PRs. Never push to `main`, never force-push, never change global git
  config.
- Never submit real payments on the live site; the simulator is dry run.
- AI is advisory only: it may escalate a payment to HOLD, never decide or lower a decision.
- No fabricated numbers in the app, the docs or reports. Metrics come from `model/metrics.json`.
