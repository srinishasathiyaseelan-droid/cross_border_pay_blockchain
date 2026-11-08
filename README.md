# Risk-Adaptive Smart Contract Settlement for SME Cross-Border Payments

An academic prototype web application integrating **KYC Verification**, **Machine Learning Risk Prediction (Random Forest)**, and **Risk-Adaptive Smart Contract Blockchain Settlement** for Small and Medium Enterprises (SMEs).

---

## 📌 Project Overview

Cross-border trade finance is critical for Small and Medium Enterprises (SMEs), yet traditional correspondent banking systems suffer from high remittance fees (up to 7–10%), long settlement delays (3–5 business days), lack of transparency, and vulnerability to financial fraud. 

This project implements a **Risk-Adaptive Smart Contract Settlement Engine** that dynamically evaluates SME transaction risk before committing settlement onto a distributed ledger.

### Core Objectives
1. **SME Identity Compliance:** Verify SME identity and credentials prior to initiating transactions via a simulated KYC process.
2. **Machine Learning Risk Prediction:** Use a scikit-learn **Random Forest Classifier** to evaluate cross-border transaction behavioral parameters (amount, velocity, historical suspicious count, account age, corridor risk) into **LOW**, **MEDIUM**, or **HIGH** risk.
3. **Risk-Adaptive Decision Engine:**
   - **LOW RISK** $\rightarrow$ **APPROVE** $\rightarrow$ Settle and record on Blockchain via Smart Contract.
   - **MEDIUM RISK** $\rightarrow$ **HOLD** $\rightarrow$ Place in compliance escrow for secondary audit.
   - **HIGH RISK** $\rightarrow$ **BLOCK** $\rightarrow$ Reject settlement; prevent blockchain ledger recording.
4. **Smart Contract & Cryptographic Blockchain:** Enforce settlement rules via Solidity Smart Contract logic and record approved settlements on a tamper-resistant SHA-256 Proof-of-Work blockchain ledger.
5. **Traceable Audit & Dashboard:** Provide an interactive analytics dashboard and searchable transaction history.

---

## 🏗️ System Workflow

The entire application strictly follows this proposed methodology:

```
USER / SME
    ↓
KYC VERIFICATION (Simulated Entity Check)
    ↓
PAYMENT REQUEST (Corridor, Amount, Velocity, History)
    ↓
RANDOM FOREST RISK PREDICTION (Scikit-Learn Classifier)
    ↓
RISK-BASED DECISION
    ├─► LOW RISK    ──► APPROVE ──► SMART CONTRACT ──► BLOCKCHAIN BLOCK MINED ──► SETTLED
    ├─► MEDIUM RISK ──► HOLD    ──► ESCROW HOLD    ──► AWAITING COMPLIANCE AUDIT
    └─► HIGH RISK   ──► BLOCK   ──► POLICY REJECT  ──► NOT RECORDED ON CHAIN
    ↓
TRANSACTION HISTORY & ANALYTICS DASHBOARD
```

---

## 💻 Technologies Used

| Layer | Technology | Description |
|---|---|---|
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Chart.js | Modern fintech dark UI, glassmorphism, responsive status badges, interactive charts |
| **Backend** | Python 3.12, Flask 3.1 | REST API routes, session management, rule engine |
| **Machine Learning** | Python, Scikit-learn, NumPy, Pandas | **Random Forest Classifier** (`random_state=42`), Accuracy: **98.67%**, F1: **98.66%** |
| **Database** | SQLite (`database/database.db`) | Relational storage for users, KYC records, and transactions |
| **Blockchain** | Python (`blockchain.py`), SHA-256, Proof-of-Work | Local tamper-proof ledger with cryptographic chain integrity validation |
| **Smart Contract** | Solidity (`smart_contract.sol`) + Simulation Engine | Conditional execution rules for SME payments |

---

## 📁 Project Structure

```
CrossPay-main/
│
├── app.py                      # Main Flask application and API routes
├── requirements.txt            # Python dependencies (flask, scikit-learn, joblib, pandas)
├── README.md                   # Complete project documentation
│
├── model/
│   ├── train_model.py          # Synthetic dataset generator & Random Forest training pipeline
│   ├── random_forest_model.pkl # Trained Random Forest model binary
│   ├── dataset.csv             # 6,000 SME transaction training samples
│   └── metrics.json            # Model evaluation metrics (Accuracy, Precision, Recall, F1)
│
├── database/
│   ├── db.py                   # SQLite schema initialization and seed data
│   └── database.db             # SQLite database file
│
├── blockchain/
│   ├── blockchain.py           # Cryptographic SHA-256 blockchain & smart contract runtime
│   ├── smart_contract.sol      # Solidity smart contract specification
│   └── blockchain_ledger.json  # Persistent JSON blockchain ledger
│
├── templates/
│   ├── base.html               # Master layout with navigation and footer
│   ├── index.html              # Landing page with interactive workflow diagram
│   ├── login.html              # User login with 1-click demo accounts
│   ├── register.html           # New SME registration
│   ├── kyc.html                # KYC verification form with simulated states
│   ├── payment.html            # Payment request form with 1-Click Demo Scenarios
│   ├── result.html             # Risk prediction and smart contract decision result
│   ├── dashboard.html          # Analytics dashboard with Chart.js
│   ├── transactions.html       # Searchable transaction history and compliance hold release
│   └── blockchain.html         # Visual blockchain ledger explorer and integrity auditor
│
└── static/
    ├── css/
    │   └── style.css           # Premium fintech styling and responsive layouts
    └── js/
        └── script.js           # Scenario autofill, live risk preview, blockchain verifier
```

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
Ensure you have Python 3.10+ installed on your computer.

### 2. Install Dependencies
Open your terminal (PowerShell or Command Prompt) in the project directory:

```bash
pip install -r requirements.txt
```

### 3. Train the Random Forest Machine Learning Model
Train the model on the SME transaction dataset:

```bash
python model/train_model.py
```
*Output will display Accuracy: 98.67%, Precision: 98.67%, Recall: 98.67%, F1 Score: 98.66%.*

### 4. Initialize the Database
Set up the SQLite database and seed initial demo accounts:

```bash
python database/db.py
```

### 5. Launch the Web Application
Start the Flask development server:

```bash
python app.py
```

### 6. Open in Browser
Navigate to:
```
http://127.0.0.1:5000
```

---

## 🎯 System Validation Scenarios

The **Payment Request** page features **1-Click Scenario Buttons** for validating the three risk profiles:

### Scenario 1 – Low Risk (Auto-Approve)
- **Settlement Amount:** $4,500.00 USD
- **Corridor:** United States $\rightarrow$ Germany (Low risk)
- **Velocity:** 2 transactions/week
- **Previous Successful Transactions:** 48
- **Previous Suspicious Flags:** 0
- **Account Age:** 26 months
- **Expected Result:**
  - Random Forest ML: **LOW RISK (8.4% Risk Probability)**
  - Decision: **APPROVED**
  - Smart Contract: **EXECUTED_SETTLED**
  - Blockchain: **Mined into new Block with SHA-256 Tx Hash**

---

### Scenario 2 – Medium Risk (Hold in Escrow)
- **Settlement Amount:** $28,500.00 EUR
- **Corridor:** United States $\rightarrow$ Brazil (Medium risk)
- **Velocity:** 7 transactions/week (Unusual spike)
- **Previous Successful Transactions:** 6
- **Previous Suspicious Flags:** 1
- **Account Age:** 6 months (Relatively new account)
- **Expected Result:**
  - Random Forest ML: **MEDIUM RISK (62.8% Risk Probability)**
  - Decision: **HOLD**
  - Smart Contract: **HELD_IN_ESCROW**
  - Blockchain: **PENDING ADDITIONAL VERIFICATION**
  - *Action:* Demonstrate compliance officer resolving hold in **Transaction History** $\rightarrow$ clicks **Release** $\rightarrow$ newly mined to blockchain!

---

### Scenario 3 – High Risk (Block & Prevent)
- **Settlement Amount:** $145,000.00 USD
- **Corridor:** United States $\rightarrow$ Nigeria (Elevated corridor risk)
- **Velocity:** 19 transactions/week (Severe anomaly)
- **Previous Successful Transactions:** 1
- **Previous Suspicious Flags:** 4
- **Account Age:** 1 month (Brand new SME account)
- **Expected Result:**
  - Random Forest ML: **HIGH RISK (94.6% Risk Probability)**
  - Decision: **BLOCKED**
  - Smart Contract: **REJECTED_BLOCKED**
  - Blockchain: **NOT RECORDED (Security Block)**

---

---

## 💱 Real-Time Currency Conversion Module

The application includes an authentic **Multi-Currency Cross-Border Settlement Engine** integrated directly into the payment workflow:

### Supported Global Currencies
| Code | Currency Name | Symbol | Decimals | Reference Country |
|---|---|---|---|---|
| **USD** | US Dollar | `$` | 2 | United States 🇺🇸 |
| **EUR** | Euro | `€` | 2 | Germany 🇩🇪 |
| **GBP** | British Pound | `£` | 2 | United Kingdom 🇬🇧 |
| **INR** | Indian Rupee | `₹` | 2 | India 🇮🇳 |
| **SGD** | Singapore Dollar | `S$` | 2 | Singapore 🇸🇬 |
| **AED** | UAE Dirham | `AED` | 2 | United Arab Emirates 🇦🇪 |
| **AUD** | Australian Dollar | `A$` | 2 | Australia 🇦🇺 |
| **CAD** | Canadian Dollar | `C$` | 2 | Canada 🇨🇦 |
| **JPY** | Japanese Yen | `¥` | 0 | Japan 🇯🇵 |

### Conversion Calculation Formula
$$\text{Converted Amount} = \text{Transaction Amount} \times \text{Exchange Rate}$$

- **Decimal Precision**: All financial calculations use Python's `Decimal` with `ROUND_HALF_UP` rounding to avoid IEEE 754 floating-point inaccuracies.
- **JPY Special Case**: Quantized to integer (0 decimal places), while other fiat currencies are quantized to 2 decimal places.
- **Rate Snapshots**: When a user confirms a settlement, the exact confirmed exchange rate, provider, and timestamp are captured as an immutable snapshot stored in SQLite and cryptographically hashed into the blockchain block.

### Exchange-Rate API Configuration & Environment Variables
The application connects to **ExchangeRate-API** to fetch real-time market rates. It works out-of-the-box via open public endpoints, and also supports personal API keys via environment variables:

| Environment Variable | Description | Default Value |
|---|---|---|
| `EXCHANGE_RATE_API_KEY` | Optional API key from [ExchangeRate-API](https://www.exchangerate-api.com/) | *None (uses open endpoint)* |
| `EXCHANGE_RATE_API_URL` | Custom endpoint template (e.g. `https://v6.exchangerate-api.com/v6/{api_key}/latest/{base}`) | `https://open.er-api.com/v6/latest/{base}` |
| `EXCHANGE_RATE_PROVIDER` | Display name of the rate provider | `ExchangeRate-API` |
| `EXCHANGE_RATE_CACHE_TTL` | Cache duration in seconds before refreshing rates | `3600` (1 hour) |
| `EXCHANGE_RATE_TIMEOUT` | HTTP request timeout in seconds | `8.0` |

#### How to Configure in PowerShell:
```powershell
$env:EXCHANGE_RATE_API_KEY="your_api_key_here"
python app.py
```

### Machine Learning Compatibility (Reference Currency Normalization)
The Random Forest model evaluates 7 behavioural features calibrated on USD scale:
1. `amount` (Normalized USD equivalent)
2. `frequency`
3. `previous_transactions`
4. `suspicious_transactions`
5. `account_age`
6. `corridor_risk`
7. `amount_to_age_ratio`

When a transaction is submitted in non-USD currencies (e.g. INR or JPY), CrossPay dynamically converts the transaction amount to its **normalized USD reference equivalent** before risk inference. This preserves the trained Random Forest feature distribution, preventing large currency denominations (e.g. ₹500,000 INR or ¥1,000,000 JPY) from being falsely flagged as high-risk anomalies, while preserving the exact original and converted amounts in the database and blockchain ledger.

---

## 🧪 Automated Testing

Run the automated test suites:

### 1. Currency Conversion Unit & Mocked Tests (12 Tests)
```bash
python -m unittest tests/test_currency_conversion.py
```
*Validates successful conversion, decimal precision, JPY rounding, same-currency parity, invalid/zero/negative amounts, unsupported codes, API timeouts/failures, snapshot immutability, KYC enforcement, and ML risk decision handling.*

### 2. End-to-End System Integration Flow (12 Verification Checks)
```bash
python tests/test_flow.py
```
*Validates the full pipeline: Home $\rightarrow$ SME Login $\rightarrow$ KYC Verification $\rightarrow$ Payment Request $\rightarrow$ Currency APIs $\rightarrow$ 3 Risk Scenarios $\rightarrow$ Blockchain Audit $\rightarrow$ Dashboard Analytics $\rightarrow$ Transaction History.*

---

## ⚠️ Academic Prototype Scope & Limitations

As required for academic rigor:
1. **KYC Verification:** The KYC module uses a realistic simulated verification engine and does not connect to live governmental tax/registry APIs.
2. **Machine Learning Model:** Trained on calibrated synthetic SME transaction distributions for algorithmic feasibility demonstration; real-world production deployment would incorporate live banking telemetry.
3. **Blockchain & Smart Contract:** Operates on an authentic local cryptographic SHA-256 ledger with Solidity specifications (`smart_contract.sol`) rather than mainnet Ethereum to guarantee fast, gas-free execution on a student laptop.
4. **Financial Settlement:** This is an academic research prototype and does not execute real fiat monetary wire transfers or live bank clearing.

