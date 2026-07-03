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
| **GET** | `/api/devices` | Retrieves the states of all 15 IoT devices (Drawing Room, Work Rooms). |
| **POST** | `/api/devices/{device_id}/toggle` | Toggles the ON/OFF state of a device and broadcasts it via WebSockets. |
| **GET** | `/api/usage` | Calculates total live wattage, per-zone breakdown, and daily usage (kWh). |
| **GET** | `/api/alerts` | Checks and returns active warning or critical anomalies. |
| **POST** | `/api/admin/override-time` | Overrides the virtual office clock (0-23) to test after-hours alerts. |
| **POST** | `/api/admin/reset-time` | Resets the virtual clock to match local system time. |
| **POST** | `/api/admin/simulate-anomaly` | Forces all devices in a room ON and offsets timestamps to trigger 2h warnings. |

---

## 6. AI Integration & Anonymized Reports
- **Local LLM**: Utilizes `qwen2.5-coder:3b` (Quantized Q4_K_M) via Ollama.
- **Anonymization & Constraints**: The prompt engineering parameters strictly enforce anonymity rules. The AI translates raw JSON logs into conversational alerts while completely avoiding employee names (such as Nafisa or Tanvir) or administrative roles to prevent security leakage.
- **Proactive Warnings**: A background listener queries `/api/alerts` periodically. If a warning (after-hours usage) or critical alert (extreme off-hours load) is active, the bot generates a friendly, high-urgency message block containing warning indicators (e.g. 🚨, 🔥) and posts it to the configured channel.

---

## 7. Representative Hardware Schematic Pin-Mapping

The project includes a complete Wokwi hardware prototype mapping in the `/hardware` folder representing a single office zone (e.g. 2 Fans and 3 Lights) wired to an ESP32 microcontroller:

| Component | ESP32 GPIO Pin | Physical Connection | Description |
|---|---|---|---|
| **Fan 1 Actuator** | `GPIO 5` (D5) | Relay Module IN1 | Toggles Fan 1 power relay (COM to 5V, NO to Fan Motor 1 pin 1) |
| **Fan 2 Actuator** | `GPIO 18` (D18) | Relay Module IN2 | Toggles Fan 2 power relay (COM to 5V, NO to Fan Motor 2 pin 1) |
| **Light 1 Indicator** | `GPIO 19` (D19) | 330Ω -> LED 1 Anode | Drives Light 1 indicator LED |
| **Light 2 Indicator** | `GPIO 21` (D21) | 330Ω -> LED 2 Anode | Drives Light 2 indicator LED |
| **Light 3 Indicator** | `GPIO 22` (D22) | 330Ω -> LED 3 Anode | Drives Light 3 indicator LED |
| **Fan 1 Manual Switch** | `GPIO 12` (D12) | Pushbutton Pin 1A | Manual toggle switch for Fan 1 (2A to GND) |
| **Fan 2 Manual Switch** | `GPIO 13` (D13) | Pushbutton Pin 1A | Manual toggle switch for Fan 2 (2A to GND) |
| **Light 1 Manual Switch** | `GPIO 14` (D14) | Pushbutton Pin 1A | Manual toggle switch for Light 1 (2A to GND) |
| **Light 2 Manual Switch** | `GPIO 25` (D25) | Pushbutton Pin 1A | Manual toggle switch for Light 2 (2A to GND) |
| **Light 3 Manual Switch** | `GPIO 26` (D26) | Pushbutton Pin 1A | Manual toggle switch for Light 3 (2A to GND) |
| **ACS712 Current Sensor** | `GPIO 34` (D34) | Potentiometer wiper SIG | Analog signal input simulating current draw |

---

## 8. Discord Commands & Administrative Security

The Discord Bot client responds to prefix commands (`!`) and supports secure administrative commands:

- **`!status`**: Displays a humanized conversational report of the active devices across the three rooms.
- **`!room <room_name>`**: Fetches the active appliance count and status for a specific target room.
- **`!usage`**: Summarizes the office load in Watts, actual daily accumulated energy (kWh), and the projected 24-hour cycle estimation.
- **`!shutdown`**: *(Admin Only)* Triggers a remote bulk command to instantly turn off all 15 active lights and fans. This command is restricted using `@commands.has_permissions(administrator=True)`. Attempting execution without admin permissions outputs: `❌ Access Denied: You do not have the required permissions to execute this command.`

---

## 9. Hackathon Project Metadata
- **Team Name**: `ULAB_Anonymous_3.0`
- **Team Lead**: `Only Ovi`
- **Institution**: University of Liberal Arts Bangladesh (ULAB)
