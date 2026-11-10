"""AI utilisation and live-operations work: decision-claim guard (both ways), backfill, explain button, self-test."""
import pytest

from crosspay.ai import guard

NEUTRAL_ON_HOLD = [
    "The payment is not yet settled and is on hold for a compliance review.",
    "The SME has two prior blocked payments.",
    "Previous rejected transfers exist on this account.",
    "Policy placed it on hold for officer review.",
    "Request the invoice and check the beneficiary name.",
    "Corridor risk is moderate; settlement is pending review.",
    "No funds have been released yet.",
    "Earlier payments that were held or stopped raise concern.",
]

CLAIMS_ON_HOLD = [
    ("This payment will be approved shortly.", "APPROVED"),
    ("APPROVE, risk is low.", "APPROVED"),
    ("Recommend we release the payment today.", "APPROVED"),
    ("The transfer should be blocked.", "BLOCKED"),
    ("I would reject this.", "REJECTED"),
    ("It is now cleared.", "APPROVED"),
    ("Release the payment.", "APPROVED"),
    ("Status: BLOCKED", "BLOCKED"),
    ("Officers can safely approve it.", "APPROVED"),
    ("This is green-lit.", "APPROVED"),
    ("I suggest declining the transfer.", "REJECTED"),
]


@pytest.mark.parametrize("text", NEUTRAL_ON_HOLD)
def test_neutral_mentions_pass_on_hold(text):
    assert guard.decision_claims(text, "HOLD") == []
    clean, code, _ = guard.check({"case_summary": text}, stored_decision="HOLD", faithfulness=False)
    assert code == "OK" and clean["case_summary"] == text


@pytest.mark.parametrize("text,claimed", CLAIMS_ON_HOLD)
def test_real_claims_still_rejected_on_hold(text, claimed):
    assert claimed in guard.decision_claims(text, "HOLD")
    clean, code, _ = guard.check({"draft_memo": text}, stored_decision="HOLD", faithfulness=False)
    assert clean is None and code == "REJECTED_GUARD:DECISION_CLAIM"


def test_stored_outcome_may_be_named():
    assert guard.decision_claims("This payment was blocked by the policy.", "BLOCKED") == []
    assert guard.decision_claims("The payment has been settled.", "APPROVED") == []
    assert guard.decision_claims("APPROVE, risk is low.", "BLOCKED") == ["APPROVED"]


def test_guard_fails_closed_when_claim_check_errors(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("regex engine exploded")

    monkeypatch.setattr(guard, "decision_claims", boom)
    clean, code, _ = guard.check({"summary": "On hold for review."}, stored_decision="HOLD", faithfulness=False)
    assert clean is None and code == "REJECTED_GUARD:DECISION_CLAIM"
