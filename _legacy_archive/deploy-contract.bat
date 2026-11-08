@echo off
REM ========================================
REM EventChain Contract Deployment Script
REM Using Hardhat
REM ========================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo EventChain - Contract Deployment
echo Using Hardhat
echo ========================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo.
    echo Please install Node.js from: https://nodejs.org/
    echo After installation, restart this script.
    pause
    exit /b 1
)

REM Check if npm is installed
where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm is not installed or not in PATH
    echo.
    echo Please install npm (comes with Node.js)
    pause
    exit /b 1
)

echo [OK] Node.js and npm are installed
echo.

REM Check if package.json exists
if not exist "package.json" (
    echo [ERROR] package.json not found in current directory
    echo.
    echo Please run this script from the EventChain project root directory.
    pause
    exit /b 1
)

REM Check if node_modules exists (dependencies installed)
if not exist "node_modules" (
    echo [INFO] Dependencies not found. Installing...
    echo.
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo.
    echo [OK] Dependencies installed successfully
    echo.
) else (
    echo [OK] Dependencies already installed
    echo.
)

REM Check if hardhat.config.js exists
if not exist "hardhat.config.js" (
    echo [ERROR] hardhat.config.js not found
    echo.
    echo Please ensure hardhat.config.js exists in the project root.
    pause
    exit /b 1
)

REM Check if contract exists
if not exist "contracts\EventChain.sol" (
    echo [ERROR] contracts\EventChain.sol not found
    echo.
    echo Please ensure the contract file exists.
    pause
    exit /b 1
)

REM Check if deployment script exists
if not exist "scripts\deploy-with-hardhat.js" (
    echo [ERROR] scripts\deploy-with-hardhat.js not found
    echo.
    echo Please ensure the deployment script exists.
    pause
    exit /b 1
)

echo [INFO] Checking Ganache connection...
echo.

REM Try to check if Ganache is running (optional check)
curl -s http://127.0.0.1:7545 >nul 2>nul
if errorlevel 1 (
    echo [WARNING] Cannot connect to Ganache at http://127.0.0.1:7545
    echo.
    echo Please ensure Ganache is running before deploying.
    echo.
    set /p continue="Continue anyway? (y/n): "
    if /i not "!continue!"=="y" (
        echo Deployment cancelled.
        pause
        exit /b 0
    )
    echo.
) else (
    echo [OK] Ganache is running
    echo.
)

REM Compile contract
echo ========================================
echo Step 1: Compiling Contract
echo ========================================
echo.

call npx hardhat compile
if errorlevel 1 (
    echo [ERROR] Contract compilation failed
    pause
    exit /b 1
)

echo.
echo [OK] Contract compiled successfully
echo.

REM Deploy contract
echo ========================================
echo Step 2: Deploying Contract to Ganache
echo ========================================
echo.

call npx hardhat run scripts\deploy-with-hardhat.js --network ganache
if errorlevel 1 (
    echo.
    echo [ERROR] Contract deployment failed
    echo.
    echo Troubleshooting:
    echo - Make sure Ganache is running
    echo - Check that your private key in hardhat.config.js is correct
    echo - Ensure the account has sufficient balance
    pause
    exit /b 1
)

echo.
echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Copy the contract address from above
echo 2. Update src\main\resources\application.properties:
echo    blockchain.contract.address=YOUR_CONTRACT_ADDRESS
echo.
echo Press any key to exit...
pause >nul
