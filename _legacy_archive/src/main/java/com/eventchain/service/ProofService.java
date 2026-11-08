package com.eventchain.service;

import com.eventchain.dto.ProofJson;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigInteger;
import java.time.Instant;

@Slf4j
@Service
public class ProofService {

    private final ObjectMapper objectMapper;

    public ProofService() {
        this.objectMapper = new ObjectMapper();
        this.objectMapper.registerModule(new JavaTimeModule());
        this.objectMapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
    }

    /**
     * Generate proof JSON for an event
     */
    public ProofJson generateProofJson(String eventHash, String metadataHash, String actor, BigInteger timestamp, String txHash) {
        log.info("Generating proof JSON for event: {}", eventHash);

        Instant instant = Instant.ofEpochSecond(timestamp.longValue());
        String timestampString = instant.toString();

        return ProofJson.builder()
                .eventHash(eventHash)
                .metadataHash(metadataHash)
                .actor(actor)
                .timestamp(timestampString)
                .txHash(txHash)
                .build();
    }

    /**
     * Convert proof JSON to string
     */
    public String proofJsonToString(ProofJson proofJson) {
        try {
            return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(proofJson);
        } catch (Exception e) {
            log.error("Error converting proof JSON to string", e);
            throw new RuntimeException("Failed to serialize proof JSON", e);
        }
    }
}

