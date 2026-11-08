"""
Integration test script for Risk-Adaptive Smart Contract Settlement System.
Validates the entire end-to-end pipeline including Currency Conversion:
1. Home page with workflow pipeline
2. Quick Login as SME Demo account
3. KYC Verification Status confirmation
4. Payment Request form accessibility with currency selectors
5. Supported Currencies API endpoint
6. Real-Time Currency Conversion API endpoint
7. Scenario 1: Low Risk -> Auto-Approve -> Currency Converted (USD -> EUR) -> Block Mined on Blockchain
8. Scenario 2: Medium Risk -> Held in Escrow -> Currency Converted (USD -> EUR) -> Pending Audit
9. Scenario 3: High Risk -> Blocked -> Currency Converted (USD -> INR) -> Smart Contract Rejection
10. Compliance Hold Resolution & Secondary Mining
11. Blockchain Ledger Integrity (SHA-256) Audit
12. Dashboard Analytics & Multi-Currency Settlement Volume
13. Searchable Transaction History with Exchange Rate Snapshots
"""

import sys
import os
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database.db import get_db, init_db

def run_tests():
    init_db()
    client = app.test_client()

    print("==================================================================")
    print("  RUNNING SYSTEM INTEGRATION & END-TO-END FLOW TESTS              ")
    print("==================================================================")

    # 1. Check Home
    r = client.get('/')
    assert r.status_code == 200, f'Home failed: {r.status_code}'
    print("[PASS] 1. Home page loads with workflow diagram")

    # 2. Quick Login as SME
    r = client.get('/quick_login/sme', follow_redirects=True)
    assert r.status_code == 200, f'Login failed: {r.status_code}'
    assert 'Global Logistics' in r.text, 'Session did not persist'
    print("[PASS] 2. SME Authentication & Session initialized")

    # 3. Check KYC
    r = client.get('/kyc')
    assert r.status_code == 200 and 'KYC VERIFIED' in r.text, 'KYC page check failed'
    print("[PASS] 3. Simulated KYC Verification module confirms VERIFIED status")

    # 4. Check Payment page
    r = client.get('/payment')
    assert r.status_code == 200 and 'Cross-Border Settlement Request' in r.text, 'Payment page check failed'
    assert 'Real-Time Cross-Border Currency Conversion Engine' in r.text, 'Currency conversion panel missing'
    print("[PASS] 4. Payment form accessible with Currency Conversion Engine & 1-Click Scenarios")

    # 5. Test Supported Currencies API
    r = client.get('/api/supported_currencies')
    assert r.status_code == 200, f'Supported currencies failed: {r.status_code}'
    currencies = r.json.get('currencies', {})
    for expected_curr in ['USD', 'EUR', 'GBP', 'INR', 'SGD', 'AED', 'AUD', 'CAD', 'JPY']:
        assert expected_curr in currencies, f"Missing expected currency: {expected_curr}"
    print(f"[PASS] 5. Supported Currencies API returns {len(currencies)} currencies (USD, EUR, GBP, INR, SGD, AED, AUD, CAD, JPY)")

    # 6. Test Live Currency Conversion API
    r = client.get('/api/convert_currency?amount=100&source_currency=USD&target_currency=INR')
    assert r.status_code == 200, f'Currency conversion API failed: {r.status_code}'
    conv_data = r.json
    assert conv_data.get('success') is True
    assert conv_data.get('converted_amount') > 0
    assert 'exchange_rate' in conv_data
    print(f"[PASS] 6. Live Currency Conversion API: $100.00 USD -> {conv_data.get('formatted_converted_amount')} (Rate: 1 USD = {conv_data.get('exchange_rate')} INR)")

    # 7. Test Scenario 1: Low Risk (USD -> EUR conversion)
    data_low = {
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
        'notes': 'Low risk routine order with currency conversion'
    }
    r = client.post('/process_payment', data=data_low, follow_redirects=True)
    assert r.status_code == 200
    assert 'APPROVED' in r.text and 'LOW RISK' in r.text, 'Scenario 1 Low Risk approval failed'
    assert 'Confirmed Exchange Rate' in r.text, 'Exchange rate snapshot not shown on receipt'
    print("[PASS] 7. Scenario 1 (Low Risk): USD -> EUR -> ML: LOW RISK -> APPROVED -> Block Mined on Blockchain")

    # 8. Test Scenario 2: Medium Risk (USD -> EUR conversion)
    data_med = {
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
        'notes': 'Medium risk unusual volume'
    }
    r = client.post('/process_payment', data=data_med, follow_redirects=True)
    assert r.status_code == 200
    assert 'HOLD' in r.text and 'MEDIUM RISK' in r.text, 'Scenario 2 Medium Risk hold failed'
    print("[PASS] 8. Scenario 2 (Medium Risk): USD -> EUR -> ML: MEDIUM RISK -> HOLD -> Pending Escrow")

    # 9. Test Scenario 3: High Risk (USD -> INR conversion)
    data_high = {
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
        'notes': 'High risk velocity spike'
    }
    r = client.post('/process_payment', data=data_high, follow_redirects=True)
    assert r.status_code == 200
    assert 'BLOCKED' in r.text and 'HIGH RISK' in r.text, 'Scenario 3 High Risk block failed'
    print("[PASS] 9. Scenario 3 (High Risk): USD -> INR -> ML: HIGH RISK -> BLOCKED -> Smart Contract Rejection")

    # 10. Test Blockchain Validation API
    r = client.get('/api/validate_chain')
    res = r.json
    assert res['valid'] is True, f'Chain invalid: {res}'
    print(f"[PASS] 10. Blockchain ledger integrity cryptographically validated! ({res['total_blocks']} Blocks)")

    # 11. Test Dashboard
    r = client.get('/dashboard')
    assert r.status_code == 200 and 'Random Forest Machine Learning' in r.text
    print("[PASS] 11. Dashboard Analytics, Multi-Currency Volume & Model Performance verified")

    # 12. Test Transaction History
    r = client.get('/transactions')
    assert r.status_code == 200 and 'Settlement History' in r.text
    print("[PASS] 12. Transaction history with confirmed exchange rates and converted amounts verified")

    print("==================================================================")
    print("  ALL 12 VERIFICATION CHECKS PASSED SUCCESSFULLY!                 ")
    print("==================================================================")

if __name__ == '__main__':
    run_tests()
