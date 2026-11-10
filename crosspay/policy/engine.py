"""Deterministic settlement policy. The ONLY component that turns risk evidence into a decision.

Adapted from Netvrio (sandysunny99/razorpay-ai-risk-manager @98bbc09) backend/policy/engine.py — CrossPay
decisions (APPROVED/HOLD/BLOCKED/REJECTED), thresholds REVIEW_AT/BLOCK_AT from config, model class as a
stricter-only override, and an escalate-only hook for AI signals. The signature takes no LLM output.
"""
from dataclasses import dataclass, field
from typing import Iterable, List

APPROVED, HOLD, BLOCKED, REJECTED = "APPROVED", "HOLD", "BLOCKED", "REJECTED"
SEVERITY = {APPROVED: 0, HOLD: 1, BLOCKED: 2, REJECTED: 3}

# Deterministic overrides that may only make the decision stricter.
STRICT_OVERRIDES = {
    "SANCTIONS_EXACT_MATCH": BLOCKED,
    "SANCTIONS_NEAR_MATCH": HOLD,
    "INVOICE_MISMATCH": HOLD,
}
# AI-derived signals (P5.5). Escalate-only: they can move an APPROVED payment to HOLD and nothing else.
AI_ESCALATIONS = {"PURPOSE_RED_FLAG", "INVOICE_MISMATCH", "INVOICE_UNVERIFIED"}

STATUS = {
    APPROVED: "EXECUTED_SETTLED",
    HOLD: "HELD_IN_ESCROW",
    BLOCKED: "REJECTED_BLOCKED",
    REJECTED: "REJECTED_UNVERIFIED_KYC",
}


@dataclass(frozen=True)
class PolicyDecision:
    decision: str
    reason_codes: List[str] = field(default_factory=list)
    policy_id: str = "risk_pol_v1"

    @property
    def contract_status(self) -> str:
        return STATUS[self.decision]


def _stricter(current: str, candidate: str) -> str:
    return candidate if SEVERITY[candidate] > SEVERITY[current] else current


def evaluate(kyc_status: str, risk_level: str, risk_score: float, review_at: float, block_at: float,
             overrides: Iterable[str] = (), ai_escalations: Iterable[str] = ()) -> PolicyDecision:
    reasons: List[str] = []

    # 1. Hard gate: KYC (fail closed)
    if kyc_status != "VERIFIED":
        return PolicyDecision(REJECTED, ["KYC_NOT_VERIFIED"], "kyc_pol_v1")

    # 2. Thresholds on the deterministic risk score
    decision = APPROVED
    if risk_score >= block_at:
        decision = BLOCKED
        reasons.append("RISK_SCORE_AT_OR_ABOVE_BLOCK_AT")
    elif risk_score >= review_at:
        decision = HOLD
        reasons.append("RISK_SCORE_AT_OR_ABOVE_REVIEW_AT")

    # 3. The model's predicted class can only tighten the outcome
    if risk_level == "HIGH" and SEVERITY[decision] < SEVERITY[BLOCKED]:
        decision = BLOCKED
        reasons.append("MODEL_CLASS_HIGH")
    elif risk_level == "MEDIUM" and decision == APPROVED:
        decision = HOLD
        reasons.append("MODEL_CLASS_MEDIUM")

    # 4. Deterministic overrides: stricter-only
    for code in overrides:
        target = STRICT_OVERRIDES.get(code)
        if target and SEVERITY[target] > SEVERITY[decision]:
            decision = target
            reasons.append(code)

    # 5. AI escalations: may only send an otherwise-approved payment to a human. Never lowers, never blocks.
    escalations = [c for c in ai_escalations if c in AI_ESCALATIONS]
    if escalations and decision == APPROVED:
        decision = HOLD
        reasons.extend(f"AI_ESCALATION:{c}" for c in escalations)

    return PolicyDecision(decision, reasons, "risk_pol_v1")
