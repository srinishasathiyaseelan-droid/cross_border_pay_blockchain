package com.eventchain.controller;

import com.eventchain.dto.EventRequest;
import com.eventchain.dto.EventResponse;
import com.eventchain.dto.ProofJson;
import com.eventchain.dto.VerifyResponse;
import com.eventchain.model.Event;
import com.eventchain.service.BlockchainService;
import com.eventchain.service.IpfsService;
import com.eventchain.service.ProofService;
import com.eventchain.service.QRCodeService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.Valid;
import java.math.BigInteger;
import java.security.MessageDigest;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@RestController
@RequestMapping("/events")
@CrossOrigin(origins = "*")
public class EventController {

    private final BlockchainService blockchainService;
    private final IpfsService ipfsService;
    private final ProofService proofService;
    private final QRCodeService qrCodeService;

    @Autowired
    public EventController(BlockchainService blockchainService,
                          IpfsService ipfsService,
                          ProofService proofService,
                          QRCodeService qrCodeService) {
        this.blockchainService = blockchainService;
        this.ipfsService = ipfsService;
        this.proofService = proofService;
        this.qrCodeService = qrCodeService;
    }

    /**
     * POST /events - Upload event details to IPFS, get hash, call smart contract to store event
     */
    @PostMapping
    public ResponseEntity<EventResponse> createEvent(@Valid @RequestBody EventRequest request) {
        try {
            log.info("Creating new event: type={}", request.getEventType());

            // Step 1: Upload metadata to IPFS
            String ipfsHash = ipfsService.uploadToIpfs(request.getMetadata());
            log.info("Metadata uploaded to IPFS with hash: {}", ipfsHash);

            // Step 2: Get current event count (to determine new event index)
            BigInteger eventCountBefore = blockchainService.getEventCount();
            log.info("Current event count: {}", eventCountBefore);

            // Step 3: Add event to blockchain
            String txHash = blockchainService.addEvent(request.getEventType(), ipfsHash);
            log.info("Event added to blockchain with transaction: {}", txHash);

            // Step 4: Wait for transaction to be mined
            blockchainService.waitForTransactionReceipt(txHash, 30); // Wait up to 30 seconds
            log.info("Transaction confirmed");

            // Step 5: Get new event count and verify it increased
            BigInteger eventCountAfter = blockchainService.getEventCount();
            log.info("New event count: {}", eventCountAfter);
            
            if (eventCountAfter.compareTo(eventCountBefore) <= 0) {
                throw new RuntimeException("Event count did not increase after transaction");
            }

            // Step 6: Get the new event by index (last event = count - 1)
            BigInteger newEventIndex = eventCountAfter.subtract(BigInteger.ONE);
            Event newEvent = blockchainService.getEvent(newEventIndex);
            
            // Verify it's the correct event
            if (!ipfsHash.equals(newEvent.getMetadataHash())) {
                // If not found at expected index, search all events
                log.warn("Event not at expected index, searching all events");
                List<Event> allEvents = blockchainService.getAllEvents();
                newEvent = allEvents.stream()
                        .filter(e -> ipfsHash.equals(e.getMetadataHash()))
                        .findFirst()
                        .orElseThrow(() -> new RuntimeException("Event not found after creation"));
            }

            newEvent.setTransactionHash(txHash);

            // Step 5: Generate event hash
            String eventHash = generateEventHash(newEvent);

            // Step 6: Generate proof JSON
            ProofJson proofJson = proofService.generateProofJson(
                    eventHash,
                    newEvent.getMetadataHash(),
                    newEvent.getActor(),
                    newEvent.getTimestamp(),
                    txHash
            );

            // Step 7: Generate QR code
            String qrCodeBase64 = qrCodeService.generateQRCodeBase64(proofService.proofJsonToString(proofJson));

            // Step 8: Build response
            EventResponse response = EventResponse.builder()
                    .index(newEvent.getIndex())
                    .actor(newEvent.getActor())
                    .eventType(newEvent.getEventType())
                    .metadataHash(newEvent.getMetadataHash())
                    .timestamp(newEvent.getTimestamp())
                    .transactionHash(newEvent.getTransactionHash())
                    .proofJson(proofService.proofJsonToString(proofJson))
                    .qrCodeBase64(qrCodeBase64)
                    .build();

            return ResponseEntity.status(HttpStatus.CREATED).body(response);

        } catch (IllegalStateException e) {
            if (e.getMessage() != null && e.getMessage().contains("Blockchain contract address")) {
                log.warn("Blockchain not configured. Cannot create event. Configure blockchain.contract.address in application.properties to enable blockchain features.");
                throw new RuntimeException("Blockchain not configured. Please configure blockchain.contract.address in application.properties", e);
            }
            log.error("Error creating event", e);
            throw new RuntimeException("Failed to create event: " + e.getMessage(), e);
        } catch (Exception e) {
            log.error("Error creating event", e);
            throw new RuntimeException("Failed to create event: " + e.getMessage(), e);
        }
    }

    /**
     * GET /events - Fetch all events from blockchain
     */
    @GetMapping
    public ResponseEntity<List<EventResponse>> getAllEvents() {
        try {
            log.info("Fetching all events");

            List<Event> events = blockchainService.getAllEvents();

            List<EventResponse> responses = events.stream()
                    .map(event -> {
                        try {
                            String eventHash = generateEventHash(event);
                            ProofJson proofJson = proofService.generateProofJson(
                                    eventHash,
                                    event.getMetadataHash(),
                                    event.getActor(),
                                    event.getTimestamp(),
                                    event.getTransactionHash() != null ? event.getTransactionHash() : ""
                            );
                            String qrCodeBase64 = qrCodeService.generateQRCodeBase64(
                                    proofService.proofJsonToString(proofJson)
                            );

                            return EventResponse.builder()
                                    .index(event.getIndex())
                                    .actor(event.getActor())
                                    .eventType(event.getEventType())
                                    .metadataHash(event.getMetadataHash())
                                    .timestamp(event.getTimestamp())
                                    .transactionHash(event.getTransactionHash())
                                    .proofJson(proofService.proofJsonToString(proofJson))
                                    .qrCodeBase64(qrCodeBase64)
                                    .build();
                        } catch (Exception e) {
                            log.error("Error processing event {}", event.getIndex(), e);
                            return null;
                        }
                    })
                    .filter(response -> response != null)
                    .collect(Collectors.toList());

            return ResponseEntity.ok(responses);

        } catch (IllegalStateException e) {
            // Blockchain not configured - return empty list instead of error
            if (e.getMessage() != null && e.getMessage().contains("Blockchain contract address")) {
                log.debug("Blockchain not configured. Returning empty event list.");
                return ResponseEntity.ok(List.of());
            }
            log.error("Error fetching events", e);
            throw new RuntimeException("Failed to fetch events: " + e.getMessage(), e);
        } catch (Exception e) {
            log.error("Error fetching events", e);
            throw new RuntimeException("Failed to fetch events: " + e.getMessage(), e);
        }
    }

    /**
     * GET /events/{id} - Fetch single event by index
     */
    @GetMapping("/{id}")
    public ResponseEntity<EventResponse> getEventById(@PathVariable("id") BigInteger id) {
        try {
            log.info("Fetching event at index: {}", id);

            Event event = blockchainService.getEvent(id);

            String eventHash = generateEventHash(event);
            ProofJson proofJson = proofService.generateProofJson(
                    eventHash,
                    event.getMetadataHash(),
                    event.getActor(),
                    event.getTimestamp(),
                    event.getTransactionHash() != null ? event.getTransactionHash() : ""
            );
            String qrCodeBase64 = qrCodeService.generateQRCodeBase64(
                    proofService.proofJsonToString(proofJson)
            );

            EventResponse response = EventResponse.builder()
                    .index(event.getIndex())
                    .actor(event.getActor())
                    .eventType(event.getEventType())
                    .metadataHash(event.getMetadataHash())
                    .timestamp(event.getTimestamp())
                    .transactionHash(event.getTransactionHash())
                    .proofJson(proofService.proofJsonToString(proofJson))
                    .qrCodeBase64(qrCodeBase64)
                    .build();

            return ResponseEntity.ok(response);

        } catch (IllegalStateException e) {
            if (e.getMessage() != null && e.getMessage().contains("Blockchain contract address")) {
                log.debug("Blockchain not configured. Cannot fetch event.");
                return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                        .body(null);
            }
            log.error("Error fetching event {}", id, e);
            throw new RuntimeException("Failed to fetch event: " + e.getMessage(), e);
        } catch (Exception e) {
            log.error("Error fetching event {}", id, e);
            throw new RuntimeException("Failed to fetch event: " + e.getMessage(), e);
        }
    }

    /**
     * GET /verify/{hash} - Verify if a given event hash exists on-chain
     */
    @GetMapping("/verify/{hash}")
    public ResponseEntity<VerifyResponse> verifyHash(@PathVariable("hash") String hash) {
        try {
            log.info("Verifying hash: {}", hash);

            boolean exists = blockchainService.verifyHash(hash);

            VerifyResponse response = VerifyResponse.builder()
                    .exists(exists)
                    .message(exists ? "Hash verified and exists on-chain" : "Hash not found on-chain")
                    .build();

            if (exists) {
                // Get all events to find the index
                List<Event> events = blockchainService.getAllEvents();
                Event foundEvent = events.stream()
                        .filter(e -> hash.equals(e.getMetadataHash()))
                        .findFirst()
                        .orElse(null);
                if (foundEvent != null) {
                    response.setIndex(foundEvent.getIndex());
                }
            }

            return ResponseEntity.ok(response);

        } catch (IllegalStateException e) {
            if (e.getMessage() != null && e.getMessage().contains("Blockchain contract address")) {
                log.debug("Blockchain not configured. Cannot verify hash.");
                VerifyResponse response = VerifyResponse.builder()
                        .exists(false)
                        .message("Blockchain not configured. Please configure blockchain.contract.address in application.properties")
                        .build();
                return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(response);
            }
            log.error("Error verifying hash {}", hash, e);
            throw new RuntimeException("Failed to verify hash: " + e.getMessage(), e);
        } catch (Exception e) {
            log.error("Error verifying hash {}", hash, e);
            throw new RuntimeException("Failed to verify hash: " + e.getMessage(), e);
        }
    }

    /**
     * Generate a unique hash for an event
     */
    private String generateEventHash(Event event) {
        try {
            String data = event.getActor() + 
                         event.getEventType() + 
                         event.getMetadataHash() + 
                         event.getTimestamp().toString() + 
                         event.getIndex().toString();
            
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hashBytes = digest.digest(data.getBytes("UTF-8"));
            
            StringBuilder hexString = new StringBuilder("0x");
            for (byte b : hashBytes) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) {
                    hexString.append('0');
                }
                hexString.append(hex);
            }
            
            return hexString.toString();
        } catch (Exception e) {
            log.error("Error generating event hash", e);
            throw new RuntimeException("Failed to generate event hash", e);
        }
    }
}

