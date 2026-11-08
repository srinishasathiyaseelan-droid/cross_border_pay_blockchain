const axios = require('axios');
const crypto = require('crypto');
const MockIPFS = require('../models/MockIPFS');

class IpfsService {
    constructor() {
        this.ipfsUrl = process.env.IPFS_API_URL || 'http://127.0.0.1:5001/api/v0';
        this.mockMemory = new Map(); // Fast in-memory cache
    }

    async loadFromDB() {
        try {
            const entries = await MockIPFS.find().lean();
            for (const entry of entries) {
                this.mockMemory.set(entry.hash, entry.content);
            }
            if (entries.length > 0) {
                console.log(`[MOCK IPFS] Loaded ${entries.length} entries from MongoDB`);
            }
        } catch (e) {
            console.warn('Mock IPFS DB load failed:', e.message);
        }
    }

    async _persistMock(hash, data) {
        this.mockMemory.set(hash, data);
        try {
            await MockIPFS.findOneAndUpdate(
                { hash },
                { hash, content: data },
                { upsert: true }
            );
        } catch (err) {
            console.warn('Mock IPFS persist error:', err.message);
        }
    }

    async uploadJSON(data) {
        try {
            const jsonString = JSON.stringify(data);
            const FormData = require('form-data');
            const formData = new FormData();
            formData.append('file', Buffer.from(jsonString), 'data.json');

            const response = await axios.post(`${this.ipfsUrl}/add`, formData, {
                headers: { ...formData.getHeaders() },
                params: { 'pin': true },
                timeout: 5000
            });

            if (response.data && response.data.Hash) {
                console.log(`IPFS Upload Success: ${response.data.Hash}`);
                // Also persist in mock for fallback
                await this._persistMock(response.data.Hash, data);
                return response.data.Hash;
            } else {
                throw new Error('Invalid IPFS response');
            }
        } catch (error) {
            console.warn('IPFS Connection Failed (using Mock IPFS Fallback):', error.message);
            const jsonString = JSON.stringify(data);
            const hash = crypto.createHash('sha256').update(jsonString).digest('hex');
            const mockCid = `Qm${hash.substring(0, 44)}`;

            await this._persistMock(mockCid, data);
            console.log(`[MOCK] Stored data with hash: ${mockCid}`);
            return mockCid;
        }
    }

    async getJSON(hash) {
        // Check in-memory cache first (fastest)
        if (this.mockMemory.has(hash)) {
            console.log(`[MOCK] Retrieved data for hash: ${hash}`);
            return this.mockMemory.get(hash);
        }

        // Check MongoDB storage
        try {
            const doc = await MockIPFS.findOne({ hash }).lean();
            if (doc) {
                this.mockMemory.set(hash, doc.content); // re-cache
                console.log(`[MOCK DB] Retrieved data for hash: ${hash}`);
                return doc.content;
            }
        } catch (e) {
            console.warn('Mock IPFS DB read error:', e.message);
        }

        // Try real IPFS gateway
        try {
            const gatewayUrl = process.env.IPFS_GATEWAY_URL || 'http://127.0.0.1:8080/ipfs';
            const response = await axios.get(`${gatewayUrl}/${hash}`, { timeout: 5000 });
            return response.data;
        } catch (error) {
            console.error(`IPFS Fetch Failed for ${hash}:`, error.message);
            return null;
        }
    }
}

module.exports = new IpfsService();
