# EventChain Deployment Guide

## Smart Contract Deployment

### Option 1: Using Remix IDE (Recommended for beginners)

1. Go to https://remix.ethereum.org
2. Create a new file `EventChain.sol` in the contracts folder
3. Copy the contract code from `contracts/EventChain.sol`
4. Select Solidity compiler version 0.8.19
5. Compile the contract
6. Navigate to "Deploy & Run Transactions"
7. Select your network (Polygon, Mumbai testnet, etc.)
8. Connect your wallet (MetaMask recommended)
9. Click "Deploy"
10. Copy the deployed contract address

### Option 2: Using Hardhat

```bash
# Install Hardhat
npm install --save-dev hardhat

# Initialize project
npx hardhat

# Create deployment script
# Deploy contract
npx hardhat run scripts/deploy.js --network polygon
```

### Option 3: Using Truffle

```bash
# Install Truffle
npm install -g truffle

# Initialize project
truffle init

# Configure networks in truffle-config.js
# Deploy
truffle migrate --network polygon
```

## Backend Deployment

### Local Development

1. **Start IPFS Node**:
   ```bash
   ipfs daemon
   ```

2. **Configure application.properties**:
   ```properties
   blockchain.network.url=https://polygon-rpc.com
   blockchain.contract.address=YOUR_DEPLOYED_CONTRACT_ADDRESS
   blockchain.private.key=YOUR_PRIVATE_KEY
   ```

3. **Run Application**:
   ```bash
   mvn spring-boot:run
   ```

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM openjdk:17-jdk-slim

WORKDIR /app

COPY target/eventchain-1.0.0.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
```

Build and run:
```bash
mvn clean package
docker build -t eventchain .
docker run -p 8080:8080 \
  -e BLOCKCHAIN_CONTRACT_ADDRESS=YOUR_ADDRESS \
  -e BLOCKCHAIN_PRIVATE_KEY=YOUR_KEY \
  eventchain
```

### Cloud Deployment (AWS/GCP/Azure)

1. Build JAR:
   ```bash
   mvn clean package
   ```

2. Use environment variables for configuration:
   ```bash
   export BLOCKCHAIN_NETWORK_URL=https://polygon-rpc.com
   export BLOCKCHAIN_CONTRACT_ADDRESS=0x...
   export BLOCKCHAIN_PRIVATE_KEY=0x...
   export IPFS_HOST=your-ipfs-host
   export IPFS_PORT=5001
   ```

3. Deploy to cloud service (Elastic Beanstalk, Cloud Run, App Service)

## Environment Variables

Instead of hardcoding in `application.properties`, use environment variables:

```properties
blockchain.network.url=${BLOCKCHAIN_NETWORK_URL:https://polygon-rpc.com}
blockchain.contract.address=${BLOCKCHAIN_CONTRACT_ADDRESS:}
blockchain.private.key=${BLOCKCHAIN_PRIVATE_KEY:}
ipfs.host=${IPFS_HOST:127.0.0.1}
ipfs.port=${IPFS_PORT:5001}
ipfs.protocol=${IPFS_PROTOCOL:http}
```

## Security Best Practices

1. **Never commit private keys** to version control
2. **Use environment variables** or secret management services (AWS Secrets Manager, HashiCorp Vault)
3. **Use a dedicated wallet** with limited funds for the application
4. **Enable HTTPS** in production
5. **Implement rate limiting** for API endpoints
6. **Add authentication/authorization** for production use

## Network Configuration

### Polygon Mainnet
- RPC: https://polygon-rpc.com
- Chain ID: 137
- Gas costs: Very low

### Polygon Mumbai Testnet
- RPC: https://rpc-mumbai.maticvigil.com
- Chain ID: 80001
- Faucet: https://faucet.polygon.technology/

### Ethereum Mainnet
- RPC: Use Infura/Alchemy
- Chain ID: 1
- Gas costs: High

### Ethereum Goerli Testnet
- RPC: Use Infura/Alchemy
- Chain ID: 5
- Faucet: https://goerlifaucet.com/

## IPFS Setup

### Local IPFS Node
```bash
# Install IPFS
# macOS: brew install ipfs
# Linux: Download from https://dist.ipfs.tech/#go-ipfs

# Initialize
ipfs init

# Start daemon
ipfs daemon
```

### IPFS Pinata (Managed IPFS)
1. Sign up at https://pinata.cloud
2. Get API key
3. Use Pinata API endpoint instead of local node

### IPFS Infura
1. Sign up at https://infura.io
2. Create IPFS project
3. Use Infura IPFS gateway

