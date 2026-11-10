"""Live operations: VELOCITY_BURST (escalate-only), enriched decision events, AI one-liner events."""
from crosspay.policy import engine
from crosspay.realtime import ADMIN

BASE = {"receiver": "EuroTech Industrial GmbH", "sender_country": "United States", "receiver_country": "Germany",
        "sender_currency": "USD", "receiver_currency": "EUR", "amount": "4500", "notes": "Invoice 1"}


def _last(db):
    return dict(db.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 1").fetchone())


def test_velocity_burst_is_escalate_only():
    # APPROVED -> HOLD
    d = engine.evaluate("VERIFIED", "LOW", 5.0, 40, 80, overrides=["VELOCITY_BURST"])
    assert d.decision == "HOLD" and "VELOCITY_BURST" in d.reason_codes
    # never lowers BLOCKED or REJECTED
    assert engine.evaluate("VERIFIED", "HIGH", 95.0, 40, 80, overrides=["VELOCITY_BURST"]).decision == "BLOCKED"
    assert engine.evaluate("PENDING", "LOW", 5.0, 40, 80, overrides=["VELOCITY_BURST"]).decision == "REJECTED"


def test_velocity_burst_holds_the_nth_payment_in_an_hour(app, sme_client, db):
    app.config["VELOCITY_BURST_1H"] = 3
    decisions = []
    for _ in range(3):
        sme_client.post("/process_payment", data={**BASE, "scenario": "low"})
        tx = _last(db)
        decisions.append((tx["decision"], tx["policy_reasons"]))
    assert decisions[0][0] == "APPROVED" and decisions[1][0] == "APPROVED"
    assert decisions[2][0] == "HOLD" and "VELOCITY_BURST" in decisions[2][1]


def test_velocity_burst_off_when_zero(app, sme_client, db):
    app.config["VELOCITY_BURST_1H"] = 0
    for _ in range(4):
        sme_client.post("/process_payment", data={**BASE, "scenario": "low"})
    assert _last(db)["decision"] == "APPROVED"


def test_decision_event_carries_reasons_trace_and_latency(app, sme_client, db):
    bus = app.extensions["events"]
    q = bus.subscribe(ADMIN)
    sme_client.post("/process_payment", data={**BASE, "scenario": "high"})
    ev = q.get_nowait()
    assert ev["type"] == "decision" and ev["decision"] in ("HOLD", "BLOCKED")
    assert ev["reasons"] and ev["why"] and ev["policy_id"] == "risk_pol_v1"
    assert ev["latency_ms"] is not None and ev["latency_ms"] >= 0
    assert ev["currency"] == "USD" and ev["amount_usd"] == 4500.0
    t = ev["trace"]
    assert t["kyc"] == "VERIFIED" and set(t["features"]) >= {"amount", "corridor_risk"}
    assert t["reasons"][0]["label"] and t["ledger"].startswith("NOT RECORDED")


def test_ai_explanation_publishes_one_liner(app, sme_client, db, fake_llm):
    bus = app.extensions["events"]
    q = bus.subscribe(ADMIN)
    sme_client.post("/process_payment", data={**BASE, "scenario": "medium"})
    events = []
    while not q.empty():
        events.append(q.get_nowait())
    ai = [e for e in events if e["type"] == "ai"]
    assert ai and ai[0]["tx_id"] == events[0]["tx_id"] and ai[0]["summary"]
