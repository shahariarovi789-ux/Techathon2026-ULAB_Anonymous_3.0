@echo off
title Lumina Setup Launcher (Windows)
echo ==========================================================
echo 💡 LUMINA IoT OBSERVABILITY SYSTEM STARTUP LAUNCHER
echo ==========================================================

:: 1. Verify/Create Virtual Environment
if not exist "venv" (
    echo ⚙️ Creating Python virtual environment...
    python -m venv venv
)

echo ⚙️ Activating virtual environment...
call venv\Scripts\activate

echo ⚙️ Installing dependencies...
pip install -r backend/requirements.txt

echo ----------------------------------------------------------
echo 🚀 Launching FastAPI Telemetry Backend (port 8000)...
start "Lumina Backend API" cmd /k "venv\Scripts\activate && python backend/main.py"

echo ⏳ Waiting for backend to initialize...
timeout /t 3 /nobreak > nul

:: Check .env configuration
if exist "backend\.env" (
    findstr /r "^DISCORD_BOT_TOKEN=[a-zA-Z0-9]" backend\.env >nul
    if errorlevel 1 (
        echo ⚠️ DISCORD_BOT_TOKEN not configured in backend/.env
        echo ⚠️ The Discord Bot will not start automatically.
        echo ⚠️ Once you configure your token, run: python backend/bot.py
        echo.
        echo ✅ Telemetry Engine backend is active at http://localhost:8000
        echo 👉 Open 'frontend/index.html' in your browser to view the Digital Twin!
        pause
        exit /b
      )
) else (
    echo ⚠️ backend/.env file not found. Copy backend/.env.example to backend/.env
    echo ⚠️ The Discord Bot will not start automatically.
    echo.
    echo ✅ Telemetry Engine backend is active at http://localhost:8000
    echo 👉 Open 'frontend/index.html' in your browser to view the Digital Twin!
    pause
    exit /b
)

echo 🚀 Starting LLM-powered Discord Bot...
start "Lumina Discord Bot" cmd /k "venv\Scripts\activate && python backend/bot.py"

echo ----------------------------------------------------------
echo ✅ Central Telemetry Server is running at http://localhost:8000
echo ✅ Discord Bot is online in the background.
echo 👉 Open 'frontend/index.html' in your web browser to observe the twin.
echo ==========================================================
pause
