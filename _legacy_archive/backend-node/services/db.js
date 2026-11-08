const mongoose = require('mongoose');
const Batch = require('../models/Batch');
const Certificate = require('../models/Certificate');
const Transfer = require('../models/Transfer');
const FraudAnalysis = require('../models/FraudAnalysis');

class DatabaseService {
    constructor() {
        this.connected = false;
    }

    async connect() {
        try {
            const uri = process.env.MONGODB_URI || 'mongodb://localhost:27017/seedchain';
            await mongoose.connect(uri);
            this.connected = true;
            console.log(`Connected to MongoDB: ${uri}`);
        } catch (err) {
            console.error('MongoDB connection error:', err.message);
            throw err;
        }
    }

    // ======================== BATCH ========================

    async saveBatch(data) {
        const update = {
            batchId: data.batchId,
            cropType: data.cropType,
            seedVariety: data.seedVariety,
            quantity: data.quantity,
            expiryDate: data.expiryDate,
            ipfsHash: data.ipfsHash || '',
            certIPFSHash: data.certIPFSHash || '',
            ownerAddress: data.ownerAddress || '',
            parentBatchId: data.parentBatchId || 0,
            status: data.status || 'ACTIVE',
            txHash: data.txHash || '',
            anomalyDetected: data.anomalyDetected || false,
            anomalyScore: data.anomalyScore || 0,
            riskLevel: data.riskLevel || 'LOW',
            anomalyReasons: data.anomalyReasons || [],
            anomalyHash: data.anomalyHash || ''
        };
        return Batch.findOneAndUpdate(
            { batchId: data.batchId },
            update,
            { upsert: true, new: true, setDefaultsOnInsert: true }
        );
    }

    async getAllBatches() {
        return Batch.find().sort({ createdAt: -1 }).lean();
    }

    async getBatchById(batchId) {
        return Batch.findOne({ batchId }).lean();
    }

    async getAnomalyBatches() {
        return Batch.find({ anomalyDetected: true }).sort({ anomalyScore: -1 }).lean();
    }

    async updateBatchAnomaly(batchId, anomalyData) {
        return Batch.findOneAndUpdate(
            { batchId },
            {
                anomalyDetected: anomalyData.anomalyDetected,
                anomalyScore: anomalyData.anomalyScore,
                riskLevel: anomalyData.riskLevel,
                anomalyReasons: anomalyData.anomalyReasons || [],
                anomalyHash: anomalyData.anomalyHash || ''
            },
            { new: true }
        );
    }

    // ======================== CERTIFICATE ========================

    async saveCertificate(data) {
        return Certificate.findOneAndUpdate(
            { certId: data.certId },
            {
                certId: data.certId,
                batchId: data.batchId,
                issuerAddress: data.issuerAddress || '',
                ipfsHash: data.ipfsHash || '',
                digitalSignature: data.digitalSignature || '',
                issuedAt: data.issuedAt,
                expiryDate: data.expiryDate,
                isValid: data.isValid !== undefined ? data.isValid : true,
                txHash: data.txHash || ''
            },
            { upsert: true, new: true, setDefaultsOnInsert: true }
        );
    }

    async getCertificateByBatch(batchId) {
        return Certificate.findOne({ batchId }).lean();
    }

    async getAllCertificates() {
        return Certificate.find().sort({ createdAt: -1 }).lean();
    }

    // ======================== TRANSFERS / LEDGER ========================

    async saveTransfer(data) {
        return new Transfer({
            batchId: data.batchId,
            fromAddress: data.fromAddress || '',
            toAddress: data.toAddress || '',
            txHash: data.txHash || '',
            transferType: data.transferType || 'TRANSFER',
            quantity: data.quantity || 0,
            metadata: data.metadata || {}
        }).save();
    }

    async getTransfersByBatch(batchId) {
        return Transfer.find({ batchId }).sort({ createdAt: -1 }).lean();
    }

    async getAllTransfers() {
        return Transfer.find().sort({ createdAt: -1 }).lean();
    }

    async getLedger(limit = 100) {
        return Transfer.find().sort({ createdAt: -1 }).limit(limit).lean();
    }

    // ======================== FRAUD ANALYSIS ========================

    async saveFraudAnalysis(data) {
        return new FraudAnalysis({
            batchId: data.batchId,
            fraudScore: data.fraudScore || 0,
            riskLevel: data.riskLevel || 'LOW',
            reasons: data.reasons || [],
            mlScore: data.mlScore || 0,
            ruleScore: data.ruleScore || 0,
            statisticalScore: data.statisticalScore || 0,
            source: data.source || 'HYBRID',
            anomalyHash: data.anomalyHash || ''
        }).save();
    }

    async getFraudAnalysisByBatch(batchId) {
        return FraudAnalysis.find({ batchId }).sort({ createdAt: -1 }).lean();
    }

    async getRecentAnomalies(limit = 20) {
        return FraudAnalysis.find({ fraudScore: { $gte: 0.4 } })
            .sort({ createdAt: -1 })
            .limit(limit)
            .lean();
    }

    // ======================== METRICS ========================

    async getDashboardMetrics() {
        const [
            totalBatches,
            activeBatches,
            totalCertificates,
            totalTransfers,
            fraudAlerts,
            highRiskCount,
            mediumRiskCount,
            avgFraudScore
        ] = await Promise.all([
            Batch.countDocuments(),
            Batch.countDocuments({ status: 'ACTIVE' }),
            Certificate.countDocuments(),
            Transfer.countDocuments(),
            FraudAnalysis.countDocuments({ fraudScore: { $gte: 0.7 } }),
            Batch.countDocuments({ riskLevel: 'HIGH' }),
            Batch.countDocuments({ riskLevel: 'MEDIUM' }),
            FraudAnalysis.aggregate([
                { $group: { _id: null, avg: { $avg: '$fraudScore' } } }
            ])
        ]);

        return {
            totalBatches,
            activeBatches,
            totalCertificates,
            totalTransfers,
            fraudAlerts,
            highRiskCount,
            mediumRiskCount,
            averageFraudScore: avgFraudScore[0]?.avg || 0,
            anomalyBatches: await Batch.countDocuments({ anomalyDetected: true })
        };
    }
}

module.exports = new DatabaseService();
