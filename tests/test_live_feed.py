"""Live decision feed: tenant scoping, publish-after-commit, SSE framing, dry-run simulator."""
import json
import random

from crosspay.realtime import ADMIN, EventBus, TrafficSimulator

BASE = {"receiver": "EuroTech Industrial GmbH", "sender_country": "United States", "receiver_country": "Germany",
        "sender_currency": "USD", "receiver_currency": "EUR", "amount": "4500", "notes": "Invoice 1"}
ORIGIN = {"Origin": "http://localhost"}


def _count(db, table):
    return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_bus_scopes_events_by_tenant():
    bus = EventBus()
    sme_q, other_q, admin_q = bus.subscribe(1), bus.subscribe(2), bus.subscribe(ADMIN)
    bus.publish({"type": "decision", "tx_id": "TX-A", "user_id": 1, "decision": "APPROVED"})
    bus.publish({"type": "decision", "tx_id": "SIM-1", "user_id": None, "decision": "HOLD", "simulated": True})
    assert [sme_q.get_nowait()["tx_id"]] == ["TX-A"] and sme_q.empty()
    assert other_q.empty()
    assert [admin_q.get_nowait()["tx_id"], admin_q.get_nowait()["tx_id"]] == ["TX-A", "SIM-1"]
    assert all("user_id" not in e for e in bus.recent(ADMIN))
    assert [e["tx_id"] for e in bus.recent(2)] == []


def test_slow_subscriber_drops_oldest_instead_of_blocking():
    bus = EventBus()
    q = bus.subscribe(ADMIN)
    for i in range(600):
        bus.publish({"type": "decision", "tx_id": f"TX-{i}", "user_id": 1, "decision": "APPROVED"})
    assert q.qsize() == 500


def test_payment_publishes_after_commit_and_sme_sees_only_own(app, sme_client, admin_client, db):
    app.extensions["events"].publish({"type": "decision", "tx_id": "TX-OTHER", "user_id": 99999,
                                      "decision": "BLOCKED", "simulated": False})
    sme_client.post("/process_payment", data={**BASE, "scenario": "low"})
    tx = db.execute("SELECT transaction_id, decision FROM transactions ORDER BY id DESC LIMIT 1").fetchone()
    mine = sme_client.get("/api/live/snapshot").get_json()["events"]
    assert [e["tx_id"] for e in mine] == [tx["transaction_id"]]
    assert mine[0]["decision"] == tx["decision"] and "user_id" not in mine[0]
    assert set(mine[0]) >= {"amount_usd", "corridor", "risk_level", "risk_score", "seq", "ts"}
    assert "receiver" not in mine[0] and "notes" not in mine[0]
    every = admin_client.get("/api/live/snapshot").get_json()["events"]
    assert {e["tx_id"] for e in every} == {"TX-OTHER", tx["transaction_id"]}


def test_failed_settlement_publishes_nothing(app, sme_client):
    sme_client.post("/process_payment", data={**BASE, "receiver_country": "Atlantis"})
    assert app.extensions["events"].recent(ADMIN) == []


def test_sse_stream_frames_events(app, sme_client):
    resp = sme_client.get("/api/live/events?max=1", buffered=False)
    assert resp.mimetype == "text/event-stream"
    chunks = iter(resp.response)
    assert next(chunks).startswith(b"retry:")
    from crosspay.db import connect

    conn = connect(app.config["DB_PATH"])
    sme_id = conn.execute("SELECT id FROM users WHERE role = 'sme' ORDER BY id LIMIT 1").fetchone()[0]
    conn.close()
    app.extensions["events"].publish({"type": "decision", "tx_id": "TX-SSE", "user_id": sme_id,
                                      "decision": "HOLD", "simulated": False})
    frame = b"".join(chunks).decode()
    assert "event: decision" in frame and '"tx_id":"TX-SSE"' in frame and "user_id" not in frame
    resp.close()


def test_feed_needs_login(client):
    assert client.get("/api/live/events").status_code == 401
    assert client.get("/api/live/snapshot").status_code == 401


def test_simulator_is_admin_and_demo_only(app, sme_client, admin_client):
    assert sme_client.post("/api/live/simulator", json={"running": False}, headers=ORIGIN).status_code == 403
    app.config["DEMO_MODE"] = False
    assert admin_client.post("/api/live/simulator", json={"running": False}, headers=ORIGIN).status_code == 404
    app.config["DEMO_MODE"] = True
    r = admin_client.post("/api/live/simulator", json={"rate_per_sec": 99}, headers=ORIGIN)
    assert r.status_code == 200 and r.get_json()["rate_per_sec"] == 10.0 and r.get_json()["dry_run"] is True
    assert admin_client.post("/api/live/simulator", json={"running": True}).status_code == 403  # same-origin check


def test_simulator_is_a_dry_run_through_the_real_policy(app, db):
    before = {t: _count(db, t) for t in ("transactions", "audit_chain", "llm_calls")}
    sim = TrafficSimulator(app, rng=random.Random(7))
    events = [sim.emit_once() for _ in range(60)]
    after = {t: _count(db, t) for t in ("transactions", "audit_chain", "llm_calls")}
    assert before == after  # nothing stored, nothing mined, no AI call
    assert all(e["simulated"] and e["tx_id"].startswith("SIM-") and e["block"] is None for e in events)
    assert {e["decision"] for e in events} <= {"APPROVED", "HOLD", "BLOCKED"}
    assert len({e["decision"] for e in events}) >= 2
    contract, scorer = app.extensions["contract"], app.extensions["scorer"]
    for e in events[:10]:  # the decision is the real policy engine's verdict on the real model's score
        assert e["decision"] == contract.decide("VERIFIED", e["risk_level"], e["risk_score"]).decision
    assert all(e["engine"] == scorer.engine for e in events)


def test_simulated_events_never_reach_smes(app, sme_client):
    TrafficSimulator(app, rng=random.Random(1)).emit_once()
    assert sme_client.get("/api/live/snapshot").get_json()["events"] == []


def test_dashboard_renders_feed(sme_client, admin_client):
    sme = sme_client.get("/dashboard").get_data(as_text=True)
    assert 'id="live-feed"' in sme and "sim-toggle" not in sme
    adm = admin_client.get("/dashboard").get_data(as_text=True)
    assert 'id="sim-toggle"' in adm and "dry run" in adm
