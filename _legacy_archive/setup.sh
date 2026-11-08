#!/bin/bash
set -e

echo "🤖 PDS System Setup Initiated..."

# 1. Start Ganache
echo "Starting Local Blockchain (Ganache)..."
docker-compose up -d ganache
echo "Waiting for Ganache to ready..."
sleep 5

# 2. Deploy Contract
echo "Deploying Smart Contract..."
# We use the docker network configured in hardhat.config.js
# Ensure we catch the output
DEPLOY_OUTPUT=$(npx hardhat run scripts/deploy-ration.js --network docker 2>&1)
echo "$DEPLOY_OUTPUT"

# Parse Address
ADDRESS=$(echo "$DEPLOY_OUTPUT" | grep "deployed to:" | awk '{print $NF}')

if [ -z "$ADDRESS" ]; then
  echo "❌ Error: Could not capture contract address. Deployment failed?"
  exit 1
fi

echo "✅ Contract Deployed at: $ADDRESS"

# Copy Artifacts to Backend for Docker Build
echo "Preparing Backend Assets..."
cp -r artifacts backend-node/

# 3. Configure Backend
echo "Configuring Backend Environment..."
# Create a .env file in the root or pass to docker-compose
# We will create a .env file for docker-compose to read, or pass it inline
echo "CONTRACT_ADDRESS=$ADDRESS" > .env

# 4. Start Full System
echo "Starting Application Stack..."
docker-compose up -d --build

echo "🎉 System Deployed Successfully!"
echo "------------------------------------------------"
echo "👉 Dashboard UI: http://localhost:3000/pds"
echo "👉 Backend API:  http://localhost:4000"
echo "👉 AI Service:   http://localhost:5000"
echo "------------------------------------------------"
