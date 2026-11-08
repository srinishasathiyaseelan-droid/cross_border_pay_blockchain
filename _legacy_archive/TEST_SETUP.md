# Test/Educational Setup Guide

This guide helps you set up EventChain for testing and education without using real cryptocurrency.

## 🎓 Local Test Environment Setup

### Option 1: Using Ganache (Recommended - Easiest)

Ganache provides a local Ethereum blockchain with test accounts and fake ETH.

#### Step 1: Install Ganache

1. Download Ganache from: https://trufflesuite.com/ganache/
2. Install and launch Ganache
3. Click "Quickstart" to create a new workspace
4. Ganache will start on `http://127.0.0.1:7545` (default)

#### Step 2: Get Test Account Details

1. In Ganache, you'll see 10 test accounts with 100 ETH each
2. Copy one of the **Private Keys** (click the key icon to reveal)
3. Copy the **RPC Server** URL (usually `http://127.0.0.1:7545`)

#### Step 3: Deploy Smart Contract

**Using Remix IDE (Easiest):**

1. Go to https://remix.ethereum.org
2. Create a new file `EventChain.sol` in the `contracts` folder
3. Copy the content from `contracts/EventChain.sol`
4. Compile the contract (Solidity version 0.8.19)
5. Go to "Deploy & Run Transactions"
6. Select "Injected Web3" or "Web3 Provider"
7. Enter Ganache RPC URL: `http://127.0.0.1:7545`
8. Connect MetaMask to Ganache:
   - Open MetaMask
   - Go to Settings → Networks → Add Network
   - Network Name: Ganache Local
   - RPC URL: http://127.0.0.1:7545
   - Chain ID: 1337
   - Currency Symbol: ETH
9. Import a Ganache account into MetaMask using the private key
10. Deploy the contract from Remix
11. Copy the deployed contract address

#### Step 4: Configure Application

Update `src/main/resources/application.properties`:

```properties
# Server Configuration
server.port=8080

# Blockchain Configuration - Local Ganache
blockchain.network.url=http://127.0.0.1:7545
blockchain.contract.address=YOUR_DEPLOYED_CONTRACT_ADDRESS_FROM_STEP_3
blockchain.private.key=YOUR_GANACHE_PRIVATE_KEY_FROM_STEP_2

# IPFS Configuration
ipfs.host=127.0.0.1
ipfs.port=5001
ipfs.protocol=http

# Application Configuration
app.name=EventChain
app.version=1.0.0
```

### Option 2: Using Hardhat Local Node

#### Step 1: Install Hardhat

```bash
npm install --save-dev hardhat
npx hardhat init
```

#### Step 2: Start Local Node

```bash
npx hardhat node
```

This starts a local node on `http://127.0.0.1:8545` with test accounts.

#### Step 3: Deploy Contract

Create `scripts/deploy.js`:

```javascript
async function main() {
  const EventChain = await ethers.getContractFactory("EventChain");
  const eventChain = await EventChain.deploy();
  await eventChain.deployed();
  console.log("EventChain deployed to:", eventChain.address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
```

Deploy:
```bash
npx hardhat run scripts/deploy.js --network localhost
```

#### Step 4: Configure Application

Update `application.properties`:

```properties
blockchain.network.url=http://127.0.0.1:8545
blockchain.contract.address=YOUR_DEPLOYED_CONTRACT_ADDRESS
blockchain.private.key=YOUR_HARDHAT_TEST_ACCOUNT_PRIVATE_KEY
```

### Option 3: Using Polygon Mumbai Testnet (Free Test Tokens)

If you want to test on a real testnet (no real money):

1. Get test tokens from: https://faucet.polygon.technology/
2. Deploy contract to Mumbai testnet
3. Use Mumbai RPC: `https://rpc-mumbai.maticvigil.com`
4. Configure with Mumbai contract address

## 🚀 Quick Start Script

I'll create a helper script to set up Ganache automatically (optional).

## 📝 Test Account Setup

### Ganache Test Accounts

Ganache provides 10 accounts with:
- **100 ETH each** (fake/test ETH)
- **Private keys** (click key icon to reveal)
- **No real value** - completely safe for testing

### Using Test Accounts

1. **Backend**: Use one private key in `application.properties`
2. **Frontend**: Import another account into MetaMask for testing
3. All transactions use fake ETH - no real money involved!

## ✅ Verification

After setup, verify everything works:

1. Start backend: `mvn spring-boot:run`
2. Start frontend: `cd frontend && npm start`
3. Connect MetaMask to Ganache network
4. Try creating an event - it should work with fake ETH!

## 🔧 Troubleshooting

### Contract Deployment Issues
- Ensure Ganache is running
- Check RPC URL matches Ganache
- Verify contract compiled successfully

### Connection Issues
- Check Ganache is running on correct port
- Verify RPC URL in application.properties
- Ensure private key is correct (no 0x prefix needed)

### MetaMask Connection
- Add Ganache as custom network
- Import account using private key
- Ensure you're on the Ganache network when using frontend

## 🎯 Benefits of Local Testing

- ✅ No real cryptocurrency needed
- ✅ Instant transactions (no waiting for confirmations)
- ✅ Free test ETH
- ✅ Safe for experimentation
- ✅ Perfect for education and development
