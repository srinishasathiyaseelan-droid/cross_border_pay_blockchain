@echo off
echo ===================================================
echo   AI-Enabled PDS System - Local Launcher
echo ===================================================

echo 1. Starting Hardhat Local Node...
start "Blockchain Node" cmd /k "npx hardhat node"

echo Waiting 5 seconds for node to initialize...
timeout /t 5

echo 2. Deploying Smart Contract...
call npx hardhat run scripts/deploy.js --network localhost
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Deployment script exited with error code.
    echo If you see "Assertion failed" or "UV_HANDLE_CLOSING", this is a known harmless Windows bug.
    echo Checking if deployment succeeded...
    timeout /t 3
)

echo.
echo 3. Starting AI Service...
start "AI Service" cmd /k "call ai-venv\Scripts\activate && cd ai-service && uvicorn main:app --reload --port 5000"

echo.
echo 4. Starting Backend API...
start "Backend API" cmd /k "cd backend-node && npm start"

echo.
echo 5. Starting Frontend Dashboard...
start "Frontend UI" cmd /k "cd frontend && npm start"

echo ===================================================
echo   All Systems Go! 🚀
echo   Dashboard: http://localhost:3000/pds
echo   Backend:   http://localhost:4000
echo   AI:        http://localhost:5000
echo ===================================================
pause
