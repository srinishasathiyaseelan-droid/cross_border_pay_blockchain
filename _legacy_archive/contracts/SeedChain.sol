// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title SeedChain
 * @dev Blockchain-based Agricultural Seed Supply Chain with Digital Certificate Verification
 */
contract SeedChain {

    // ======================== ENUMS ========================

    enum BatchStatus { ACTIVE, EXPIRED, TRANSFERRED }
    enum Role { NONE, PRODUCER, LAB_AUTHORITY, DISTRIBUTOR, RETAILER }

    // ======================== STRUCTS ========================

    struct SeedBatch {
        uint256 batchId;
        string cropType;
        string seedVariety;
        uint256 quantity;          // in grams
        uint256 expiryDate;        // unix timestamp
        string ipfsHash;           // metadata IPFS hash
        string certIPFSHash;       // certificate IPFS hash (empty until certified)
        address ownerAddress;
        uint256 parentBatchId;     // 0 if no parent
        BatchStatus status;
        uint256 createdAt;
    }

    struct Certificate {
        uint256 certId;
        uint256 batchId;
        address issuerAddress;
        string ipfsHash;
        bytes digitalSignature;
        uint256 issuedAt;
        uint256 expiryDate;
        bool isValid;
    }

    // ======================== STATE ========================

    uint256 private batchCounter;
    uint256 private certCounter;

    mapping(uint256 => SeedBatch) public batches;
    mapping(uint256 => Certificate) public certificates;
    mapping(uint256 => uint256[]) public batchChildren;     // parent => children
    mapping(uint256 => uint256) public batchCertificate;    // batchId => certId
    mapping(address => Role) public roles;

    address public admin;

    // ======================== EVENTS ========================

    event BatchCreated(
        uint256 indexed batchId,
        address indexed owner,
        string cropType,
        string seedVariety,
        uint256 quantity,
        uint256 expiryDate,
        string ipfsHash,
        uint256 timestamp
    );

    event CertificateRegistered(
        uint256 indexed certId,
        uint256 indexed batchId,
        address indexed issuer,
        string ipfsHash,
        uint256 expiryDate,
        uint256 timestamp
    );

    event BatchTransferred(
        uint256 indexed batchId,
        address indexed fromOwner,
        address indexed toOwner,
        uint256 timestamp
    );

    event BatchSplit(
        uint256 indexed parentBatchId,
        uint256 indexed childBatchId,
        uint256 childQuantity,
        address indexed owner,
        uint256 timestamp
    );

    // ======================== MODIFIERS ========================

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin");
        _;
    }

    modifier batchExists(uint256 _batchId) {
        require(_batchId > 0 && _batchId <= batchCounter, "Batch does not exist");
        _;
    }

    modifier onlyBatchOwner(uint256 _batchId) {
        require(batches[_batchId].ownerAddress == msg.sender, "Not batch owner");
        _;
    }

    modifier batchActive(uint256 _batchId) {
        require(batches[_batchId].status == BatchStatus.ACTIVE, "Batch not active");
        require(batches[_batchId].expiryDate > block.timestamp, "Batch expired");
        _;
    }

    // ======================== CONSTRUCTOR ========================

    constructor() {
        admin = msg.sender;
        roles[msg.sender] = Role.PRODUCER; // Admin gets producer role by default
    }

    // ======================== ROLE MANAGEMENT ========================

    function assignRole(address _user, Role _role) public onlyAdmin {
        roles[_user] = _role;
    }

    function getRole(address _user) public view returns (Role) {
        return roles[_user];
    }

    // ======================== BATCH FUNCTIONS ========================

    function createBatch(
        string memory _cropType,
        string memory _seedVariety,
        uint256 _quantity,
        uint256 _expiryDate,
        string memory _ipfsHash
    ) public returns (uint256) {
        require(bytes(_cropType).length > 0, "Crop type required");
        require(bytes(_seedVariety).length > 0, "Seed variety required");
        require(_quantity > 0, "Quantity must be positive");
        require(_expiryDate > block.timestamp, "Expiry must be in the future");
        require(bytes(_ipfsHash).length > 0, "IPFS hash required");

        batchCounter++;
        uint256 newBatchId = batchCounter;

        batches[newBatchId] = SeedBatch({
            batchId: newBatchId,
            cropType: _cropType,
            seedVariety: _seedVariety,
            quantity: _quantity,
            expiryDate: _expiryDate,
            ipfsHash: _ipfsHash,
            certIPFSHash: "",
            ownerAddress: msg.sender,
            parentBatchId: 0,
            status: BatchStatus.ACTIVE,
            createdAt: block.timestamp
        });

        emit BatchCreated(
            newBatchId,
            msg.sender,
            _cropType,
            _seedVariety,
            _quantity,
            _expiryDate,
            _ipfsHash,
            block.timestamp
        );

        return newBatchId;
    }

    function getBatch(uint256 _batchId) public view batchExists(_batchId) returns (SeedBatch memory) {
        return batches[_batchId];
    }

    function getBatchCount() public view returns (uint256) {
        return batchCounter;
    }

    // ======================== TRANSFER ========================

    function transferBatch(
        uint256 _batchId,
        address _newOwner
    ) public batchExists(_batchId) onlyBatchOwner(_batchId) batchActive(_batchId) {
        require(_newOwner != address(0), "Invalid address");
        require(_newOwner != msg.sender, "Cannot transfer to self");

        address previousOwner = batches[_batchId].ownerAddress;
        batches[_batchId].ownerAddress = _newOwner;
        // Status remains ACTIVE so new owner can operate on the batch

        emit BatchTransferred(
            _batchId,
            previousOwner,
            _newOwner,
            block.timestamp
        );
    }

    // ======================== SPLIT ========================

    function splitBatch(
        uint256 _batchId,
        uint256 _splitQuantity,
        string memory _newIpfsHash
    ) public batchExists(_batchId) onlyBatchOwner(_batchId) batchActive(_batchId) returns (uint256) {
        SeedBatch storage parentBatch = batches[_batchId];

        require(_splitQuantity > 0, "Split quantity must be positive");
        require(_splitQuantity < parentBatch.quantity, "Split qty must be less than parent");
        require(bytes(_newIpfsHash).length > 0, "IPFS hash required");

        // Reduce parent quantity
        parentBatch.quantity -= _splitQuantity;

        // Create child batch
        batchCounter++;
        uint256 childBatchId = batchCounter;

        batches[childBatchId] = SeedBatch({
            batchId: childBatchId,
            cropType: parentBatch.cropType,
            seedVariety: parentBatch.seedVariety,
            quantity: _splitQuantity,
            expiryDate: parentBatch.expiryDate,
            ipfsHash: _newIpfsHash,
            certIPFSHash: parentBatch.certIPFSHash,
            ownerAddress: msg.sender,
            parentBatchId: _batchId,
            status: BatchStatus.ACTIVE,
            createdAt: block.timestamp
        });

        // Record parent-child linkage
        batchChildren[_batchId].push(childBatchId);

        emit BatchSplit(
            _batchId,
            childBatchId,
            _splitQuantity,
            msg.sender,
            block.timestamp
        );

        return childBatchId;
    }

    function getChildBatches(uint256 _batchId) public view batchExists(_batchId) returns (uint256[] memory) {
        return batchChildren[_batchId];
    }

    // ======================== CERTIFICATE ========================

    function registerCertificate(
        uint256 _batchId,
        string memory _ipfsHash,
        bytes memory _digitalSignature,
        uint256 _expiryDate
    ) public batchExists(_batchId) returns (uint256) {
        require(bytes(_ipfsHash).length > 0, "Certificate IPFS hash required");
        require(_digitalSignature.length > 0, "Digital signature required");
        require(_expiryDate > block.timestamp, "Certificate expiry must be in the future");

        certCounter++;
        uint256 newCertId = certCounter;

        certificates[newCertId] = Certificate({
            certId: newCertId,
            batchId: _batchId,
            issuerAddress: msg.sender,
            ipfsHash: _ipfsHash,
            digitalSignature: _digitalSignature,
            issuedAt: block.timestamp,
            expiryDate: _expiryDate,
            isValid: true
        });

        // Link certificate to batch
        batches[_batchId].certIPFSHash = _ipfsHash;
        batchCertificate[_batchId] = newCertId;

        emit CertificateRegistered(
            newCertId,
            _batchId,
            msg.sender,
            _ipfsHash,
            _expiryDate,
            block.timestamp
        );

        return newCertId;
    }

    function getCertificate(uint256 _certId) public view returns (Certificate memory) {
        require(_certId > 0 && _certId <= certCounter, "Certificate does not exist");
        return certificates[_certId];
    }

    function getCertificateByBatch(uint256 _batchId) public view batchExists(_batchId) returns (Certificate memory) {
        uint256 certId = batchCertificate[_batchId];
        require(certId > 0, "No certificate for this batch");
        return certificates[certId];
    }

    function getCertificateCount() public view returns (uint256) {
        return certCounter;
    }

    function verifyCertificate(uint256 _certId) public view returns (
        bool isValid,
        bool isExpired,
        address issuer,
        uint256 batchId,
        string memory ipfsHash,
        bytes memory signature
    ) {
        require(_certId > 0 && _certId <= certCounter, "Certificate does not exist");
        Certificate memory cert = certificates[_certId];

        isExpired = cert.expiryDate <= block.timestamp;
        isValid = cert.isValid && !isExpired;
        issuer = cert.issuerAddress;
        batchId = cert.batchId;
        ipfsHash = cert.ipfsHash;
        signature = cert.digitalSignature;
    }

    function revokeCertificate(uint256 _certId) public {
        require(_certId > 0 && _certId <= certCounter, "Certificate does not exist");
        require(certificates[_certId].issuerAddress == msg.sender || msg.sender == admin, "Not authorized");
        certificates[_certId].isValid = false;
    }
}
