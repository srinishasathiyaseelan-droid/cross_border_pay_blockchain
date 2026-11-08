const fs = require('fs');
const path = require('path');

async function main() {
    // We get the contract to deploy
    console.log("🚀 Starting SeedChain deployment...");
    const [deployer] = await ethers.getSigners();
    console.log("👤 Deployer account:", deployer.address);

    const SeedChain = await ethers.getContractFactory("SeedChain");
    const seedChain = await SeedChain.deploy();

    console.log("📦 Deploying contract...");
    await seedChain.waitForDeployment();

    const address = await seedChain.getAddress();
    console.log("✅ SeedChain deployed to:", address);

    // Save configuration to backend-node/.env
    const envPath = path.join(__dirname, '../backend-node/.env');

    // Default Hardhat Localhost config
    const rpcUrl = "http://127.0.0.1:8545";
    const privateKey = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"; // Account #0 from Hardhat node

    const envContent = `CONTRACT_ADDRESS=${address}
BLOCKCHAIN_RPC_URL=${rpcUrl}
BLOCKCHAIN_PRIVATE_KEY=${privateKey}
IPFS_API_URL=http://127.0.0.1:5001/api/v0
`;

    fs.writeFileSync(envPath, envContent);
    console.log(`📄 Verified config saved to: ${envPath}`);
}

main()
    .then(async () => {
        console.log("Deployment finished successfully. Waiting for pending operations...");
        // Add a generous delay to allow IO handles (Windows console/files) to settle
        await new Promise(resolve => setTimeout(resolve, 2000));
        console.log("Exiting deployment script naturally.");
        // process.exit(0) removed to avoid Windows UV_HANDLE_CLOSING assertion race condition
    })
    .catch((error) => {
        console.error("❌ Deployment failed:", error);
        process.exitCode = 1;
    });
