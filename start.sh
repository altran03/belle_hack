#!/bin/bash

# BugSniper Pro Startup Script
echo "🐛 Starting BugSniper Pro..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from env.example..."
    cp env.example .env
    echo "📝 Please edit .env file with your API keys and configuration"
    echo "   Required: GEMINI_API_KEY, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_WEBHOOK_SECRET"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
pip install -r requirements.txt

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd ../frontend
npm install

# Go back to root
cd ..

echo "🚀 Starting BugSniper Pro..."
echo ""
echo "Backend will run on: http://localhost:8000"
echo "Frontend will run on: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both services"
echo ""

# Start both services in parallel
(trap 'kill 0' SIGINT; 
 cd backend && ../venv/bin/python main.py &
 cd frontend && npm run dev &
 wait
)
