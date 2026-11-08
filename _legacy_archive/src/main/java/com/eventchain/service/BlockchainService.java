package com.eventchain.service;

import com.eventchain.model.Event;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.web3j.abi.FunctionEncoder;
import org.web3j.abi.FunctionReturnDecoder;
import org.web3j.abi.TypeReference;
import org.web3j.abi.datatypes.*;
import org.web3j.abi.datatypes.generated.Uint256;
import org.web3j.crypto.Credentials;
import org.web3j.protocol.Web3j;
import org.web3j.protocol.core.DefaultBlockParameterName;
import org.web3j.protocol.core.methods.request.Transaction;
import org.web3j.protocol.core.methods.response.*;
import org.web3j.tx.gas.DefaultGasProvider;

import java.io.IOException;
import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

@Slf4j
@Service
public class BlockchainService {

    private final Web3j web3j;
    private final Credentials credentials;
    private final String contractAddress;
    private final BigInteger gasLimit;

    public BlockchainService(Web3j web3j, Credentials credentials, 
                           @Value("${blockchain.contract.address:}") String contractAddress,
                           @Value("${blockchain.gas.limit:3000000}") BigInteger gasLimit) {
        this.web3j = web3j;
        this.credentials = credentials;
        this.contractAddress = contractAddress;
        this.gasLimit = gasLimit;
        if (contractAddress == null || contractAddress.isEmpty()) {
            log.warn("Blockchain contract address is not configured. Blockchain features will not be available.");
            log.warn("Please configure 'blockchain.contract.address' in application.properties");
        }
        log.info("Gas limit configured: {}", gasLimit);
    }
    
    private void checkContractAddress() {
        if (contractAddress == null || contractAddress.isEmpty()) {
            throw new IllegalStateException("Blockchain contract address must be configured in application.properties");
        }
    }

    /**
     * Add an event to the blockchain
     */
    public String addEvent(String eventType, String metadataHash) throws Exception {
        checkContractAddress();
        log.info("Adding event to blockchain: type={}, hash={}", eventType, metadataHash);
        log.info("Using contract address: {}", contractAddress);
        log.info("Using account address: {}", credentials.getAddress());

        // Check account balance
        EthGetBalance balanceResponse = web3j.ethGetBalance(
                credentials.getAddress(), DefaultBlockParameterName.LATEST).send();
        
        if (balanceResponse.hasError()) {
            log.warn("Failed to get account balance: {}", balanceResponse.getError().getMessage());
        } else {
            BigInteger balance = balanceResponse.getBalance();
            BigInteger ethDivisor = BigInteger.valueOf(1000000000000000000L);
            BigInteger ethBalance = balance.divide(ethDivisor);
            log.info("Account balance: {} Wei ({} ETH)", balance, ethBalance);
            
            if (balance.compareTo(BigInteger.ZERO) == 0) {
                log.warn("Account balance is zero. Transaction may fail due to insufficient funds.");
            }
        }

        // Prepare the function call
        Function function = new Function(
                "addEvent",
                Arrays.asList(
                        new org.web3j.abi.datatypes.Utf8String(eventType),
                        new org.web3j.abi.datatypes.Utf8String(metadataHash)
                ),
                Collections.emptyList()
        );

        String encodedFunction = FunctionEncoder.encode(function);

        // Get nonce
        EthGetTransactionCount ethGetTransactionCount = web3j.ethGetTransactionCount(
                credentials.getAddress(), DefaultBlockParameterName.LATEST).send();
        
        if (ethGetTransactionCount.hasError()) {
            throw new RuntimeException("Failed to get transaction count: " + ethGetTransactionCount.getError().getMessage());
        }
        
        BigInteger nonce = ethGetTransactionCount.getTransactionCount();
        log.debug("Transaction nonce: {}", nonce);

        // Get gas price
        EthGasPrice ethGasPrice = web3j.ethGasPrice().send();
        
        if (ethGasPrice.hasError()) {
            throw new RuntimeException("Failed to get gas price: " + ethGasPrice.getError().getMessage());
        }
        
        BigInteger gasPrice = ethGasPrice.getGasPrice();
        log.debug("Gas price: {} Wei", gasPrice);

        // Build transaction
        org.web3j.tx.RawTransactionManager transactionManager = 
                new org.web3j.tx.RawTransactionManager(web3j, credentials);
        
        // Use configured gas limit (default: 3,000,000 for Ganache compatibility)
        // Ganache's default block gas limit is ~6.7M, but using 3M is safer
        log.info("Using gas limit: {} (configured in application.properties)", gasLimit);
        
        // Send transaction
        EthSendTransaction ethSendTransaction = transactionManager.sendTransaction(
                gasPrice,
                gasLimit,
                contractAddress,
                encodedFunction,
                BigInteger.ZERO
        );

        // Check for errors in the response
        if (ethSendTransaction.hasError()) {
            String errorMessage = ethSendTransaction.getError().getMessage();
            String errorCode = String.valueOf(ethSendTransaction.getError().getCode());
            log.error("Transaction failed: code={}, message={}", errorCode, errorMessage);
            throw new RuntimeException("Failed to send transaction: " + errorMessage + " (code: " + errorCode + ")");
        }

        String txHash = ethSendTransaction.getTransactionHash();
        
        if (txHash == null || txHash.isEmpty()) {
            log.error("Transaction hash is null or empty. Response: {}", ethSendTransaction);
            throw new RuntimeException("Transaction hash is null. Transaction may not have been sent successfully.");
        }

        log.info("Transaction sent successfully: {}", txHash);
        return txHash;
    }

    /**
     * Get a single event by index
     */
    public Event getEvent(BigInteger index) throws Exception {
        checkContractAddress();
        log.info("Fetching event at index: {}", index);

        Function function = new Function(
                "getEvent",
                Arrays.asList(new Uint256(index)),
                Arrays.asList(
                        new TypeReference<Address>() {},
                        new TypeReference<Utf8String>() {},
                        new TypeReference<Utf8String>() {},
                        new TypeReference<Uint256>() {}
                )
        );

        String encodedFunction = FunctionEncoder.encode(function);

        EthCall response = web3j.ethCall(
                Transaction.createEthCallTransaction(
                        credentials.getAddress(),
                        contractAddress,
                        encodedFunction
                ),
                DefaultBlockParameterName.LATEST
        ).send();

        if (response.hasError()) {
            throw new RuntimeException("Error calling contract: " + response.getError().getMessage());
        }

        List<Type> decoded = FunctionReturnDecoder.decode(
                response.getValue(),
                function.getOutputParameters()
        );

        if (decoded.isEmpty()) {
            throw new RuntimeException("No data returned from contract");
        }

        Event event = new Event();
        event.setIndex(index);
        event.setActor(((Address) decoded.get(0)).getValue());
        event.setEventType(((Utf8String) decoded.get(1)).getValue());
        event.setMetadataHash(((Utf8String) decoded.get(2)).getValue());
        event.setTimestamp(((Uint256) decoded.get(3)).getValue());

        return event;
    }

    /**
     * Get all events from the blockchain
     */
    public List<Event> getAllEvents() throws Exception {
        checkContractAddress();
        log.info("Fetching all events from blockchain");

        Function function = new Function(
                "getAllEvents",
                Collections.emptyList(),
                Arrays.asList(
                        new TypeReference<DynamicArray<Address>>() {},
                        new TypeReference<DynamicArray<Utf8String>>() {},
                        new TypeReference<DynamicArray<Utf8String>>() {},
                        new TypeReference<DynamicArray<Uint256>>() {}
                )
        );

        String encodedFunction = FunctionEncoder.encode(function);

        EthCall response = web3j.ethCall(
                Transaction.createEthCallTransaction(
                        credentials.getAddress(),
                        contractAddress,
                        encodedFunction
                ),
                DefaultBlockParameterName.LATEST
        ).send();

        if (response.hasError()) {
            throw new RuntimeException("Error calling contract: " + response.getError().getMessage());
        }

        List<Type> decoded = FunctionReturnDecoder.decode(
                response.getValue(),
                function.getOutputParameters()
        );

        if (decoded.isEmpty()) {
            return new ArrayList<>();
        }

        @SuppressWarnings("unchecked")
        DynamicArray<Address> actors = (DynamicArray<Address>) decoded.get(0);
        @SuppressWarnings("unchecked")
        DynamicArray<Utf8String> eventTypes = (DynamicArray<Utf8String>) decoded.get(1);
        @SuppressWarnings("unchecked")
        DynamicArray<Utf8String> metadataHashes = (DynamicArray<Utf8String>) decoded.get(2);
        @SuppressWarnings("unchecked")
        DynamicArray<Uint256> timestamps = (DynamicArray<Uint256>) decoded.get(3);

        List<Event> events = new ArrayList<>();
        int size = actors.getValue().size();

        for (int i = 0; i < size; i++) {
            Event event = new Event();
            event.setIndex(BigInteger.valueOf(i));
            event.setActor(actors.getValue().get(i).getValue());
            event.setEventType(eventTypes.getValue().get(i).getValue());
            event.setMetadataHash(metadataHashes.getValue().get(i).getValue());
            event.setTimestamp(timestamps.getValue().get(i).getValue());
            events.add(event);
        }

        return events;
    }

    /**
     * Verify if a metadata hash exists on-chain
     */
    public boolean verifyHash(String metadataHash) throws Exception {
        checkContractAddress();
        log.info("Verifying hash: {}", metadataHash);

        Function function = new Function(
                "verifyHash",
                Arrays.asList(new Utf8String(metadataHash)),
                Arrays.asList(
                        new TypeReference<Bool>() {},
                        new TypeReference<Uint256>() {}
                )
        );

        String encodedFunction = FunctionEncoder.encode(function);

        EthCall response = web3j.ethCall(
                Transaction.createEthCallTransaction(
                        credentials.getAddress(),
                        contractAddress,
                        encodedFunction
                ),
                DefaultBlockParameterName.LATEST
        ).send();

        if (response.hasError()) {
            throw new RuntimeException("Error calling contract: " + response.getError().getMessage());
        }

        List<Type> decoded = FunctionReturnDecoder.decode(
                response.getValue(),
                function.getOutputParameters()
        );

        if (decoded.isEmpty()) {
            return false;
        }

        return ((Bool) decoded.get(0)).getValue();
    }

    /**
     * Get the total number of events
     */
    public BigInteger getEventCount() throws Exception {
        checkContractAddress();
        log.debug("Fetching event count");

        Function function = new Function(
                "getEventCount",
                Collections.emptyList(),
                Arrays.asList(new TypeReference<Uint256>() {})
        );

        String encodedFunction = FunctionEncoder.encode(function);

        EthCall response = web3j.ethCall(
                Transaction.createEthCallTransaction(
                        credentials.getAddress(),
                        contractAddress,
                        encodedFunction
                ),
                DefaultBlockParameterName.LATEST
        ).send();

        if (response.hasError()) {
            throw new RuntimeException("Error calling contract: " + response.getError().getMessage());
        }

        List<Type> decoded = FunctionReturnDecoder.decode(
                response.getValue(),
                function.getOutputParameters()
        );

        if (decoded.isEmpty()) {
            return BigInteger.ZERO;
        }

        return ((Uint256) decoded.get(0)).getValue();
    }

    /**
     * Wait for transaction to be mined and return receipt
     */
    public TransactionReceipt waitForTransactionReceipt(String txHash, int maxAttempts) throws Exception {
        checkContractAddress();
        log.info("Waiting for transaction receipt: {}", txHash);
        
        for (int i = 0; i < maxAttempts; i++) {
            EthGetTransactionReceipt receiptResponse = web3j.ethGetTransactionReceipt(txHash).send();
            if (receiptResponse.getTransactionReceipt().isPresent()) {
                TransactionReceipt receipt = receiptResponse.getTransactionReceipt().get();
                log.info("Transaction mined in block: {}", receipt.getBlockNumber());
                return receipt;
            }
            Thread.sleep(1000); // Wait 1 second between attempts
            log.debug("Transaction not mined yet, attempt {}/{}", i + 1, maxAttempts);
        }
        
        throw new RuntimeException("Transaction not mined after " + maxAttempts + " attempts");
    }

    /**
     * Get transaction receipt to extract transaction hash details
     */
    public TransactionReceipt getTransactionReceipt(String txHash) throws IOException {
        EthGetTransactionReceipt receipt = web3j.ethGetTransactionReceipt(txHash).send();
        return receipt.getTransactionReceipt().orElse(null);
    }
}

