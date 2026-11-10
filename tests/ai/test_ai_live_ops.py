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


# ---- AI self-test and live console -----------------------------------------------------------------------
def test_selftest_runs_every_feature_and_logs(app, admin_client, db, fake_llm):
    r = admin_client.post("/admin/ai", data={"action": "selftest"})
    assert r.status_code == 200 and "AI self-test" in r.text
    tasks = {row[0] for row in db.execute("SELECT DISTINCT task FROM llm_calls")}
    assert tasks >= {"explain", "purpose", "copilot", "invoice", "nl_filter", "assistant", "report"}
    assert db.execute("SELECT COUNT(*) FROM transactions WHERE transaction_id = 'TX-SELFTEST-0001'").fetchone()[0] == 0


def test_selftest_reports_disabled_when_ai_off(app, admin_client, db):
    r = admin_client.post("/admin/ai", data={"action": "selftest"})
    assert r.status_code == 200 and "DISABLED" in r.text


def test_selftest_is_admin_only(sme_client):
    assert sme_client.post("/admin/ai", data={"action": "selftest"}).status_code in (302, 403)


def test_live_console_and_stats(app, admin_client, sme_client, db):
    page = admin_client.get("/admin/live")
    assert page.status_code == 200 and 'id="live-ops"' in page.text and "Needs a decision" in page.text
    hold = db.execute("SELECT COUNT(*) FROM transactions WHERE decision='HOLD'").fetchone()[0]
    assert page.text.count('class="ops-queue-item"') == min(hold, 25)
    stats = admin_client.get("/api/live/stats").get_json()
    assert stats["hold"] == hold and "approval_rate" in stats and "p95_ms" in stats
    assert sme_client.get("/admin/live").status_code in (302, 403)
    assert sme_client.get("/api/live/stats").status_code in (302, 403)


def test_restart_releases_jobs_left_pending(tmp_path, fx_mock):
    from crosspay import create_app
    from crosspay.config import TestConfig
    from crosspay.db import connect

    over = {"DB_PATH": str(tmp_path / "r.db"), "LEDGER_PATH": str(tmp_path / "l.json"), "UPLOAD_DIR": str(tmp_path / "u")}
    app = create_app("test", over)
    conn = connect(app.config["DB_PATH"])
    conn.execute("INSERT INTO ai_jobs (task, tx_id, status, created_at, updated_at) VALUES "
                 "('explain', 'TX-X', 'PENDING', 'now', 'now')")
    conn.close()
    create_app("test", over)  # restart
    conn = connect(app.config["DB_PATH"])
    assert conn.execute("SELECT status, error_code FROM ai_jobs WHERE tx_id='TX-X'").fetchone()[:] == ("FAILED", "INTERRUPTED")
    conn.close()
    assert TestConfig.AI_BACKFILL is False


def test_weekly_report_context_precomputes_derived_figures(app, db):
    from crosspay.ai import context

    with app.app_context():
        f = context.weekly_report(db, days=3650).facts
    total = sum(v["count"] for v in f["payments_by_decision"].values())
    assert f["total_payments"] == total and total > 0
    assert abs(sum(v["share_of_payments_percent"] for v in f["payments_by_decision"].values()) - 100) < 0.5
    assert 0 <= f["approval_rate_percent"] <= 100


def test_report_quoting_given_shares_passes_and_invented_math_is_still_rejected(app, db, fake_llm, admin_client):
    from crosspay.ai import context
    from crosspay.ai.pipeline import run_task

    with app.app_context():
        f = context.weekly_report(db, days=3650).facts
        rate = f["approval_rate_percent"]
        fake_llm.script("report", {"title": "Weekly summary", "body": f"Approval rate was {rate}% of "
                                   f"{f['total_payments']} payments.", "key_points": []})
        assert run_task("report", context.weekly_report(db, days=3650), 1, db).status == "OK"
        fake_llm.script("report", {"title": "Weekly summary", "body": "Volume grew 37.9% week on week.",
                                   "key_points": []})
        assert run_task("report", context.weekly_report(db, days=3649), 1, db).status == \
            "REJECTED_GUARD:UNSUPPORTED_NUMBER"
