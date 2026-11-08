const { ethers } = require('ethers');
const fs = require('fs');
const path = require('path');

// Load SeedChain ABI
const ARTIFACT_PATH_DOCKER = path.resolve(__dirname, '../artifacts/contracts/SeedChain.sol/SeedChain.json');
const ARTIFACT_PATH_LOCAL = path.resolve(__dirname, '../../artifacts/contracts/SeedChain.sol/SeedChain.json');

let SeedChainArtifact;

try {
    if (fs.existsSync(ARTIFACT_PATH_DOCKER)) {
        SeedChainArtifact = require(ARTIFACT_PATH_DOCKER);
    } else {
        SeedChainArtifact = require(ARTIFACT_PATH_LOCAL);
    }
} catch (e) {
    console.error("Could not load SeedChain artifact. Ensure contracts are compiled.");
    SeedChainArtifact = { abi: [] };
}

class BlockchainService {
    constructor() {
        this.provider = null;
        this.wallet = null;
        this.contract = null;
        this.connected = false;
    }

    async init() {
        try {
            const rpcUrl = process.env.BLOCKCHAIN_RPC_URL || 'http://127.0.0.1:8545';
            const privateKey = process.env.BLOCKCHAIN_PRIVATE_KEY;
            const contractAddress = process.env.CONTRACT_ADDRESS;

            if (!privateKey || !contractAddress) {
                console.warn("Blockchain config missing. Features will fail.");
                return;
            }

            this.provider = new ethers.JsonRpcProvider(rpcUrl);
            this.wallet = new ethers.Wallet(privateKey, this.provider);
            this.contract = new ethers.Contract(contractAddress, SeedChainArtifact.abi, this.wallet);

            this.connected = true;
            console.log(`Blockchain Connected (SeedChain): ${contractAddress}`);
        } catch (error) {
            console.error("Blockchain Connection Failed:", error.message);
        }
    }

    // ======================== BATCH ========================

    async createBatch(cropType, seedVariety, quantity, expiryDate, ipfsHash) {
        if (!this.connected) throw new Error("Blockchain not connected");
        try {
            const tx = await this.contract.createBatch(cropType, seedVariety, quantity, expiryDate, ipfsHash);
            const receipt = await tx.wait();

            // Extract batchId from BatchCreated event
            let batchId = null;
            for (const log of receipt.logs) {
                try {
                    const parsed = this.contract.interface.parseLog(log);
                    if (parsed && parsed.name === 'BatchCreated') {
                        batchId = Number(parsed.args[0]);
                        break;
                    }
                } catch (e) { /* skip non-matching logs */ }
            }

            return { success: true, txHash: tx.hash, block: receipt.blockNumber, batchId };
        } catch (error) {
            console.error("createBatch Error:", error.reason || error.message);
            throw error;
        }
    }

    async getBatch(batchId) {
        if (!this.connected) throw new Error("Blockchain not connected");
        try {
            const batch = await this.contract.getBatch(batchId);
            return {
                batchId: Number(batch.batchId),
                cropType: batch.cropType,
                seedVariety: batch.seedVariety,
                quantity: Number(batch.quantity),
                expiryDate: Number(batch.expiryDate),
                ipfsHash: batch.ipfsHash,
                certIPFSHash: batch.certIPFSHash,
                ownerAddress: batch.ownerAddress,
                parentBatchId: Number(batch.parentBatchId),
                status: Number(batch.status), // 0=ACTIVE, 1=EXPIRED, 2=TRANSFERRED
                createdAt: Number(batch.createdAt)
            };
        } catch (error) {
            console.error("getBatch Error:", error.reason || error.message);
            throw error;
        }
    }

    async getBatchCount() {
        if (!this.connected) return 0;
        try {
            return Number(await this.contract.getBatchCount());
        } catch (error) {
            console.error("getBatchCount Error:", error.message);
            return 0;
        }
    }

    // ======================== TRANSFER ========================

    async transferBatch(batchId, newOwner) {
        if (!this.connected) throw new Error("Blockchain not connected");
        try {
            const tx = await this.contract.transferBatch(batchId, newOwner);
            const receipt = await tx.wait();
            return { success: true, txHash: tx.hash, block: receipt.blockNumber };
        } catch (error) {
            console.error("transferBatch Error:", error.reason || error.message);
            throw error;
        }
    }

    // ======================== SPLIT ========================

    async splitBatch(batchId, splitQuantity, newIpfsHash) {
        if (!this.connected) throw new Error("Blockchain not connected");
        try {
            const tx = await this.contract.splitBatch(batchId, splitQuantity, newIpfsHash);
            const receipt = await tx.wait();

            let childBatchId = null;
            for (const log of receipt.logs) {
                try {
                    const parsed = this.contract.interface.parseLog(log);
                    if (parsed && parsed.name === 'BatchSplit') {
                        childBatchId = Number(parsed.args[1]);
                        break;
                    }
                } catch (e) { /* skip */ }
            }

            return { success: true, txHash: tx.hash, block: receipt.blockNumber, childBatchId };
        } catch (error) {
            console.error("splitBatch Error:", error.reason || error.message);
            throw error;
        }
    }

    async getChildBatches(batchId) {
        if (!this.connected) return [];
        try {
            const children = await this.contract.getChildBatches(batchId);
            return children.map(c => Number(c));
        } catch (error) {
            console.error("getChildBatches Error:", error.message);
            return [];
        }
    }

    // ======================== CERTIFICATE ========================

    async registerCertificate(batchId, ipfsHash, digitalSignature, expiryDate) {
        if (!this.connected) throw new Error("Blockchain not connected");
        try {
            const sigBytes = ethers.getBytes(digitalSignature);
            const tx = await this.contract.registerCertificate(batchId, ipfsHash, sigBytes, expiryDate);
            const receipt = await tx.wait();

            let certId = null;
            for (const log of receipt.logs) {
                try {
                    const parsed = this.contract.interface.parseLog(log);
                    if (parsed && parsed.name === 'CertificateRegistered') {
                        certId = Number(parsed.args[0]);
                        break;
                    }
                } catch (e) { /* skip */ }
            }

            return { success: true, txHash: tx.hash, block: receipt.blockNumber, certId };
        } catch (error) {
            console.error("registerCertificate Error:", error.reason || error.message);
            throw error;
        }
    }

    async getCertificate(certId) {
        if (!this.connected) throw new Error("Blockchain not connected");
        try {
            const cert = await this.contract.getCertificate(certId);
            return {
                certId: Number(cert.certId),
                batchId: Number(cert.batchId),
                issuerAddress: cert.issuerAddress,
                ipfsHash: cert.ipfsHash,
                digitalSignature: ethers.hexlify(cert.digitalSignature),
                issuedAt: Number(cert.issuedAt),
                expiryDate: Number(cert.expiryDate),
                isValid: cert.isValid
            };
        } catch (error) {
            console.error("getCertificate Error:", error.reason || error.message);
            throw error;
        }
    }

    async getCertificateByBatch(batchId) {
        if (!this.connected) throw new Error("Blockchain not connected");
        try {
            const cert = await this.contract.getCertificateByBatch(batchId);
            return {
                certId: Number(cert.certId),
                batchId: Number(cert.batchId),
                issuerAddress: cert.issuerAddress,
                ipfsHash: cert.ipfsHash,
                digitalSignature: ethers.hexlify(cert.digitalSignature),
                issuedAt: Number(cert.issuedAt),
                expiryDate: Number(cert.expiryDate),
                isValid: cert.isValid
            };
        } catch (error) {
            console.error("getCertificateByBatch Error:", error.reason || error.message);
            throw error;
        }
    }

    async verifyCertificate(certId) {
        if (!this.connected) throw new Error("Blockchain not connected");
        try {
            const result = await this.contract.verifyCertificate(certId);
            return {
                isValid: result[0],
                isExpired: result[1],
                issuer: result[2],
                batchId: Number(result[3]),
                ipfsHash: result[4],
                signature: ethers.hexlify(result[5])
            };
        } catch (error) {
            console.error("verifyCertificate Error:", error.reason || error.message);
            throw error;
        }
    }

    async getCertificateCount() {
        if (!this.connected) return 0;
        try {
            return Number(await this.contract.getCertificateCount());
        } catch (error) {
            console.error("getCertificateCount Error:", error.message);
            return 0;
        }
    }

    // ======================== EVENTS (BLOCKCHAIN LOGS) ========================

    async getBlockchainEvents() {
        if (!this.connected) return [];
        try {
            const events = [];

            // Get BatchCreated events
            const batchFilter = this.contract.filters.BatchCreated();
            const batchEvents = await this.contract.queryFilter(batchFilter, 0, "latest");
            for (const e of batchEvents) {
                try {
                    const parsed = this.contract.interface.parseLog(e);
                    events.push({
                        type: 'BatchCreated',
                        batchId: Number(parsed.args[0]),
                        owner: parsed.args[1],
                        cropType: parsed.args[2],
                        seedVariety: parsed.args[3],
                        quantity: Number(parsed.args[4]),
                        expiryDate: Number(parsed.args[5]),
                        ipfsHash: parsed.args[6],
                        timestamp: Number(parsed.args[7]),
                        txHash: e.transactionHash,
                        blockNumber: e.blockNumber
                    });
                } catch (err) { /* skip */ }
            }

            // Get CertificateRegistered events
            const certFilter = this.contract.filters.CertificateRegistered();
            const certEvents = await this.contract.queryFilter(certFilter, 0, "latest");
            for (const e of certEvents) {
                try {
                    const parsed = this.contract.interface.parseLog(e);
                    events.push({
                        type: 'CertificateRegistered',
                        certId: Number(parsed.args[0]),
                        batchId: Number(parsed.args[1]),
                        issuer: parsed.args[2],
                        ipfsHash: parsed.args[3],
                        expiryDate: Number(parsed.args[4]),
                        timestamp: Number(parsed.args[5]),
                        txHash: e.transactionHash,
                        blockNumber: e.blockNumber
                    });
                } catch (err) { /* skip */ }
            }

            // Get BatchTransferred events
            const txFilter = this.contract.filters.BatchTransferred();
            const txEvents = await this.contract.queryFilter(txFilter, 0, "latest");
            for (const e of txEvents) {
                try {
                    const parsed = this.contract.interface.parseLog(e);
                    events.push({
                        type: 'BatchTransferred',
                        batchId: Number(parsed.args[0]),
                        fromOwner: parsed.args[1],
                        toOwner: parsed.args[2],
                        timestamp: Number(parsed.args[3]),
                        txHash: e.transactionHash,
                        blockNumber: e.blockNumber
                    });
                } catch (err) { /* skip */ }
            }

            // Get BatchSplit events
            const splitFilter = this.contract.filters.BatchSplit();
            const splitEvents = await this.contract.queryFilter(splitFilter, 0, "latest");
            for (const e of splitEvents) {
                try {
                    const parsed = this.contract.interface.parseLog(e);
                    events.push({
                        type: 'BatchSplit',
                        parentBatchId: Number(parsed.args[0]),
                        childBatchId: Number(parsed.args[1]),
                        childQuantity: Number(parsed.args[2]),
                        owner: parsed.args[3],
                        timestamp: Number(parsed.args[4]),
                        txHash: e.transactionHash,
                        blockNumber: e.blockNumber
                    });
                } catch (err) { /* skip */ }
            }

            // Sort by timestamp descending
            events.sort((a, b) => b.timestamp - a.timestamp);
            return events;
        } catch (error) {
            console.error("Error fetching events:", error);
            return [];
        }
    }

    // ======================== UTILITY ========================

    signMessage(message) {
        return this.wallet.signMessage(message);
    }
}

module.exports = new BlockchainService();
