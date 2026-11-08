/**
 * Deploy EventChain.sol contract using ethers.js
 * 
 * Usage:
 *   node scripts/deploy-eventchain.js
 * 
 * Make sure to:
 *   1. Install dependencies: npm install ethers
 *   2. Set environment variables or edit the config below
 *   3. Have Ganache running or use a testnet
 */

const { ethers } = require('ethers');
const fs = require('fs');
const path = require('path');

// Configuration - Edit these values
const CONFIG = {
  // Ganache local network
  networkUrl: process.env.NETWORK_URL || 'http://127.0.0.1:7545',
  // Private key (without 0x prefix) - Get from Ganache or use a test account
  privateKey: process.env.PRIVATE_KEY || '0x8714d8d07b6624f30c7568a8780692422a0d69f7e9026a75c5764ee89abc393c',
  // Contract file path
  contractPath: path.join(__dirname, '../contracts/EventChain.sol')
};

async function deploy() {
  try {
    console.log('🚀 Starting EventChain deployment...\n');

    // Check if contract file exists
    if (!fs.existsSync(CONFIG.contractPath)) {
      throw new Error(`Contract file not found: ${CONFIG.contractPath}`);
    }

    // Read contract source
    const contractSource = fs.readFileSync(CONFIG.contractPath, 'utf8');
    console.log('✅ Contract file loaded\n');

    // Connect to network
    const provider = new ethers.JsonRpcProvider(CONFIG.networkUrl);
    const wallet = new ethers.Wallet(CONFIG.privateKey, provider);

    console.log('📡 Network:', CONFIG.networkUrl);
    console.log('👤 Deployer address:', wallet.address);

    // Check balance
    const balance = await provider.getBalance(wallet.address);
    console.log('💰 Balance:', ethers.formatEther(balance), 'ETH\n');

    if (balance === 0n) {
      console.warn('⚠️  Warning: Account balance is zero. Transaction may fail!\n');
    }

    // Compile contract (requires solc)
    console.log('📦 Compiling contract...');
    console.log('⚠️  Note: This script requires the contract to be compiled first.');
    console.log('   You can compile using: solc --bin --abi contracts/EventChain.sol\n');
    
    // For now, we'll use a simpler approach - deploy using bytecode if available
    // Or use Hardhat/Truffle for compilation
    
    console.log('💡 Alternative: Use Hardhat for compilation and deployment');
    console.log('   See: scripts/deploy-with-hardhat.js\n');

    // If you have compiled bytecode and ABI, uncomment below:
    /*
    const bytecode = 'YOUR_COMPILED_BYTECODE_HERE';
    const abi = [/* YOUR_ABI_HERE */];
    
    const factory = new ethers.ContractFactory(abi, bytecode, wallet);
    console.log('📤 Deploying contract...');
    
    const contract = await factory.deploy();
    await contract.waitForDeployment();
    
    const address = await contract.getAddress();
    console.log('\n✅ Contract deployed successfully!');
    console.log('📍 Contract address:', address);
    console.log('\n📝 Update your application.properties:');
    console.log(`   blockchain.contract.address=${address}`);
    */

  } catch (error) {
    console.error('\n❌ Deployment failed:', error.message);
    if (error.code === 'INVALID_ARGUMENT') {
      console.error('   Check your private key format (should be 64 hex characters)');
    } else if (error.code === 'NETWORK_ERROR') {
      console.error('   Check your network URL and ensure Ganache is running');
    }
    process.exit(1);
  }
}

// Run deployment
deploy();
