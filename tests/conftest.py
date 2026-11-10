"""Shared pytest fixtures. Every test gets its own temp DB and ledger; FX is always mocked."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crosspay import create_app  # noqa: E402

USD_RATES = {"USD": 1.0, "EUR": 0.92, "GBP": 0.79, "INR": 83.25, "SGD": 1.34, "AED": 3.6725,
             "AUD": 1.52, "CAD": 1.36, "JPY": 150.0}


class FakeFX:
    """Stands in for requests.get against the rate API. Rates are derived from USD_RATES."""

    def __init__(self):
        self.calls = []
        self.fail = None  # None | "timeout" | "network" | "http500"
        self.drop = {}  # base -> set of currencies missing from that base's response
        self.provider = "MockExchangeRateAPI"
        self.last_update = "Sat, 24 Oct 2026 00:00:01 +0000"

    def __call__(self, url, headers=None, timeout=None):
        import requests

        self.calls.append(url)
        if self.fail == "timeout":
            raise requests.exceptions.Timeout("timeout")
        if self.fail == "network":
            raise requests.exceptions.ConnectionError("down")
        resp = MagicMock()
        if self.fail == "http500":
            resp.status_code = 500
            resp.text = "server error"
            return resp
        base = url.rstrip("/").split("/")[-1]
        k = USD_RATES[base]
        rates = {c: round(v / k, 6) for c, v in USD_RATES.items()}
        for c in self.drop.get(base, ()):
            rates.pop(c, None)
        resp.status_code = 200
        resp.json.return_value = {"result": "success", "provider": self.provider, "rates": rates,
                                  "time_last_update_utc": self.last_update}
        return resp


@pytest.fixture
def fx_mock():
    fake = FakeFX()
    with patch("crosspay.services.currency.requests.get", side_effect=fake):
        yield fake


@pytest.fixture
def app(tmp_path, fx_mock):
    application = create_app("test", {
        "DB_PATH": str(tmp_path / "test.db"),
        "LEDGER_PATH": str(tmp_path / "ledger.json"),
        "UPLOAD_DIR": str(tmp_path / "uploads"),
        "WTF_CSRF_ENABLED": False,
    })
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


def _login(app, role):
    c = app.test_client()
    resp = c.get(f"/quick_login/{role}")
    assert resp.status_code == 302
    return c


@pytest.fixture
def sme_client(app):
    return _login(app, "sme")


@pytest.fixture
def admin_client(app):
    return _login(app, "admin")


@pytest.fixture
def db(app):
    from crosspay.db import connect

    conn = connect(app.config["DB_PATH"])
    yield conn
    conn.close()
