# 🚀 Building in Public: Unifying IoT Digital Twins & Conversational Agents

I just finished building **Lumina**—an Enterprise IoT Observability dashboard & conversational assistant, designed to solve the age-old office problem: leaving lights and HVAC running after hours. 

Here are the key architectural challenges we solved:

### 1. Zero-Drift Data Parity ⚖️
A common pitfall in multi-interface systems (like having a Web UI and a Discord bot) is when they go out of sync. If the Web UI says the Drawing Room fan is ON, but the Discord bot reports it's OFF, trust is lost. 
We solved this by establishing a **single source of truth backend** using FastAPI. Both the real-time SVG floor plan and the `discord.py` client consume the *same* backend state API, ensuring 100% data parity at all times.

### 2. Sub-Second Observability with WebSockets ⚡
Static pages require browser refreshes. To make the dashboard feel alive, we implemented a persistent **WebSocket gateway**. The backend runs a telemetry simulation loop, mutation engine, and anomaly checker on background threads. The instant a device state shifts, updates are pushed down to the client DOM seamlessly with no page reloads.

### 3. Humanizing Telemetry with Local LLMs 🧠
Robotic text dumps are hard to read. Instead of hardcoding responses for Discord commands like `!status` or `!usage`, we integrated a local **4-bit quantized Qwen-3B model** running offline via Ollama. The bot parses raw JSON status data into a contextual prompt, instructing the model to generate concise, friendly, and human-readable operational summaries. 

### 4. Proactive Anomaly Detection Loop 🚨
Lumina runs a continuous polling routine in the background. If a zone remains active past 5:00 PM (non-operational hours) or all devices in a room have been drawing load for more than 2 hours continuously, the system triggers alerts, prompts the LLM to explain the danger friendly, and posts proactive warnings directly to Discord.

We also designed a full **ESP32 hardware schematic** utilizing galvanic opto-isolation and Root Mean Square (RMS) equations for ACS712 current sensing to complete the bridge between software and physical hardware.

Built with Python, FastAPI, WebSockets, Vanilla JS, and Tailwind CSS. 

Check out the repository layout here! Let me know your thoughts on event-driven IoT architectures in the comments! 👇

#IoT #DigitalTwin #FastAPI #WebSockets #Python #LLM #Ollama #EdgeAI #EmbeddedSystems #Engineering
