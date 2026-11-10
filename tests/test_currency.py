"""Currency conversion unit tests (converted from the original unittest suite to pytest; FX mocked)."""
from decimal import Decimal

import pytest

from crosspay.services.currency import (
    CurrencyService,
    ExchangeRateAPIError,
    InvalidAmountError,
    UnsupportedCurrencyError,
)


@pytest.fixture
def svc(fx_mock):
    s = CurrencyService()
    s.clear_cache()
    return s


def test_successful_conversion(svc):
    res = svc.convert(100, "USD", "INR")
    assert res["source_currency"] == "USD" and res["target_currency"] == "INR"
    assert res["exchange_rate"] == 83.25
    assert res["converted_amount"] == 8325.0
    assert res["formatted_converted_amount"] == "₹8,325.00"
    assert res["provider"] == "MockExchangeRateAPI"


@pytest.mark.parametrize("src,tgt,amount,expected,fmt", [
    ("USD", "EUR", 1000, 920.00, "€920.00"),
    ("USD", "GBP", 250, 197.50, "£197.50"),
    ("USD", "JPY", 10, 1500, "¥1,500"),
    ("USD", "SGD", 100, 134.00, "S$134.00"),
])
def test_currency_pairs(svc, src, tgt, amount, expected, fmt):
    res = svc.convert(amount, src, tgt)
    assert res["converted_amount"] == pytest.approx(expected, abs=0.01)
    assert res["formatted_converted_amount"] == fmt


def test_same_currency_parity(svc, fx_mock):
    res = svc.convert("250.50", "USD", "USD")
    assert res["exchange_rate"] == 1.0
    assert res["converted_amount"] == 250.50
    assert res["formatted_converted_amount"] == "$250.50"
    assert fx_mock.calls == []


@pytest.mark.parametrize("bad", [0, -5, "abc", None, ""])
def test_invalid_amounts(svc, bad):
    with pytest.raises(InvalidAmountError):
        svc.convert(bad, "USD", "EUR")


@pytest.mark.parametrize("src,tgt", [("XYZ", "USD"), ("USD", "BTC"), ("", "USD")])
def test_unsupported_currencies(svc, src, tgt):
    with pytest.raises(UnsupportedCurrencyError):
        svc.convert(10, src, tgt)


@pytest.mark.parametrize("mode", ["timeout", "network", "http500"])
def test_api_failures_raise(svc, fx_mock, mode):
    fx_mock.fail = mode
    with pytest.raises(ExchangeRateAPIError):
        svc.convert(10, "USD", "EUR")


def test_decimal_rounding(svc):
    jpy = svc.convert("103.79", "USD", "JPY")
    assert jpy["converted_amount"] == 15569.0  # 15568.5 rounds half up, 0 decimals
    assert jpy["formatted_converted_amount"] == "¥15,569"
    eur = svc.convert("97.0434", "USD", "EUR")
    assert eur["converted_amount"] == 89.28
    assert svc.quantize_amount(Decimal("89.275"), "EUR") == Decimal("89.28")


def test_cache_avoids_second_fetch(svc, fx_mock):
    svc.convert(1, "USD", "EUR")
    svc.convert(2, "USD", "EUR")
    assert len(fx_mock.calls) == 1
