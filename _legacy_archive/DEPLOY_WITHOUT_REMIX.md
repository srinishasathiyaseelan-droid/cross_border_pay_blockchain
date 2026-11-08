# Deploy EventChain Contract Without Remix IDE

This guide shows you how to deploy the `EventChain.sol` contract using command-line tools instead of Remix IDE.

## 🎯 Quick Options

### Option 1: Using Hardhat (Recommended) ⭐

**Best for:** Full control, easy to automate, great for development

#### Step 1: Install Hardhat

```bash
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox
```

#### Step 2: Initialize Hardhat (if not already done)

```bash
npx hardhat init
# Select: "Create a JavaScript project"
```

#### Step 3: Configure Hardhat

Edit `hardhat.config.js` (already created in this project):

```javascript
module.exports = {
  solidity: "0.8.19",
  networks: {
    ganache: {
      url: "http://127.0.0.1:7545",
      chainId: 1337,
      accounts: ["YOUR_PRIVATE_KEY_HERE"] // Get from Ganache
    }
  }
};
```

#### Step 4: Deploy Contract

```bash
# Make sure Ganache is running first!
npx hardhat run scripts/deploy-with-hardhat.js --network ganache
```

**Output:**
```
✅ EventChain deployed to: 0x1234567890abcdef...
```

#### Step 5: Update application.properties

```properties
blockchain.contract.address=0x1234567890abcdef...
blockchain.private.key=YOUR_PRIVATE_KEY_HERE
```

---

### Option 2: Using solc (Solidity Compiler) + ethers.js

**Best for:** Simple deployments, minimal setup

#### Step 1: Install Dependencies

```bash
npm install ethers solc
```

#### Step 2: Compile Contract

```bash
# Install solc globally or use npx
npx solc --bin --abi contracts/EventChain.sol -o build/
```

This creates:
- `build/EventChain.bin` (bytecode)
- `build/EventChain.abi` (ABI)

#### Step 3: Deploy Using Node.js Script

Create `deploy-simple.js`:

```javascript
const { ethers } = require('ethers');
const fs = require('fs');

const bytecode = fs.readFileSync('build/EventChain.bin', 'utf8');
const abi = JSON.parse(fs.readFileSync('build/EventChain.abi', 'utf8'));

const provider = new ethers.JsonRpcProvider('http://127.0.0.1:7545');
const wallet = new ethers.Wallet('YOUR_PRIVATE_KEY', provider);

async function deploy() {
  const factory = new ethers.ContractFactory(abi, bytecode, wallet);
  const contract = await factory.deploy();
  await contract.waitForDeployment();
  console.log('Deployed to:', await contract.getAddress());
}

deploy();
```

Run:
```bash
node deploy-simple.js
```

---

### Option 3: Using Truffle

**Best for:** If you're already familiar with Truffle

#### Step 1: Install Truffle

```bash
npm install -g truffle
```

#### Step 2: Initialize Truffle

```bash
truffle init
```

#### Step 3: Configure truffle-config.js

```javascript
module.exports = {
  networks: {
    ganache: {
      host: "127.0.0.1",
      port: 7545,
      network_id: "*"
    }
  },
  compilers: {
    solc: {
      version: "0.8.19"
    }
  }
};
```

#### Step 4: Create Migration

Create `migrations/2_deploy_eventchain.js`:

```javascript
const EventChain = artifacts.require("EventChain");

module.exports = function (deployer) {
  deployer.deploy(EventChain);
};
```

#### Step 5: Deploy

```bash
truffle migrate --network ganache
```

---

### Option 4: Using Foundry (forge)

**Best for:** Fast compilation and deployment

#### Step 1: Install Foundry

```bash
# On Windows (PowerShell)
irm https://github.com/foundry-rs/foundry/releases/latest/download/foundry_nightly_x86_64-pc-windows-msvc.tar.gz | tar -xz
```

Or follow: https://book.getfoundry.sh/getting-started/installation

#### Step 2: Initialize Foundry

```bash
forge init --force
```

#### Step 3: Copy Contract

```bash
cp contracts/EventChain.sol src/EventChain.sol
```

#### Step 4: Deploy

```bash
forge create src/EventChain.sol:EventChain \
  --rpc-url http://127.0.0.1:7545 \
  --private-key YOUR_PRIVATE_KEY
```

---

## 🚀 Quick Start with Hardhat (Recommended)

### Option A: Using Batch File (Windows - Easiest!) ⭐

**For Windows users, use the automated batch file:**

1. **Make sure Ganache is running**
2. **Double-click `deploy-contract.bat`** (or `deploy-contract-auto.bat` for auto-update)

That's it! The script will:
- Check prerequisites
- Install dependencies if needed
- Compile the contract
- Deploy to Ganache
- Show you the contract address

**Two versions available:**
- `deploy-contract.bat` - Basic deployment (manual property update)
- `deploy-contract-auto.bat` - Advanced (automatically updates `application.properties`)

### Option B: Using Command Line

```bash
# 1. Install dependencies
npm install

# 2. Make sure Ganache is running

# 3. Edit hardhat.config.js and add your private key to the accounts array

# 4. Deploy
npm run deploy:hardhat
# Or: npx hardhat run scripts/deploy-with-hardhat.js --network ganache
```

That's it! You'll get the contract address to use in `application.properties`.

**Alternative using npm scripts:**
```bash
npm run deploy:hardhat        # Deploy to Ganache
npm run deploy:hardhat:localhost  # Deploy to Hardhat local node
npm run compile               # Compile contracts
npm run node                  # Start Hardhat local node
```

---

## 📋 Prerequisites

Before deploying, make sure you have:

1. **Ganache running** (for local testing)
   - Download: https://trufflesuite.com/ganache/
   - Click "Quickstart"
   - Running on `http://127.0.0.1:7545`

2. **Node.js installed**
   ```bash
   node --version  # Should be 16+
   ```

3. **Private key from Ganache**
   - Click the key icon 🔑 next to any account
   - Copy the private key (without 0x)

---

## 🔧 Troubleshooting

**"Cannot find module 'hardhat'"**
```bash
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox
```

**"Network connection error"**
- Make sure Ganache is running
- Check the RPC URL in `hardhat.config.js`

**"Insufficient funds"**
- Make sure your Ganache account has ETH
- Ganache accounts start with 100 ETH each

**"Contract compilation error"**
- Check Solidity version is 0.8.19
- Verify contract syntax is correct

---

## 📚 Additional Resources

- **Hardhat Docs**: https://hardhat.org/docs
- **ethers.js Docs**: https://docs.ethers.org/
- **Solidity Docs**: https://docs.soliditylang.org/

---

## ✅ After Deployment

Once deployed, update `src/main/resources/application.properties`:

```properties
blockchain.network.url=http://127.0.0.1:7545
blockchain.contract.address=YOUR_DEPLOYED_ADDRESS
blockchain.private.key=YOUR_PRIVATE_KEY
```

Then restart your Spring Boot application!
