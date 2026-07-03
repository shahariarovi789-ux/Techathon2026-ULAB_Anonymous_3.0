import asyncio
import json
import random
import sqlite3
import csv
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Lumina: Enterprise IoT Workspace Orchestrator API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration overrides for demo/judging purposes
VIRTUAL_HOUR_OVERRIDE: Optional[int] = None  # None means use actual time
SIMULATION_ACTIVE: bool = True               # True = Auto, False = Manual (demonstration)
CUMULATIVE_WH_OFFSET: float = 4200.0         # Starting daily offset (Wh)
SERVER_START_TIME = datetime.utcnow()

DATABASE_PATH = "lumina_history.db"

def get_virtual_time_string() -> str:
    current_time = datetime.now()
    if VIRTUAL_HOUR_OVERRIDE is not None:
        h = VIRTUAL_HOUR_OVERRIDE
        suffix = "PM" if h >= 12 else "AM"
        display_h = h - 12 if h > 12 else (12 if h == 0 else h)
        return f"{display_h:02d}:00 {suffix}"
    else:
        # Use localized 12-hour format with minutes, e.g. "08:12 PM"
        return current_time.strftime("%I:%M %p")

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS power_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        total_watts REAL NOT NULL,
        drawing_room REAL NOT NULL,
        work_room_1 REAL NOT NULL,
        work_room_2 REAL NOT NULL
    )
    """)
    conn.commit()
    
    # Pre-populate database with 24 hours of dynamic, realistic mock data if empty
    cursor.execute("SELECT COUNT(*) FROM power_history")
    if cursor.fetchone()[0] == 0:
        print("⚡ Pre-populating 24 hours of historical energy telemetry data...")
        now = datetime.utcnow()
        for i in range(24, 0, -1):
            time_point = now - timedelta(hours=i)
            hour = (time_point.hour + 6) % 24 # Convert to BST approx (+6)
            # Create realistic load curves: higher during 9 AM - 5 PM, lower at night
            if 9 <= hour <= 17:
                base_load = random.randint(180, 420)
            else:
                base_load = random.randint(20, 80)
                
            drawing = base_load * 0.2
            work1 = base_load * 0.4
            work2 = base_load * 0.4
            
            cursor.execute(
                "INSERT INTO power_history (timestamp, total_watts, drawing_room, work_room_1, work_room_2) VALUES (?, ?, ?, ?, ?)",
                (time_point.isoformat() + "Z", base_load, drawing, work1, work2)
            )
        conn.commit()
    conn.close()

def log_power_metric():
    try:
        metrics = get_metrics()
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO power_history (timestamp, total_watts, drawing_room, work_room_1, work_room_2) VALUES (?, ?, ?, ?, ?)",
            (
                datetime.utcnow().isoformat() + "Z",
                metrics["total_watts"],
                metrics["room_breakdown"]["Drawing Room"],
                metrics["room_breakdown"]["Work Room 1"],
                metrics["room_breakdown"]["Work Room 2"]
            )
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Database Warning] Failed to log power metrics: {e}")

# Centralized State Database (Strict Schema + helper fields)
DEVICES: Dict[str, dict] = {
    # Drawing Room
    "drawing_room_fan_1": {"name": "Fan 1", "type": "fan", "room": "Drawing Room", "status": False, "power_draw": 0, "nominal_power": 60, "last_changed": ""},
    "drawing_room_fan_2": {"name": "Fan 2", "type": "fan", "room": "Drawing Room", "status": False, "power_draw": 0, "nominal_power": 60, "last_changed": ""},
    "drawing_room_light_1": {"name": "Light 1", "type": "light", "room": "Drawing Room", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "drawing_room_light_2": {"name": "Light 2", "type": "light", "room": "Drawing Room", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "drawing_room_light_3": {"name": "Light 3", "type": "light", "room": "Drawing Room", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    # Work Room 1
    "work_room_1_fan_1": {"name": "Fan 1", "type": "fan", "room": "Work Room 1", "status": False, "power_draw": 0, "nominal_power": 60, "last_changed": ""},
    "work_room_1_fan_2": {"name": "Fan 2", "type": "fan", "room": "Work Room 1", "status": False, "power_draw": 0, "nominal_power": 60, "last_changed": ""},
    "work_room_1_light_1": {"name": "Light 1", "type": "light", "room": "Work Room 1", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "work_room_1_light_2": {"name": "Light 2", "type": "light", "room": "Work Room 1", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "work_room_1_light_3": {"name": "Light 3", "type": "light", "room": "Work Room 1", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    # Work Room 2
    "work_room_2_fan_1": {"name": "Fan 1", "type": "fan", "room": "Work Room 2", "status": False, "power_draw": 0, "nominal_power": 60, "last_changed": ""},
    "work_room_2_fan_2": {"name": "Fan 2", "type": "fan", "room": "Work Room 2", "status": False, "power_draw": 0, "nominal_power": 60, "last_changed": ""},
    "work_room_2_light_1": {"name": "Light 1", "type": "light", "room": "Work Room 2", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "work_room_2_light_2": {"name": "Light 2", "type": "light", "room": "Work Room 2", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "work_room_2_light_3": {"name": "Light 3", "type": "light", "room": "Work Room 2", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
}

# Initialize timestamps
startup_ts = datetime.utcnow().isoformat() + "Z"
for device_id in DEVICES:
    DEVICES[device_id]["last_changed"] = startup_ts

ALERTS: List[dict] = []

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        # Clean disconnected WebSockets if broadcast fails
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# Helper Metric Calculator
def get_metrics() -> dict:
    total_watts = sum(dev["power_draw"] for dev in DEVICES.values())
    
    # Per room breakdown
    room_breakdown = {}
    for room in ["Drawing Room", "Work Room 1", "Work Room 2"]:
        room_breakdown[room] = sum(dev["power_draw"] for dev in DEVICES.values() if dev["room"] == room)
    
    # Calculate simulated daily usage (kWh)
    # Wh consumed since server startup = (current average load * hours online)
    uptime_hours = (datetime.utcnow() - SERVER_START_TIME).total_seconds() / 3600.0
    accumulated_wh = total_watts * uptime_hours
    estimated_kwh = (CUMULATIVE_WH_OFFSET + accumulated_wh) / 1000.0
    
    # Calculate remaining hours of the simulated day to project 24h total
    current_time = datetime.now()
    hour = current_time.hour
    if VIRTUAL_HOUR_OVERRIDE is not None:
        hour = VIRTUAL_HOUR_OVERRIDE
    
    remaining_hours = max(0, 24 - hour)
    projected_additional_wh = total_watts * remaining_hours
    projected_kwh = (CUMULATIVE_WH_OFFSET + accumulated_wh + projected_additional_wh) / 1000.0
    
    return {
        "total_watts": total_watts,
        "room_breakdown": room_breakdown,
        "estimated_daily_kwh": round(estimated_kwh, 3),
        "projected_daily_kwh": round(projected_kwh, 3),
        "uptime_seconds": int((datetime.utcnow() - SERVER_START_TIME).total_seconds()),
        "simulation_active": SIMULATION_ACTIVE,
        "virtual_time": get_virtual_time_string()
    }

# Anomaly Alerts Checker
def check_all_alerts():
    global ALERTS
    ALERTS = []
    
    current_sim_time = get_virtual_time_string()
    
    # 1. After-hours warning (09:00 - 17:00 operational hours)
    current_time = datetime.now()
    hour = current_time.hour
    if VIRTUAL_HOUR_OVERRIDE is not None:
        hour = VIRTUAL_HOUR_OVERRIDE
        
    is_after_hours = (hour < 9 or hour >= 17)
    
    if is_after_hours:
        on_devices = [dev for dev_id, dev in DEVICES.items() if dev["status"]]
        if on_devices:
            # Group by room
            room_groups = {}
            for dev in on_devices:
                room_groups.setdefault(dev["room"], []).append(f"{dev['name']} ({dev['type']})")
            
            for room, names in room_groups.items():
                active_count = len(names)
                # Extreme off-hours load: if 3 or more devices are active (out of 5 per room)
                is_extreme = active_count >= 3
                severity = "critical" if is_extreme else "warning"
                title = f"CRITICAL: Extreme Off-Hours Load ({room})" if is_extreme else f"After-Hours Alert ({room})"
                
                # Make the ID dynamic based on the active devices set so toggles push fresh alerts
                room_key = room.replace(" ", "_").lower()
                devices_slug = "_".join(sorted(names)).replace(" ", "_").lower()
                alert_id = f"after_hours_{room_key}_{devices_slug}"
                
                ALERTS.append({
                    "id": alert_id,
                    "type": "after_hours",
                    "title": title,
                    "description": f"{active_count} devices left ON during non-operational hours ({current_sim_time}). Active: {', '.join(names)}",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "severity": severity,
                    "simulation_time": current_sim_time
                })

    # 2. Continuous active load warning (> 2 hours continuous run for all devices in a room)
    for room in ["Drawing Room", "Work Room 1", "Work Room 2"]:
        room_devices = [dev for dev in DEVICES.values() if dev["room"] == room]
        all_on = all(dev["status"] for dev in room_devices)
        if all_on:
            try:
                # Find the most recent toggle timestamp in the room
                timestamps = []
                for dev in room_devices:
                    ts_str = dev["last_changed"].replace("Z", "")
                    dt = datetime.fromisoformat(ts_str)
                    timestamps.append(dt)
                
                # The room became fully ON when the latest device was toggled ON
                latest_on_time = max(timestamps)
                duration_sec = (datetime.utcnow() - latest_on_time).total_seconds()
                
                # Trigger critical alert if all ON for > 2 hours (7200 seconds)
                if duration_sec > 7200:
                    hours = round(duration_sec / 3600.0, 1)
                    ALERTS.append({
                        "id": f"continuous_{room.replace(' ', '_').lower()}",
                        "type": "continuous_on",
                        "title": f"Critical Load Alert ({room})",
                        "description": f"All devices in {room} have been ON continuously for {hours} hours (detected at {current_sim_time}). High probability of neglected space.",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "severity": "critical",
                        "simulation_time": current_sim_time
                    })
            except Exception as e:
                print(f"Alert check failure: {e}")

# Probabilistic State Mutation Daemon (Every 15s)
async def simulation_loop():
    while True:
        await asyncio.sleep(15)
        
        if SIMULATION_ACTIVE:
            # Probabilistically toggle 1 or 2 random devices
            num_mutations = random.randint(1, 2)
            target_ids = random.sample(list(DEVICES.keys()), num_mutations)
            
            for dev_id in target_ids:
                dev = DEVICES[dev_id]
                # Mutate state
                new_status = not dev["status"]
                dev["status"] = new_status
                dev["power_draw"] = dev["nominal_power"] if new_status else 0
                dev["last_changed"] = datetime.utcnow().isoformat() + "Z"
                
            check_all_alerts()
            
            # Broadcast state update to WebSocket clients
            await manager.broadcast({
                "type": "telemetry_update",
                "devices": DEVICES,
                "alerts": ALERTS,
                "metrics": get_metrics()
            })

async def metrics_logger_loop():
    while True:
        log_power_metric()
        await asyncio.sleep(10) # Log every 10 seconds for live demo graphs

@app.on_event("startup")
async def startup_event():
    init_db()
    # Start telemetry simulation loop in background
    asyncio.create_task(simulation_loop())
    # Start metrics logging loop in background
    asyncio.create_task(metrics_logger_loop())

# REST API Endpoints
@app.get("/api/devices")
async def get_devices():
    return DEVICES

class ToggleRequest(BaseModel):
    status: Optional[bool] = None

@app.post("/api/devices/{device_id}/toggle")
async def toggle_device(device_id: str, payload: Optional[ToggleRequest] = None):
    if device_id not in DEVICES:
        raise HTTPException(status_code=404, detail="Device not found")
    
    dev = DEVICES[device_id]
    
    if payload and payload.status is not None:
        dev["status"] = payload.status
    else:
        dev["status"] = not dev["status"]
        
    dev["power_draw"] = dev["nominal_power"] if dev["status"] else 0
    dev["last_changed"] = datetime.utcnow().isoformat() + "Z"
    
    check_all_alerts()
    
    # Broadcast change
    data = {
        "type": "telemetry_update",
        "devices": DEVICES,
        "alerts": ALERTS,
        "metrics": get_metrics()
    }
    await manager.broadcast(data)
    return dev

@app.get("/api/usage")
async def get_usage():
    return get_metrics()

@app.get("/api/alerts")
async def get_alerts():
    check_all_alerts()
    return ALERTS

# Administrative Simulation Controls (for Demo and Evaluation)
@app.post("/api/admin/override-time")
async def override_time(hour: int):
    global VIRTUAL_HOUR_OVERRIDE
    if hour < 0 or hour > 23:
        raise HTTPException(status_code=400, detail="Invalid hour (0-23)")
    VIRTUAL_HOUR_OVERRIDE = hour
    check_all_alerts()
    await manager.broadcast({
        "type": "telemetry_update",
        "devices": DEVICES,
        "alerts": ALERTS,
        "metrics": get_metrics()
    })
    return {"message": f"Time overridden to {hour:02d}:00", "virtual_hour": hour}

@app.post("/api/admin/reset-time")
async def reset_time():
    global VIRTUAL_HOUR_OVERRIDE
    VIRTUAL_HOUR_OVERRIDE = None
    check_all_alerts()
    await manager.broadcast({
        "type": "telemetry_update",
        "devices": DEVICES,
        "alerts": ALERTS,
        "metrics": get_metrics()
    })
    return {"message": "Virtual clock synced with actual system time"}

@app.post("/api/admin/simulate-anomaly")
async def simulate_anomaly(room: str = "Work Room 2"):
    if room not in ["Drawing Room", "Work Room 1", "Work Room 2"]:
        raise HTTPException(status_code=400, detail="Invalid room name")
    
    # Force all devices in this room to ON and set their last changed to 3 hours ago
    three_hours_ago = (datetime.utcnow() - timedelta(hours=3)).isoformat() + "Z"
    for dev_id, dev in DEVICES.items():
        if dev["room"] == room:
            dev["status"] = True
            dev["power_draw"] = dev["nominal_power"]
            dev["last_changed"] = three_hours_ago
            
    check_all_alerts()
    await manager.broadcast({
        "type": "telemetry_update",
        "devices": DEVICES,
        "alerts": ALERTS,
        "metrics": get_metrics()
    })
    return {"message": f"Critical 3-hour continuous load anomaly simulated in {room}."}

class SimulationModeRequest(BaseModel):
    active: bool

@app.post("/api/admin/simulation-mode")
async def set_simulation_mode(payload: SimulationModeRequest):
    global SIMULATION_ACTIVE
    SIMULATION_ACTIVE = payload.active
    
    # Broadcast current state with updated mode info
    await manager.broadcast({
        "type": "telemetry_update",
        "devices": DEVICES,
        "alerts": ALERTS,
        "metrics": get_metrics()
    })
    return {"message": f"Simulation mode set to {'Auto' if SIMULATION_ACTIVE else 'Manual'}", "active": SIMULATION_ACTIVE}

@app.post("/api/admin/shutdown")
async def shutdown_all_devices():
    for dev_id, dev in DEVICES.items():
        dev["status"] = False
        dev["power_draw"] = 0
        dev["last_changed"] = datetime.utcnow().isoformat() + "Z"
        
    check_all_alerts()
    await manager.broadcast({
        "type": "telemetry_update",
        "devices": DEVICES,
        "alerts": ALERTS,
        "metrics": get_metrics()
    })
    return {"message": "All office utilities have been shut down successfully.", "devices": DEVICES}

# Real-Time Observation WebSocket Gateway
@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial full state immediately upon connection
        await websocket.send_json({
            "type": "initial_state",
            "devices": DEVICES,
            "alerts": ALERTS,
            "metrics": get_metrics()
        })
        while True:
            # Keep connection alive; discard any client input
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

@app.get("/api/history")
async def get_history(start_date: Optional[str] = None, end_date: Optional[str] = None):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    query = "SELECT timestamp, total_watts, drawing_room, work_room_1, work_room_2 FROM power_history"
    params = []
    
    if start_date and end_date:
        query += " WHERE timestamp BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    elif start_date:
        query += " WHERE timestamp >= ?"
        params.append(start_date)
    elif end_date:
        query += " WHERE timestamp <= ?"
        params.append(end_date)
        
    query += " ORDER BY timestamp ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for r in rows:
        history.append({
            "timestamp": r[0],
            "total_watts": r[1],
            "drawing_room": r[2],
            "work_room_1": r[3],
            "work_room_2": r[4]
        })
    return history

@app.get("/api/history/download")
async def download_history(start_date: Optional[str] = None, end_date: Optional[str] = None):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    query = "SELECT timestamp, total_watts, drawing_room, work_room_1, work_room_2 FROM power_history"
    params = []
    
    if start_date and end_date:
        query += " WHERE timestamp BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    elif start_date:
        query += " WHERE timestamp >= ?"
        params.append(start_date)
    elif end_date:
        query += " WHERE timestamp <= ?"
        params.append(end_date)
        
    query += " ORDER BY timestamp ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp (UTC)", "Total Power (W)", "Drawing Room (W)", "Work Room 1 (W)", "Work Room 2 (W)"])
    for r in rows:
        writer.writerow(r)
        
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="lumina_power_usage_report.csv"'
    }
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)

# Serve static files for the frontend dashboard
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
