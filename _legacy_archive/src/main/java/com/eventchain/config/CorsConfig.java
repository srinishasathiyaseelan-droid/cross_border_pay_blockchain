package com.eventchain.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;

import java.util.Arrays;
import java.util.List;

@Configuration
public class CorsConfig {

    @Bean
    public CorsFilter corsFilter() {
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        CorsConfiguration config = new CorsConfiguration();
        
        // Allow all origins for development
        // Note: Using setAllowedOrigins with "*" doesn't work with credentials
        // For development, we allow all origins without credentials restriction
        config.addAllowedOriginPattern("*");
        
        // Allow credentials (set to false when using wildcard pattern)
        // For development with wildcard, credentials are typically not needed
        config.setAllowCredentials(false);
        
        // Allow all headers
        config.setAllowedHeaders(Arrays.asList("*"));
        
        // Allow all HTTP methods
        config.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"));
        
        // Exposed headers
        config.setExposedHeaders(Arrays.asList("Content-Type", "Authorization"));
        
        // Cache preflight requests for 1 hour
        config.setMaxAge(3600L);
        
        // Register CORS configuration for all paths
        source.registerCorsConfiguration("/**", config);
        
        return new CorsFilter(source);
    }
}
