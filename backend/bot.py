import os
import re
import json
import asyncio
import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load local environment configuration
load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Dummy user data strictly enforced per requirements
DUMMY_USERS = [
    {"name": "Nafisa Rahman", "email": "nafisa.rahman@yahoo.com", "phone": "+8801812345678"},
    {"name": "Tanvir Hossain", "email": "tanvir.hossain@yahoo.com", "phone": "+8801912345678"}
]

# Set up bot with command prefix
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Set of notified alert IDs to avoid spamming
notified_alerts = set()

async def query_local_llm(prompt: str) -> str:
    """Queries the local 4-bit quantized Qwen2.5-coder:3b model via Ollama."""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "qwen2.5-coder:3b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 120
                }
            }
            async with session.post("http://localhost:11434/api/generate", json=payload, timeout=6) as response:
                if response.status == 200:
                    res_json = await response.json()
                    text = res_json.get("response", "").strip()
                    if text:
                        return text
    except Exception as e:
        print(f"[Ollama LLM Warning] Local LLM offline or unreachable. Fallback template will be used. Error: {e}")
    return ""

async def generate_conversational_response(raw_summary: str, context_type: str) -> str:
    """Wrapper that tries to generate an LLM response, falling back to a structured template."""
    if context_type == "alert":
        prompt = f"""
You are Lumina, the AI energy guardian for our office.
Your task is to write a highly creative, warm, and conversational alert message to the office members in our Discord channel.
Avoid boring, repetitive templates. Be spontaneous, fun, yet clear!
Vary your tone—sometimes use light humor, sometimes a friendly eco-warning, and sometimes a late-night check-in.

CRITICAL CONSTRAINT: Do NOT mention any individual staff member names or employee names (like Nafisa, Tanvir, etc.) in the alert message. The warning must be anonymous.

Alert Details: {raw_summary}

Write a unique, friendly alert notification. Do NOT copy the standard example verbatim; invent something fresh, fun, and organic.

Friendly Alert Message:"""
    else:
        prompt = f"""
You are Lumina, a helpful and friendly Enterprise IoT assistant for our office.
Your task is to translate the raw status summary below into a warm, natural, and human-readable operational message.
Avoid raw data dumps or robotic bullet lists. Write 2-3 friendly sentences.

You should occasionally mention who might be responsible using the registered team staff:
- Nafisa Rahman (Email: nafisa.rahman@yahoo.com, Phone: +8801812345678)
- Tanvir Hossain (Email: tanvir.hossain@yahoo.com, Phone: +8801912345678)

Context type: {context_type}
Raw status summary: {raw_summary}

Friendly Response:"""

    llm_response = await query_local_llm(prompt)
    if llm_response:
        return llm_response
    
    # Fallback template if Ollama is not active
    user_mention = DUMMY_USERS[0]["name"] if "Drawing" in raw_summary else DUMMY_USERS[1]["name"]
    
    if context_type == "status":
        return (f"Hi there! Here's what's currently running: {raw_summary}. "
                f"It looks like {user_mention} might still be wrapping up some tasks in those active zones.")
    elif context_type == "room":
        return f"Sure thing! For that room, here is the current update: {raw_summary}. Let me know if you need help toggling anything!"
    elif context_type == "usage":
        return (f"Here is our current power draw report: {raw_summary}. "
                f"We are keeping an eye on it. Let's make sure Nafisa and Tanvir know to turn off devices when leaving!")
    elif context_type == "alert":
        room = "Work Room 2"
        if "Drawing" in raw_summary:
            room = "Drawing Room"
        elif "Work Room 1" in raw_summary or "work1" in raw_summary:
            room = "Work Room 1"
        
        fans_count = "1 fan"
        if "2 fans" in raw_summary or "2 active" in raw_summary:
            fans_count = "2 fans"
            
        lights_count = "2 lights"
        if "3 lights" in raw_summary or "3 active" in raw_summary:
            lights_count = "3 lights"
        elif "1 light" in raw_summary or "1 active" in raw_summary:
            lights_count = "1 light"
            
        # Parse simulated hour
        hour_str = "late"
        time_match = re.search(r"Simulated Time:\s*([0-9a-zA-Z:\s]+)\b", raw_summary)
        if time_match:
            hour_str = time_match.group(1).strip()
        else:
            for h in range(24):
                if f"({h:02d}:00)" in raw_summary or f" {h:02d}:00" in raw_summary:
                    if h >= 12:
                        hour_str = f"{h-12 if h > 12 else 12} PM"
                    else:
                        hour_str = f"{h if h > 0 else 12} AM"
                    break
                
        import random
        
        # Array of anonymous creative warnings
        templates = [
            f"⚡ **Energy Guardian Alert** | Hey team! It's {hour_str} and the {room} still has {fans_count} and {lights_count} running. Did someone forget to switch them off?",
            f"🕵️‍♂️ **Late Night Check** | Looks like the lights are still burning in {room}! We have {fans_count} and {lights_count} active at {hour_str}. Is someone still wrapping up work?",
            f"🍃 **Eco-Nudge** | Let's save some green squares! {room} is currently empty but has {fans_count} and {lights_count} left ON at {hour_str}. Could someone nearby toggle them off?",
            f"💤 **Sleep Mode Check** | The office has gone quiet, but {room} is still drawing power! {fans_count} and {lights_count} are active at {hour_str}. Did someone leave their desk running?",
            f"🚨 **Quick Reminder** | Non-operational hours are here, but the {room} is still humming ({fans_count} and {lights_count} ON at {hour_str}). Please turn them off if you're heading home!"
        ]
        return random.choice(templates)
    return f"Here is the latest update: {raw_summary}"

# Bot commands
@bot.event
async def on_ready():
    print(f"🤖 Discord Bot connected as {bot.user.name} ({bot.user.id})")
    # Start the live WebSocket alert listener
    bot.loop.create_task(websocket_alert_listener())

@bot.command(name="status")
async def status_command(ctx):
    """Fetch status for all rooms and humanize."""
    print("Received command: !status")
    async with ctx.typing():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BACKEND_URL}/api/devices") as response:
                    if response.status == 200:
                        devices = await response.json()
                        # Group devices by room and state
                        room_summaries = []
                        for room in ["Drawing Room", "Work Room 1", "Work Room 2"]:
                            room_devs = [dev for dev in devices.values() if dev["room"] == room]
                            active_fans = sum(1 for dev in room_devs if dev["status"] and dev["type"] == "fan")
                            active_lights = sum(1 for dev in room_devs if dev["status"] and dev["type"] == "light")
                            
                            total_active = active_fans + active_lights
                            if total_active == 0:
                                room_summaries.append(f"{room}: all off")
                            else:
                                details = []
                                if active_fans > 0:
                                    details.append(f"{active_fans} fan{'s' if active_fans > 1 else ''} ON")
                                if active_lights > 0:
                                    details.append(f"{active_lights} light{'s' if active_lights > 1 else ''} ON")
                                room_summaries.append(f"{room}: {', '.join(details)}")
                        
                        raw_summary = ". ".join(room_summaries) + "."
                        friendly_summary = await generate_conversational_response(raw_summary, "status")
                        await ctx.send(friendly_summary)
                    else:
                        await ctx.send("⚠️ Failed to reach the state manager backend API.")
        except Exception as e:
            await ctx.send(f"⚠️ Error occurred while communication with backend: {e}")

@bot.command(name="room")
async def room_command(ctx, *, room_name: str):
    """Fetch status for a specific room."""
    print(f"Received command: !room {room_name}")
    async with ctx.typing():
        # Clean the input to map to rooms
        room_clean = room_name.lower().replace("_", " ").strip()
        target_room = None
        if "draw" in room_clean:
            target_room = "Drawing Room"
        elif "work1" in room_clean or "work room 1" in room_clean or "room 1" in room_clean:
            target_room = "Work Room 1"
        elif "work2" in room_clean or "work room 2" in room_clean or "room 2" in room_clean:
            target_room = "Work Room 2"
            
        if not target_room:
            await ctx.send("❌ Room not recognized. Please specify: `Drawing Room`, `Work Room 1`, or `Work Room 2`.")
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BACKEND_URL}/api/devices") as response:
                    if response.status == 200:
                        devices = await response.json()
                        room_devs = [dev for dev in devices.values() if dev["room"] == target_room]
                        
                        # Count states
                        active_fans = sum(1 for dev in room_devs if dev["status"] and dev["type"] == "fan")
                        active_lights = sum(1 for dev in room_devs if dev["status"] and dev["type"] == "light")
                        
                        total_active = active_fans + active_lights
                        if total_active == 0:
                            raw_summary = f"All 6 devices in {target_room} are currently switched OFF."
                        else:
                            details = []
                            if active_fans > 0:
                                details.append(f"{active_fans} fan{'s' if active_fans > 1 else ''} active")
                            if active_lights > 0:
                                details.append(f"{active_lights} light{'s' if active_lights > 1 else ''} active")
                            raw_summary = f"In {target_room}, we have {', '.join(details)}."
                            
                        friendly_summary = await generate_conversational_response(raw_summary, "room")
                        await ctx.send(friendly_summary)
                    else:
                        await ctx.send("⚠️ Failed to reach the state manager backend API.")
        except Exception as e:
            await ctx.send(f"⚠️ Error communicating with backend: {e}")

@bot.command(name="usage")
async def usage_command(ctx):
    """Fetch total power draw and daily estimated usage."""
    print("Received command: !usage")
    async with ctx.typing():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BACKEND_URL}/api/usage") as response:
                    if response.status == 200:
                        metrics = await response.json()
                        total_watts = metrics.get("total_watts", 0)
                        daily_kwh = metrics.get("estimated_daily_kwh", 0.0)
                        
                        raw_summary = f"Total power right now: {total_watts}W. Today's estimated usage is {daily_kwh} kWh."
                        friendly_summary = await generate_conversational_response(raw_summary, "usage")
                        await ctx.send(friendly_summary)
                    else:
                        await ctx.send("⚠️ Failed to reach the usage API.")
        except Exception as e:
            await ctx.send(f"⚠️ Error communicating with backend: {e}")

# Live WebSocket alert listener
async def websocket_alert_listener():
    """Listens to the backend WebSocket gateway and dispatches alerts instantly (sub-second latency)."""
    global notified_alerts
    await bot.wait_until_ready()
    
    # Resolve target channel
    target_channel = None
    if CHANNEL_ID:
        try:
            target_channel = bot.get_channel(int(CHANNEL_ID)) or await bot.fetch_channel(int(CHANNEL_ID))
        except Exception as e:
            print(f"[Discord Bot Warning] Could not resolve channel ID {CHANNEL_ID}: {e}")
            
    ws_url = BACKEND_URL.replace("http://", "ws://") + "/ws/telemetry"
    print(f"🔌 WebSocket Alert Listener connecting to {ws_url}...")
    
    while not bot.is_closed():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url) as ws:
                    print("🔌 WebSocket Alert Listener Connected & Live!")
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            alerts = data.get("alerts", [])
                            current_alert_ids = set()
                            
                            for alert in alerts:
                                alert_id = alert["id"]
                                current_alert_ids.add(alert_id)
                                
                                # If alert is new, dispatch message instantly
                                if alert_id not in notified_alerts:
                                    title = alert["title"]
                                    desc = alert["description"]
                                    sim_time = alert.get("simulation_time", "late")
                                    
                                    # Generate conversational warning message via local LLM / template fallback
                                    # Pass simulation time inside raw_summary for prompt matching
                                    raw_sum = f"Alert: {title}. Details: {desc}. Simulated Time: {sim_time}."
                                    friendly_alert = await generate_conversational_response(raw_sum, "alert")
                                    
                                    if target_channel:
                                        await target_channel.send(friendly_alert)
                                        print(f"[WebSocket Alert Sent] {friendly_alert}")
                                    else:
                                        print(f"[Console Only Alert - Channel ID Not Configured] {friendly_alert}")
                                        
                                    notified_alerts.add(alert_id)
                            
                            # Clean up resolved alerts
                            notified_alerts = notified_alerts.intersection(current_alert_ids)
        except Exception as e:
            print(f"[WebSocket Loop Warning] Connection lost or failed: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

def main():
    if not TOKEN:
        print("[Discord Bot Error] DISCORD_BOT_TOKEN not found in environment. Please set it in backend/.env")
        return
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
