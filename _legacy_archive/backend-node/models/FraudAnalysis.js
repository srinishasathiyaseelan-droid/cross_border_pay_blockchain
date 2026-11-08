const mongoose = require('mongoose');

const fraudAnalysisSchema = new mongoose.Schema({
    batchId: { type: Number, required: true, index: true },
    fraudScore: { type: Number, default: 0 },
    riskLevel: { type: String, enum: ['LOW', 'MEDIUM', 'HIGH', 'UNKNOWN'], default: 'LOW' },
    reasons: [{ type: String }],
    // Breakdown of detection sources
    mlScore: { type: Number, default: 0 },        // Python AI service score
    ruleScore: { type: Number, default: 0 },       // Rule-based score
    statisticalScore: { type: Number, default: 0 }, // Statistical score
    source: { type: String, enum: ['ML', 'RULES', 'HYBRID'], default: 'HYBRID' },
    anomalyHash: { type: String, default: '' }  // IPFS hash of full report
}, {
    timestamps: true
});

fraudAnalysisSchema.index({ fraudScore: -1 });
fraudAnalysisSchema.index({ riskLevel: 1 });

module.exports = mongoose.model('FraudAnalysis', fraudAnalysisSchema);
