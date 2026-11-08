# EventChain

EventChain - Universal Verifiable Event Ledger. A full-stack blockchain application that provides a verifiable, append-only event ledger using Solidity smart contracts, IPFS for decentralized storage, and a Java Spring Boot backend.

## 🚀 Getting Started

### Prerequisites

- Node.js 16+ and npm (or yarn)
- MetaMask browser extension installed
- Backend API running on `http://localhost:8080` (or configure `REACT_APP_API_URL`)
- **Important**: The backend must have CORS enabled to allow requests from the frontend. If you encounter CORS errors, add a CORS configuration to your Spring Boot backend.

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. (Optional) Configure API URL:
   - Create a `.env` file in the `frontend` directory
   - Add: `REACT_APP_API_URL=http://localhost:8080`
   - If not set, defaults to `http://localhost:8080`

### Running the Application

Start the development server:
```bash
npm start
```

The application will open in your browser at `http://localhost:3000`.

## 📁 Project Structure

```
frontend/
├── public/
│   └── index.html          # HTML template
├── src/
│   ├── components/         # Reusable components
│   │   ├── Navbar.js       # Navigation bar
│   │   ├── WalletConnector.js  # Wallet connection component
│   │   ├── EventForm.js    # Form for adding events
│   │   ├── EventTimeline.js    # Timeline view of events
│   │   └── VerifyEvent.js  # Verification component
│   ├── pages/              # Page components
│   │   ├── Home.js         # Home page
│   │   ├── AddEvent.js     # Add event page
│   │   ├── Timeline.js     # Timeline page
│   │   └── VerifyEvent.js  # Verify event page
│   ├── context/            # React context
│   │   └── WalletContext.js    # Wallet state management
│   ├── services/           # API services
│   │   └── api.js          # Backend API client
│   ├── App.js              # Main app component with routing
│   └── index.js            # Entry point
└── package.json
```

## 🎯 Features

### Wallet Connection
- Connect MetaMask wallet
- Display connected wallet address
- Handle wallet disconnection
- Listen for account changes

### Add Events
- Upload files (text, JSON, or binary)
- Specify event type
- Files are sent to backend which handles IPFS upload and blockchain storage
- Display success response with QR code

### Event Timeline
- View all events from the blockchain
- Display event details:
  - Actor (wallet address)
  - Event type
  - Timestamp
  - IPFS hash
  - Transaction hash
  - QR code
- Copy hashes to clipboard
- Responsive grid layout

### Verify Events
- Enter IPFS hash manually
- Scan QR code using camera
- Verify event authenticity
- Display verification results

## 🔧 Technologies Used

- **React 18** - UI library
- **React Router DOM** - Client-side routing
- **Material-UI (MUI)** - UI component library
- **ethers.js** - Ethereum wallet integration
- **Axios** - HTTP client for API calls
- **react-qr-reader** - QR code scanning

## 📡 API Integration

The frontend communicates with the backend API at the following endpoints:

- `GET /events` - Fetch all events
- `GET /events/{id}` - Get event by index
- `POST /events` - Create new event
- `GET /events/verify/{hash}` - Verify event hash

## 🌐 Environment Variables

Create a `.env` file in the `frontend` directory:

```
REACT_APP_API_URL=http://localhost:8080
```

## 🐛 Troubleshooting

### Wallet Connection Issues
- Ensure MetaMask is installed and unlocked
- Check that you're on a supported network (Ethereum, Polygon, etc.)
- Try refreshing the page

### API Connection Errors
- Verify the backend is running on the configured port
- Check CORS settings in the backend
- Ensure the API URL in `.env` is correct

### QR Scanner Not Working
- Grant camera permissions when prompted
- Use HTTPS in production (required for camera access)
- Try a different browser if issues persist

## 📝 Building for Production

```bash
npm run build
```

This creates an optimized production build in the `build` folder.

## 📄 License

MIT License
