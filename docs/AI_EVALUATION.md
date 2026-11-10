# AI evaluation (P7)

All numbers below were measured on 2026-11-10 against the configured provider chain (`groq,nvidia,cloudflare`;
Groq `openai/gpt-oss-120b` served every successful call). Raw results: `model/evaluation/ai_golden_eval.json`,
`model/evaluation/guardrail_holdout.json`, `docs/AI_REDTEAM_REPORT.md`.

## Golden set (live)

`python model/evaluation/ai_golden_eval.py`: 20 explain cases (synthetic payments across the three demo vectors and
14 corridors) and 20 purpose notes (10 benign, 10 with a clear red flag; labels written by the fixture author).

| Task | Cases | Passed every guard | Rejected / unavailable | Evidence-faithful | Latency p50 / p95 | Est. cost per 100 payments |
|---|---|---|---|---|---|---|
| Risk explainer | 20 | 17 | 2 `DECISION_CLAIM`, 1 `UNAVAILABLE` | 17 / 17 | 2.05 s / 7.15 s | $0.038 |
| Purpose tagger | 20 | 19 | 1 `UNAVAILABLE` (4 s timeout) | n/a | 1.59 s / 3.40 s | $0.018 |

Purpose-tagger escalation against the author labels: **precision 1.00, recall 0.90** (TP 9, FP 0, FN 1; the timed-out
case counts as not escalated). Costs use the estimated Groq price in `crosspay/ai/providers/base.py`
(override with `LLM_PRICE_GROQ_IN/OUT`).

**What this does not show.** The outputs have not been hand-reviewed by a compliance officer for quality or
helpfulness; "passed every guard" means schema-valid, cites only given evidence, uses only given numbers/IDs and makes no
outcome claim. 20 cases per task is small. The copilot, invoice reader, NL filter, assistant and report tasks are
covered by the fake-provider tests (`tests/ai/test_ai_features_p6.py`) and the red-team suite, not by this live set.
`TODO:` a compliance officer should review 20 outputs per task and record a quality score here.

## Guardrails

| Measure | Result |
|---|---|
| Input guard, adversarial notes blocked | 83 / 100 (100 / 100 flagged) |
| Input guard, benign notes blocked (FPR) | 0 / 200 |
| Red-team suite, fake provider obeying every attack (CI) | 45 / 45 expected outcome |
| Red-team suite, live provider | 45 / 45 safe (see report) |

## Observations

- The decision-word check rejected 2 of 20 honest explanations that used an outcome word other than the stored one.
  This keeps misinformation out at the cost of some availability; the receipt then shows the model's own top factors.
- Provider latency has a long tail (p95 7 s), which is why explanations run in the background and the purpose tagger
  has a 4 s timeout with a record-only retry.
