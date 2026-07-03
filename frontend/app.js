// Core Dashboard Observability Logic

const BACKEND_REST = "http://localhost:8000";
const BACKEND_WS = "ws://localhost:8000/ws/telemetry";

let socket = null;
let deviceCoordinates = {
  "drawing_room_fan_1": {"top": 21.5, "left": 17.5},
  "drawing_room_fan_2": {"top": 51.5, "left": 17.5},
  "drawing_room_light_1": {"top": 19.5, "left": 11.0},
  "drawing_room_light_2": {"top": 19.5, "left": 24.0},
  "drawing_room_light_3": {"top": 60.5, "left": 17.5},
  "work_room_1_fan_1": {"top": 21.5, "left": 42.5},
  "work_room_1_fan_2": {"top": 51.5, "left": 42.5},
  "work_room_1_light_1": {"top": 19.5, "left": 35.5},
  "work_room_1_light_2": {"top": 19.5, "left": 49.5},
  "work_room_1_light_3": {"top": 60.5, "left": 42.5},
  "work_room_2_fan_1": {"top": 21.5, "left": 66.5},
  "work_room_2_fan_2": {"top": 51.5, "left": 66.5},
  "work_room_2_light_1": {"top": 19.5, "left": 59.5},
  "work_room_2_light_2": {"top": 19.5, "left": 73.5},
  "work_room_2_light_3": {"top": 60.5, "left": 66.5}
};
let calibrationMode = false;
let currentDevices = {};

// Load coordinates config
async function initCoordinates() {
  try {
    const res = await fetch("floorplan_coords.json");
    const loadedCoords = await res.json();
    deviceCoordinates = loadedCoords;
    console.log("Device coordinates loaded successfully from JSON:", deviceCoordinates);
  } catch (err) {
    console.warn("Could not load floorplan_coords.json via HTTP/Fetch (possibly file:// protocol restriction). Using local hardcoded coordinates fallback.", err);
  }
}

// Establish real-time WebSocket connection
function connectWebSocket() {
  socket = new WebSocket(BACKEND_WS);

  const statusIndicator = document.getElementById("conn-status");

  socket.onopen = () => {
    console.log("📡 Observability WebSocket Gateway Connected!");
    statusIndicator.className = "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border border-emerald-500/20 bg-emerald-500/10 text-emerald-400";
    statusIndicator.innerHTML = '<span class="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>ONLINE';
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "initial_state" || data.type === "telemetry_update") {
        currentDevices = data.devices;
        renderDashboard(data.devices, data.alerts, data.metrics);
      }
    } catch (err) {
      console.error("WebSocket message parsing error:", err);
    }
  };

  socket.onclose = () => {
    console.warn("🔌 WebSocket disconnected. Retrying connection in 3 seconds...");
    statusIndicator.className = "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border border-red-500/20 bg-red-500/10 text-red-400";
    statusIndicator.innerHTML = '<span class="h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>DISCONNECTED';
    setTimeout(connectWebSocket, 3000);
  };

  socket.onerror = (err) => {
    console.error("WebSocket encounterd error:", err);
    socket.close();
  };
}

// Toggle device state manually via REST endpoint
async function toggleDevice(deviceId) {
  if (calibrationMode) return; // Prevent toggle when calibrating coordinates
  
  try {
    const res = await fetch(`${BACKEND_REST}/api/devices/${deviceId}/toggle`, {
      method: "POST"
    });
    if (res.status === 200) {
      console.log(`Device ${deviceId} toggled successfully.`);
    }
  } catch (err) {
    console.error(`Failed to toggle device ${deviceId}:`, err);
  }
}

// Format timestamp to localized readable string
function formatTimestamp(isoString) {
  if (!isoString) return "N/A";
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch (err) {
    return isoString;
  }
}

// Render device indicators overlay on the floor plan
function renderFloorplanOverlays(devices) {
  const overlayContainer = document.getElementById("floorplan-overlays");
  overlayContainer.innerHTML = "";

  for (const [id, dev] of Object.entries(devices)) {
    const coords = deviceCoordinates[id] || { top: 50, left: 50 }; // Fallback to center
    
    const node = document.createElement("div");
    node.className = `absolute device-node tooltip w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold border transition-all duration-300 pointer-events-auto ${
      dev.type === "fan" 
        ? (dev.status ? "fan-spin" : "fan-off") 
        : (dev.status ? "light-glow" : "light-off")
    }`;
    node.style.top = `${coords.top}%`;
    node.style.left = `${coords.left}%`;

    // Inner icon structure
    let icon = "";
    if (dev.type === "fan") {
      icon = `
        <svg class="h-4.5 w-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <circle cx="12" cy="12" r="3" stroke-width="2" />
        </svg>`;
    } else {
      icon = `
        <svg class="h-4.5 w-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>`;
    }
    
    node.innerHTML = `
      ${icon}
      <span class="tooltip-text">
        <strong class="text-indigo-400 block">${dev.room}</strong>
        ${dev.name} (${dev.type.toUpperCase()})<br>
        Status: <span class="${dev.status ? "text-green-400" : "text-slate-400"}">${dev.status ? "ON" : "OFF"}</span><br>
        Power: ${dev.power_draw}W<br>
        Last Changed: ${formatTimestamp(dev.last_changed)}
      </span>
    `;

    // Wire single click to toggle device
    node.addEventListener("click", (e) => {
      e.stopPropagation(); // Stop click propagating to the floor plan container in calibration mode
      toggleDevice(id);
    });

    overlayContainer.appendChild(node);
  }
}

// Render Room/Zone Detailed cards in the bottom
function renderRoomLists(devices) {
  const rooms = {
    "Drawing Room": document.getElementById("room-list-drawing"),
    "Work Room 1": document.getElementById("room-list-work1"),
    "Work Room 2": document.getElementById("room-list-work2"),
  };

  // Clear lists
  for (const el of Object.values(rooms)) {
    el.innerHTML = "";
  }

  for (const [id, dev] of Object.entries(devices)) {
    const listEl = rooms[dev.room];
    if (!listEl) continue;

    const row = document.createElement("div");
    row.className = "flex justify-between items-center bg-slate-900/40 hover:bg-slate-900/80 p-2 rounded-lg border border-white/5 transition";
    
    const icon = dev.type === "fan" 
      ? `<svg class="h-4 w-4 text-blue-400 ${dev.status ? 'animate-spin' : ''}" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /></svg>`
      : `<svg class="h-4 w-4 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>`;

    row.innerHTML = `
      <div class="flex items-center gap-2">
        ${icon}
        <span class="font-medium text-slate-300">${dev.name}</span>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-[10px] text-slate-500 font-semibold uppercase">${dev.power_draw}W</span>
        <button class="px-2 py-0.5 rounded text-[10px] font-bold transition ${
          dev.status 
            ? "bg-green-500/10 text-green-400 border border-green-500/20" 
            : "bg-slate-800 text-slate-400 border border-slate-700"
        }">${dev.status ? "ON" : "OFF"}</button>
      </div>
    `;

    // Click handler for list toggles
    row.querySelector("button").addEventListener("click", () => {
      toggleDevice(id);
    });

    listEl.appendChild(row);
  }
}

// Render Alert Nodes
function renderAlerts(alerts) {
  const alertsContainer = document.getElementById("alerts-container");
  const alertCountEl = document.getElementById("alert-count");
  
  alertCountEl.textContent = alerts.length;
  alertsContainer.innerHTML = "";

  if (alerts.length === 0) {
    alertsContainer.innerHTML = `
      <div class="text-center py-8 text-slate-500 text-sm">
        <svg class="h-8 w-8 mx-auto mb-2 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.952 11.952 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
        System secure. No anomalies detected.
      </div>
    `;
    return;
  }

  alerts.forEach(alert => {
    const alertDiv = document.createElement("div");
    
    // Choose styling based on severity
    const isCritical = alert.severity === "critical";
    const borderCol = isCritical ? "border-red-500/30 bg-red-500/5 text-red-300" : "border-amber-500/30 bg-amber-500/5 text-amber-300";
    const tagBg = isCritical ? "bg-red-500/10 text-red-400 border border-red-500/20" : "bg-amber-500/10 text-amber-400 border border-amber-500/20";
    const emoji = isCritical ? "🚨" : "⚠️";

    alertDiv.className = `border rounded-xl p-3 text-xs flex flex-col gap-1.5 transition ${borderCol}`;
    alertDiv.innerHTML = `
      <div class="flex justify-between items-center">
        <span class="font-bold flex items-center gap-1.5">
          <span>${emoji}</span>
          ${alert.title}
        </span>
        <span class="px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${tagBg}">
          ${alert.severity}
        </span>
      </div>
      <p class="text-slate-400">${alert.description}</p>
      <span class="text-[9px] text-slate-500 font-mono text-right">Time: ${formatTimestamp(alert.timestamp)}</span>
    `;
    alertsContainer.appendChild(alertDiv);
  });
}

// Render Dashboard Data Parity
function renderDashboard(devices, alerts, metrics) {
  // Update power load metrics
  document.getElementById("metric-watts").textContent = metrics.total_watts;
  document.getElementById("metric-kwh").textContent = metrics.estimated_daily_kwh.toFixed(3);

  // Update Progress Bars & breakdown values
  const breakdowns = {
    "Drawing Room": { watts: metrics.room_breakdown["Drawing Room"], bar: "bar-drawing", text: "breakdown-drawing" },
    "Work Room 1": { watts: metrics.room_breakdown["Work Room 1"], bar: "bar-work1", text: "breakdown-work1" },
    "Work Room 2": { watts: metrics.room_breakdown["Work Room 2"], bar: "bar-work2", text: "breakdown-work2" },
  };

  const maxPower = 300; // Reference maximum for progress bar scaling (e.g. 300W maximum room load)
  for (const [room, data] of Object.entries(breakdowns)) {
    document.getElementById(data.text).textContent = `${data.watts}W`;
    const percentage = Math.min((data.watts / maxPower) * 100, 100);
    document.getElementById(data.bar).style.width = `${percentage}%`;
  }

  // Render nodes and list elements
  renderFloorplanOverlays(devices);
  renderRoomLists(devices);
  renderAlerts(alerts);

  // Update Simulation Mode Switcher Buttons
  const btnAuto = document.getElementById("btn-mode-auto");
  const btnManual = document.getElementById("btn-mode-manual");
  const indicatorAuto = document.getElementById("indicator-auto");
  const indicatorManual = document.getElementById("indicator-manual");
  
  if (metrics.simulation_active) {
    // Auto Mode active styling
    btnAuto.className = "flex-grow py-2 px-3 rounded-lg text-xs font-bold transition duration-300 flex items-center justify-center gap-1.5 bg-blue-600/20 text-blue-400 border border-blue-500/20";
    btnManual.className = "flex-grow py-2 px-3 rounded-lg text-xs font-bold transition duration-300 flex items-center justify-center gap-1.5 text-slate-400 hover:text-slate-200";
    indicatorAuto.className = "h-2.5 w-2.5 rounded-full bg-blue-500 animate-pulse";
    indicatorManual.className = "h-2.5 w-2.5 rounded-full bg-slate-600";
  } else {
    // Manual Mode active styling
    btnAuto.className = "flex-grow py-2 px-3 rounded-lg text-xs font-bold transition duration-300 flex items-center justify-center gap-1.5 text-slate-400 hover:text-slate-200";
    btnManual.className = "flex-grow py-2 px-3 rounded-lg text-xs font-bold transition duration-300 flex items-center justify-center gap-1.5 bg-emerald-600/20 text-emerald-400 border border-emerald-500/20";
    indicatorAuto.className = "h-2.5 w-2.5 rounded-full bg-slate-600";
    indicatorManual.className = "h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse";
  }
}

// Setup Event Listeners
function setupEventListeners() {
  const calToggle = document.getElementById("cal-toggle");
  const calibrationLog = document.getElementById("calibration-log");
  const calCoordsSpan = document.getElementById("cal-coords");
  const btnCopyCoords = document.getElementById("btn-copy-coords");
  
  const timeSlider = document.getElementById("time-slider");
  const btnOverrideTime = document.getElementById("btn-override-time");
  const btnResetTime = document.getElementById("btn-reset-time");
  const timeOverrideLabel = document.getElementById("time-override-label");
  
  const btnTriggerAnomaly = document.getElementById("btn-trigger-anomaly");
  const floorplanImage = document.getElementById("floorplan-image");

  // Handle Calibration Toggle
  calToggle.addEventListener("change", () => {
    calibrationMode = calToggle.checked;
    if (calibrationMode) {
      calibrationLog.classList.remove("hidden");
      console.log("Calibration Mode Activated. Click on floorplan to measure percentages.");
    } else {
      calibrationLog.classList.add("hidden");
    }
  });

  // Measure relative percentages on click
  floorplanImage.addEventListener("click", (e) => {
    if (!calibrationMode) return;

    const rect = floorplanImage.getBoundingClientRect();
    // Calculate click coordinates as percentages of the image size
    const xPercent = ((e.clientX - rect.left) / rect.width) * 100;
    const yPercent = ((e.clientY - rect.top) / rect.height) * 100;

    const coordsStr = `"top": ${yPercent.toFixed(1)}, "left": ${xPercent.toFixed(1)}`;
    calCoordsSpan.textContent = coordsStr;
    console.log(`Calibrated coordinates: {${coordsStr}}`);
  });

  // Copy coordinates to clipboard
  btnCopyCoords.addEventListener("click", () => {
    const textToCopy = calCoordsSpan.textContent;
    navigator.clipboard.writeText(`{ ${textToCopy} }`)
      .then(() => {
        const originalColor = btnCopyCoords.className;
        btnCopyCoords.className = "text-green-400 bg-slate-800 p-1.5 rounded-lg border border-green-500/20";
        setTimeout(() => {
          btnCopyCoords.className = originalColor;
        }, 1500);
      })
      .catch(err => console.error("Clipboard copy failed:", err));
  });

  // Time Slider Changes
  timeSlider.addEventListener("input", () => {
    const val = parseInt(timeSlider.value);
    const label = val >= 12 ? `${val === 12 ? 12 : val - 12}:00 PM` : `${val === 0 ? 12 : val}:00 AM`;
    timeOverrideLabel.textContent = label;
  });

  // Override time
  btnOverrideTime.addEventListener("click", async () => {
    const val = parseInt(timeSlider.value);
    try {
      const res = await fetch(`${BACKEND_REST}/api/admin/override-time?hour=${val}`, { method: "POST" });
      if (res.status === 200) {
        timeOverrideLabel.className = "text-xs bg-red-950 px-2 py-0.5 rounded text-red-400 font-bold border border-red-500/20 animate-pulse";
      }
    } catch (err) {
      console.error("Time override request failed:", err);
    }
  });

  // Reset time
  btnResetTime.addEventListener("click", async () => {
    try {
      const res = await fetch(`${BACKEND_REST}/api/admin/reset-time`, { method: "POST" });
      if (res.status === 200) {
        timeOverrideLabel.textContent = "Real Time";
        timeOverrideLabel.className = "text-xs bg-slate-800 px-2 py-0.5 rounded text-blue-400 font-bold border border-white/5";
      }
    } catch (err) {
      console.error("Time reset request failed:", err);
    }
  });

  // Trigger Anomaly simulation
  btnTriggerAnomaly.addEventListener("click", async () => {
    try {
      const res = await fetch(`${BACKEND_REST}/api/admin/simulate-anomaly?room=Work Room 2`, { method: "POST" });
      if (res.status === 200) {
        console.log("Anomaly simulated successfully.");
      }
    } catch (err) {
      console.error("Failed to simulate anomaly:", err);
    }
  });

  // Simulation Mode Controls
  const btnModeAuto = document.getElementById("btn-mode-auto");
  const btnModeManual = document.getElementById("btn-mode-manual");

  btnModeAuto.addEventListener("click", async () => {
    try {
      const res = await fetch(`${BACKEND_REST}/api/admin/simulation-mode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: true })
      });
      if (res.status === 200) {
        console.log("Simulation set to AUTO mode.");
      }
    } catch (err) {
      console.error("Failed to set simulation to auto:", err);
    }
  });

  btnModeManual.addEventListener("click", async () => {
    try {
      const res = await fetch(`${BACKEND_REST}/api/admin/simulation-mode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: false })
      });
      if (res.status === 200) {
        console.log("Simulation set to MANUAL mode.");
      }
    } catch (err) {
      console.error("Failed to set simulation to manual:", err);
    }
  });
}

// Entry Point
window.addEventListener("DOMContentLoaded", async () => {
  await initCoordinates();
  setupEventListeners();
  connectWebSocket();
});
