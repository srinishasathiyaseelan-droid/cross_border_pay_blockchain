// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title RiskAdaptiveCrossBorderSettlement
 * @dev Academic Prototype: Risk-Adaptive Smart Contract Settlement for SME Cross-Border Payments
 *
 * REFERENCE DESIGN ONLY. This contract has never been deployed; the Flask app simulates its rules in Python
 * (crosspay/policy/engine.py) and the address shown in the UI is labelled "simulated".
 *
 * Hardening (Nov 2026, audit H7):
 *  - the risk input can only be submitted by the risk oracle (the CrossPay backend's key) via onlyOracle,
 *    so a sender can no longer pass its own RiskLevel.LOW;
 *  - only keccak256(governmentId) is stored on chain, never the raw ID.
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
        bytes32 governmentIdHash; // keccak256 of the ID, computed off-chain; the raw ID never goes on chain
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
    address public riskOracle;
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
    modifier onlyOracle() {
        require(msg.sender == riskOracle, "Only the risk oracle can submit risk assessments");
        _;
    }

    modifier onlyAdmin() {
        require(msg.sender == complianceAdmin, "Only compliance admin can execute this action");
        _;
    }

    modifier onlyVerifiedKYC(address _sme) {
        require(smeRegistry[_sme].isKYCVerified, "KYC Verification required before payment execution");
        _;
    }

    constructor(address _riskOracle) {
        complianceAdmin = msg.sender;
        riskOracle = _riskOracle;
    }

    function setRiskOracle(address _riskOracle) external onlyAdmin {
        riskOracle = _riskOracle;
    }

    // --- KYC Management ---
    function registerKYC(
        address _sme,
        string memory _businessName,
        string memory _country,
        bytes32 _govIdHash,
        bool _verified
    ) external onlyAdmin {
        smeRegistry[_sme] = SMECustomer({
            businessName: _businessName,
            country: _country,
            governmentIdHash: _govIdHash,
            isKYCVerified: _verified,
            registeredTimestamp: block.timestamp
        });
        emit KYCRegistered(_sme, _businessName, _verified);
    }

    // --- Core Risk-Adaptive Settlement Engine ---
    function processSettlement(
        address _sme,
        string memory _txId,
        string memory _receiverBusiness,
        string memory _senderCountry,
        string memory _receiverCountry,
        string memory _currency,
        uint256 _amount,
        RiskLevel _risk,
        uint256 _riskScorePercentage
    ) external onlyOracle onlyVerifiedKYC(_sme) returns (SettlementStatus) {
        require(bytes(_txId).length > 0, "Invalid transaction ID");
        require(_amount > 0, "Amount must be greater than zero");

        totalTransactionsCount++;
        emit RiskEvaluated(_txId, _risk, _riskScorePercentage);

        // Risk-Adaptive Decision Logic
        if (_risk == RiskLevel.LOW) {
            // LOW RISK: Auto-Approve and record on-chain
            bytes32 txHash = keccak256(abi.encodePacked(_txId, _sme, _amount, block.timestamp, block.number));
            
            ledger[_txId] = CrossBorderTransaction({
                transactionId: _txId,
                senderAddress: _sme,
                senderBusiness: smeRegistry[_sme].businessName,
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
                senderAddress: _sme,
                senderBusiness: smeRegistry[_sme].businessName,
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
                senderAddress: _sme,
                senderBusiness: smeRegistry[_sme].businessName,
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
