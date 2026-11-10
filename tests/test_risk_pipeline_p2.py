"""P2 acceptance: C4, C5, H1, H5, M5, L1."""
import inspect

import pytest

from crosspay import create_app
from crosspay.db import connect
from crosspay.services.currency import CurrencyService, ExchangeRateAPIError

BASE = {"receiver": "EuroTech Industrial GmbH", "sender_country": "United States", "receiver_country": "Germany",
        "sender_currency": "USD", "receiver_currency": "EUR", "amount": "4500", "notes": "Invoice 1"}
ORIGIN = {"Origin": "http://localhost"}


def _last_tx(db):
    return db.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 1").fetchone()


def test_form_posted_behaviour_features_are_ignored(sme_client, db):
    data = {**BASE, "suspicious_transactions": "0", "account_age": "60", "frequency": "1",
            "previous_transactions": "999"}
    sme_client.post("/process_payment", data=data)
    row = _last_tx(db)
    # Demo SME history: 3 past payments, 2 of them HOLD/BLOCKED, account opened ~26 months ago.
    assert row["previous_transactions"] == 3
    assert row["suspicious_transactions"] == 2
    assert row["account_age"] != 60 and row["account_age"] >= 24
    assert row["feature_source"] == "db"


def test_same_input_same_score(app):
    scorer = app.extensions["scorer"]
    f = {"amount": 28500.0, "frequency": 7, "previous_transactions": 6, "suspicious_transactions": 1,
         "account_age": 6, "corridor_risk": 0.402, "amount_to_age_ratio": 4384.62}
    results = [scorer.score(f) for _ in range(10)]
    assert all(r == results[0] for r in results)
    r = results[0]
    assert r["engine"] == "model"
    assert r["score"] == round((r["p_med"] * 0.5 + r["p_high"]) * 100, 1) or abs(
        r["score"] - (r["p_med"] * 0.5 + r["p_high"]) * 100) < 0.06


def test_no_random_in_scoring():
    import crosspay.services.scoring as sc

    assert "random" not in inspect.getsource(sc)


def test_inr_to_eur_without_usd_rate_fails_and_stores_nothing(sme_client, db, fx_mock):
    fx_mock.drop = {"INR": {"USD"}}
    with pytest.raises(ExchangeRateAPIError):
        CurrencyService().convert(1000000, "INR", "EUR")
    before = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    r = sme_client.post("/process_payment", data={**BASE, "sender_currency": "INR", "amount": "1000000"},
                        follow_redirects=True)
    assert "nothing was stored" in r.text
    assert db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == before


def test_usd_amount_uses_same_response(fx_mock):
    res = CurrencyService().convert(1000, "INR", "EUR")
    assert res["normalized_usd_amount"] == pytest.approx(1000 / 83.25, abs=0.01)
    assert len(fx_mock.calls) == 1


def test_new_user_cannot_self_verify(tmp_path, fx_mock):
    app = create_app("test", {"DB_PATH": str(tmp_path / "k.db"), "LEDGER_PATH": str(tmp_path / "l.json"),
                              "WTF_CSRF_ENABLED": False, "DEMO_MODE": False})
    c = app.test_client()
    c.post("/register", data={"name": "New SME", "email": "new@sme.test", "password": "long-password-1"})
    for action in ("", "auto_validate", "demo_verify", "verify"):
        c.post("/kyc", data={"business_name": "New SME", "country": "India", "business_type": "x",
                             "government_id": "IN-PAN-ABCDE1234F", "address": "1 Road", "simulate_action": action})
        conn = connect(app.config["DB_PATH"])
        st = conn.execute("SELECT k.status FROM kyc k JOIN users u ON u.id = k.user_id "
                          "WHERE u.email = 'new@sme.test' ORDER BY k.id DESC").fetchone()[0]
        conn.close()
        assert st == "PENDING"
    r = c.post("/process_payment", data=BASE, follow_redirects=True)
    assert "Access Denied" in r.text


def test_admin_verifies_from_queue(app, client, db):
    client.post("/register", data={"name": "Queue SME", "email": "q@sme.test", "password": "long-password-1"})
    client.post("/kyc", data={"business_name": "Queue SME", "country": "India", "business_type": "x",
                              "government_id": "IN-PAN-ABCDE1234F", "address": "1 Road"})
    kyc_id = db.execute("SELECT k.id FROM kyc k JOIN users u ON u.id = k.user_id "
                        "WHERE u.email = 'q@sme.test' ORDER BY k.id DESC").fetchone()[0]
    admin = app.test_client()
    admin.get("/quick_login/admin")
    assert "IN-PAN-ABCDE1234F" in admin.get("/admin/kyc").text
    admin.post(f"/admin/kyc/{kyc_id}", data={"action": "approve", "reason": "short"})
    assert db.execute("SELECT status FROM kyc WHERE id = ?", (kyc_id,)).fetchone()[0] == "PENDING"
    admin.post(f"/admin/kyc/{kyc_id}", data={"action": "approve", "reason": "Registry and address checked"})
    row = db.execute("SELECT status, reviewed_by FROM kyc WHERE id = ?", (kyc_id,)).fetchone()
    assert row[0] == "VERIFIED" and row[1] is not None


def test_sme_cannot_open_kyc_queue(sme_client):
    assert sme_client.get("/admin/kyc").status_code == 403


@pytest.mark.parametrize("override,msg", [
    ({"receiver": ""}, "Receiver name"),
    ({"receiver": "x" * 121}, "Receiver name"),
    ({"receiver_country": "Atlantis"}, "supported list"),
    ({"receiver_country": ""}, "supported list"),
])
def test_payment_validation(sme_client, db, override, msg):
    before = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    r = sme_client.post("/process_payment", data={**BASE, **override}, follow_redirects=True)
    assert msg in r.text
    assert db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == before


def test_risk_preview_matches_payment_and_writes_nothing(sme_client, db):
    before = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    data = sme_client.post("/api/risk_preview", json=BASE, headers=ORIGIN).get_json()
    assert data["success"] and data["engine"] == "model"
    assert db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == before
    sme_client.post("/process_payment", data=BASE)
    row = _last_tx(db)
    assert row["risk_score"] == data["score"] and row["risk_level"] == data["level"]


def test_demo_scenarios_are_badged(sme_client, db):
    sme_client.post("/process_payment", data={**BASE, "scenario": "low"})
    row = _last_tx(db)
    assert row["feature_source"] == "demo_vector" and row["account_age"] == 26
    assert "DEMO VECTOR" in sme_client.get(f"/result/{row['transaction_id']}").text


def test_scenario_ignored_without_demo_mode(tmp_path, fx_mock):
    app = create_app("test", {"DB_PATH": str(tmp_path / "d.db"), "LEDGER_PATH": str(tmp_path / "l.json"),
                              "WTF_CSRF_ENABLED": False, "DEMO_MODE": False})
    conn = connect(app.config["DB_PATH"])
    uid = conn.execute("SELECT id FROM users WHERE role = 'sme'").fetchone()[0]
    c = app.test_client()
    with c.session_transaction() as s:
        s["user_id"] = uid
    c.post("/process_payment", data={**BASE, "scenario": "low"})
    assert conn.execute("SELECT feature_source FROM transactions ORDER BY id DESC LIMIT 1").fetchone()[0] == "db"
    conn.close()
