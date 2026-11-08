// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract RationDistribution {
    struct Transaction {
        bytes32 beneficiary_id_hash;
        string shop_id;
        uint256 quantity;
        uint256 timestamp;
        string region;
        uint256 ai_fraud_score; // Scaled by 100 (e.g. 0.75 -> 75)
        bool verification_status;
    }

    mapping(bytes32 => uint256) public beneficiaryMonthlyQuota;
    mapping(bytes32 => uint256) public beneficiaryMonthlyConsumed;
    
    // Arrays to store transaction history
    Transaction[] public transactions;

    // Events
    event TransactionRecorded(
        bytes32 indexed beneficiary_id_hash,
        string shop_id,
        uint256 quantity,
        uint256 timestamp,
        uint256 ai_fraud_score,
        bool status
    );

    event FraudAlert(
        bytes32 indexed beneficiary_id_hash,
        string shop_id,
        uint256 ai_fraud_score,
        string reason,
        uint256 timestamp
    );

    event QuotaExceeded(
        bytes32 indexed beneficiary_id_hash,
        uint256 requested,
        uint256 remaining
    );

    // Default quota if not set (could be dynamic)
    uint256 public constant DEFAULT_QUOTA = 50; 

    // Thresholds
    uint256 public constant FRAUD_SCORE_THRESHOLD = 70; // 0.70 * 100

    constructor() {}

    /**
     * @dev Record a ration transaction.
     * @param _beneficiary_id_hash Hash of the beneficiary ID
     * @param _shop_id Shop ID
     * @param _quantity Quantity of ration requested
     * @param _region Region code
     * @param _ai_fraud_score Fraud score from AI (0-100)
     */
    function recordTransaction(
        bytes32 _beneficiary_id_hash,
        string memory _shop_id,
        uint256 _quantity,
        string memory _region,
        uint256 _ai_fraud_score
    ) public {
        uint256 currentQuota = beneficiaryMonthlyQuota[_beneficiary_id_hash];
        if (currentQuota == 0) {
            currentQuota = DEFAULT_QUOTA;
        }
        
        uint256 consumed = beneficiaryMonthlyConsumed[_beneficiary_id_hash];
        uint256 remaining = currentQuota > consumed ? currentQuota - consumed : 0;

        // check fraud score
        if (_ai_fraud_score > FRAUD_SCORE_THRESHOLD) {
             emit FraudAlert(
                _beneficiary_id_hash, 
                _shop_id, 
                _ai_fraud_score, 
                "High Fraud Score", 
                block.timestamp
            );
            return;
        }

        // check quota
        if (_quantity > remaining) {
             emit QuotaExceeded(_beneficiary_id_hash, _quantity, remaining);
             // We allow recording the attempt but mark it as failed verification/rejected in logic if needed.
             // For strict enforcement, we can revert or just emit and return.
             // Requirement says "reject transaction and emit FraudAlert/QuotaExceeded".
             // We will emit and not store the transaction as 'verified'.
             return;
        }

        // Process successful transaction
        beneficiaryMonthlyConsumed[_beneficiary_id_hash] += _quantity;

        Transaction memory newTx = Transaction({
            beneficiary_id_hash: _beneficiary_id_hash,
            shop_id: _shop_id,
            quantity: _quantity,
            timestamp: block.timestamp,
            region: _region,
            ai_fraud_score: _ai_fraud_score,
            verification_status: true
        });

        transactions.push(newTx);

        emit TransactionRecorded(
            _beneficiary_id_hash,
            _shop_id,
            _quantity,
            block.timestamp,
            _ai_fraud_score,
            true
        );
    }

    function getTransactionCount() public view returns (uint256) {
        return transactions.length;
    }

    function getTransaction(uint256 index) public view returns (Transaction memory) {
        return transactions[index];
    }
}
