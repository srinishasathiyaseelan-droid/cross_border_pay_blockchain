"""
Unit and Integration Test Suite for CrossPay Currency Conversion Feature.

Tests cover:
1. Successful currency conversion
2. Different currency pairs (USD->EUR, USD->INR, EUR->JPY, etc.)
3. Same-currency conversion (USD->USD, rate 1.0)
4. Invalid, zero, and negative amounts
5. Unsupported currency codes
6. API timeout and network failure handling
7. Invalid API responses (HTTP error, malformed JSON, error result)
8. Decimal precision and rounding (JPY 0 decimals, USD/INR 2 decimals, ROUND_HALF_UP)
9. Exchange-rate snapshot storage and immutability
10. Integration with KYC, Random Forest ML risk prediction, and Smart Contract settlement
11. Approved (LOW), Held (MEDIUM), and Blocked (HIGH) workflows with multi-currency
12. Regression tests ensuring existing endpoints remain operational
"""

import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
import requests
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database.db import get_db, init_db
from currency_service import (
    CurrencyService,
    currency_service,
    CurrencyConversionError,
    UnsupportedCurrencyError,
    InvalidAmountError,
    ExchangeRateAPIError,
    SUPPORTED_CURRENCIES
)
from blockchain.blockchain import blockchain, smart_contract

class TestCurrencyConversion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure database is initialized
        init_db()

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.service = CurrencyService()
        self.service.clear_cache()

    # -------------------------------------------------------------------------
    # 1. Successful Conversion (Mocked API)
    # -------------------------------------------------------------------------
    @patch('requests.get')
    def test_successful_conversion_mocked(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "result": "success",
            "provider": "MockExchangeRateAPI",
            "time_last_update_utc": "Sat, 24 Oct 2026 00:00:00 UTC",
            "rates": {
                "INR": 83.250000,
                "EUR": 0.920000,
                "USD": 1.0
            }
        }
        mock_get.return_value = mock_resp

        result = self.service.convert(amount=100, source_currency="USD", target_currency="INR")

        self.assertEqual(result["source_currency"], "USD")
        self.assertEqual(result["target_currency"], "INR")
        self.assertEqual(result["original_amount"], 100.0)
        self.assertEqual(result["exchange_rate"], 83.25)
        self.assertEqual(result["converted_amount"], 8325.0)
        self.assertEqual(result["formatted_converted_amount"], "₹8,325.00")
        self.assertEqual(result["provider"], "MockExchangeRateAPI")
        self.assertIn("Sat, 24 Oct 2026", result["last_updated"])

    # -------------------------------------------------------------------------
    # 2. Different Currency Pairs
    # -------------------------------------------------------------------------
    @patch('requests.get')
    def test_different_currency_pairs(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "result": "success",
            "provider": "MockExchangeRateAPI",
            "time_last_update_utc": "Sat, 24 Oct 2026 00:00:00 UTC",
            "rates": {
                "EUR": 0.92,
                "GBP": 0.78,
                "SGD": 1.34,
                "AED": 3.67,
                "AUD": 1.52,
                "CAD": 1.36,
                "JPY": 155.0,
                "USD": 1.0
            }
        }
        mock_get.return_value = mock_resp

        pairs = [
            ("USD", "EUR", 100, 92.00, "€92.00"),
            ("USD", "SGD", 50, 67.00, "S$67.00"),
            ("USD", "AED", 100, 367.00, "AED367.00"),
            ("USD", "AUD", 200, 304.00, "A$304.00"),
            ("USD", "CAD", 100, 136.00, "C$136.00")
        ]

        for src, tgt, amt, expected_conv, expected_fmt in pairs:
            res = self.service.convert(amt, src, tgt)
            self.assertAlmostEqual(res["converted_amount"], expected_conv, places=2)
            self.assertEqual(res["formatted_converted_amount"], expected_fmt)

    # -------------------------------------------------------------------------
    # 3. Same-Currency Conversion
    # -------------------------------------------------------------------------
    def test_same_currency_conversion(self):
        # Should execute with exact 1.0 parity and no network requirement
        res = self.service.convert(amount=250.50, source_currency="USD", target_currency="USD")
        self.assertEqual(res["exchange_rate"], 1.0)
        self.assertEqual(res["converted_amount"], 250.50)
        self.assertEqual(res["formatted_converted_amount"], "$250.50")

        res_inr = self.service.convert(amount=50000, source_currency="INR", target_currency="INR")
        self.assertEqual(res_inr["exchange_rate"], 1.0)
        self.assertEqual(res_inr["converted_amount"], 50000.0)
        self.assertEqual(res_inr["formatted_converted_amount"], "₹50,000.00")

    # -------------------------------------------------------------------------
    # 4. Invalid, Zero, and Negative Amounts
    # -------------------------------------------------------------------------
    def test_invalid_zero_and_negative_amounts(self):
        invalid_inputs = [0, "0", -50, "-12.5", "not_a_number", None, ""]
        for val in invalid_inputs:
            with self.assertRaises(InvalidAmountError):
                self.service.convert(amount=val, source_currency="USD", target_currency="EUR")

    # -------------------------------------------------------------------------
    # 5. Unsupported Currency Codes
    # -------------------------------------------------------------------------
    def test_unsupported_currency_codes(self):
        unsupported = ["XYZ", "BITCOIN", "USDT", "123", ""]
        for code in unsupported:
            with self.assertRaises(UnsupportedCurrencyError):
                self.service.convert(amount=100, source_currency=code, target_currency="USD")
            with self.assertRaises(UnsupportedCurrencyError):
                self.service.convert(amount=100, source_currency="USD", target_currency=code)

    # -------------------------------------------------------------------------
    # 6. API Timeout and Network Failure
    # -------------------------------------------------------------------------
    @patch('requests.get')
    def test_api_timeout_and_network_failure(self, mock_get):
        # Timeout
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
        with self.assertRaises(ExchangeRateAPIError):
            self.service.convert(100, "USD", "EUR")

        # Network disconnect
        mock_get.side_effect = requests.exceptions.ConnectionError("Network is unreachable")
        with self.assertRaises(ExchangeRateAPIError):
            self.service.convert(100, "USD", "INR")

    # -------------------------------------------------------------------------
    # 7. Invalid API Responses
    # -------------------------------------------------------------------------
    @patch('requests.get')
    def test_invalid_api_responses(self, mock_get):
        # HTTP 500 Internal Server Error
        mock_500 = MagicMock()
        mock_500.status_code = 500
        mock_500.text = "Server Error"
        mock_get.return_value = mock_500
        with self.assertRaises(ExchangeRateAPIError):
            self.service.convert(100, "USD", "EUR")

        # Malformed non-JSON
        mock_bad_json = MagicMock()
        mock_bad_json.status_code = 200
        mock_bad_json.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_bad_json
        with self.assertRaises(ExchangeRateAPIError):
            self.service.convert(100, "USD", "EUR")

        # Error result from API
        mock_err_result = MagicMock()
        mock_err_result.status_code = 200
        mock_err_result.json.return_value = {"result": "error", "error-type": "invalid-key"}
        mock_get.return_value = mock_err_result
        with self.assertRaises(ExchangeRateAPIError):
            self.service.convert(100, "USD", "EUR")

        # Missing rates dictionary
        mock_missing_rates = MagicMock()
        mock_missing_rates.status_code = 200
        mock_missing_rates.json.return_value = {"result": "success"}
        mock_get.return_value = mock_missing_rates
        with self.assertRaises(ExchangeRateAPIError):
            self.service.convert(100, "USD", "EUR")

    # -------------------------------------------------------------------------
    # 8. Decimal Precision and Rounding
    # -------------------------------------------------------------------------
    @patch('requests.get')
    def test_decimal_precision_and_rounding(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "result": "success",
            "rates": {
                "JPY": 155.6789,
                "EUR": 0.892784,
                "USD": 1.0
            }
        }
        mock_get.return_value = mock_resp

        # JPY must have 0 decimal places
        jpy_conv = self.service.convert(100, "USD", "JPY")
        self.assertEqual(jpy_conv["converted_amount"], 15568.0)
        self.assertEqual(jpy_conv["formatted_converted_amount"], "¥15,568")

        # EUR must have 2 decimal places with ROUND_HALF_UP
        eur_conv = self.service.convert(100, "USD", "EUR")
        self.assertEqual(eur_conv["converted_amount"], 89.28)
        self.assertEqual(eur_conv["formatted_converted_amount"], "€89.28")

        # Precision arithmetic check
        amt_dec = Decimal("100.00")
        rate_dec = Decimal("0.892784")
        quantized = self.service.quantize_amount(amt_dec * rate_dec, "EUR")
        self.assertEqual(quantized, Decimal("89.28"))

    # -------------------------------------------------------------------------
    # 9. Exchange Rate Snapshot Storage in SQLite
    # -------------------------------------------------------------------------
    @patch('currency_service.currency_service.convert')
    def test_exchange_rate_snapshot_storage(self, mock_convert):
        mock_convert.return_value = {
            "source_currency": "USD",
            "target_currency": "INR",
            "original_amount": 1000.0,
            "exchange_rate": 83.2500,
            "converted_amount": 83250.0,
            "normalized_usd_amount": 1000.0,
            "provider": "SnapshotTestProvider",
            "last_updated": "2026-10-24 10:00:00 UTC",
            "formatted_converted_amount": "₹83,250.00"
        }

        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_name'] = 'Global Logistics Ltd (SME Demo)'
            sess['user_role'] = 'sme'

        tx_payload = {
            'sender': 'Global Logistics SME Ltd',
            'receiver': 'EuroTech Industrial Gmbh',
            'sender_country': 'United States',
            'receiver_country': 'Germany',
            'sender_currency': 'USD',
            'receiver_currency': 'INR',
            'amount': '1000.00',
            'frequency': '2',
            'previous_transactions': '48',
            'suspicious_transactions': '0',
            'account_age': '26',
            'notes': 'Snapshot verification test invoice'
        }

        resp = self.client.post('/process_payment', data=tx_payload, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Verify SQLite row
        conn = get_db()
        tx_row = conn.execute(
            "SELECT * FROM transactions WHERE notes = ? ORDER BY id DESC LIMIT 1",
            ('Snapshot verification test invoice',)
        ).fetchone()
        conn.close()

        self.assertIsNotNone(tx_row)
        self.assertEqual(tx_row['source_currency'], 'USD')
        self.assertEqual(tx_row['target_currency'], 'INR')
        self.assertEqual(tx_row['exchange_rate'], 83.25)
        self.assertEqual(tx_row['converted_amount'], 83250.0)
        self.assertEqual(tx_row['exchange_rate_provider'], 'SnapshotTestProvider')
        self.assertEqual(tx_row['rate_timestamp'], '2026-10-24 10:00:00 UTC')

    # -------------------------------------------------------------------------
    # 10. KYC Guard Enforcement
    # -------------------------------------------------------------------------
    def test_unverified_kyc_blocked_from_settlement(self):
        # Register a new unverified SME
        with self.client.session_transaction() as sess:
            sess['user_id'] = 9999
            sess['user_name'] = 'Unverified SME Corp'
            sess['user_role'] = 'sme'

        conn = get_db()
        conn.execute("DELETE FROM kyc WHERE user_id = 9999")
        conn.commit()
        conn.close()

        tx_payload = {
            'sender': 'Unverified SME Corp',
            'receiver': 'Partner Corp',
            'sender_country': 'United States',
            'receiver_country': 'Germany',
            'sender_currency': 'USD',
            'receiver_currency': 'EUR',
            'amount': '500.00',
            'frequency': '1',
            'previous_transactions': '0',
            'suspicious_transactions': '0',
            'account_age': '1'
        }

        resp = self.client.post('/process_payment', data=tx_payload, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Access Denied", resp.text)

    # -------------------------------------------------------------------------
    # 11. Multi-Currency Flow: Approved, Held, and Blocked
    # -------------------------------------------------------------------------
    @patch('currency_service.currency_service.convert')
    def test_scenarios_with_currency_conversion(self, mock_convert):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_name'] = 'Global Logistics Ltd (SME Demo)'
            sess['user_role'] = 'sme'

        # --- A. LOW RISK (USD -> EUR, $4,500 USD equivalent) -> APPROVE
        mock_convert.return_value = {
            "source_currency": "USD",
            "target_currency": "EUR",
            "original_amount": 4500.0,
            "exchange_rate": 0.92,
            "converted_amount": 4140.0,
            "normalized_usd_amount": 4500.0,
            "provider": "ExchangeRate-API",
            "last_updated": "2026-10-24 00:00:00 UTC",
            "formatted_converted_amount": "€4,140.00"
        }
        res_low = self.client.post('/process_payment', data={
            'sender': 'Global Logistics SME Ltd',
            'receiver': 'EuroTech Industrial Gmbh',
            'sender_country': 'United States',
            'receiver_country': 'Germany',
            'sender_currency': 'USD',
            'receiver_currency': 'EUR',
            'amount': '4500.00',
            'frequency': '2',
            'previous_transactions': '48',
            'suspicious_transactions': '0',
            'account_age': '26',
            'notes': 'Unit test low risk approval'
        }, follow_redirects=True)
        self.assertIn("APPROVED", res_low.text)
        self.assertIn("LOW RISK", res_low.text)

        # --- B. MEDIUM RISK (USD -> EUR, $28,500 USD equivalent) -> HOLD
        mock_convert.return_value = {
            "source_currency": "USD",
            "target_currency": "EUR",
            "original_amount": 28500.0,
            "exchange_rate": 0.92,
            "converted_amount": 26220.0,
            "normalized_usd_amount": 28500.0,
            "provider": "ExchangeRate-API",
            "last_updated": "2026-10-24 00:00:00 UTC",
            "formatted_converted_amount": "€26,220.00"
        }
        res_med = self.client.post('/process_payment', data={
            'sender': 'Global Logistics SME Ltd',
            'receiver': 'Apex Pacific Trade Corp',
            'sender_country': 'United States',
            'receiver_country': 'Brazil',
            'sender_currency': 'USD',
            'receiver_currency': 'EUR',
            'amount': '28500.00',
            'frequency': '7',
            'previous_transactions': '6',
            'suspicious_transactions': '1',
            'account_age': '6',
            'notes': 'Unit test medium risk hold'
        }, follow_redirects=True)
        self.assertIn("ON HOLD", res_med.text)
        self.assertIn("MEDIUM RISK", res_med.text)

        # --- C. HIGH RISK (USD -> INR, $145,000 USD equivalent) -> BLOCK
        mock_convert.return_value = {
            "source_currency": "USD",
            "target_currency": "INR",
            "original_amount": 145000.0,
            "exchange_rate": 83.25,
            "converted_amount": 12071250.0,
            "normalized_usd_amount": 145000.0,
            "provider": "ExchangeRate-API",
            "last_updated": "2026-10-24 00:00:00 UTC",
            "formatted_converted_amount": "₹12,071,250.00"
        }
        res_high = self.client.post('/process_payment', data={
            'sender': 'Global Logistics SME Ltd',
            'receiver': 'Shadow Frontier Express',
            'sender_country': 'United States',
            'receiver_country': 'Nigeria',
            'sender_currency': 'USD',
            'receiver_currency': 'INR',
            'amount': '145000.00',
            'frequency': '19',
            'previous_transactions': '1',
            'suspicious_transactions': '4',
            'account_age': '1',
            'notes': 'Unit test high risk block'
        }, follow_redirects=True)
        self.assertIn("BLOCKED", res_high.text)
        self.assertIn("HIGH RISK", res_high.text)

    # -------------------------------------------------------------------------
    # 12. Regression Tests for Existing System Routes
    # -------------------------------------------------------------------------
    def test_existing_system_routes_regression(self):
        # 1. Home page
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)

        # 2. Quick login SME
        r = self.client.get('/quick_login/sme', follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn('Global Logistics', r.text)

        # 3. KYC page
        r = self.client.get('/kyc')
        self.assertEqual(r.status_code, 200)
        self.assertIn('VERIFIED', r.text)

        # 4. Payment page
        r = self.client.get('/payment')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Real-Time Cross-Border Currency Conversion Engine', r.text)

        # 5. Blockchain API validation
        r = self.client.get('/api/validate_chain')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json.get('valid'))

        # 6. Dashboard
        r = self.client.get('/dashboard')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Random Forest Machine Learning', r.text)

        # 7. Transaction history
        r = self.client.get('/transactions')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Settlement History', r.text)


if __name__ == '__main__':
    unittest.main()
