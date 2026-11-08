# Task Checklist - PDS & AI Enhancements

## AI Fraud Detection Logic
- [x] Enhance Synthetic Data Ranges
    - [x] Legit: Q(3-12), F(1-4), R(0-1), T(0.5-2)
    - [x] Fraud: Q(12-30), F(4-10), R(1.2-3), T(0.1-0.5)
- [x] Implement Rule-Based Boosting
    - [x] Quantity >= 10 (+0.08)
    - [x] Frequency >= 3 (+0.12)
    - [x] Region Risk >= 1 (+0.10)
    - [x] Beneficiary History (+0.03/tx, max 0.15)
- [x] Add Random Noise (+/- 5%)
- [x] Normalize scores (0-1) and Map Risk Labels (<0.4 Low, 0.4-0.7 Med, >0.7 High)
- [x] Integrate `history_count` in Backend

## Verification System (Completed)
- [x] Fix PDF layout (Government Grade)
- [x] Fix QR Scanner JSON parsing
- [x] Add Integrity Proofs
