#!/bin/bash
# Quick Start Script - Run RAG Debugger with UI

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          🚀 RAG Debugger - Quick Start                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this from the rag-debugger directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -e . -q
fi

echo ""
echo "✅ Environment ready!"
echo ""

# Generate test data if database doesn't exist
if [ ! -f "$HOME/.ragdebug/ragdebug.db" ]; then
    echo "📊 Generating sample test data..."
    python3 ui/generate_test_data.py
    echo ""
fi

echo "════════════════════════════════════════════════════════════════"
echo "Starting RAG Debugger..."
echo "════════════════════════════════════════════════════════════════"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    kill $API_PID 2>/dev/null
    kill $UI_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start API server in background
echo "🔌 Starting API server on port 8000..."
uvicorn api.main:app --port 8000 --log-level warning > /tmp/ragdebug-api.log 2>&1 &
API_PID=$!

# Wait for API to start
sleep 2

# Check if API started successfully
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Failed to start API server"
    echo "   Check logs: tail /tmp/ragdebug-api.log"
    kill $API_PID 2>/dev/null
    exit 1
fi

echo "✅ API server running (PID: $API_PID)"
echo ""

# Start UI server in background
echo "🎨 Starting UI server on port 3000..."
cd ui && python3 serve.py > /tmp/ragdebug-ui.log 2>&1 &
UI_PID=$!
cd ..

# Wait for UI to start
sleep 1

echo "✅ UI server running (PID: $UI_PID)"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "✨ RAG Debugger is running!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📡 API Server:    http://localhost:8000"
echo "   API Docs:      http://localhost:8000/docs"
echo "   Health Check:  http://localhost:8000/health"
echo ""
echo "🌐 Web UI:        http://localhost:3000"
echo ""
echo "📊 Logs:"
echo "   API:  tail -f /tmp/ragdebug-api.log"
echo "   UI:   tail -f /tmp/ragdebug-ui.log"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "🎯 Quick Tips:"
echo "   • Open http://localhost:3000 in your browser"
echo "   • Browse sample sessions in the Sessions view"
echo "   • Click on a session to see the timeline"
echo "   • Toggle dark mode with the 🌙 button"
echo "   • Press Ctrl+C to stop all servers"
echo ""
echo "📚 Documentation:"
echo "   • README.md - Full documentation"
echo "   • ui/README.md - Web UI guide"
echo "   • QUICKSTART.md - 3-minute tutorial"
echo ""
echo "🚀 Opening browser..."

# Open browser (macOS)
sleep 2
open http://localhost:3000 2>/dev/null || echo "   Please open http://localhost:3000 manually"

echo ""
echo "Press Ctrl+C to stop all servers..."
echo ""

# Keep script running
wait
