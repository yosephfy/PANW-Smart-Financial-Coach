#!/bin/bash

# Smart Financial Coach - Startup Script
# Starts both backend and frontend on localhost:3000 with path prefixes

echo "🚀 Starting Smart Financial Coach"
echo "=================================="
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    if [[ -n $BACKEND_PID ]]; then
        kill $BACKEND_PID 2>/dev/null
        echo "✅ Backend stopped"
    fi
    if [[ -n $FRONTEND_PID ]]; then
        kill $FRONTEND_PID 2>/dev/null
        echo "✅ Frontend stopped"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check if required directories exist
if [[ ! -d "services/api" ]]; then
    echo "❌ Error: services/api directory not found"
    exit 1
fi

if [[ ! -d "apps/web" ]]; then
    echo "❌ Error: apps/web directory not found"
    exit 1
fi

echo "📦 Installing dependencies..."

# Install backend dependencies
echo "  → Installing backend dependencies..."
cd services/api
if [[ ! -d "../../.venv" ]]; then
    python3 -m venv ../../.venv
fi
../../.venv/bin/pip install -q -U pip setuptools wheel
../../.venv/bin/pip install -q -r requirements.txt
cd ../..

# Install frontend dependencies
echo "  → Installing frontend dependencies..."
cd apps/web
if [[ ! -d "node_modules" ]]; then
    npm install --silent
fi
cd ../..

echo ""
echo "🚀 Starting services..."

# Start backend on port 3000 with /backend prefix
echo "  → Starting backend (FastAPI) on http://localhost:3000/backend/"
cd services/api
../../.venv/bin/uvicorn app.main:app --port 3000 --log-level warning &
BACKEND_PID=$!
cd ../..

# Wait a moment for backend to start
sleep 2

# Start frontend on port 3000 with /frontend prefix
echo "  → Starting frontend (Next.js) on http://localhost:3000/frontend/"
cd apps/web
npm run dev > /dev/null 2>&1 &
FRONTEND_PID=$!
cd ../..

# Wait a moment for frontend to start
sleep 3

echo ""
echo "✅ Services started successfully!"
echo "=================================="
echo "🌐 Application URLs:"
echo "  • Frontend: http://localhost:3000/frontend/"
echo "  • Backend API: http://localhost:3000/backend/"
echo "  • API Docs: http://localhost:3000/backend/docs"
echo "  • Health Check: http://localhost:3000/backend/health"
echo ""
echo "💡 Both services are running on the same port (3000) with different path prefixes"
echo "📋 Press Ctrl+C to stop both services"
echo ""

# Keep script running and monitor processes
while true; do
    # Check if backend is still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo "❌ Backend process stopped unexpectedly"
        cleanup
    fi
    
    # Check if frontend is still running
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "❌ Frontend process stopped unexpectedly"  
        cleanup
    fi
    
    sleep 5
done
