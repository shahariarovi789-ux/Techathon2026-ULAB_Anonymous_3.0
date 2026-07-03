import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
CUMULATIVE_WH_OFFSET: float = 4200.0         # Starting daily offset (Wh)
SERVER_START_TIME = datetime.utcnow()

# Centralized State Database (Strict Schema + helper fields)
DEVICES: Dict[str, dict] = {
    # Drawing Room
    "drawing_room_fan_1": {"name": "Fan 1", "type": "fan", "room": "Drawing Room", "status": False, "power_draw": 0, "nominal_power": 60, "last_changed": ""},
    "drawing_room_fan_2": {"name": "Fan 2", "type": "fan", "room": "Drawing Room", "status": False, "power_draw": 0, "nominal_power": 60, "last_changed": ""},
    "drawing_room_light_1": {"name": "Light 1", "type": "light", "room": "Drawing Room", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "drawing_room_light_2": {"name": "Light 2", "type": "light", "room": "Drawing Room", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "drawing_room_light_3": {"name": "Light 3", "type": "light", "room": "Drawing Room", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "drawing_room_light_4": {"name": "Light 4", "type": "light", "room": "Drawing Room", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    # Work Room 1
    "work_room_1_fan_1": {"name": "Fan 1", "type": "fan", "room": "Work Room 1", "status": False, "power_draw": 0, "nominal_power": 60, "last_changed": ""},
    "work_room_1_fan_2": {"name": "Fan 2", "type": "fan", "room": "Work Room 1", "status": False, "power_draw": 0, "nominal_power": 60, "last_changed": ""},
    "work_room_1_light_1": {"name": "Light 1", "type": "light", "room": "Work Room 1", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "work_room_1_light_2": {"name": "Light 2", "type": "light", "room": "Work Room 1", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "work_room_1_light_3": {"name": "Light 3", "type": "light", "room": "Work Room 1", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "work_room_1_light_4": {"name": "Light 4", "type": "light", "room": "Work Room 1", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    # Work Room 2
    "work_room_2_fan_1": {"name": "Fan 1", "type": "fan", "room": "Work Room 2", "status": False, "power_draw": 0, "nominal_power": 60, "last_changed": ""},
    "work_room_2_fan_2": {"name": "Fan 2", "type": "fan", "room": "Work Room 2", "status": False, "power_draw": 0, "nominal_power": 60, "last_changed": ""},
    "work_room_2_light_1": {"name": "Light 1", "type": "light", "room": "Work Room 2", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "work_room_2_light_2": {"name": "Light 2", "type": "light", "room": "Work Room 2", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "work_room_2_light_3": {"name": "Light 3", "type": "light", "room": "Work Room 2", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
    "work_room_2_light_4": {"name": "Light 4", "type": "light", "room": "Work Room 2", "status": False, "power_draw": 0, "nominal_power": 15, "last_changed": ""},
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
    
    return {
        "total_watts": total_watts,
        "room_breakdown": room_breakdown,
        "estimated_daily_kwh": round(estimated_kwh, 3),
        "uptime_seconds": int((datetime.utcnow() - SERVER_START_TIME).total_seconds())
    }

# Anomaly Alerts Checker
def check_all_alerts():
    global ALERTS
    ALERTS = []
    
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
                ALERTS.append({
                    "id": f"after_hours_{room.replace(' ', '_').lower()}",
                    "type": "after_hours",
                    "title": f"After-Hours Alert ({room})",
                    "description": f"{len(names)} devices left ON during non-operational hours ({hour:02d}:00). Active: {', '.join(names)}",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "severity": "warning"
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
                        "description": f"All devices in {room} have been ON continuously for {hours} hours. High probability of neglected space.",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "severity": "critical"
                    })
            except Exception as e:
                print(f"Alert check failure: {e}")

# Probabilistic State Mutation Daemon (Every 15s)
async def simulation_loop():
    while True:
        await asyncio.sleep(15)
        
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

@app.on_event("startup")
async def startup_event():
    # Start telemetry simulation loop in background
    asyncio.create_task(simulation_loop())

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
