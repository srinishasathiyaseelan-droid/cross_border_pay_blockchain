package com.eventchain.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Controller to handle favicon requests gracefully
 * Prevents 404 errors in logs when browsers request favicon.ico
 */
@RestController
public class FaviconController {

    @GetMapping("favicon.ico")
    public ResponseEntity<Void> favicon() {
        // Return 204 No Content instead of 404
        // This prevents the error from appearing in logs
        return ResponseEntity.status(HttpStatus.NO_CONTENT).build();
    }
}
