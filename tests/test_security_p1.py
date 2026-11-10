"""P1 acceptance: C1, C2, C3, H3, H4, L6."""
import pytest

from crosspay import create_app


def _decision(db, tx_id):
    return db.execute("SELECT decision FROM transactions WHERE transaction_id = ?", (tx_id,)).fetchone()[0]


def test_anonymous_resolve_redirects_and_hold_unchanged(client, db):
    r = client.post("/resolve_hold/TX-2026-8802", data={"action": "approve"})
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert _decision(db, "TX-2026-8802") == "HOLD"


def test_sme_resolve_forbidden(sme_client, db):
    r = sme_client.post("/resolve_hold/TX-2026-8802", data={"action": "approve"})
    assert r.status_code == 403
    assert _decision(db, "TX-2026-8802") == "HOLD"


def test_forged_session_role_is_ignored(sme_client, db):
    with sme_client.session_transaction() as s:
        s["user_role"] = "admin"  # role is read from the DB, not the cookie
    assert sme_client.post("/resolve_hold/TX-2026-8802", data={"action": "approve"}).status_code == 403


def test_admin_can_resolve(admin_client, db):
    r = admin_client.post("/resolve_hold/TX-2026-8802", data={"action": "reject", "reason": "x" * 25})
    assert r.status_code == 302
    assert _decision(db, "TX-2026-8802") in ("BLOCKED", "REJECTED")


def _other_tenant_tx(app, db):
    from werkzeug.security import generate_password_hash

    db.execute("INSERT INTO users (name, email, password, role, created_at) VALUES "
               "('Other SME', 'other@x.test', ?, 'sme', '2026-01-01T00:00:00Z')", (generate_password_hash("p" * 12),))
    other = db.execute("SELECT id FROM users WHERE email = 'other@x.test'").fetchone()[0]
    db.execute("UPDATE transactions SET user_id = ? WHERE transaction_id = 'TX-2026-8803'", (other,))
    return "TX-2026-8803"


def test_cross_tenant_receipt_404(app, sme_client, db):
    tx = _other_tenant_tx(app, db)
    assert sme_client.get(f"/result/{tx}").status_code == 404
    assert tx not in sme_client.get("/transactions").text
    assert tx not in sme_client.get("/dashboard").text


def test_admin_sees_all(app, admin_client, db):
    tx = _other_tenant_tx(app, db)
    assert admin_client.get(f"/result/{tx}").status_code == 200
    assert tx in admin_client.get("/transactions").text


@pytest.mark.parametrize("path", ["/result/TX-2026-8801", "/dashboard", "/transactions", "/blockchain", "/payment"])
def test_pages_require_login(client, path):
    r = client.get(path)
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_sme_does_not_see_release_button(sme_client):
    assert "resolve_hold" not in sme_client.get("/result/TX-2026-8802").text
    assert "resolve_hold" not in sme_client.get("/transactions").text


def test_post_without_csrf_token_is_400(tmp_path, fx_mock):
    app = create_app("test", {"DB_PATH": str(tmp_path / "c.db"), "LEDGER_PATH": str(tmp_path / "l.json"),
                              "WTF_CSRF_ENABLED": True})
    c = app.test_client()
    assert c.post("/login", data={"email": "a@b.co", "password": "x"}).status_code == 400
    c.get("/quick_login/admin")
    assert c.post("/resolve_hold/TX-2026-8802", data={"action": "approve"}).status_code == 400


def test_api_rejects_cross_origin_post(sme_client):
    r = sme_client.post("/api/convert_currency", json={"amount": 1, "from": "USD", "to": "EUR"},
                        headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    ok = sme_client.post("/api/convert_currency", json={"amount": 1, "from": "USD", "to": "EUR"},
                         headers={"Origin": "http://localhost"})
    assert ok.status_code == 200


def test_quick_login_404_without_demo_mode(tmp_path, fx_mock):
    app = create_app("test", {"DB_PATH": str(tmp_path / "c.db"), "LEDGER_PATH": str(tmp_path / "l.json"),
                              "DEMO_MODE": False})
    assert app.test_client().get("/quick_login/admin").status_code == 404


def test_prod_requires_secret_key(tmp_path, monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    import crosspay.config as cfg

    monkeypatch.setattr(cfg.ProdConfig, "SECRET_KEY", "")
    with pytest.raises(RuntimeError):
        create_app("prod", {"DB_PATH": str(tmp_path / "p.db")})


def test_register_rules(client, db):
    r = client.post("/register", data={"name": "A", "email": "not-an-email", "password": "x" * 12})
    assert db.execute("SELECT COUNT(*) FROM users WHERE email='not-an-email'").fetchone()[0] == 0
    client.post("/register", data={"name": "A", "email": "a@b.co", "password": "short"})
    assert db.execute("SELECT COUNT(*) FROM users WHERE email='a@b.co'").fetchone()[0] == 0
    client.post("/register", data={"name": "A", "email": "a@b.co", "password": "long-enough-pw"})
    assert db.execute("SELECT COUNT(*) FROM users WHERE email='a@b.co'").fetchone()[0] == 1


def test_government_id_encrypted_and_masked(sme_client, db):
    stored = db.execute("SELECT government_id FROM kyc ORDER BY id LIMIT 1").fetchone()[0]
    assert stored.startswith("gAAAA") and "984721094" not in stored
    page = sme_client.get("/kyc").text
    assert "US-EIN-984721094" not in page and "1094" in page


def test_logout_requires_post(sme_client):
    assert sme_client.get("/logout").status_code == 405
    assert sme_client.post("/logout").status_code == 302
