# Quick Start Guide

## 🚀 Get Started in 3 Steps

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Start Backend (if not already running)
Make sure your Spring Boot backend is running on `http://localhost:8080`

### 3. Start Frontend
```bash
npm start
```

The app will open automatically at `http://localhost:3000`

## 📋 First Steps

1. **Connect Wallet**: Click "Connect Wallet" in the navbar and approve the MetaMask connection
2. **Add Event**: Navigate to "Add Event", enter an event type, upload a file, and submit
3. **View Timeline**: Check "Timeline" to see all events
4. **Verify Event**: Go to "Verify Event" and enter an IPFS hash or scan a QR code

## ⚠️ Troubleshooting

### CORS Errors
If you see CORS errors, see `CORS_CONFIG.md` for backend configuration.

### Wallet Connection Issues
- Make sure MetaMask is installed and unlocked
- Check that you're on a supported network
- Try refreshing the page

### API Connection Errors
- Verify backend is running: `curl http://localhost:8080/events`
- Check the API URL in `.env` file (or default `http://localhost:8080`)

## 📝 Environment Variables

Create `.env` file in `frontend/` directory:
```
REACT_APP_API_URL=http://localhost:8080
```
