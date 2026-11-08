package com.eventchain.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigInteger;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class EventResponse {
    private BigInteger index;
    private String actor;
    private String eventType;
    private String metadataHash;
    private BigInteger timestamp;
    private String transactionHash;
    private String proofJson;
    private String qrCodeBase64;
}

