# CORS Configuration for Backend

If you encounter CORS errors when the frontend tries to connect to the backend, you'll need to add CORS configuration to your Spring Boot application.

## Option 1: Add CORS Configuration Class

Create a new file in your backend: `src/main/java/com/eventchain/config/CorsConfig.java`

```java
package com.eventchain.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;

@Configuration
public class CorsConfig {

    @Bean
    public CorsFilter corsFilter() {
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowCredentials(true);
        config.addAllowedOriginPattern("*"); // In production, replace with specific frontend URL
        config.addAllowedHeader("*");
        config.addAllowedMethod("*");
        source.registerCorsConfiguration("/**", config);
        return new CorsFilter(source);
    }
}
```

## Option 2: Add @CrossOrigin to Controller

Alternatively, add `@CrossOrigin(origins = "*")` to your `EventController` class:

```java
@CrossOrigin(origins = "*")
@RestController
@RequestMapping("/events")
public class EventController {
    // ... existing code
}
```

## Production Note

For production, replace `"*"` with your actual frontend domain:
- `config.addAllowedOrigin("https://yourdomain.com")`
- Or `@CrossOrigin(origins = "https://yourdomain.com")`
