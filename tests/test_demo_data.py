"""Demo dataset top-up: idempotent, decided by the real engine, signed and mined, ledger still valid."""
import json
import random

from crosspay.services import demo_data


def _counts(db):
    return {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("users", "transactions", "audit_chain", "llm_calls", "hold_reviews")}


def test_seed_adds_labelled_data_through_the_real_engine(app, db):
    before = _counts(db)
    out = demo_data.seed(app, db, rng=random.Random(1))
    after = _counts(db)
    assert out["applied"] and out["payments"] >= demo_data.PAYMENTS
    assert after["users"] == before["users"] + len(demo_data.DEMO_SMES)
    assert after["transactions"] == before["transactions"] + out["payments"]
    assert after["audit_chain"] == before["audit_chain"] + out["payments"]       # every payment signed
    assert after["llm_calls"] == before["llm_calls"] and after["hold_reviews"] == before["hold_reviews"]  # no AI, no fake reviews
    assert out["by_decision"].get("HOLD", 0) >= demo_data.MIN_HOLDS
    v = app.extensions["ledger"].verify(db)
    assert v["valid"], v["message"]
    rows = db.execute("SELECT * FROM transactions WHERE feature_source = 'demo_seed'").fetchall()
    contract = app.extensions["contract"]
    for r in rows:  # the stored decision is exactly what the policy engine says for the stored score
        reasons = json.loads(r["policy_reasons"])
        overrides = ["VELOCITY_BURST"] if "VELOCITY_BURST" in reasons else []
        assert r["decision"] == contract.decide("VERIFIED", r["risk_level"], r["risk_score"], overrides=overrides).decision
        assert r["exchange_rate_provider"] == "demo seed (fixed rate)"
        assert (r["block_number"] is not None) == (r["decision"] == "APPROVED")
    names = [n for (n,) in db.execute("SELECT name FROM users WHERE email LIKE '%@demo.invalid'")]
    assert names and all(n.startswith("Demo ") for n in names)


def test_seed_is_idempotent(app, db):
    demo_data.seed(app, db, rng=random.Random(2))
    before = _counts(db)
    assert demo_data.seed(app, db)["applied"] is False
    assert _counts(db) == before


def test_seed_starts_after_the_startup_writes(tmp_path, fx_mock, monkeypatch):
    """The seed holds the DB write lock for tens of seconds. Started before create_app's own writes (log purge,
    ai_jobs reset), those writes waited out busy_timeout on Render and the worker failed to boot."""
    from crosspay import create_app
    from crosspay.ai import log as ailog

    order = []
    real_purge, real_seed = ailog.purge, demo_data.seed
    monkeypatch.setattr(ailog, "purge", lambda *a, **k: order.append("purge") or real_purge(*a, **k))
    monkeypatch.setattr(demo_data, "seed", lambda *a, **k: order.append("seed") or real_seed(*a, **k))
    create_app("test", {"DB_PATH": str(tmp_path / "x.db"), "LEDGER_PATH": str(tmp_path / "l.json"),
                        "UPLOAD_DIR": str(tmp_path / "u"), "DEMO_MODE": True, "DEMO_DATASET": True})
    assert order == ["purge", "seed"]


def test_background_seed_waits_and_runs_off_the_main_thread(app, monkeypatch):
    import threading

    import crosspay

    seen = []
    monkeypatch.setattr(demo_data, "seed", lambda *a, **k: seen.append(threading.current_thread().name))
    app.config.update(TESTING=False, DEMO_DATASET_DELAY=0.05)
    timer = crosspay._start_demo_dataset(app)
    assert timer.daemon and not seen  # nothing runs inline
    timer.join(5)
    assert seen == ["crosspay-demo-seed"]


def test_seed_runs_at_startup_only_in_demo_mode(tmp_path, fx_mock):
    from crosspay import create_app
    from crosspay.db import connect

    for demo, expect in ((False, 0), (True, 1)):
        p = tmp_path / f"d{int(demo)}"
        app = create_app("test", {"DB_PATH": str(p / "x.db"), "LEDGER_PATH": str(p / "l.json"),
                                  "UPLOAD_DIR": str(p / "u"), "DEMO_MODE": demo, "DEMO_DATASET": True})
        conn = connect(app.config["DB_PATH"])
        assert conn.execute("SELECT COUNT(*) FROM ai_settings WHERE key = ?", (demo_data.MARKER,)).fetchone()[0] == expect
        conn.close()
