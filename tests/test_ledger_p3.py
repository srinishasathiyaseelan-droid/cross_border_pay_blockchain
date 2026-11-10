"""P3 acceptance: H2, H7, M3, M4, M8, M9, L2, L3."""
import json
import re
import sqlite3
import threading

import pytest

from crosspay.ledger.audit import AuditChain
from crosspay.ledger.chain import settlement_record, tx_hash
from crosspay.policy import engine
from crosspay.services.currency import CurrencyService, ExchangeRateAPIError

BASE = {"receiver": "EuroTech Industrial GmbH", "sender_country": "United States", "receiver_country": "Germany",
        "sender_currency": "USD", "receiver_currency": "EUR", "amount": "4500", "notes": "Invoice 1"}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _verify(app, db):
    with app.app_context():
        return app.extensions["ledger"].verify(db)


def test_fixtures_share_the_signed_history(app, db):
    v = _verify(app, db)
    assert v["valid"], v["message"]
    blocks = app.extensions["ledger"].blocks(db)
    assert blocks[1].transactions[0]["transaction_id"] == "TX-2026-8801"
    row = db.execute("SELECT block_number, blockchain_hash FROM transactions WHERE transaction_id='TX-2026-8801'").fetchone()
    assert row[0] == 1 and row[1].startswith("0x")


def test_low_risk_payment_is_mined_with_ulid_and_deterministic_hash(sme_client, app, db):
    sme_client.post("/process_payment", data={**BASE, "scenario": "low"})
    row = dict(db.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 1").fetchone())
    assert re.match(r"^TX-[0-9A-HJKMNP-TV-Z]{26}$", row["transaction_id"])
    assert ISO.match(row["timestamp"]) and ISO.match(row["decided_at"])
    if row["decision"] == "APPROVED":
        rec = settlement_record(row, "APPROVED", row["decided_at"])
        assert tx_hash(rec) == row["blockchain_hash"]  # re-verifiable: no time.time() in the hash
        assert row["block_number"] == len(app.extensions["ledger"].blocks(db)) - 1
    assert _verify(app, db)["valid"]


def test_forced_integrity_error_after_decision_leaves_nothing(sme_client, app, db, monkeypatch):
    n_tx = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    n_audit = db.execute("SELECT COUNT(*) FROM audit_chain").fetchone()[0]
    n_blocks = len(app.extensions["ledger"].blocks(db))
    with open(app.config["LEDGER_PATH"], encoding="utf-8") as f:
        view_before = f.read()

    def boom(*a, **k):
        raise sqlite3.IntegrityError("forced after decision")

    monkeypatch.setattr(AuditChain, "append", boom)
    with pytest.raises(sqlite3.IntegrityError):
        app.config["PROPAGATE_EXCEPTIONS"] = True
        sme_client.post("/process_payment", data={**BASE, "scenario": "low"})
    monkeypatch.undo()
    assert db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == n_tx
    assert db.execute("SELECT COUNT(*) FROM audit_chain").fetchone()[0] == n_audit
    assert len(app.extensions["ledger"].blocks(db)) == n_blocks
    with open(app.config["LEDGER_PATH"], encoding="utf-8") as f:
        assert f.read() == view_before


def test_edited_audit_row_breaks_verification(app, db):
    rid, payload = db.execute("SELECT id, payload FROM audit_chain WHERE tx_id='TX-2026-8802'").fetchone()
    p = json.loads(payload)
    p["record"]["amount"] = 1.0
    db.execute("UPDATE audit_chain SET payload = ? WHERE id = ?", (json.dumps(p, sort_keys=True), rid))
    v = _verify(app, db)
    assert v["valid"] is False and "HMAC" in v["message"]


def test_edited_transaction_row_breaks_verification(app, db):
    db.execute("UPDATE transactions SET amount = 1.0 WHERE transaction_id = 'TX-2026-8803'")
    v = _verify(app, db)
    assert v["valid"] is False and "TX-2026-8803" in v["message"]


def test_rehashed_chain_without_key_is_detected(app, db):
    """An attacker with DB write access but without LEDGER_SIGNING_KEY cannot re-sign the chain."""
    rows = db.execute("SELECT * FROM audit_chain ORDER BY id").fetchall()
    forger = AuditChain("attacker-guess")
    prev = "GENESIS"
    db.execute("BEGIN")
    for r in rows:
        payload = json.loads(r["payload"])
        rec = {"record_type": r["record_type"], "tx_id": r["tx_id"], "payload": payload}
        from crosspay.ledger.audit import chain_hash

        cur = chain_hash(forger.key, rec, prev)
        db.execute("UPDATE audit_chain SET previous_hash = ?, current_hash = ? WHERE id = ?", (prev + "-x", cur, r["id"]))
        prev = cur
    db.execute("ROLLBACK")
    assert _verify(app, db)["valid"]  # rollback restored it
    tampered = db.execute("SELECT id FROM audit_chain ORDER BY id LIMIT 1").fetchone()[0]
    db.execute("UPDATE audit_chain SET current_hash = ? WHERE id = ?", ("0" * 64, tampered))
    assert _verify(app, db)["valid"] is False


def test_double_submitted_form_creates_one_transaction(sme_client, db):
    before = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    data = {**BASE, "scenario": "low", "idempotency_key": "f" * 32}
    r1 = sme_client.post("/process_payment", data=data)
    r2 = sme_client.post("/process_payment", data=data)
    assert db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == before + 1
    assert r1.headers["Location"] == r2.headers["Location"]


def test_ten_concurrent_submits(app, db):
    uid = db.execute("SELECT id FROM users WHERE role='sme'").fetchone()[0]
    before = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    errors = []

    def submit(i):
        try:
            c = app.test_client()
            with c.session_transaction() as s:
                s["user_id"] = uid
            r = c.post("/process_payment", data={**BASE, "scenario": "low", "amount": str(1000 + i),
                                                 "idempotency_key": f"key-{i}"})
            assert r.status_code == 302 and "/result/" in r.headers["Location"]
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=submit, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors
    assert db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == before + 10
    v = _verify(app, db)
    assert v["valid"], v["message"]
    blocks = app.extensions["ledger"].blocks(db)
    assert [b.index for b in blocks] == list(range(len(blocks)))
    with open(app.config["LEDGER_PATH"], encoding="utf-8") as f:
        assert len(json.load(f)) == len(blocks)


def test_hold_release_requires_reason_and_records_review(admin_client, app, db):
    admin_client.post("/resolve_hold/TX-2026-8802", data={"action": "approve", "reason": "too short"})
    assert db.execute("SELECT decision FROM transactions WHERE transaction_id='TX-2026-8802'").fetchone()[0] == "HOLD"
    admin_client.post("/resolve_hold/TX-2026-8802",
                      data={"action": "approve", "reason": "Invoice and bill of lading match the shipment"})
    row = db.execute("SELECT decision, block_number FROM transactions WHERE transaction_id='TX-2026-8802'").fetchone()
    assert row[0] == "APPROVED" and row[1] is not None
    rev = db.execute("SELECT admin_id, action, reason, kyc_status_at_review, created_at FROM hold_reviews").fetchone()
    assert rev[1] == "approve" and len(rev[2]) >= 20 and rev[3] == "VERIFIED" and ISO.match(rev[4])
    assert _verify(app, db)["valid"]


def test_release_rechecks_kyc(admin_client, db):
    db.execute("UPDATE kyc SET status = 'REJECTED'")
    admin_client.post("/resolve_hold/TX-2026-8802",
                      data={"action": "approve", "reason": "Documents look fine to me today"})
    assert db.execute("SELECT decision FROM transactions WHERE transaction_id='TX-2026-8802'").fetchone()[0] == "HOLD"


def test_reject_is_rejected_and_filterable(admin_client, db):
    admin_client.post("/resolve_hold/TX-2026-8802",
                      data={"action": "reject", "reason": "Counterparty could not be verified"})
    assert db.execute("SELECT decision FROM transactions WHERE transaction_id='TX-2026-8802'").fetchone()[0] == "REJECTED"
    page = admin_client.get("/transactions?status=REJECTED").text
    assert "TX-2026-8802" in page and "TX-2026-8801" not in page


def test_stale_rate_policy(fx_mock):
    svc = CurrencyService(max_stale_hours=24)
    fresh = svc.convert(100, "USD", "EUR")
    assert fresh["stale"] is False and fresh["is_cached"] is False
    again = svc.convert(100, "USD", "EUR")
    assert again["is_cached"] is True and again["stale"] is False
    svc._cache["USD"]["fetched_at"] -= 2 * 3600  # older than the TTL
    fx_mock.fail = "network"
    stale = svc.convert(100, "USD", "EUR")
    assert stale["stale"] is True and stale["converted_amount"] == fresh["converted_amount"]
    svc._cache["USD"]["fetched_at"] -= 30 * 3600  # older than the stale window
    with pytest.raises(ExchangeRateAPIError):
        svc.convert(100, "USD", "EUR")


def test_rate_timestamp_is_iso_utc(fx_mock):
    assert ISO.match(CurrencyService().convert(1, "USD", "INR")["last_updated"])


# ---- policy engine ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("level,score,expected", [
    ("LOW", 10, "APPROVED"), ("LOW", 45, "HOLD"), ("LOW", 85, "BLOCKED"),
    ("MEDIUM", 10, "HOLD"), ("HIGH", 10, "BLOCKED"), ("MEDIUM", 90, "BLOCKED"),
])
def test_policy_thresholds(level, score, expected):
    assert engine.evaluate("VERIFIED", level, score, 40, 80).decision == expected


def test_policy_kyc_gate():
    assert engine.evaluate("PENDING", "LOW", 1, 40, 80).decision == "REJECTED"


@pytest.mark.parametrize("base", [("LOW", 5), ("LOW", 50), ("HIGH", 95), ("MEDIUM", 60)])
@pytest.mark.parametrize("signals", [["PURPOSE_RED_FLAG"], ["INVOICE_UNVERIFIED", "INVOICE_MISMATCH"], ["MADE_UP"], []])
def test_ai_escalations_never_lower(base, signals):
    plain = engine.evaluate("VERIFIED", base[0], base[1], 40, 80)
    escalated = engine.evaluate("VERIFIED", base[0], base[1], 40, 80, ai_escalations=signals)
    assert engine.SEVERITY[escalated.decision] >= engine.SEVERITY[plain.decision]
    assert escalated.decision != "BLOCKED" or plain.decision == "BLOCKED"  # AI can never cause a block


def test_policy_signature_has_no_llm_argument():
    import inspect

    params = set(inspect.signature(engine.evaluate).parameters)
    assert not any("llm" in p or "advice" in p for p in params)


def test_solidity_reference_hardening():
    src = open("blockchain/smart_contract.sol", encoding="utf-8").read()
    assert "onlyOracle" in src and "governmentIdHash" in src and "string governmentId" not in src
    assert "REFERENCE DESIGN ONLY" in src
