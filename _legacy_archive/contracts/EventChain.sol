// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title EventChain
 * @dev Universal Verifiable Event Ledger - An append-only event storage contract
 */
contract EventChain {
    // Event structure
    struct Event {
        address actor;          // Wallet address of the event creator
        string eventType;       // Type of event (e.g., "document", "certificate")
        string metadataHash;    // IPFS hash of event metadata
        uint256 timestamp;      // Block timestamp when event was added
    }

    // Array to store all events
    Event[] private events;

    // Mapping to track event indices by hash for quick verification
    mapping(string => uint256) private hashToIndex;
    mapping(string => bool) private hashExists;

    // Event emitted when a new event is added
    event EventAdded(
        uint256 indexed index,
        address indexed actor,
        string eventType,
        string metadataHash,
        uint256 timestamp,
        bytes32 indexed eventHash
    );

    /**
     * @dev Add a new event to the ledger
     * @param eventType The type of event
     * @param metadataHash The IPFS hash of the event metadata
     */
    function addEvent(string memory eventType, string memory metadataHash) public {
        require(bytes(metadataHash).length > 0, "Metadata hash cannot be empty");
        require(bytes(eventType).length > 0, "Event type cannot be empty");
        require(!hashExists[metadataHash], "Event with this hash already exists");

        Event memory newEvent = Event({
            actor: msg.sender,
            eventType: eventType,
            metadataHash: metadataHash,
            timestamp: block.timestamp
        });

        uint256 index = events.length;
        events.push(newEvent);
        hashToIndex[metadataHash] = index;
        hashExists[metadataHash] = true;

        // Calculate event hash for indexing
        bytes32 eventHash = keccak256(abi.encodePacked(
            msg.sender,
            eventType,
            metadataHash,
            block.timestamp,
            index
        ));

        emit EventAdded(
            index,
            msg.sender,
            eventType,
            metadataHash,
            block.timestamp,
            eventHash
        );
    }

    /**
     * @dev Get a single event by index
     * @param index The index of the event
     * @return actor The wallet address of the event creator
     * @return eventType The type of event
     * @return metadataHash The IPFS hash
     * @return timestamp The block timestamp
     */
    function getEvent(uint256 index) public view returns (
        address actor,
        string memory eventType,
        string memory metadataHash,
        uint256 timestamp
    ) {
        require(index < events.length, "Event index out of bounds");
        Event memory eventItem = events[index];
        return (
            eventItem.actor,
            eventItem.eventType,
            eventItem.metadataHash,
            eventItem.timestamp
        );
    }

    /**
     * @dev Get all events
     * @return actors Array of actor addresses
     * @return eventTypes Array of event types
     * @return metadataHashes Array of IPFS hashes
     * @return timestamps Array of timestamps
     */
    function getAllEvents() public view returns (
        address[] memory actors,
        string[] memory eventTypes,
        string[] memory metadataHashes,
        uint256[] memory timestamps
    ) {
        uint256 length = events.length;
        actors = new address[](length);
        eventTypes = new string[](length);
        metadataHashes = new string[](length);
        timestamps = new uint256[](length);

        for (uint256 i = 0; i < length; i++) {
            actors[i] = events[i].actor;
            eventTypes[i] = events[i].eventType;
            metadataHashes[i] = events[i].metadataHash;
            timestamps[i] = events[i].timestamp;
        }

        return (actors, eventTypes, metadataHashes, timestamps);
    }

    /**
     * @dev Get the total number of events
     * @return The count of events
     */
    function getEventCount() public view returns (uint256) {
        return events.length;
    }

    /**
     * @dev Verify if a metadata hash exists in the ledger
     * @param metadataHash The IPFS hash to verify
     * @return exists True if hash exists, false otherwise
     * @return index The index of the event if it exists
     */
    function verifyHash(string memory metadataHash) public view returns (bool exists, uint256 index) {
        exists = hashExists[metadataHash];
        if (exists) {
            index = hashToIndex[metadataHash];
        }
        return (exists, index);
    }
}

