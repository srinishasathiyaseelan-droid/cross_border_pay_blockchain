import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:4000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

export const seedService = {
  // ======================== BATCHES ========================
  createBatch: async (data) => {
    const response = await api.post('/batches', data);
    return response.data;
  },
  getAllBatches: async () => {
    const response = await api.get('/batches');
    return response.data;
  },
  getBatch: async (id) => {
    const response = await api.get(`/batches/${id}`);
    return response.data;
  },
  getBatchHistory: async (id) => {
    const response = await api.get(`/batches/${id}/history`);
    return response.data;
  },

  // ======================== TRANSFER ========================
  transferBatch: async (id, newOwner) => {
    const response = await api.post(`/batches/${id}/transfer`, { newOwner });
    return response.data;
  },

  // ======================== SPLIT ========================
  splitBatch: async (id, splitQuantity) => {
    const response = await api.post(`/batches/${id}/split`, { splitQuantity });
    return response.data;
  },

  // ======================== CERTIFICATES ========================
  registerCertificate: async (data) => {
    const response = await api.post('/certificates', data);
    return response.data;
  },
  verifyCertificate: async (certId) => {
    const response = await api.get(`/certificates/verify/${certId}`);
    return response.data;
  },
  getCertificateByBatch: async (batchId) => {
    const response = await api.get(`/certificates/batch/${batchId}`);
    return response.data;
  },

  // ======================== EVENTS ========================
  getBlockchainEvents: async () => {
    const response = await api.get('/events');
    return response.data;
  },

  // ======================== DASHBOARD ========================
  getDashboardMetrics: async () => {
    const response = await api.get('/dashboard-metrics');
    return response.data;
  },

  // ======================== IPFS ========================
  getIPFSContent: async (hash) => {
    const response = await api.get(`/ipfs/${hash}`);
    return response.data;
  },
};

export default api;
