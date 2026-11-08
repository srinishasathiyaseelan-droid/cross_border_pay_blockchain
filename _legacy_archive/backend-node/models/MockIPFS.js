const mongoose = require('mongoose');

const mockIPFSSchema = new mongoose.Schema({
    hash: { type: String, unique: true, required: true, index: true },
    content: { type: mongoose.Schema.Types.Mixed, required: true }
}, {
    timestamps: true
});

module.exports = mongoose.model('MockIPFS', mockIPFSSchema);
