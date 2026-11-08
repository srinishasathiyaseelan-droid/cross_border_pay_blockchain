@echo off
title EventChain Launcher
color 0A

echo ========================================
echo   EventChain - Backend and Frontend Launcher
echo ========================================
echo.

REM Check if Maven is available
where mvn >nul 2>nul
if errorlevel 1 goto :maven_error

REM Check if Node.js is available
where node >nul 2>nul
if errorlevel 1 goto :node_error

REM Check if npm is available
where npm >nul 2>nul
if errorlevel 1 goto :npm_error

echo [OK] All prerequisites found!
echo.
echo Starting Backend (Spring Boot)...
start "EventChain Backend" cmd /k "cd /d %~dp0 && title EventChain Backend && mvn spring-boot:run"

REM Wait for backend initialization
echo Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

echo Starting Frontend (React)...
start "EventChain Frontend" cmd /k "cd /d %~dp0\frontend && title EventChain Frontend && npm start"

echo.
echo ========================================
echo   Services are starting in new windows
echo ========================================
echo   Backend:  http://localhost:8080
echo   Frontend: http://localhost:3000
echo ========================================
echo.
echo Close the service windows to stop them.
timeout /t 3 /nobreak >nul
exit

:maven_error
echo [ERROR] Maven (mvn) is not found in PATH.
echo.
echo To fix this:
echo 1. Install Maven from: https://maven.apache.org/download.cgi
echo 2. Extract to a folder like C:\Program Files\Apache\maven
echo 3. Add the bin folder to your system PATH
echo 4. Restart this command prompt and try again
echo.
echo OR use an IDE like IntelliJ IDEA or Eclipse which includes Maven
echo.
pause
exit /b 1

:node_error
echo [ERROR] Node.js is not found in PATH.
echo.
echo Please install Node.js from: https://nodejs.org/
echo This will also install npm
echo.
pause
exit /b 1

:npm_error
echo [ERROR] npm is not found in PATH.
echo.
echo Please install Node.js from: https://nodejs.org/
echo npm comes bundled with Node.js
echo.
pause
exit /b 1
