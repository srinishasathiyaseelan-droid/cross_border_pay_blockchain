/**
 * SeedChain Anomaly Detector
 * Rule-based + Statistical anomaly detection for seed supply chain
 * Works alongside the Python ML service for hybrid detection
 */

const Batch = require('../models/Batch');
const FraudAnalysis = require('../models/FraudAnalysis');

class AnomalyDetector {

    /**
     * Run full anomaly detection on a batch
     * @param {Object} batchData - The batch being analyzed
     * @param {Object} mlResult - Result from Python AI service (optional)
     * @returns {Object} Combined anomaly result
     */
    async analyze(batchData, mlResult = null) {
        const ruleResult = await this.runRuleBasedDetection(batchData);
        const statResult = await this.runStatisticalDetection(batchData);

        // Combine scores: 40% ML, 35% rules, 25% statistical
        const mlScore = mlResult?.fraud_score || 0;
        const ruleScore = ruleResult.score;
        const statScore = statResult.score;

        const combinedScore = (
            0.40 * mlScore +
            0.35 * ruleScore +
            0.25 * statScore
        );

        const clampedScore = Math.min(Math.max(combinedScore, 0), 1);

        // Determine risk level
        let riskLevel = 'LOW';
        if (clampedScore >= 0.7) riskLevel = 'HIGH';
        else if (clampedScore >= 0.4) riskLevel = 'MEDIUM';

        // Merge all reasons
        const allReasons = [
            ...(mlResult?.reasons || []),
            ...ruleResult.reasons,
            ...statResult.reasons
        ];

        return {
            anomalyDetected: clampedScore >= 0.4,
            anomalyScore: Math.round(clampedScore * 1000) / 1000,
            riskLevel,
            reasons: [...new Set(allReasons)], // dedupe
            mlScore: Math.round(mlScore * 1000) / 1000,
            ruleScore: Math.round(ruleScore * 1000) / 1000,
            statisticalScore: Math.round(statScore * 1000) / 1000,
            source: mlResult ? 'HYBRID' : 'RULES'
        };
    }

    /**
     * Rule-based detection: checks for known suspicious patterns
     */
    async runRuleBasedDetection(batchData) {
        let score = 0;
        const reasons = [];
        const now = Math.floor(Date.now() / 1000);

        // 1. Near-expiry batch
        const daysToExpiry = (batchData.expiryDate - now) / 86400;
        if (daysToExpiry < 7) {
            score += 0.4;
            reasons.push(`Near-expiry batch (${Math.max(0, Math.round(daysToExpiry))} days remaining)`);
        } else if (daysToExpiry < 30) {
            score += 0.2;
            reasons.push(`Short expiry window (${Math.round(daysToExpiry)} days remaining)`);
        }

        // 2. Suspicious quantity
        if (batchData.quantity > 50000) {
            score += 0.3;
            reasons.push(`Unusually large quantity (${batchData.quantity}g)`);
        } else if (batchData.quantity > 20000) {
            score += 0.15;
            reasons.push(`Large quantity detected (${batchData.quantity}g)`);
        }

        // 3. Past-dated expiry (expired at creation)
        if (batchData.expiryDate <= now) {
            score += 0.5;
            reasons.push('Batch created with already-expired date');
        }

        // 4. Duplicate IPFS hash detection
        if (batchData.ipfsHash) {
            try {
                const duplicates = await Batch.countDocuments({
                    ipfsHash: batchData.ipfsHash,
                    batchId: { $ne: batchData.batchId }
                });
                if (duplicates > 0) {
                    score += 0.6;
                    reasons.push(`Duplicate IPFS hash found across ${duplicates} other batch(es)`);
                }
            } catch (e) { /* non-blocking */ }
        }

        // 5. Rapid batch creation (>5 batches in last 5 minutes)
        try {
            const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000);
            const recentCount = await Batch.countDocuments({ createdAt: { $gte: fiveMinAgo } });
            if (recentCount > 10) {
                score += 0.4;
                reasons.push(`Rapid batch creation detected (${recentCount} batches in 5 minutes)`);
            } else if (recentCount > 5) {
                score += 0.2;
                reasons.push(`High batch creation rate (${recentCount} batches in 5 minutes)`);
            }
        } catch (e) { /* non-blocking */ }

        // 6. Suspiciously small quantity
        if (batchData.quantity < 10) {
            score += 0.2;
            reasons.push(`Unusually small quantity (${batchData.quantity}g)`);
        }

        return {
            score: Math.min(score, 1),
            reasons
        };
    }

    /**
     * Statistical detection: Z-score analysis against historical data
     */
    async runStatisticalDetection(batchData) {
        let score = 0;
        const reasons = [];

        try {
            // Get historical batches of same crop type
            const historicalBatches = await Batch.find({
                cropType: batchData.cropType,
                batchId: { $ne: batchData.batchId }
            }).lean();

            if (historicalBatches.length >= 5) {
                // Z-score on quantity
                const quantities = historicalBatches.map(b => b.quantity);
                const mean = quantities.reduce((a, b) => a + b, 0) / quantities.length;
                const stdDev = Math.sqrt(quantities.reduce((sum, q) => sum + Math.pow(q - mean, 2), 0) / quantities.length);

                if (stdDev > 0) {
                    const zScore = Math.abs((batchData.quantity - mean) / stdDev);
                    if (zScore > 3) {
                        score += 0.5;
                        reasons.push(`Quantity is ${zScore.toFixed(1)} standard deviations from mean for ${batchData.cropType}`);
                    } else if (zScore > 2) {
                        score += 0.25;
                        reasons.push(`Quantity deviates significantly (Z=${zScore.toFixed(1)}) for ${batchData.cropType}`);
                    }
                }

                // Check expiry consistency
                const expiries = historicalBatches.map(b => b.expiryDate);
                const avgExpiry = expiries.reduce((a, b) => a + b, 0) / expiries.length;
                const expiryDiff = Math.abs(batchData.expiryDate - avgExpiry) / 86400; // days
                if (expiryDiff > 365) {
                    score += 0.2;
                    reasons.push(`Expiry date unusually far from average for ${batchData.cropType}`);
                }
            }

            // Transfer frequency analysis
            const Transfer = require('../models/Transfer');
            const transferCount = await Transfer.countDocuments({ batchId: batchData.batchId });
            if (transferCount > 8) {
                score += 0.4;
                reasons.push(`High transfer frequency (${transferCount} transfers)`);
            } else if (transferCount > 5) {
                score += 0.2;
                reasons.push(`Elevated transfer frequency (${transferCount} transfers)`);
            }

        } catch (e) {
            // Non-blocking: if stats fail, just return 0
            console.warn('Statistical analysis warning:', e.message);
        }

        return {
            score: Math.min(score, 1),
            reasons
        };
    }
}

module.exports = new AnomalyDetector();
