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


# ---- backfill and "Explain with AI" ----------------------------------------------------------------------
ORIGIN = {"Origin": "http://localhost"}


def _seed_tx(db):
    return db.execute("SELECT transaction_id FROM transactions ORDER BY id LIMIT 1").fetchone()[0]


def test_backfill_skipped_when_ai_off(app, db):
    from crosspay.ai.tasks import backfill

    assert backfill(app, db) == {"explain": 0, "purpose": 0}
    assert db.execute("SELECT COUNT(*) FROM ai_jobs").fetchone()[0] == 0


def test_backfill_explains_existing_payments_once(app, db, fake_llm):
    from crosspay.ai.tasks import backfill

    counts = backfill(app, db)
    n = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    assert counts["explain"] == n
    assert db.execute("SELECT COUNT(*) FROM ai_jobs WHERE task='explain' AND status='DONE'").fetchone()[0] == n
    assert backfill(app, db)["explain"] == 0  # idempotent
    decisions = [r[0] for r in db.execute("SELECT decision FROM transactions ORDER BY id")]
    backfill(app, db)
    assert decisions == [r[0] for r in db.execute("SELECT decision FROM transactions ORDER BY id")]


def test_explain_button_requeues_for_visible_payment(app, admin_client, db, fake_llm):
    tx = _seed_tx(db)
    r = admin_client.post(f"/api/ai/explain/{tx}", json={}, headers=ORIGIN)
    assert r.status_code == 200 and r.get_json()["status"] == "DONE"
    assert admin_client.get(f"/api/ai/explain/{tx}").get_json()["result"]["summary"]
    assert 'data-ai-explain=' in admin_client.get(f"/admin/review/{tx}").text


def test_explain_button_guards(app, admin_client, sme_client, db, fake_llm):
    tx = _seed_tx(db)
    assert admin_client.post(f"/api/ai/explain/{tx}", json={}).status_code == 403  # no Origin
    assert admin_client.post("/api/ai/explain/TX-NOPE-0000", json={}, headers=ORIGIN).status_code == 404
    app.config["LLM_ENABLED"] = False
    assert admin_client.post(f"/api/ai/explain/{tx}", json={}, headers=ORIGIN).status_code == 503
