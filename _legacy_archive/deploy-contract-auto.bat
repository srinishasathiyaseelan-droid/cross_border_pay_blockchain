@echo off
REM ========================================
REM EventChain Contract Deployment Script (Auto-update)
REM Using Hardhat - Automatically updates application.properties
REM ========================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo EventChain - Contract Deployment (Auto)
echo Using Hardhat with auto-configuration
echo ========================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo.
    echo Please install Node.js from: https://nodejs.org/
    pause
    exit /b 1
)

REM Check if npm is installed
where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm is not installed or not in PATH
    pause
    exit /b 1
)

echo [OK] Node.js and npm are installed
echo.

REM Check if package.json exists
if not exist "package.json" (
    echo [ERROR] package.json not found
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "node_modules" (
    echo [INFO] Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
    echo.
)

REM Compile contract
echo [INFO] Compiling contract...
call npx hardhat compile >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Compilation failed
    pause
    exit /b 1
)
echo [OK] Contract compiled
echo.

REM Deploy and capture output
echo [INFO] Deploying contract...
echo.

REM Create temp file for output
set TEMP_FILE=%TEMP%\eventchain_deploy_%RANDOM%.txt

call npx hardhat run scripts\deploy-with-hardhat.js --network ganache > "%TEMP_FILE%" 2>&1
set DEPLOY_EXIT=%ERRORLEVEL%

REM Display output
type "%TEMP_FILE%"

if %DEPLOY_EXIT% NEQ 0 (
    echo.
    echo [ERROR] Deployment failed
    del "%TEMP_FILE%" >nul 2>&1
    pause
    exit /b 1
)

REM Extract contract address from output
set CONTRACT_ADDRESS=
for /f "tokens=*" %%a in ('type "%TEMP_FILE%" ^| findstr /i "deployed to:"') do (
    set LINE=%%a
    REM Extract address after "deployed to:"
    for /f "tokens=2 delims=:" %%b in ("!LINE!") do (
        set CONTRACT_ADDRESS=%%b
        set CONTRACT_ADDRESS=!CONTRACT_ADDRESS: =!
    )
)

del "%TEMP_FILE%" >nul 2>&1

if "!CONTRACT_ADDRESS!"=="" (
    echo.
    echo [WARNING] Could not extract contract address from output
    echo Please update application.properties manually
    pause
    exit /b 0
)

echo.
echo [INFO] Extracted contract address: !CONTRACT_ADDRESS!
echo.

REM Update application.properties
set PROPERTIES_FILE=src\main\resources\application.properties

if not exist "%PROPERTIES_FILE%" (
    echo [WARNING] application.properties not found
    echo Contract address: !CONTRACT_ADDRESS!
    pause
    exit /b 0
)

echo [INFO] Updating application.properties...

REM Create backup
copy "%PROPERTIES_FILE%" "%PROPERTIES_FILE%.backup" >nul 2>&1

REM Update contract address using PowerShell (more reliable for regex)
powershell -Command "(Get-Content '%PROPERTIES_FILE%') -replace 'blockchain\.contract\.address=.*', 'blockchain.contract.address=!CONTRACT_ADDRESS!' | Set-Content '%PROPERTIES_FILE%'"

if errorlevel 1 (
    echo [WARNING] Failed to auto-update application.properties
    echo.
    echo Please manually update:
    echo   blockchain.contract.address=!CONTRACT_ADDRESS!
    echo.
) else (
    echo [OK] Updated application.properties
    echo.
)

echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo Contract Address: !CONTRACT_ADDRESS!
echo.
echo application.properties has been updated.
echo Backup saved to: %PROPERTIES_FILE%.backup
echo.
pause
