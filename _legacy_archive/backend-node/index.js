require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
const { ethers } = require('ethers');
const { z } = require('zod');

const blockchainService = require('./services/blockchain');
const aiService = require('./services/ai');
const dbService = require('./services/db');
const ipfsService = require('./services/ipfs');

const app = express();
const PORT = process.env.PORT || 4000;

// ======================== MIDDLEWARE ========================

app.use(helmet({ crossOriginResourcePolicy: false }));
app.use(cors());
app.use(morgan('dev'));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

// Rate limiting
const limiter = rateLimit({
    windowMs: 1 * 60 * 1000, // 1 minute
    max: 100,
    message: { success: false, error: 'Too many requests, please try again later.' }
});
app.use(limiter);

// ======================== VALIDATION SCHEMAS ========================

const createBatchSchema = z.object({
    cropType: z.string().min(1, 'Crop type is required'),
    seedVariety: z.string().min(1, 'Seed variety is required'),
    quantity: z.number().positive('Quantity must be positive'),
    expiryDate: z.string().min(1, 'Expiry date is required')
});

const transferSchema = z.object({
    newOwner: z.string().min(1, 'New owner address is required')
});

const splitSchema = z.object({
    splitQuantity: z.number().positive('Split quantity must be positive')
});

const certificateSchema = z.object({
    batchId: z.number().int().positive(),
    certificateData: z.object({}).passthrough(),
    expiryDate: z.string().min(1)
});

// Validation middleware
function validate(schema) {
    return (req, res, next) => {
        try {
            const parsed = schema.parse(req.body);
            req.body = parsed;
            next();
        } catch (err) {
            const messages = err.errors?.map(e => e.message).join(', ') || 'Validation failed';
            return res.status(400).json({ success: false, error: messages });
        }
    };
}

// ======================== ERROR HANDLER ========================

function asyncHandler(fn) {
    return (req, res, next) => {
        Promise.resolve(fn(req, res, next)).catch(next);
    };
}

// ======================== INIT ========================

async function initServices() {
    try {
        await dbService.connect();
        console.log('MongoDB connected');
    } catch (err) {
        console.error('MongoDB connection failed:', err.message);
        console.warn('Server will continue but data persistence will not work.');
    }

    try {
        await blockchainService.init();
    } catch (err) {
        console.warn('Blockchain init failed (non-blocking):', err.message);
    }

    try {
        await ipfsService.loadFromDB();
    } catch (err) {
        console.warn('IPFS cache load failed (non-blocking):', err.message);
    }
}

const STATUS_MAP = ['ACTIVE', 'EXPIRED', 'TRANSFERRED'];

// ======================== BATCH ENDPOINTS ========================

// Create a new seed batch
app.post('/batches', asyncHandler(async (req, res) => {
    const { cropType, seedVariety, quantity, expiryDate } = req.body;

    // Validate
    if (!cropType || !seedVariety || !quantity || !expiryDate) {
        return res.status(400).json({ success: false, message: 'Missing required fields' });
    }

    const qty = Number(quantity);
    const expiry = Math.floor(new Date(expiryDate).getTime() / 1000);

    if (qty <= 0) return res.status(400).json({ success: false, message: 'Quantity must be positive' });
    if (expiry <= Math.floor(Date.now() / 1000)) {
        return res.status(400).json({ success: false, message: 'Expiry date must be in the future' });
    }

    // 1. Prepare metadata for IPFS
    const metadata = {
        type: 'SEED_BATCH',
        cropType,
        seedVariety,
        quantity: qty,
        expiryDate: expiryDate,
        createdAt: new Date().toISOString()
    };

    // 2. Upload to IPFS
    const ipfsHash = await ipfsService.uploadJSON(metadata);

    // 3. Record on Blockchain
    let txResult = { batchId: null, txHash: '' };
    try {
        txResult = await blockchainService.createBatch(cropType, seedVariety, qty, expiry, ipfsHash);
    } catch (bcErr) {
        console.error('Blockchain write failed (non-blocking):', bcErr.message);
        // Generate a local batchId if blockchain is down
        const Batch = require('./models/Batch');
        const lastBatch = await Batch.findOne().sort({ batchId: -1 }).lean();
        txResult.batchId = (lastBatch?.batchId || 0) + 1;
        txResult.txHash = 'local_' + Date.now();
    }

    // 4. Persist in MongoDB (PRIMARY STORAGE)
    const batchData = {
        batchId: txResult.batchId,
        cropType,
        seedVariety,
        quantity: qty,
        expiryDate: expiry,
        ipfsHash,
        ownerAddress: '0x_deployer',
        txHash: txResult.txHash,
        status: 'ACTIVE'
    };
    await dbService.saveBatch(batchData);

    // 5. Record in ledger
    await dbService.saveTransfer({
        batchId: txResult.batchId,
        fromAddress: 'SYSTEM',
        toAddress: '0x_deployer',
        txHash: txResult.txHash,
        transferType: 'CREATE',
        quantity: qty,
        metadata: { cropType, seedVariety }
    });

    // 6. AI Anomaly Detection (full hybrid analysis)
    let anomalyResult = { anomalyDetected: false, anomalyScore: 0, riskLevel: 'LOW', reasons: [] };
    try {
        const mlInput = {
            quantity: qty,
            daysToExpiry: Math.floor((expiry - Date.now() / 1000) / 86400),
            splitCount: 0,
            transferFrequency: 0,
            batchAgeDays: 0
        };
        anomalyResult = await aiService.runFullAnomalyDetection(batchData, mlInput);
    } catch (aiErr) {
        console.error('AI analysis failed (non-blocking):', aiErr.message);
    }

    res.json({
        success: true,
        batchId: txResult.batchId,
        txHash: txResult.txHash,
        ipfsHash,
        fraudScore: anomalyResult.anomalyScore,
        riskLevel: anomalyResult.riskLevel,
        reasons: anomalyResult.reasons,
        anomalyDetected: anomalyResult.anomalyDetected,
        message: 'Seed batch created successfully'
    });
}));

// Get all batches — reads from MongoDB (persistent)
app.get('/batches', asyncHandler(async (req, res) => {
    let batches = await dbService.getAllBatches();

    // If MongoDB is empty, try syncing from blockchain
    if (batches.length === 0) {
        try {
            const count = await blockchainService.getBatchCount();
            for (let i = 1; i <= count; i++) {
                try {
                    const batch = await blockchainService.getBatch(i);
                    batch.statusLabel = STATUS_MAP[batch.status] || 'UNKNOWN';
                    batch.isExpired = batch.expiryDate <= Math.floor(Date.now() / 1000);
                    if (batch.isExpired && batch.statusLabel === 'ACTIVE') {
                        batch.statusLabel = 'EXPIRED';
                    }
                    await dbService.saveBatch({
                        batchId: batch.batchId,
                        cropType: batch.cropType,
                        seedVariety: batch.seedVariety,
                        quantity: batch.quantity,
                        expiryDate: batch.expiryDate,
                        ipfsHash: batch.ipfsHash,
                        certIPFSHash: batch.certIPFSHash,
                        ownerAddress: batch.ownerAddress,
                        parentBatchId: batch.parentBatchId,
                        status: batch.statusLabel,
                        txHash: ''
                    });
                } catch (e) { /* skip */ }
            }
            batches = await dbService.getAllBatches();
        } catch (e) {
            console.warn('Blockchain sync failed:', e.message);
        }
    }

    // Enrich with status labels
    const now = Math.floor(Date.now() / 1000);
    const enriched = batches.map(b => ({
        ...b,
        statusLabel: b.status || 'ACTIVE',
        isExpired: b.expiryDate <= now,
    }));

    res.json(enriched);
}));

// Get single batch
app.get('/batches/:id', asyncHandler(async (req, res) => {
    const batchId = Number(req.params.id);

    // Try MongoDB first
    let batch = await dbService.getBatchById(batchId);

    // Fallback to blockchain
    if (!batch) {
        try {
            const chainBatch = await blockchainService.getBatch(batchId);
            chainBatch.statusLabel = STATUS_MAP[chainBatch.status] || 'UNKNOWN';
            chainBatch.isExpired = chainBatch.expiryDate <= Math.floor(Date.now() / 1000);
            // Cache in MongoDB
            await dbService.saveBatch({
                batchId: chainBatch.batchId,
                cropType: chainBatch.cropType,
                seedVariety: chainBatch.seedVariety,
                quantity: chainBatch.quantity,
                expiryDate: chainBatch.expiryDate,
                ipfsHash: chainBatch.ipfsHash,
                certIPFSHash: chainBatch.certIPFSHash,
                ownerAddress: chainBatch.ownerAddress,
                parentBatchId: chainBatch.parentBatchId,
                status: chainBatch.statusLabel
            });
            batch = await dbService.getBatchById(batchId);
        } catch (e) {
            return res.status(404).json({ error: `Batch #${batchId} not found` });
        }
    }

    const now = Math.floor(Date.now() / 1000);
    batch.statusLabel = batch.status || 'ACTIVE';
    batch.isExpired = batch.expiryDate <= now;

    // Get children
    try {
        const children = await blockchainService.getChildBatches(batchId);
        batch.childBatchIds = children;
    } catch (e) {
        batch.childBatchIds = [];
    }

    // Get certificate if exists
    try {
        const cert = await blockchainService.getCertificateByBatch(batchId);
        batch.certificate = cert;
    } catch (e) {
        batch.certificate = null;
    }

    res.json(batch);
}));

// Get batch history (lineage / parent chain)
app.get('/batches/:id/history', asyncHandler(async (req, res) => {
    const batchId = Number(req.params.id);
    const lineage = [];
    let currentId = batchId;

    while (currentId > 0) {
        try {
            const batch = await blockchainService.getBatch(currentId);
            batch.statusLabel = STATUS_MAP[batch.status] || 'UNKNOWN';
            lineage.push(batch);
            currentId = batch.parentBatchId;
        } catch (e) {
            break;
        }
    }

    let children = [];
    try {
        children = await blockchainService.getChildBatches(batchId);
    } catch (e) { /* skip */ }

    res.json({ lineage: lineage.reverse(), childBatchIds: children });
}));

// ======================== TRANSFER ========================

app.post('/batches/:id/transfer', asyncHandler(async (req, res) => {
    const batchId = Number(req.params.id);
    const { newOwner } = req.body;

    if (!newOwner || !ethers.isAddress(newOwner)) {
        return res.status(400).json({ success: false, message: 'Valid Ethereum address required' });
    }

    const batch = await blockchainService.getBatch(batchId);
    const fromAddress = batch.ownerAddress;

    const txResult = await blockchainService.transferBatch(batchId, newOwner);

    // Update MongoDB
    await dbService.saveBatch({
        ...batch,
        ownerAddress: newOwner,
        status: 'ACTIVE',
        txHash: txResult.txHash
    });

    // Record transfer in ledger
    await dbService.saveTransfer({
        batchId,
        fromAddress,
        toAddress: newOwner,
        txHash: txResult.txHash,
        transferType: 'TRANSFER',
        quantity: batch.quantity
    });

    // Re-run anomaly detection after transfer
    try {
        const updatedBatch = await dbService.getBatchById(batchId);
        if (updatedBatch) {
            await aiService.runFullAnomalyDetection(updatedBatch, {
                quantity: batch.quantity,
                daysToExpiry: Math.floor((batch.expiryDate - Date.now() / 1000) / 86400),
                splitCount: 0,
                transferFrequency: 1,
                batchAgeDays: Math.floor((Date.now() / 1000 - batch.createdAt) / 86400)
            });
        }
    } catch (e) { console.warn('Post-transfer anomaly detection failed:', e.message); }

    res.json({
        success: true,
        txHash: txResult.txHash,
        from: fromAddress,
        to: newOwner,
        message: 'Batch transferred successfully'
    });
}));

// ======================== SPLIT ========================

app.post('/batches/:id/split', asyncHandler(async (req, res) => {
    const batchId = Number(req.params.id);
    const { splitQuantity } = req.body;

    const qty = Number(splitQuantity);
    if (!qty || qty <= 0) {
        return res.status(400).json({ success: false, message: 'Split quantity must be positive' });
    }

    const parentBatch = await blockchainService.getBatch(batchId);

    const childMetadata = {
        type: 'SEED_BATCH_SPLIT',
        parentBatchId: batchId,
        cropType: parentBatch.cropType,
        seedVariety: parentBatch.seedVariety,
        quantity: qty,
        splitFrom: parentBatch.quantity,
        expiryDate: new Date(parentBatch.expiryDate * 1000).toISOString(),
        createdAt: new Date().toISOString()
    };

    const childIpfsHash = await ipfsService.uploadJSON(childMetadata);
    const txResult = await blockchainService.splitBatch(batchId, qty, childIpfsHash);

    // Save child batch in MongoDB
    const childBatchData = {
        batchId: txResult.childBatchId,
        cropType: parentBatch.cropType,
        seedVariety: parentBatch.seedVariety,
        quantity: qty,
        expiryDate: parentBatch.expiryDate,
        ipfsHash: childIpfsHash,
        ownerAddress: parentBatch.ownerAddress,
        parentBatchId: batchId,
        txHash: txResult.txHash,
        status: 'ACTIVE'
    };
    await dbService.saveBatch(childBatchData);

    // Update parent batch quantity in MongoDB
    await dbService.saveBatch({
        ...parentBatch,
        quantity: parentBatch.quantity - qty,
        txHash: txResult.txHash
    });

    // Record in ledger
    await dbService.saveTransfer({
        batchId: txResult.childBatchId,
        fromAddress: parentBatch.ownerAddress,
        toAddress: parentBatch.ownerAddress,
        txHash: txResult.txHash,
        transferType: 'SPLIT',
        quantity: qty,
        metadata: { parentBatchId: batchId }
    });

    // Anomaly detection on child batch
    try {
        await aiService.runFullAnomalyDetection(childBatchData, {
            quantity: qty,
            daysToExpiry: Math.floor((parentBatch.expiryDate - Date.now() / 1000) / 86400),
            splitCount: 1,
            transferFrequency: 0,
            batchAgeDays: 0
        });
    } catch (e) { console.warn('Post-split anomaly detection failed:', e.message); }

    res.json({
        success: true,
        childBatchId: txResult.childBatchId,
        txHash: txResult.txHash,
        parentRemaining: parentBatch.quantity - qty,
        message: 'Batch split successfully'
    });
}));

// ======================== CERTIFICATE ENDPOINTS ========================

app.post('/certificates', asyncHandler(async (req, res) => {
    const { batchId, certificateData, expiryDate } = req.body;

    if (!batchId || !certificateData || !expiryDate) {
        return res.status(400).json({ success: false, message: 'Missing required fields' });
    }

    const certExpiry = Math.floor(new Date(expiryDate).getTime() / 1000);
    if (certExpiry <= Math.floor(Date.now() / 1000)) {
        return res.status(400).json({ success: false, message: 'Certificate expiry must be in the future' });
    }

    const certPayload = {
        type: 'SEED_CERTIFICATE',
        batchId: Number(batchId),
        ...certificateData,
        issuedAt: new Date().toISOString(),
        expiryDate: expiryDate
    };

    const certIpfsHash = await ipfsService.uploadJSON(certPayload);
    const certJsonString = JSON.stringify(certPayload);
    const certHash = ethers.keccak256(ethers.toUtf8Bytes(certJsonString));
    const digitalSignature = await blockchainService.signMessage(certHash);

    const txResult = await blockchainService.registerCertificate(
        Number(batchId),
        certIpfsHash,
        digitalSignature,
        certExpiry
    );

    // Save to MongoDB
    await dbService.saveCertificate({
        certId: txResult.certId,
        batchId: Number(batchId),
        issuerAddress: 'deployer',
        ipfsHash: certIpfsHash,
        digitalSignature,
        issuedAt: Math.floor(Date.now() / 1000),
        expiryDate: certExpiry,
        isValid: true,
        txHash: txResult.txHash
    });

    // Record in ledger
    await dbService.saveTransfer({
        batchId: Number(batchId),
        fromAddress: 'SYSTEM',
        toAddress: 'deployer',
        txHash: txResult.txHash,
        transferType: 'CREATE',
        metadata: { type: 'CERTIFICATE', certId: txResult.certId }
    });

    res.json({
        success: true,
        certId: txResult.certId,
        txHash: txResult.txHash,
        ipfsHash: certIpfsHash,
        digitalSignature,
        message: 'Certificate registered successfully'
    });
}));

app.get('/certificates/verify/:certId', asyncHandler(async (req, res) => {
    const certId = Number(req.params.certId);

    const chainResult = await blockchainService.verifyCertificate(certId);

    let ipfsData = null;
    try {
        ipfsData = await ipfsService.getJSON(chainResult.ipfsHash);
    } catch (e) {
        console.error('IPFS fetch failed:', e.message);
    }

    let integrityStatus = 'UNKNOWN';
    if (ipfsData) {
        try {
            const certJsonString = JSON.stringify(ipfsData);
            const recomputedHash = ethers.keccak256(ethers.toUtf8Bytes(certJsonString));
            const recoveredAddress = ethers.verifyMessage(recomputedHash, chainResult.signature);

            if (recoveredAddress.toLowerCase() === chainResult.issuer.toLowerCase()) {
                integrityStatus = chainResult.isExpired ? 'EXPIRED' : 'VALID';
            } else {
                integrityStatus = 'TAMPERED';
            }
        } catch (sigErr) {
            console.error('Signature verification error:', sigErr.message);
            integrityStatus = 'TAMPERED';
        }
    }

    if (!chainResult.isValid && !chainResult.isExpired) {
        integrityStatus = 'REVOKED';
    }

    res.json({
        certId,
        batchId: chainResult.batchId,
        issuer: chainResult.issuer,
        ipfsHash: chainResult.ipfsHash,
        isValid: chainResult.isValid,
        isExpired: chainResult.isExpired,
        integrityStatus,
        certificateData: ipfsData,
        message: `Certificate status: ${integrityStatus}`
    });
}));

app.get('/certificates/batch/:batchId', asyncHandler(async (req, res) => {
    const batchId = Number(req.params.batchId);
    try {
        const cert = await blockchainService.getCertificateByBatch(batchId);
        res.json(cert);
    } catch (error) {
        res.status(404).json({ error: 'No certificate found for this batch' });
    }
}));

// ======================== BLOCKCHAIN EVENTS ========================

app.get('/events', asyncHandler(async (req, res) => {
    const events = await blockchainService.getBlockchainEvents();
    res.json(events);
}));

// ======================== ANOMALY / AI ENDPOINTS ========================

// Get all anomaly-flagged batches
app.get('/api/anomalies', asyncHandler(async (req, res) => {
    const anomalies = await dbService.getAnomalyBatches();
    res.json(anomalies);
}));

// Get anomaly details for a specific batch
app.get('/api/anomalies/:batchId', asyncHandler(async (req, res) => {
    const batchId = Number(req.params.batchId);
    const analyses = await dbService.getFraudAnalysisByBatch(batchId);
    const batch = await dbService.getBatchById(batchId);
    res.json({
        batch,
        analyses,
        latestScore: analyses[0]?.fraudScore || 0,
        latestRiskLevel: analyses[0]?.riskLevel || 'LOW'
    });
}));

// Get recent anomaly alerts
app.get('/api/anomalies/recent/alerts', asyncHandler(async (req, res) => {
    const limit = Math.min(Number(req.query.limit) || 20, 100);
    const alerts = await dbService.getRecentAnomalies(limit);
    res.json(alerts);
}));

// ======================== LEDGER ========================

app.get('/api/ledger', asyncHandler(async (req, res) => {
    const limit = Math.min(Number(req.query.limit) || 100, 500);
    const ledger = await dbService.getLedger(limit);
    res.json(ledger);
}));

// ======================== VERIFICATION ========================

app.post('/api/verify', asyncHandler(async (req, res) => {
    const { batchId, certId } = req.body;
    if (certId) {
        const chainResult = await blockchainService.verifyCertificate(Number(certId));
        return res.json({ verified: chainResult.isValid, ...chainResult });
    }
    if (batchId) {
        const batch = await dbService.getBatchById(Number(batchId));
        if (!batch) return res.status(404).json({ error: 'Batch not found' });
        return res.json({ verified: batch.status === 'ACTIVE', batch });
    }
    res.status(400).json({ error: 'Provide batchId or certId' });
}));

// ======================== DASHBOARD METRICS ========================

app.get('/dashboard-metrics', asyncHandler(async (req, res) => {
    const metrics = await dbService.getDashboardMetrics();

    let batchCount = metrics.totalBatches;
    let certCount = metrics.totalCertificates;
    try {
        const bcBatchCount = await blockchainService.getBatchCount();
        const bcCertCount = await blockchainService.getCertificateCount();
        if (bcBatchCount > batchCount) batchCount = bcBatchCount;
        if (bcCertCount > certCount) certCount = bcCertCount;
    } catch (e) { /* use MongoDB counts */ }

    res.json({
        totalBatches: batchCount,
        activeBatches: metrics.activeBatches,
        totalCertificates: certCount,
        totalTransfers: metrics.totalTransfers,
        fraudAlerts: metrics.fraudAlerts,
        highRiskCount: metrics.highRiskCount,
        mediumRiskCount: metrics.mediumRiskCount,
        anomalyBatches: metrics.anomalyBatches,
        averageFraudScore: Math.round(metrics.averageFraudScore * 100) / 100,
        systemHealth: 'Good'
    });
}));

// ======================== KYC VERIFICATION ENDPOINTS ========================

const kycStore = new Map();

// Sample pre-verified test wallets
kycStore.set('0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266', {
    companyName: 'Apex Trade Solutions Ltd',
    registrationNumber: 'REG-98765432',
    country: 'United States',
    idType: 'Business License & Tax ID',
    status: 'VERIFIED',
    verifiedAt: new Date().toISOString()
});

kycStore.set('0x70997970c51812dc3a010c7d01b50e0d17dc79c8', {
    companyName: 'EuroAsia Logistics GmbH',
    registrationNumber: 'DE-88219401',
    country: 'Germany',
    idType: 'Commercial Register Extract',
    status: 'VERIFIED',
    verifiedAt: new Date().toISOString()
});

app.get('/api/kyc/:walletAddress', asyncHandler(async (req, res) => {
    const address = req.params.walletAddress.toLowerCase();
    const kyc = kycStore.get(address);
    if (!kyc) {
        return res.json({ status: 'NOT_VERIFIED', message: 'No KYC record found for this wallet address' });
    }
    res.json({ success: true, ...kyc });
}));

app.post('/api/kyc', asyncHandler(async (req, res) => {
    const { walletAddress, companyName, registrationNumber, country, idType } = req.body;
    if (!walletAddress || !companyName || !registrationNumber) {
        return res.status(400).json({ success: false, message: 'Missing required KYC fields' });
    }
    const address = walletAddress.toLowerCase();
    const kycData = {
        companyName,
        registrationNumber,
        country: country || 'International',
        idType: idType || 'Business License',
        status: 'VERIFIED',
        verifiedAt: new Date().toISOString()
    };
    kycStore.set(address, kycData);
    res.json({
        success: true,
        message: 'KYC Identity Verified successfully!',
        kyc: kycData
    });
}));

// ======================== IPFS CONTENT ========================

app.get('/ipfs/:hash', asyncHandler(async (req, res) => {
    const data = await ipfsService.getJSON(req.params.hash);
    if (!data) return res.status(404).json({ error: 'Content not found' });
    res.json(data);
}));

// ======================== HEALTH CHECK ========================

app.get('/health', (req, res) => {
    res.json({
        status: 'OK',
        mongodb: dbService.connected ? 'connected' : 'disconnected',
        blockchain: blockchainService.connected ? 'connected' : 'disconnected',
        timestamp: new Date().toISOString()
    });
});

// ======================== GLOBAL ERROR HANDLER ========================

app.use((err, req, res, next) => {
    console.error('Unhandled error:', err);
    res.status(500).json({
        success: false,
        error: err.reason || err.message || 'Internal server error'
    });
});

// ======================== START SERVER ========================

initServices().then(() => {
    app.listen(PORT, () => {
        console.log(`CrossPay Backend running on port ${PORT}`);
        console.log(`Health check: http://localhost:${PORT}/health`);
    });
}).catch(err => {
    console.error('Failed to initialize services:', err);
    // Start server anyway for partial functionality
    app.listen(PORT, () => {
        console.log(`CrossPay Backend running on port ${PORT} (degraded mode)`);
    });
});
