"""End-to-end flow (converted from the original tests/test_flow.py script; FX mocked, temp DB and ledger)."""


def test_home_page(client):
    r = client.get("/")
    assert r.status_code == 200


def test_sme_session_and_kyc(sme_client):
    r = sme_client.get("/kyc")
    assert r.status_code == 200
    assert "VERIFIED" in r.text


def test_payment_form(sme_client):
    r = sme_client.get("/payment")
    assert r.status_code == 200
    assert "sender_currency" in r.text


def test_supported_currencies_api(client):
    data = client.get("/api/supported_currencies").get_json()
    assert set(data["currencies"]) == {"USD", "EUR", "GBP", "INR", "SGD", "AED", "AUD", "CAD", "JPY"}


def test_convert_currency_api(client):
    data = client.get("/api/convert_currency?amount=100&from=USD&to=INR").get_json()
    assert data["success"] and data["converted_amount"] == 8325.0


def test_ledger_valid(sme_client):
    data = sme_client.get("/api/validate_chain").get_json()
    assert data["valid"] is True


def test_dashboard_and_history(sme_client):
    assert sme_client.get("/dashboard").status_code == 200
    r = sme_client.get("/transactions")
    assert r.status_code == 200
    assert "TX-2026-8801" in r.text
