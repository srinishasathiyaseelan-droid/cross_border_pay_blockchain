const axios = require('axios');
const anomalyDetector = require('../ai/anomalyDetector');
const dbService = require('./db');

class AIService {
    constructor() {
        this.baseUrl = process.env.AI_SERVICE_URL || 'http://127.0.0.1:5000';
    }

    /**
     * Call Python ML service for fraud prediction
     */
    async predictSeedFraud(transactionData) {
        try {
            const payload = {
                quantity: parseFloat(transactionData.quantity),
                days_to_expiry: parseFloat(transactionData.daysToExpiry || 365),
                split_count: parseInt(transactionData.splitCount || 0),
                transfer_frequency: parseInt(transactionData.transferFrequency || 0),
                batch_age_days: parseInt(transactionData.batchAgeDays || 0),
                geo_distance: parseFloat(transactionData.geoDistance || 0)
            };

            const response = await axios.post(`${this.baseUrl}/predict-seed-fraud`, payload, {
                timeout: 5000
            });
            return response.data;
        } catch (error) {
            console.error('AI Service Error:', error.message);
            return {
                fraud_score: 0.1,
                risk_level: 'UNKNOWN',
                reasons: ['AI service unavailable'],
                status: 'ERROR'
            };
        }
    }

    /**
     * Run full anomaly detection: Python ML + Node.js rules + statistics
     * @param {Object} batchData - Batch object from MongoDB
     * @param {Object} mlInputData - Features for ML model
     * @returns {Object} Combined anomaly result
     */
    async runFullAnomalyDetection(batchData, mlInputData = null) {
        // 1. Get ML prediction from Python service
        let mlResult = null;
        if (mlInputData) {
            mlResult = await this.predictSeedFraud(mlInputData);
        }

        // 2. Run local anomaly detector (rules + statistics)
        const anomalyResult = await anomalyDetector.analyze(batchData, mlResult);

        // 3. Save analysis to MongoDB
        try {
            await dbService.saveFraudAnalysis({
                batchId: batchData.batchId,
                fraudScore: anomalyResult.anomalyScore,
                riskLevel: anomalyResult.riskLevel,
                reasons: anomalyResult.reasons,
                mlScore: anomalyResult.mlScore,
                ruleScore: anomalyResult.ruleScore,
                statisticalScore: anomalyResult.statisticalScore,
                source: anomalyResult.source
            });

            // Update batch record with anomaly data
            await dbService.updateBatchAnomaly(batchData.batchId, {
                anomalyDetected: anomalyResult.anomalyDetected,
                anomalyScore: anomalyResult.anomalyScore,
                riskLevel: anomalyResult.riskLevel,
                anomalyReasons: anomalyResult.reasons
            });
        } catch (e) {
            console.error('Failed to persist anomaly data:', e.message);
        }

        return anomalyResult;
    }
}

module.exports = new AIService();
