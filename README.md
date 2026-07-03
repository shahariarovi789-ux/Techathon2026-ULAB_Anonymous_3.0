# 🎯 Techathon Nationals 2026: Lumina IoT Workspace Orchestrator

Lumina is a production-ready **Digital Twin & IoT Observability Ecosystem** designed to tackle energy waste in modern workspaces. Built on an event-driven, single-source-of-truth backend, it unifies a real-time web dashboard, an LLM-powered Discord automation agent, and a simulated physical hardware schematic.

---

## 1. Problem Understanding & Relevance
In many office spaces, electrical appliances (lights, fans) are frequently left running after hours, resulting in skyrocketing electricity bills and safety concerns. The boss's big idea is to establish:
1. ** observability**: A live visual dashboard representing the entire office's device states (lights, fans) and live power consumption.
2. **Alerts**: Instant notifications when devices are left active inappropriately.
3. **Conversational interface**: A Discord bot that answers queries about the office's energy states in friendly, humanized terms rather than dumping robotic logs.

---

## 2. Architecture & Data Flow (ASCII Diagram)

To prevent discrepancies, the system employs a **Unified Single Source of Truth** architecture:

```
                  +-----------------------------------+
                  |      Simulated Device Layer       |
                  |  (Asynchronous Python Mutator)    |
                  +-----------------------------------+
                                    │
                                    ▼ (Internal State Dict)
                  +-----------------------------------+
                  |         FastAPI Backend           |
                  |  - Centralized State Manager      |
                  |  - REST HTTP & WebSocket Servers   |
                  +-----------------------------------+
                       /                         \
                      / (WebSockets)              \ (HTTP API Polling)
                     ▼                             ▼
       +--------------------------+    +--------------------------+
       |   Real-Time Dashboard    |    |  Conversational Bot      |
       |  - React/HTML5 Canvas    |    |  - discord.py Client     |
       |  - Interactive SVG Map   |    |  - Local Qwen-3B LLM     |
       +--------------------------+    +--------------------------+
```

### Architectural Highlights
- **Sub-Second Latency**: State changes in the backend are immediately propagated to the web client using WebSockets, avoiding client-side polling.
- **Data Parity**: The Discord bot and Web UI query the exact same backend state manager endpoints, ensuring they never present conflicting realities.
- **Non-Blocking I/O**: Python's `asyncio` is used extensively to run the telemetry daemon, API requests, WebSocket broadcasts, and Discord bot tasks concurrently without thread starvation.

---

## 3. Technology Stack
- **Backend API**: Python 3.11+, FastAPI, Uvicorn, Asyncio.
- **Frontend Dashboard**: Vanilla HTML5, CSS Custom Animations, Tailwind CSS, Native WebSockets.
- **Discord Bot**: `discord.py`, `aiohttp` for async queries.
- **Local AI Engine**: Ollama running a 4-bit quantized `qwen2.5-coder:3b` model (offline, private inference).
- **Hardware Integration**: ESP32 NodeMCU, LEDs, Relays, and the ACS712 Current Sensor.

---

## 4. Setup & Running Instructions

### Prerequisites
1. **Python 3.11+** installed.
2. **Ollama** installed and running on your system with the model `qwen2.5-coder:3b` pulled:
   ```bash
   ollama run qwen2.5-coder:3b
   ```

### Quick Start (One-Command Setup)
To setup the environment, install python libraries, and boot both the FastAPI backend and the Discord bot concurrently, run the launcher script from the project root:

```bash
# Set up executable permissions
chmod +x start.sh

# Run the launcher
./start.sh
```

### Manual Step-by-Step Launch

1. **Virtual Environment & Dependencies**:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configuration**:
   Copy `.env.example` to `.env` and fill in your Discord details:
   ```bash
   cp .env.example .env
   # Add your DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID in .env
   ```

3. **Start the API Backend**:
   ```bash
   python3 main.py
   ```
   *The server runs locally at `http://localhost:8000`. The frontend can be viewed by opening `frontend/index.html` in any modern web browser.*

4. **Start the Discord Bot**:
   In a separate terminal (with virtual environment activated):
   ```bash
   python3 bot.py
   ```

---

## 5. API Endpoint Documentation

| Method | Endpoint | Description |
|---|---|---|
| **GET** | `/api/devices` | Retrieves the states of all 18 IoT devices (Drawing Room, Work Rooms). |
| **POST** | `/api/devices/{device_id}/toggle` | Toggles the ON/OFF state of a device and broadcasts it via WebSockets. |
| **GET** | `/api/usage` | Calculates total live wattage, per-zone breakdown, and daily usage (kWh). |
| **GET** | `/api/alerts` | Checks and returns active warning or critical anomalies. |
| **POST** | `/api/admin/override-time` | Overrides the virtual office clock (0-23) to test after-hours alerts. |
| **POST** | `/api/admin/reset-time` | Resets the virtual clock to match local system time. |
| **POST** | `/api/admin/simulate-anomaly` | Forces all devices in a room ON and offsets timestamps to trigger 2h warnings. |

---

## 6. AI Integration & Persona (Lumina)
- **Local LLM**: Utilizes `qwen2.5-coder:3b` (Quantized Q4_K_M) via Ollama. 
- **Prompt Engineering**: The Discord agent translates raw JSON device logs into human-friendly reports, incorporating registered team staff members (**Nafisa Rahman** and **Tanvir Hossain**) as context to create warm, natural conversational summaries.
- **Proactive Warnings**: A background thread checks the `/api/alerts` endpoint every 30 seconds. If a warning (after-hours load) or critical alarm (2-hour neglected load) is active, the bot generates a friendly prompt and dispatches an embed directly to the target Discord channel.
