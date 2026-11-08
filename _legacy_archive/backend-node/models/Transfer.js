const mongoose = require('mongoose');

const transferSchema = new mongoose.Schema({
    batchId: { type: Number, required: true, index: true },
    fromAddress: { type: String, required: true },
    toAddress: { type: String, required: true },
    txHash: { type: String, default: '' },
    transferType: { type: String, enum: ['TRANSFER', 'SPLIT', 'CREATE'], default: 'TRANSFER' },
    quantity: { type: Number, default: 0 },
    metadata: { type: mongoose.Schema.Types.Mixed, default: {} }
}, {
    timestamps: true
});

transferSchema.index({ createdAt: -1 });

module.exports = mongoose.model('Transfer', transferSchema);
