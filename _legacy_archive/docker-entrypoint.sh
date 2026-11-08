#!/bin/sh
set -e

echo "=========================================="
echo "  EventChain - Starting Services"
echo "=========================================="
echo ""

# Start Backend
echo "Starting Backend (Spring Boot)..."
java -jar app.jar &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to initialize..."
for i in 1 2 3 4 5 6 7 8 9 10; do
    if wget --quiet --tries=1 --spider http://localhost:8080/events 2>/dev/null; then
        echo "Backend is ready!"
        break
    fi
    echo "  Attempt $i/10: Backend not ready yet, waiting..."
    sleep 2
done

# Start Frontend
echo ""
echo "Starting Frontend (React)..."
cd frontend/build
serve -s . -l 3000 &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "  EventChain is running!"
echo "=========================================="
echo "  Backend:  http://localhost:8080"
echo "  Frontend: http://localhost:3000"
echo "=========================================="
echo ""

# Function to handle shutdown
cleanup() {
    echo ""
    echo "Shutting down EventChain..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "Shutdown complete."
    exit 0
}

# Trap SIGTERM and SIGINT
trap cleanup SIGTERM SIGINT

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID
