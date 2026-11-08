@echo off
title EventChain - Ganache Setup Helper
color 0B

echo ========================================
echo   EventChain - Local Test Setup Helper
echo ========================================
echo.
echo This script helps you set up a local test environment
echo using Ganache (local Ethereum blockchain).
echo.
echo Prerequisites:
echo 1. Ganache installed and running
echo 2. Smart contract deployed
echo.
pause

echo.
echo ========================================
echo   Step 1: Ganache Configuration
echo ========================================
echo.
echo Please provide the following information from Ganache:
echo.

set /p GANACHE_RPC="Enter Ganache RPC URL (default: http://127.0.0.1:7545): "
if "%GANACHE_RPC%"=="" set GANACHE_RPC=http://127.0.0.1:7545

set /p CONTRACT_ADDRESS="Enter deployed contract address: "
set /p PRIVATE_KEY="Enter private key (from Ganache, without 0x): "

echo.
echo ========================================
echo   Step 2: Updating Configuration
echo ========================================
echo.

REM Create backup
copy "src\main\resources\application.properties" "src\main\resources\application.properties.backup" >nul 2>&1

REM Update application.properties
powershell -Command "(Get-Content 'src\main\resources\application.properties') -replace 'blockchain.network.url=.*', 'blockchain.network.url=%GANACHE_RPC%' -replace 'blockchain.contract.address=.*', 'blockchain.contract.address=%CONTRACT_ADDRESS%' -replace 'blockchain.private.key=.*', 'blockchain.private.key=%PRIVATE_KEY%' | Set-Content 'src\main\resources\application.properties'"

echo Configuration updated!
echo.
echo ========================================
echo   Configuration Summary
echo ========================================
echo   RPC URL: %GANACHE_RPC%
echo   Contract: %CONTRACT_ADDRESS%
echo   Private Key: %PRIVATE_KEY:~0,10%... (hidden)
echo ========================================
echo.
echo Next steps:
echo 1. Make sure Ganache is running
echo 2. Start the backend: mvn spring-boot:run
echo 3. Start the frontend: cd frontend ^&^& npm start
echo 4. Connect MetaMask to Ganache network
echo.
echo Configuration backup saved to: application.properties.backup
echo.
pause
