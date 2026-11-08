package com.eventchain.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.web3j.protocol.Web3j;
import org.web3j.protocol.http.HttpService;
import org.web3j.crypto.Credentials;
import org.web3j.crypto.Keys;

@Configuration
public class BlockchainConfig {

    @Value("${blockchain.network.url}")
    private String networkUrl;

    @Value("${blockchain.private.key:}")
    private String privateKey;

    @Bean
    public Web3j web3j() {
        return Web3j.build(new HttpService(networkUrl));
    }

    @Bean
    public Credentials credentials() {
        if (privateKey != null && !privateKey.isEmpty()) {
            return Credentials.create(privateKey);
        }
        // Generate a new key pair if no private key is provided (for development only)
        try {
            return Credentials.create(Keys.createEcKeyPair());
        } catch (Exception e) {
            throw new RuntimeException("Failed to create credentials", e);
        }
    }
}

