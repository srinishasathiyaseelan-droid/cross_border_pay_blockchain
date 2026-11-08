require("@nomicfoundation/hardhat-toolbox");

/** @type import('hardhat/config').HardhatConfig */
module.exports = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    // Ganache local network
    ganache: {
      url: "http://127.0.0.1:7545",
      chainId: 1337,
      accounts: [
        // Add your private keys here (without 0x prefix)
        // Get from Ganache by clicking the key icon
        // Example: "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        "8714d8d07b6624f30c7568a8780692422a0d69f7e9026a75c5764ee89abc393c"
      ]
    },
    // Hardhat local node
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337
    },
    // Ganache (Docker)
    docker: {
      url: "http://127.0.0.1:8545",
      chainId: 1337,
      accounts: {
        mnemonic: "test test test test test test test test test test test junk"
      }
    },
    // Polygon Mumbai testnet
    mumbai: {
      url: "https://rpc-mumbai.maticvigil.com",
      chainId: 80001,
      accounts: [
        // Add your private key here for testnet deployment
      ]
    }
  },
  paths: {
    sources: "./contracts",
    tests: "./tests",
    cache: "./cache",
    artifacts: "./artifacts"
  }
};
