const mongoose = require('mongoose');

const batchSchema = new mongoose.Schema({
    batchId: { type: Number, unique: true, required: true, index: true },
    cropType: { type: String, required: true },
    seedVariety: { type: String, required: true },
    quantity: { type: Number, required: true, min: 1 },
    expiryDate: { type: Number, required: true }, // unix timestamp
    ipfsHash: { type: String, default: '' },
    certIPFSHash: { type: String, default: '' },
    ownerAddress: { type: String, default: '' },
    parentBatchId: { type: Number, default: 0 },
    status: { type: String, enum: ['ACTIVE', 'EXPIRED', 'TRANSFERRED'], default: 'ACTIVE' },
    txHash: { type: String, default: '' },
    // AI Anomaly Detection fields
    anomalyDetected: { type: Boolean, default: false },
    anomalyScore: { type: Number, default: 0 },
    riskLevel: { type: String, enum: ['LOW', 'MEDIUM', 'HIGH', 'UNKNOWN'], default: 'LOW' },
    anomalyReasons: [{ type: String }],
    anomalyHash: { type: String, default: '' } // blockchain hash of anomaly report
}, {
    timestamps: true
});

// Indexes for common queries
batchSchema.index({ status: 1 });
batchSchema.index({ anomalyDetected: 1 });
batchSchema.index({ riskLevel: 1 });
batchSchema.index({ ownerAddress: 1 });

module.exports = mongoose.model('Batch', batchSchema);
