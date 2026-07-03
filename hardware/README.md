# 🔌 Lumina Hardware Integration: Representative Zone Schematic

This folder contains the complete wiring guide, pin mapping, electrical reasoning, and ESP32 firmware code required to build the Hardware/Electrical Digital Twin for a single zone (e.g., Drawing Room) using an **ESP32 NodeMCU**.

---

## 1. Component Specification (Single Room: 2 Fans, 3 Lights)

To represent a single room's IoT assets, we use the following hardware components:
- **1x ESP32 NodeMCU Development Board** (30-pin or 38-pin version)
- **3x LEDs (Yellow/Warm White)** - Representing Illumination (Lights 1, 2, 3)
- **3x 330Ω Current-Limiting Resistors** - Protects LEDs from overcurrent from ESP32 pins
- **2x 5V Optocoupler-Isolated Relay Modules** (or DC motors directly) - Controls high-power Fan AC/DC lines (Fans 1, 2)
- **1x ACS712-05B Current Sensor Module** (Hall-effect) - Measures total current draw of the room

---

## 2. Pin-Mapping Table

| ESP32 GPIO Pin | Physical Component | Signal Type | Electrical Specification | Description |
|---|---|---|---|---|
| **GPIO 5** | Relay 1 (Fan 1 Control) | Digital Output | 3.3V Logic -> 5V Relay IN | Toggles Fan 1 power relay (Active Low/High depending on module) |
| **GPIO 18** | Relay 2 (Fan 2 Control) | Digital Output | 3.3V Logic -> 5V Relay IN | Toggles Fan 2 power relay |
| **GPIO 19** | Light 1 LED | Digital Output | 3.3V Logic -> 330Ω -> LED | Drives Light 1 indicator |
| **GPIO 21** | Light 2 LED | Digital Output | 3.3V Logic -> 330Ω -> LED | Drives Light 2 indicator |
| **GPIO 22** | Light 3 LED | Digital Output | 3.3V Logic -> 330Ω -> LED | Drives Light 3 indicator |
| **GPIO 34** | ACS712 Current Sensor OUT | Analog Input | Analog Voltage (ADC1_CH6) | Measures analog output of current sensor |
| **3.3V** | ACS712 VCC & LED Anodes | Power | 3.3V Power Line | Supply voltage for logic components |
| **GND** | ESP32 GND, Relay GND, ACS712 GND | Ground | Reference Ground | Common reference ground for all modules |

---

## 3. Connection & Wiring Guide

Follow this step-by-step wiring guide to assemble the circuit:

### A. LEDs (Illumination Simulation)
1. Place **Light 1 LED**, **Light 2 LED**, and **Light 3 LED** on the breadboard.
2. For each LED, connect the **Cathode (shorter leg)** to the common Ground (`GND`) rail.
3. For **Light 1 LED**, connect the **Anode (longer leg)** through a `330Ω resistor` to ESP32 **GPIO 19**.
4. For **Light 2 LED**, connect the **Anode (longer leg)** through a `330Ω resistor` to ESP32 **GPIO 21**.
5. For **Light 3 LED**, connect the **Anode (longer leg)** through a `330Ω resistor` to ESP32 **GPIO 22**.

### B. Relays (HVAC Fan Control)
1. Connect ESP32 **GND** pin to the Relay Module **GND** pin.
2. Connect ESP32 **Vin** (5V, if powered by USB) or a separate 5V power source to the Relay Module **VCC** pin.
3. Connect ESP32 **GPIO 5** to the Relay Module **IN1** pin.
4. Connect ESP32 **GPIO 18** to the Relay Module **IN2** pin.
5. Cut the Hot/Live wire of the **Fan 1** power line. Connect one end to the **Common (COM)** terminal of Relay 1 and the other end to the **Normally Open (NO)** terminal of Relay 1.
6. Repeat for **Fan 2** using the **Common (COM)** and **Normally Open (NO)** terminals of Relay 2.

### C. ACS712 Current Sensor
1. Connect ACS712 **VCC** to ESP32 **3.3V** pin (or 5V if using the 5V sensor, but use a voltage divider on the output to keep it under 3.3V to prevent ADC damage).
2. Connect ACS712 **GND** to ESP32 **GND**.
3. Connect ACS712 **OUT** (analog output) to ESP32 **GPIO 34** (ADC Pin).
4. Connect the main Hot/Live supply line feeding the room's relays *in series* through the ACS712 terminal block.

---

## 4. Electrical & Current Sensing Reasoning

### Optocoupler Isolation
AC main lines (110V/220V) can introduce dangerous electromagnetic interference (EMI) and voltage spikes back into the low-voltage microcontroller logic. Using **optocoupled relay boards** ensures complete galvanic isolation; the ESP32 drives an internal infrared LED which triggers a phototransistor to toggle the coil. No electrical path exists between the 3.3V logic circuit and the 220V power circuit.

### Power & Current Calculation
The ACS712 sensor outputs an analog voltage centered at $V_{CC} / 2$ (typically 1.65V when no current is flowing). As AC current flows, the voltage alternates sinusoidally above and below this center offset.

1. **Sampling**: The ESP32 must sample the ADC rapidly (e.g., 1000 times over 20ms for a 50Hz grid) to capture the AC waveform.
2. **RMS Calculation**:
   $$V_{RMS} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (V_i - V_{offset})^2}$$
3. **Current & Power**:
   $$I_{RMS} = \frac{V_{RMS}}{\text{Sensitivity}} \quad (185\text{mV/A for ACS712-05B})$$
   $$P_{\text{Real}} = V_{RMS\_AC} \times I_{RMS} \times \text{Power Factor}$$
   *Fans (inductive load) typically have a power factor of 0.85–0.9, while LEDs (resistive/electronic drivers) range from 0.7–0.95.*
