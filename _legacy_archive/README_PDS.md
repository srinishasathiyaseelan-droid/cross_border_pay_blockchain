# AI-Enabled Intelligent PDS Monitoring Platform

A fully functional, offline-capable, API-free system for detecting fraud in ration distribution using Blockchain and AI.

## 🚀 Features
- **Blockchain Layer**: Immutable transaction records using Solidity & Local Ganache.
- **AI Fraud Detection**: Isolation Forest model (Python/Scikit-learn) detecting anomalies in quantity, frequency, and time gaps.
- **Backend API**: Node.js/Express service bridging AI, Blockchain, and UI.
- **Dashboard UI**: React-based real-time monitoring of transactions and fraud alerts.
- **Offline & Private**: No external API keys or internet required.

## 📋 Prerequisites
- **Docker & Docker Compose** (Must be installed and running)
- **Node.js** (v16+) & **NPM** (For local contract deployment script)
- **Git Bash** (Recommended for Windows)

## 🛠️ One-Command Startup (Recommended)

1. Open your terminal (Git Bash or Terminal).
2. Run the setup script:
   ```bash
   sh setup.sh
   ```
   This script will:
   - Start the local blockchain.
   - Deploy the smart contract.
   - Configure the environment.
   - build and start all services.

3. Access the Dashboard:
   - **URL**: [http://localhost:3000/pds](http://localhost:3000/pds)

## 🧪 Testing System
1. Go to the dashboard.
2. Use the **Simulate Distribution Point** form.
3. **Normal Case**:
   - Quantity: 10
   - Region Risk: 0
   - Result: Success (Green)
4. **Fraud Case**:
   - Quantity: 50
   - Region Risk: 2
   - Result: Fraud Alert (Red), High Risk.

## 📂 Architecture
- **contracts/**: Solidity Smart Contracts (`RationDistribution.sol`).
- **ai-service/**: Python FastAPI application with ML Logic.
- **backend-node/**: Node.js Express API.
- **frontend/**: React Dashboard.

## 🔧 Manual Setup
If `setup.sh` fails:
1. `docker-compose up -d ganache`
2. `npx hardhat run scripts/deploy-ration.js --network localhost`
3. Copy the address.
4. Set `CONTRACT_ADDRESS` in `docker-compose.yml` or `.env`.
5. `docker-compose up --build`
