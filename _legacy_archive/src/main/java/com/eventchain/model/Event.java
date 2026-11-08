package com.eventchain.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigInteger;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Event {
    private BigInteger index;
    private String actor;
    private String eventType;
    private String metadataHash;
    private BigInteger timestamp;
    private String transactionHash;
}

