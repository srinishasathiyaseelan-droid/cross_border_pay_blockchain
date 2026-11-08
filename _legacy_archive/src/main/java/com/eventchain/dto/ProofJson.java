package com.eventchain.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProofJson {
    @JsonProperty("eventHash")
    private String eventHash;
    
    @JsonProperty("metadataHash")
    private String metadataHash;
    
    @JsonProperty("actor")
    private String actor;
    
    @JsonProperty("timestamp")
    private String timestamp;
    
    @JsonProperty("txHash")
    private String txHash;
}

