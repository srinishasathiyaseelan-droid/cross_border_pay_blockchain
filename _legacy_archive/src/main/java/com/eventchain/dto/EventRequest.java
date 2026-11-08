package com.eventchain.dto;

import lombok.Data;
import jakarta.validation.constraints.NotBlank;

@Data
public class EventRequest {
    @NotBlank(message = "Event type is required")
    private String eventType;
    
    @NotBlank(message = "Metadata is required")
    private String metadata;
}

