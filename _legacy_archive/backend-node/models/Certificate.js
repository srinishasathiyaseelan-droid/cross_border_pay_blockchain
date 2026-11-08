const mongoose = require('mongoose');

const certificateSchema = new mongoose.Schema({
    certId: { type: Number, unique: true, required: true, index: true },
    batchId: { type: Number, required: true, index: true },
    issuerAddress: { type: String, default: '' },
    ipfsHash: { type: String, default: '' },
    digitalSignature: { type: String, default: '' },
    issuedAt: { type: Number },    // unix timestamp
    expiryDate: { type: Number },  // unix timestamp
    isValid: { type: Boolean, default: true },
    txHash: { type: String, default: '' }
}, {
    timestamps: true
});

module.exports = mongoose.model('Certificate', certificateSchema);
