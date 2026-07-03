#!/bin/bash
# Lumina Project Startup Launcher

# Stop execution if any command fails
set -e

# Resolve the absolute path of this script's directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=========================================================="
echo "💡 LUMINA IoT OBSERVABILITY SYSTEM STARTUP LAUNCHER"
echo "=========================================================="

# 1. Verify/Create Virtual Environment
if [ ! -d "venv" ]; then
    echo "⚙️ Creating python virtual environment..."
    python3 -m venv venv
fi

echo "⚙️ Activating virtual environment..."
source venv/bin/activate

echo "⚙️ Installing dependencies from requirements.txt..."
pip install -r backend/requirements.txt

echo "----------------------------------------------------------"
echo "🚀 Launching FastAPI Telemetry Backend (port 8000)..."
python3 backend/main.py &
BACKEND_PID=$!

# Ensure backend process is terminated if script is aborted
trap "kill $BACKEND_PID" EXIT

# Wait for backend to start up
sleep 2

# Parse environmental variables
if [ -f "backend/.env" ]; then
    # Load variables from .env (ignoring comments)
    export $(grep -v '^#' backend/.env | xargs)
fi

if [ -z "$DISCORD_BOT_TOKEN" ]; then
    echo "⚠️  DISCORD_BOT_TOKEN not configured in backend/.env"
    echo "⚠️  The Discord Bot will not start automatically."
    echo "⚠️  Once you configure your token, run the bot in a separate terminal: python3 backend/bot.py"
    echo ""
    echo "✅ Telemetry Engine backend is active."
    echo "👉 Open 'frontend/index.html' in your browser to view the Digital Twin!"
    echo "👉 Press [CTRL+C] to stop the backend server."
    
    # Keep script running while backend runs
    wait $BACKEND_PID
else
    echo "🚀 Starting LLM-powered Discord Bot..."
    python3 backend/bot.py &
    BOT_PID=$!
    
    # Ensure both processes are killed on exit
    trap "kill $BACKEND_PID $BOT_PID" EXIT
    
    echo "----------------------------------------------------------"
    echo "✅ Central Telemetry Server is running at http://localhost:8000"
    echo "✅ Discord Bot is online in the background."
    echo "👉 Open 'frontend/index.html' in your web browser to observe the twin."
    echo "👉 Press [CTRL+C] to terminate all services."
    
    # Wait on both processes
    wait $BACKEND_PID $BOT_PID
fi
