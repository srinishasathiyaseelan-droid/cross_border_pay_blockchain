/**
 * Deploy RationDistribution.sol using Hardhat
 */

async function main() {
    const [deployer] = await ethers.getSigners();

    console.log("🚀 Deploying RationDistribution contract...");
    console.log("👤 Deployer address:", deployer.address);

    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("💰 Account balance:", ethers.formatEther(balance), "ETH\n");

    const RationDistribution = await ethers.getContractFactory("RationDistribution");

    console.log("📦 Deploying contract...");
    const ration = await RationDistribution.deploy();

    await ration.waitForDeployment();

    const address = await ration.getAddress();
    console.log("\n✅ RationDistribution deployed to:", address);

    // Save to Backend .env
    const fs = require('fs');
    const path = require('path');

    const backendEnvPath = path.join(__dirname, '../backend-node/.env');
    const envContent = `CONTRACT_ADDRESS=${address}\nBLOCKCHAIN_RPC_URL=http://127.0.0.1:8545\nBLOCKCHAIN_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80`; // Hardhat Account #0 Private Key
    fs.writeFileSync(backendEnvPath, envContent);
    console.log("📄 Saved config to backend-node/.env");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
