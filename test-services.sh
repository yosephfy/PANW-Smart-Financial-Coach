#!/bin/bash

# Test Script for Smart Financial Coach Unified Hosting
echo "🧪 Testing Smart Financial Coach Services"
echo "========================================="

# Test backend health
echo "📡 Testing backend (http://localhost:3000/backend/health)..."
BACKEND_RESPONSE=$(curl -s -w "%{http_code}" http://localhost:3000/backend/health -o /tmp/backend_test)
BACKEND_STATUS=$(tail -c 3 <<< "$BACKEND_RESPONSE")

if [ "$BACKEND_STATUS" = "200" ]; then
    echo "✅ Backend is healthy"
    cat /tmp/backend_test
else
    echo "❌ Backend health check failed (HTTP $BACKEND_STATUS)"
fi

echo ""

# Test frontend
echo "🖥️  Testing frontend (http://localhost:3000/frontend/)..."  
FRONTEND_RESPONSE=$(curl -s -w "%{http_code}" http://localhost:3000/frontend/ -o /tmp/frontend_test)
FRONTEND_STATUS=$(tail -c 3 <<< "$FRONTEND_RESPONSE")

if [ "$FRONTEND_STATUS" = "200" ]; then
    echo "✅ Frontend is responding"
else
    echo "❌ Frontend test failed (HTTP $FRONTEND_STATUS)"
fi

echo ""
echo "📋 Service URLs:"
echo "  • Frontend: http://localhost:3000/frontend/"
echo "  • Backend API: http://localhost:3000/backend/"
echo "  • API Docs: http://localhost:3000/backend/docs"

# Cleanup temp files
rm -f /tmp/backend_test /tmp/frontend_test
