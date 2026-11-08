/**
 * Simple deployment script using ethers.js
 * Requires: npm install ethers
 * 
 * Usage:
 *   node scripts/deploy-simple.js
 * 
 * Note: This requires the contract to be compiled first.
 * Use Hardhat for automatic compilation, or compile manually with solc.
 */

const { ethers } = require('ethers');

// Configuration
const NETWORK_URL = process.env.NETWORK_URL || 'http://127.0.0.1:7545';
const PRIVATE_KEY = process.env.PRIVATE_KEY || '8714d8d07b6624f30c7568a8780692422a0d69f7e9026a75c5764ee89abc393c';

// Contract bytecode and ABI (you need to compile first)
// To compile: npx solc --bin --abi contracts/EventChain.sol -o build/
const BYTECODE = process.env.CONTRACT_BYTECODE || ''; // Paste compiled bytecode here
const ABI = process.env.CONTRACT_ABI ? JSON.parse(process.env.CONTRACT_ABI) : []; // Paste ABI here

async function deploy() {
  if (!BYTECODE || BYTECODE === '') {
    console.error('❌ Error: Contract bytecode not provided');
    console.log('\n💡 To get bytecode:');
    console.log('   1. Use Hardhat: npx hardhat compile');
    console.log('   2. Or use solc: npx solc --bin contracts/EventChain.sol');
    console.log('   3. Then paste the bytecode here or set CONTRACT_BYTECODE env var\n');
    process.exit(1);
  }

  if (PRIVATE_KEY === 'YOUR_PRIVATE_KEY_HERE') {
    console.error('❌ Error: Private key not configured');
    console.log('\n💡 Set PRIVATE_KEY environment variable or edit this script\n');
    process.exit(1);
  }

  try {
    console.log('🚀 Deploying EventChain contract...\n');

    // Connect to network
    const provider = new ethers.JsonRpcProvider(NETWORK_URL);
    const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

    console.log('📡 Network:', NETWORK_URL);
    console.log('👤 Deployer:', wallet.address);

    // Check balance
    const balance = await provider.getBalance(wallet.address);
    const balanceEth = ethers.formatEther(balance);
    console.log('💰 Balance:', balanceEth, 'ETH\n');

    if (balance === 0n) {
      console.warn('⚠️  Warning: Account balance is zero!\n');
    }

    // Deploy contract
    console.log('📤 Deploying contract...');
    const factory = new ethers.ContractFactory(ABI, BYTECODE, wallet);
    const contract = await factory.deploy();
    
    console.log('⏳ Waiting for deployment...');
    await contract.waitForDeployment();

    const address = await contract.getAddress();
    
    console.log('\n✅ Contract deployed successfully!');
    console.log('📍 Contract address:', address);
    console.log('\n📝 Update your application.properties:');
    console.log(`   blockchain.contract.address=${address}`);
    console.log(`   blockchain.private.key=${PRIVATE_KEY.substring(0, 10)}...`);

  } catch (error) {
    console.error('\n❌ Deployment failed:', error.message);
    
    if (error.code === 'INVALID_ARGUMENT') {
      console.error('   → Check your private key format');
    } else if (error.code === 'NETWORK_ERROR' || error.message.includes('ECONNREFUSED')) {
      console.error('   → Check network URL and ensure Ganache is running');
    } else if (error.message.includes('insufficient funds')) {
      console.error('   → Account needs ETH for gas fees');
    }
    
    process.exit(1);
  }
}

deploy();
