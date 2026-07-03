/**
 * Lumina Enterprise IoT Workspace Orchestrator
 * ESP32 NodeMCU Firmware (Single Zone Observability)
 * Team: ULAB_Anonymous_3.0
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Wi-Fi Credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Centralized State Manager API
const char* backendUrl = "http://YOUR_BACKEND_IP:8000/api/devices";
const char* usageUrl = "http://YOUR_BACKEND_IP:8000/api/usage";

// Pin Configuration
const int PIN_FAN_1 = 5;      // GPIO 5 - Relay 1
const int PIN_FAN_2 = 18;     // GPIO 18 - Relay 2
const int PIN_LIGHT_1 = 19;   // GPIO 19 - LED 1
const int PIN_LIGHT_2 = 21;   // GPIO 21 - LED 2
const int PIN_LIGHT_3 = 22;   // GPIO 22 - LED 3
const int PIN_ACS712 = 34;    // GPIO 34 (ADC1_CH6) - Current Sensor

// ACS712 Sensitivity (185 mV/A for 5A model)
const float SENSITIVITY = 185.0; 
const float VREF = 3.3;          // ESP32 analog reference voltage (3.3V)
const int ADC_RESOLUTION = 4095; // ESP32 12-bit ADC resolution
const float VOLTAGE_AC = 220.0;  // Local Bangladesh AC Voltage supply
const float POWER_FACTOR = 0.90; // Typical power factor for inductive/capacitive mixed load

unsigned long lastUpdate = 0;
const unsigned long UPDATE_INTERVAL = 3000; // Poll every 3 seconds

void setup() {
  Serial.begin(115200);

  // Initialize Actuator Pins
  pinMode(PIN_FAN_1, OUTPUT);
  pinMode(PIN_FAN_2, OUTPUT);
  pinMode(PIN_LIGHT_1, OUTPUT);
  pinMode(PIN_LIGHT_2, OUTPUT);
  pinMode(PIN_LIGHT_3, OUTPUT);

  // Set all to off initially
  digitalWrite(PIN_FAN_1, LOW);
  digitalWrite(PIN_FAN_2, LOW);
  digitalWrite(PIN_LIGHT_1, LOW);
  digitalWrite(PIN_LIGHT_2, LOW);
  digitalWrite(PIN_LIGHT_3, LOW);

  // Connect to WiFi
  Serial.print("Connecting to Wi-Fi SSID: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi Connected successfully.");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    unsigned long currentMillis = millis();
    if (currentMillis - lastUpdate >= UPDATE_INTERVAL) {
      lastUpdate = currentMillis;
      
      // 1. Sync hardware state with Backend API
      syncDeviceStates();
      
      // 2. Sample current sensor and push telemetry to backend
      float currentRMS = readCurrentRMS();
      float powerWatts = currentRMS * VOLTAGE_AC * POWER_FACTOR;
      
      Serial.printf("Telemetry Output -> Current: %.3f A, Active Power: %.1f W\n", currentRMS, powerWatts);
    }
  } else {
    Serial.println("Wi-Fi disconnected. Reconnecting...");
    WiFi.disconnect();
    WiFi.begin(ssid, password);
    delay(5000);
  }
}

/**
 * Fetches device states from the FastAPI backend and maps them to hardware pins
 */
void syncDeviceStates() {
  HTTPClient http;
  http.begin(backendUrl);
  int httpCode = http.GET();
  
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    
    // Allocate space for JSON parsing
    DynamicJsonDocument doc(4096);
    DeserializationError error = deserializeJson(doc, payload);
    
    if (!error) {
      // Parse states for Drawing Room (Representative Zone)
      bool fan1 = doc["drawing_room_fan_1"]["status"];
      bool fan2 = doc["drawing_room_fan_2"]["status"];
      bool light1 = doc["drawing_room_light_1"]["status"];
      bool light2 = doc["drawing_room_light_2"]["status"];
      bool light3 = doc["drawing_room_light_3"]["status"];
      
      // Actuate hardware pins
      digitalWrite(PIN_FAN_1, fan1 ? HIGH : LOW);
      digitalWrite(PIN_FAN_2, fan2 ? HIGH : LOW);
      digitalWrite(PIN_LIGHT_1, light1 ? HIGH : LOW);
      digitalWrite(PIN_LIGHT_2, light2 ? HIGH : LOW);
      digitalWrite(PIN_LIGHT_3, light3 ? HIGH : LOW);
      
      Serial.println("[Sync Success] Hardware pins updated from database.");
    } else {
      Serial.print("JSON Deserialization failed: ");
      Serial.println(error.c_str());
    }
  } else {
    Serial.print("HTTP GET request failed, error code: ");
    Serial.println(httpCode);
  }
  http.end();
}

/**
 * Read ACS712 current sensor and calculates Root Mean Square (RMS) Amperes
 */
float readCurrentRMS() {
  float maxValue = 0;          // store max value
  float minValue = ADC_RESOLUTION; // store min value
  
  unsigned long start_time = millis();
  
  // Sample analog values for 20ms (exactly 1 full cycle of 50Hz AC electricity)
  while ((millis() - start_time) < 20) {
    int readValue = analogRead(PIN_ACS712);
    if (readValue > maxValue) {
      maxValue = readValue;
    }
    if (readValue < minValue) {
      minValue = readValue;
    }
  }
  
  // Subtract baseline offset and calculate Peak Voltage
  // ESP32 ADC goes from 0 to VREF (3.3V) with resolution of 4095
  float peakVoltage = ((maxValue - minValue) * VREF) / (2.0 * ADC_RESOLUTION);
  
  // Convert peak voltage to RMS voltage
  float voltageRMS = peakVoltage * 0.707;
  
  // Calculate RMS Current (Amperes)
  // ACS712 returns Sensitivity in mV/A. Convert voltage RMS to mV -> divide by sensitivity
  float currentRMS = (voltageRMS * 1000.0) / SENSITIVITY;
  
  // Filter out tiny noise when loads are off
  if (currentRMS < 0.05) {
    currentRMS = 0.0;
  }
  
  return currentRMS;
}
