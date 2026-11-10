"""Input-guard holdout (P5.5): detection rate on adversarial notes, false-positive rate on benign notes.

Adapted from Aegis Node (sandysunny99/aegis-node @4e64429, MIT) tests/benchmark_holdout.py — same idea, CrossPay's
payment-note fixtures. Writes model/evaluation/guardrail_holdout.json.

Run:  python model/evaluation/guardrail_holdout.py
"""
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from crosspay.ai.input_guard import evaluate  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "guardrails")
ESCALATION_FPR_LIMIT = 0.02


def run() -> dict:
    benign = json.load(open(os.path.join(FIX, "benign_notes.json"), encoding="utf-8"))
    adversarial = json.load(open(os.path.join(FIX, "adversarial_notes.json"), encoding="utf-8"))
    fp = [b for b in benign if evaluate(b["text"])["status"] == "BLOCK"]
    restrict_b = sum(1 for b in benign if evaluate(b["text"])["status"] == "RESTRICT")
    det = [a for a in adversarial if evaluate(a["text"])["status"] == "BLOCK"]
    flagged = [a for a in adversarial if evaluate(a["text"])["status"] in ("BLOCK", "RESTRICT")]
    by_cat_total = Counter(a["category"] if a["category"] != "encoding" else "encoding:" + a["encoding"] for a in adversarial)
    by_cat_hit = Counter(a["category"] if a["category"] != "encoding" else "encoding:" + a["encoding"] for a in det)
    by_lang_fp = Counter(b["lang"] + ("/hard" if b["kind"] == "hard_negative" else "") for b in fp)
    fpr = len(fp) / len(benign)
    out = {
        "benign_total": len(benign), "adversarial_total": len(adversarial),
        "detection_rate_block": round(len(det) / len(adversarial), 4),
        "detection_rate_block_or_restrict": round(len(flagged) / len(adversarial), 4),
        "false_positive_rate_block": round(fpr, 4), "benign_restrict": restrict_b,
        "detection_by_category": {k: f"{by_cat_hit.get(k, 0)}/{v}" for k, v in sorted(by_cat_total.items())},
        "false_positives_by_group": dict(by_lang_fp),
        "false_positive_examples": [b["text"] for b in fp[:10]],
        "missed_examples": [a["text"][:120] for a in adversarial if a not in det][:10],
        "escalation_trigger_allowed": fpr <= ESCALATION_FPR_LIMIT,
        "escalation_rule": f"input-guard BLOCK may escalate to HOLD only if FPR <= {ESCALATION_FPR_LIMIT:.0%}",
    }
    with open(os.path.join(ROOT, "model", "evaluation", "guardrail_holdout.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


if __name__ == "__main__":
    r = run()
    print(json.dumps({k: v for k, v in r.items() if k not in ("missed_examples", "false_positive_examples")},
                     ensure_ascii=False, indent=1))
