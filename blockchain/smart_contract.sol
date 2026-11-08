// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title RiskAdaptiveCrossBorderSettlement
 * @dev Academic Prototype: Risk-Adaptive Smart Contract Settlement for SME Cross-Border Payments
 * 
 * Flow:
 * 1. KYC verification check for sender and receiver SMEs
 * 2. Risk score input from Off-Chain Random Forest Machine Learning Model
 * 3. Autonomous Risk-Based Decision:
 *    - LOW RISK    -> APPROVE & EXECUTE ON-CHAIN SETTLEMENT
 *    - MEDIUM RISK -> HOLD IN COMPLIANCE ESCROW (Awaiting Additional Verification)
 *    - HIGH RISK   -> BLOCK TRANSACTION & PREVENT SETTLEMENT
 */
contract RiskAdaptiveCrossBorderSettlement {
    
    // --- State Definitions ---
    enum RiskLevel { LOW, MEDIUM, HIGH }
    enum SettlementStatus { PENDING, APPROVED, HELD_IN_ESCROW, BLOCKED, SETTLED }

    struct SMECustomer {
        string businessName;
        string country;
        string governmentId;
        bool isKYCVerified;
        uint256 registeredTimestamp;
    }

    struct CrossBorderTransaction {
        string transactionId;
        address senderAddress;
        string senderBusiness;
        string receiverBusiness;
        string senderCountry;
        string receiverCountry;
        string currency;
        uint256 amount;
        RiskLevel risk;
        uint256 riskScorePercentage;
        SettlementStatus status;
        bytes32 blockchainTxHash;
        uint256 timestamp;
    }

    address public complianceAdmin;
    uint256 public totalTransactionsCount;
    uint256 public approvedCount;
    uint256 public heldCount;
    uint256 public blockedCount;

    mapping(address => SMECustomer) public smeRegistry;
    mapping(string => CrossBorderTransaction) public ledger;
    string[] public transactionHistory;

    // --- Events ---
    event KYCRegistered(address indexed smeAddress, string businessName, bool isVerified);
    event RiskEvaluated(string indexed transactionId, RiskLevel risk, uint256 riskScore);
    event PaymentApproved(string indexed transactionId, uint256 amount, string currency, bytes32 txHash);
    event PaymentHeld(string indexed transactionId, string reason);
    event PaymentBlocked(string indexed transactionId, string reason);
    event HoldReleased(string indexed transactionId, bytes32 newTxHash);

    // --- Modifiers ---
    modifier onlyAdmin() {
        require(msg.sender == complianceAdmin, "Only compliance admin can execute this action");
        _;
    }

    modifier onlyVerifiedKYC(address _sme) {
        require(smeRegistry[_sme].isKYCVerified, "KYC Verification required before payment execution");
        _;
    }

    constructor() {
        complianceAdmin = msg.sender;
    }

    // --- KYC Management ---
    function registerKYC(
        address _sme,
        string memory _businessName,
        string memory _country,
        string memory _govId,
        bool _verified
    ) external onlyAdmin {
        smeRegistry[_sme] = SMECustomer({
            businessName: _businessName,
            country: _country,
            governmentId: _govId,
            isKYCVerified: _verified,
            registeredTimestamp: block.timestamp
        });
        emit KYCRegistered(_sme, _businessName, _verified);
    }

    // --- Core Risk-Adaptive Settlement Engine ---
    function processSettlement(
        string memory _txId,
        string memory _receiverBusiness,
        string memory _senderCountry,
        string memory _receiverCountry,
        string memory _currency,
        uint256 _amount,
        RiskLevel _risk,
        uint256 _riskScorePercentage
    ) external onlyVerifiedKYC(msg.sender) returns (SettlementStatus) {
        require(bytes(_txId).length > 0, "Invalid transaction ID");
        require(_amount > 0, "Amount must be greater than zero");

        totalTransactionsCount++;
        emit RiskEvaluated(_txId, _risk, _riskScorePercentage);

        // Risk-Adaptive Decision Logic
        if (_risk == RiskLevel.LOW) {
            // LOW RISK: Auto-Approve and record on-chain
            bytes32 txHash = keccak256(abi.encodePacked(_txId, msg.sender, _amount, block.timestamp, block.number));
            
            ledger[_txId] = CrossBorderTransaction({
                transactionId: _txId,
                senderAddress: msg.sender,
                senderBusiness: smeRegistry[msg.sender].businessName,
                receiverBusiness: _receiverBusiness,
                senderCountry: _senderCountry,
                receiverCountry: _receiverCountry,
                currency: _currency,
                amount: _amount,
                risk: RiskLevel.LOW,
                riskScorePercentage: _riskScorePercentage,
                status: SettlementStatus.SETTLED,
                blockchainTxHash: txHash,
                timestamp: block.timestamp
            });

            transactionHistory.push(_txId);
            approvedCount++;
            emit PaymentApproved(_txId, _amount, _currency, txHash);
            return SettlementStatus.SETTLED;

        } else if (_risk == RiskLevel.MEDIUM) {
            // MEDIUM RISK: Hold in compliance escrow for review
            ledger[_txId] = CrossBorderTransaction({
                transactionId: _txId,
                senderAddress: msg.sender,
                senderBusiness: smeRegistry[msg.sender].businessName,
                receiverBusiness: _receiverBusiness,
                senderCountry: _senderCountry,
                receiverCountry: _receiverCountry,
                currency: _currency,
                amount: _amount,
                risk: RiskLevel.MEDIUM,
                riskScorePercentage: _riskScorePercentage,
                status: SettlementStatus.HELD_IN_ESCROW,
                blockchainTxHash: bytes32(0),
                timestamp: block.timestamp
            });

            transactionHistory.push(_txId);
            heldCount++;
            emit PaymentHeld(_txId, "Transaction placed on hold pending secondary verification");
            return SettlementStatus.HELD_IN_ESCROW;

        } else {
            // HIGH RISK: Block transaction and strictly reject settlement
            ledger[_txId] = CrossBorderTransaction({
                transactionId: _txId,
                senderAddress: msg.sender,
                senderBusiness: smeRegistry[msg.sender].businessName,
                receiverBusiness: _receiverBusiness,
                senderCountry: _senderCountry,
                receiverCountry: _receiverCountry,
                currency: _currency,
                amount: _amount,
                risk: RiskLevel.HIGH,
                riskScorePercentage: _riskScorePercentage,
                status: SettlementStatus.BLOCKED,
                blockchainTxHash: bytes32(0),
                timestamp: block.timestamp
            });

            transactionHistory.push(_txId);
            blockedCount++;
            emit PaymentBlocked(_txId, "Smart Contract Policy: High-risk anomaly detected. Settlement blocked.");
            return SettlementStatus.BLOCKED;
        }
    }

    // --- Admin Release for Held Transactions ---
    function resolveHeldPayment(string memory _txId, bool _approve) external onlyAdmin {
        require(ledger[_txId].status == SettlementStatus.HELD_IN_ESCROW, "Transaction is not held");
        
        if (_approve) {
            bytes32 txHash = keccak256(abi.encodePacked(_txId, msg.sender, ledger[_txId].amount, block.timestamp));
            ledger[_txId].status = SettlementStatus.SETTLED;
            ledger[_txId].blockchainTxHash = txHash;
            approvedCount++;
            heldCount--;
            emit HoldReleased(_txId, txHash);
        } else {
            ledger[_txId].status = SettlementStatus.BLOCKED;
            blockedCount++;
            heldCount--;
            emit PaymentBlocked(_txId, "Compliance admin rejected held payment");
        }
    }

    // --- Read Helpers ---
    function getTransaction(string memory _txId) external view returns (CrossBorderTransaction memory) {
        return ledger[_txId];
    }
}
