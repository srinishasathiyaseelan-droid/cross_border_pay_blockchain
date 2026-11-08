/**
 * Deploy EventChain.sol using Hardhat
 * 
 * Prerequisites:
 *   1. npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox
 *   2. npx hardhat init (if not already initialized)
 * 
 * Usage:
 *   npx hardhat run scripts/deploy-with-hardhat.js --network localhost
 *   npx hardhat run scripts/deploy-with-hardhat.js --network ganache
 */

async function main() {
  const [deployer] = await ethers.getSigners();

  console.log("🚀 Deploying EventChain contract...");
  console.log("👤 Deployer address:", deployer.address);

  const balance = await ethers.provider.getBalance(deployer.address);
  console.log("💰 Account balance:", ethers.formatEther(balance), "ETH\n");

  // Get the ContractFactory and Signers here.
  const EventChain = await ethers.getContractFactory("EventChain");

  console.log("📦 Deploying contract...");
  const eventChain = await EventChain.deploy();

  await eventChain.waitForDeployment();

  const address = await eventChain.getAddress();
  console.log("\n✅ EventChain deployed to:", address);
  console.log("\n📝 Update your application.properties:");
  console.log(`   blockchain.contract.address=${address}`);
  console.log(`   blockchain.private.key=0x8714d8d07b6624f30c7568a8780692422a0d69f7e9026a75c5764ee89abc393c`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
