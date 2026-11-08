package com.eventchain.service;

import io.ipfs.api.IPFS;
import io.ipfs.api.MerkleNode;
import io.ipfs.api.NamedStreamable;
import io.ipfs.multihash.Multihash;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import java.io.IOException;
import java.util.List;

@Slf4j
@Service
public class IpfsService {

    @Value("${ipfs.host:127.0.0.1}")
    private String ipfsHost;

    @Value("${ipfs.port:5001}")
    private int ipfsPort;

    @Value("${ipfs.protocol:http}")
    private String ipfsProtocol;

    private IPFS ipfs;

    @PostConstruct
    public void init() {
        try {
            String ipfsUrl = ipfsProtocol + "://" + ipfsHost + ":" + ipfsPort;
            log.info("Initializing IPFS connection to: {}", ipfsUrl);
            ipfs = new IPFS(ipfsHost, ipfsPort);
            log.info("IPFS connection established");
        } catch (Exception e) {
            log.warn("Failed to initialize IPFS connection: {}", e.getMessage());
            log.warn("IPFS features will not be available. Please ensure IPFS daemon is running.");
            log.warn("To start IPFS: Run 'ipfs daemon' in a terminal");
            ipfs = null; // Set to null so we can check later
        }
    }
    
    private void checkIpfsConnection() {
        if (ipfs == null) {
            throw new IllegalStateException(
                "IPFS is not available. Please ensure IPFS daemon is running on " + 
                ipfsProtocol + "://" + ipfsHost + ":" + ipfsPort + 
                ". Start it with: ipfs daemon"
            );
        }
    }

    /**
     * Upload metadata to IPFS and return the hash
     */
    public String uploadToIpfs(String metadata) throws IOException {
        checkIpfsConnection();
        log.info("Uploading metadata to IPFS");

        try {
            NamedStreamable.ByteArrayWrapper file = new NamedStreamable.ByteArrayWrapper(
                    metadata.getBytes("UTF-8")
            );
            
            List<MerkleNode> result = ipfs.add(file);
            
            if (result.isEmpty()) {
                throw new IOException("IPFS upload returned empty result");
            }

            String hash = result.get(0).hash.toBase58();
            log.info("Metadata uploaded to IPFS with hash: {}", hash);
            return hash;
        } catch (Exception e) {
            log.error("Error uploading to IPFS", e);
            throw new IOException("Failed to upload to IPFS: " + e.getMessage(), e);
        }
    }

    /**
     * Retrieve metadata from IPFS using hash
     */
    public String getFromIpfs(String hash) throws IOException {
        checkIpfsConnection();
        log.info("Retrieving metadata from IPFS with hash: {}", hash);

        try {
            Multihash multihash = Multihash.fromBase58(hash);
            byte[] content = ipfs.cat(multihash);
            return new String(content, "UTF-8");
        } catch (Exception e) {
            log.error("Error retrieving from IPFS", e);
            throw new IOException("Failed to retrieve from IPFS: " + e.getMessage(), e);
        }
    }

    /**
     * Verify if content exists in IPFS
     */
    public boolean verifyIpfsHash(String hash) {
        checkIpfsConnection();
        try {
            Multihash multihash = Multihash.fromBase58(hash);
            ipfs.cat(multihash);
            return true;
        } catch (Exception e) {
            log.warn("IPFS hash verification failed: {}", e.getMessage());
            return false;
        }
    }
}

