# EventChain - Complete Application Documentation

## 📑 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Installation & Setup](#installation--setup)
5. [Configuration](#configuration)
6. [API Documentation](#api-documentation)
7. [Frontend Guide](#frontend-guide)
8. [Smart Contract](#smart-contract)
9. [Deployment](#deployment)
10. [Development Guide](#development-guide)
11. [Troubleshooting](#troubleshooting)
12. [Security](#security)

---

## 1. Overview

### What is EventChain?

EventChain is a **Universal Verifiable Event Ledger** - a full-stack blockchain application that provides:

- ✅ **Immutable Event Storage** - Store events permanently on the blockchain
- ✅ **IPFS Integration** - Decentralized metadata storage
- ✅ **Verification System** - Verify event authenticity using hashes
- ✅ **QR Code Generation** - Easy verification via QR codes
- ✅ **Web Interface** - User-friendly React frontend

### Use Cases

- **Certificates & Credentials** - Issue and verify educational certificates
- **Document Tracking** - Track document versions and signatures
- **Transaction Records** - Record and verify financial transactions
- **Supply Chain** - Track product events through supply chain
- **Audit Logs** - Create tamper-proof audit trails

### Technology Stack

**Backend:**
- Java 17+
- Spring Boot 3.2.0
- Web3j 4.9.8 (Blockchain integration)
- IPFS HTTP Client (Decentralized storage)
- ZXing (QR code generation)

**Frontend:**
- React 18
- Tailwind CSS
- ethers.js (Wallet integration)
- html5-qrcode (QR scanning)
- Axios (HTTP client)

**Blockchain:**
- Solidity 0.8.19
- EVM-compatible chains (Ethereum, Polygon, etc.)

---

## 2. Architecture

### System Architecture

```
┌─────────────────┐
│   React Frontend │
│   (Port 3000)    │
└────────┬─────────┘
         │ HTTP/REST
         │
┌────────▼─────────┐
│  Spring Boot API │
│   (Port 8081)     │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│ IPFS  │ │Blockchain│
│ Node  │ │(Ganache) │
└───────┘ └─────────┘
```

### Component Architecture

```
EventChain Application
│
├── Frontend Layer
│   ├── WalletConnector (MetaMask integration)
│   ├── EventForm (Create events)
│   ├── EventTimeline (View events)
│   └── VerifyEventComponent (Verify events)
│
├── Backend Layer
│   ├── EventController (REST API)
│   ├── BlockchainService (Smart contract interaction)
│   ├── IpfsService (IPFS operations)
│   ├── ProofService (Proof generation)
│   └── QRCodeService (QR code generation)
│
└── Smart Contract Layer
    └── EventChain.sol (On-chain storage)
```

### Data Flow

1. **Event Creation:**
   ```
   User Input → Frontend → Backend API
   → IPFS Upload → Get IPFS Hash
   → Blockchain Transaction → Store on-chain
   → Generate Proof & QR Code → Return to User
   ```

2. **Event Verification:**
   ```
   User Input (Hash/QR) → Backend API
   → Query Blockchain → Verify Hash Exists
   → Return Verification Result
   ```

---

## 3. Features

### Core Features

#### 1. Event Creation
- Upload metadata (JSON, text, or files)
- Automatic IPFS storage
- Blockchain transaction
- Proof generation
- QR code creation

#### 2. Event Timeline
- View all events
- Filter by type
- Display event details
- Copy hashes to clipboard
- View QR codes

#### 3. Event Verification
- Hash-based verification
- QR code scanning
- On-chain verification
- Proof validation

#### 4. Wallet Integration
- MetaMask connection
- Account management
- Network switching
- Transaction signing

### Advanced Features

- **Graceful Degradation** - Works without blockchain/IPFS configured
- **Error Handling** - Comprehensive error messages
- **CORS Support** - Cross-origin requests
- **Docker Support** - Containerized deployment
- **Multiple Networks** - Support for various blockchains

---

## 4. Installation & Setup

### Prerequisites

1. **Java 17+**
   ```bash
   java -version
   ```

2. **Maven 3.6+**
   ```bash
   mvn -version
   ```

3. **Node.js 16+**
   ```bash
   node -version
   npm -version
   ```

4. **IPFS Node** (Optional)
   - Install: https://docs.ipfs.tech/install/
   - Start: `ipfs daemon`

5. **Ganache** (For local testing)
   - Download: https://trufflesuite.com/ganache/
   - Start Quickstart

### Quick Setup (5 Minutes)

#### Step 1: Clone/Download Project
```bash
cd EventChain
```

#### Step 2: Start Ganache
- Open Ganache
- Click "Quickstart"
- Note the RPC URL: `http://127.0.0.1:7545`

#### Step 3: Deploy Contract
```bash
# Option A: Using batch file (Windows)
deploy-contract-auto.bat

# Option B: Using Hardhat
npm install
npm run deploy:hardhat
```

#### Step 4: Configure Backend
Edit `src/main/resources/application.properties`:
```properties
blockchain.network.url=http://127.0.0.1:7545
blockchain.contract.address=YOUR_DEPLOYED_ADDRESS
blockchain.private.key=YOUR_PRIVATE_KEY
```

#### Step 5: Start Application
```bash
# Option A: Using batch file
start.bat

# Option B: Manual
# Terminal 1: Backend
mvn spring-boot:run

# Terminal 2: Frontend
cd frontend
npm install
npm start
```

#### Step 6: Access Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8081

### Detailed Setup

See:
- `QUICK_TEST_SETUP.md` - Quick test setup guide
- `DEPLOY_WITHOUT_REMIX.md` - Contract deployment guide
- `DOCKER.md` - Docker deployment guide

---

## 5. Configuration

### Backend Configuration

#### `application.properties`

```properties
# Server Configuration
server.port=8081

# Blockchain Configuration
blockchain.network.url=http://127.0.0.1:7545
blockchain.contract.address=0xYourContractAddress
blockchain.private.key=0xYourPrivateKey
blockchain.gas.limit=3000000

# IPFS Configuration
ipfs.host=127.0.0.1
ipfs.port=5001
ipfs.protocol=http

# Application Configuration
app.name=EventChain
app.version=1.0.0
```

#### Configuration Options

| Property | Description | Default | Required |
|----------|-------------|---------|----------|
| `server.port` | Backend server port | 8080 | No |
| `blockchain.network.url` | Blockchain RPC URL | - | Yes* |
| `blockchain.contract.address` | Deployed contract address | - | Yes* |
| `blockchain.private.key` | Account private key | - | Yes* |
| `blockchain.gas.limit` | Transaction gas limit | 3000000 | No |
| `ipfs.host` | IPFS node host | 127.0.0.1 | No |
| `ipfs.port` | IPFS node port | 5001 | No |

*Required only if using blockchain features

### Frontend Configuration

#### Environment Variables

Create `frontend/.env`:
```env
REACT_APP_API_URL=http://localhost:8081
```

#### Hardhat Configuration

Edit `hardhat.config.js`:
```javascript
module.exports = {
  solidity: "0.8.19",
  networks: {
    ganache: {
      url: "http://127.0.0.1:7545",
      chainId: 1337,
      accounts: ["YOUR_PRIVATE_KEY"]
    }
  }
};
```

---

## 6. API Documentation

### Base URL
```
http://localhost:8081
```

### Endpoints

#### 1. Create Event

**POST** `/events`

Create a new event by uploading metadata to IPFS and storing it on the blockchain.

**Request Body:**
```json
{
  "eventType": "certificate",
  "metadata": "{\"name\":\"John Doe\",\"degree\":\"Computer Science\"}"
}
```

**Request Fields:**
- `eventType` (string, required): Type of event (e.g., "certificate", "document")
- `metadata` (string, required): JSON string containing event metadata

**Response:** `201 Created`
```json
{
  "index": 0,
  "actor": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "eventType": "certificate",
  "metadataHash": "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
  "timestamp": 1702809540,
  "transactionHash": "0xabc123...",
  "proofJson": "{\"eventHash\":\"0x...\",\"actor\":\"0x...\",\"timestamp\":\"2025-12-17T09:39:00Z\",\"txHash\":\"0x...\"}",
  "qrCodeBase64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

**Response Fields:**
- `index`: Event index on blockchain
- `actor`: Wallet address that created the event
- `eventType`: Type of event
- `metadataHash`: IPFS hash of metadata
- `timestamp`: Unix timestamp
- `transactionHash`: Blockchain transaction hash
- `proofJson`: Verifiable proof JSON string
- `qrCodeBase64`: Base64-encoded QR code PNG

**Error Responses:**
- `400 Bad Request`: Invalid request body
- `503 Service Unavailable`: Blockchain/IPFS not configured
- `500 Internal Server Error`: Transaction failed

---

#### 2. Get All Events

**GET** `/events`

Retrieve all events from the blockchain.

**Response:** `200 OK`
```json
[
  {
    "index": 0,
    "actor": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "eventType": "certificate",
    "metadataHash": "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
    "timestamp": 1702809540,
    "transactionHash": "0xabc123..."
  }
]
```

**Error Responses:**
- `503 Service Unavailable`: Blockchain not configured (returns empty array)

---

#### 3. Get Event by Index

**GET** `/events/{id}`

Get a single event by its index.

**Path Parameters:**
- `id` (BigInteger): Event index (0-based)

**Response:** `200 OK`
```json
{
  "index": 0,
  "actor": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "eventType": "certificate",
  "metadataHash": "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
  "timestamp": 1702809540,
  "transactionHash": "0xabc123..."
}
```

**Error Responses:**
- `404 Not Found`: Event index out of bounds
- `503 Service Unavailable`: Blockchain not configured

---

#### 4. Verify Event Hash

**GET** `/events/verify/{hash}`

Verify if an event hash exists on-chain.

**Path Parameters:**
- `hash` (string): IPFS metadata hash to verify

**Response:** `200 OK`
```json
{
  "exists": true,
  "index": 0,
  "message": "Hash verified and exists on-chain"
}
```

**Response Fields:**
- `exists`: Whether hash exists on-chain
- `index`: Event index if exists
- `message`: Verification message

**Error Responses:**
- `503 Service Unavailable`: Blockchain not configured

---

### API Examples

See `examples/api-requests.http` for complete examples.

**Using cURL:**
```bash
# Create event
curl -X POST http://localhost:8081/events \
  -H "Content-Type: application/json" \
  -d '{
    "eventType": "certificate",
    "metadata": "{\"name\":\"John Doe\"}"
  }'

# Get all events
curl http://localhost:8081/events

# Verify hash
curl http://localhost:8081/events/verify/QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco
```

---

## 7. Frontend Guide

### Pages

#### 1. Home Page (`/`)
- Welcome screen
- Feature overview
- Quick start guide

#### 2. Add Event (`/add-event`)
- Event creation form
- File upload
- Event type selection
- Metadata input

#### 3. Timeline (`/timeline`)
- Event list display
- Event details
- QR code viewing
- Hash copying

#### 4. Verify Event (`/verify`)
- Hash input
- QR code scanning
- Verification results

### Components

#### WalletConnector
- Connects to MetaMask
- Displays wallet address
- Handles disconnection

#### EventForm
- Form for creating events
- File upload support
- Validation
- Success/error handling

#### EventTimeline
- Grid layout for events
- Event card display
- Copy-to-clipboard
- QR code display

#### VerifyEventComponent
- Hash input field
- QR scanner
- Verification display

### Usage

1. **Connect Wallet:**
   - Click "Connect Wallet" button
   - Approve MetaMask connection
   - Select account

2. **Create Event:**
   - Navigate to "Add Event"
   - Enter event type
   - Upload file or enter metadata
   - Click "Create Event"
   - Wait for transaction confirmation
   - View QR code and proof

3. **View Events:**
   - Navigate to "Timeline"
   - View all events
   - Click event for details
   - Copy hashes or view QR codes

4. **Verify Event:**
   - Navigate to "Verify"
   - Enter hash or scan QR code
   - View verification result

---

## 8. Smart Contract

### Contract: EventChain.sol

**Location:** `contracts/EventChain.sol`

**Solidity Version:** 0.8.19

### Functions

#### `addEvent(string memory eventType, string memory metadataHash)`
Add a new event to the ledger.

**Parameters:**
- `eventType`: Type of event
- `metadataHash`: IPFS hash of metadata

**Requirements:**
- Metadata hash must not be empty
- Event type must not be empty
- Hash must not already exist

**Events:**
- `EventAdded`: Emitted when event is added

#### `getEvent(uint256 index)`
Get a single event by index.

**Parameters:**
- `index`: Event index

**Returns:**
- `actor`: Wallet address
- `eventType`: Event type
- `metadataHash`: IPFS hash
- `timestamp`: Block timestamp

#### `getAllEvents()`
Get all events.

**Returns:**
- Arrays of actors, event types, metadata hashes, timestamps

#### `getEventCount()`
Get total number of events.

**Returns:**
- `uint256`: Event count

#### `verifyHash(string memory metadataHash)`
Verify if a hash exists.

**Parameters:**
- `metadataHash`: IPFS hash to verify

**Returns:**
- `exists`: Whether hash exists
- `index`: Event index if exists

### Deployment

See `DEPLOY_WITHOUT_REMIX.md` for deployment options.

**Quick Deploy:**
```bash
deploy-contract-auto.bat
```

---

## 9. Deployment

### Local Deployment

**Using Batch File:**
```bash
start.bat
```

**Manual:**
```bash
# Backend
mvn spring-boot:run

# Frontend
cd frontend
npm start
```

### Docker Deployment

**Using Docker Compose:**
```bash
docker-compose up
```

**Manual Docker:**
```bash
docker build -t eventchain .
docker run -p 8081:8081 eventchain
```

See `DOCKER.md` for detailed instructions.

### Production Deployment

1. **Build Backend:**
   ```bash
   mvn clean package
   ```

2. **Build Frontend:**
   ```bash
   cd frontend
   npm run build
   ```

3. **Deploy Contract:**
   - Deploy to production network
   - Update contract address in config

4. **Configure Environment:**
   - Set production RPC URL
   - Configure private key securely
   - Set IPFS node

5. **Deploy Application:**
   - Use Docker or traditional deployment
   - Configure reverse proxy
   - Set up SSL/TLS

See `DEPLOYMENT.md` for production guide.

---

## 10. Development Guide

### Project Structure

```
EventChain/
├── contracts/
│   └── EventChain.sol          # Smart contract
├── src/main/java/com/eventchain/
│   ├── EventChainApplication.java
│   ├── config/                 # Configuration classes
│   ├── controller/             # REST controllers
│   ├── dto/                    # Data transfer objects
│   ├── model/                  # Domain models
│   └── service/                # Business logic
├── src/main/resources/
│   └── application.properties  # Configuration
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # Page components
│   │   ├── services/           # API client
│   │   └── context/            # React context
│   └── public/                  # Static files
├── scripts/                     # Deployment scripts
├── examples/                    # API examples
└── pom.xml                      # Maven config
```

### Adding New Features

#### 1. Add New API Endpoint

**Step 1:** Add method to `EventController.java`
```java
@GetMapping("/new-endpoint")
public ResponseEntity<?> newEndpoint() {
    // Implementation
}
```

**Step 2:** Add service method if needed
```java
// In appropriate Service class
public ReturnType newMethod() {
    // Implementation
}
```

**Step 3:** Update frontend API client
```javascript
// In frontend/src/services/api.js
export const eventService = {
  newMethod: async () => {
    const response = await api.get('/new-endpoint');
    return response.data;
  }
};
```

#### 2. Add New Frontend Page

**Step 1:** Create page component
```javascript
// frontend/src/pages/NewPage.js
import React from 'react';

export default function NewPage() {
  return <div>New Page</div>;
}
```

**Step 2:** Add route
```javascript
// frontend/src/App.js
import NewPage from './pages/NewPage';

<Route path="/new-page" element={<NewPage />} />
```

**Step 3:** Add navigation link
```javascript
// In Navbar or appropriate component
<Link to="/new-page">New Page</Link>
```

### Testing

**Backend Testing:**
```bash
mvn test
```

**Frontend Testing:**
```bash
cd frontend
npm test
```

**Integration Testing:**
- Use `examples/api-requests.http`
- Test with Postman or similar tools

### Code Style

- **Java:** Follow Spring Boot conventions
- **JavaScript:** Use ESLint configuration
- **Formatting:** Use Prettier for frontend

---

## 11. Troubleshooting

### Common Issues

#### 1. "Maven not recognized"
**Solution:**
- Install Maven and add to PATH
- Or use Maven wrapper: `./mvnw`

#### 2. "Node.js not found"
**Solution:**
- Install Node.js from https://nodejs.org/
- Restart terminal/IDE

#### 3. "Connection refused" (Ganache)
**Solution:**
- Ensure Ganache is running
- Check RPC URL is correct
- Verify port 7545 is not blocked

#### 4. "Transaction failed: exceeds block gas limit"
**Solution:**
- Reduce `blockchain.gas.limit` in `application.properties`
- Or increase Ganache block gas limit

#### 5. "CORS policy blocked"
**Solution:**
- Check `CorsConfig.java` is configured
- Verify allowed origins include frontend URL
- Check backend CORS headers

#### 6. "IPFS connection failed"
**Solution:**
- Start IPFS daemon: `ipfs daemon`
- Check IPFS host/port in config
- Application works without IPFS (optional)

#### 7. "Contract not found"
**Solution:**
- Verify contract address is correct
- Ensure contract is deployed to correct network
- Check network URL matches deployment network

#### 8. "Insufficient funds"
**Solution:**
- Ensure account has ETH/MATIC for gas
- In Ganache, accounts start with 100 ETH
- Check account balance

### Debug Mode

**Backend:**
```properties
# application.properties
logging.level.com.eventchain=DEBUG
```

**Frontend:**
- Open browser DevTools
- Check Console for errors
- Check Network tab for API calls

### Getting Help

1. Check documentation files
2. Review error logs
3. Check GitHub issues (if applicable)
4. Verify configuration

---

## 12. Security

### Best Practices

#### 1. Private Key Management
- ❌ **Never** commit private keys to git
- ✅ Use environment variables
- ✅ Use secrets management (AWS Secrets Manager, etc.)
- ✅ Use different keys for test/production

#### 2. IPFS Security
- ⚠️ IPFS content is publicly accessible
- ✅ Encrypt sensitive data before uploading
- ✅ Use private IPFS networks for sensitive data

#### 3. API Security
- ✅ Validate all inputs
- ✅ Use HTTPS in production
- ✅ Implement rate limiting
- ✅ Add authentication/authorization

#### 4. Smart Contract Security
- ✅ Audit contracts before production
- ✅ Use tested libraries
- ✅ Follow Solidity best practices
- ✅ Test thoroughly

#### 5. Frontend Security
- ✅ Validate user inputs
- ✅ Sanitize data before display
- ✅ Use HTTPS
- ✅ Implement CSP headers

### Production Checklist

- [ ] Private keys in environment variables
- [ ] HTTPS enabled
- [ ] CORS properly configured
- [ ] Input validation implemented
- [ ] Error messages don't leak sensitive info
- [ ] Contracts audited
- [ ] Rate limiting configured
- [ ] Monitoring/logging set up
- [ ] Backup strategy in place

---

## 📚 Additional Resources

### Documentation Files
- `README.md` - Main documentation
- `QUICK_TEST_SETUP.md` - Quick setup guide
- `DEPLOY_WITHOUT_REMIX.md` - Contract deployment
- `DOCKER.md` - Docker deployment
- `PROJECT_JOURNEY.md` - Development history
- `PROMPT_SUMMARY.md` - Quick reference

### External Resources
- [Spring Boot Documentation](https://spring.io/projects/spring-boot)
- [Web3j Documentation](https://docs.web3j.io/)
- [IPFS Documentation](https://docs.ipfs.tech/)
- [React Documentation](https://react.dev/)
- [Solidity Documentation](https://docs.soliditylang.org/)

---

## 📞 Support

For issues, questions, or contributions:
1. Check this documentation
2. Review troubleshooting section
3. Check project documentation files
4. Review code comments

---

**Last Updated:** December 2024  
**Version:** 1.0.0  
**Status:** ✅ Production Ready
