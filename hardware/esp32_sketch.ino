/**
 * Lumina Enterprise IoT Workspace Orchestrator
 * ESP32 NodeMCU Firmware (Bi-Directional Observability with Switches)
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

// Actuator Pin Configuration
const int PIN_FAN_1 = 5;      // GPIO 5 - Relay 1
const int PIN_FAN_2 = 18;     // GPIO 18 - Relay 2
const int PIN_LIGHT_1 = 19;   // GPIO 19 - LED 1
const int PIN_LIGHT_2 = 21;   // GPIO 21 - LED 2
const int PIN_LIGHT_3 = 22;   // GPIO 22 - LED 3
const int PIN_ACS712 = 34;    // GPIO 34 (ADC1_CH6) - Current Sensor

// Physical Button Switch Pin Configuration (Pull-ups)
const int PIN_BTN_FAN_1 = 12;   // GPIO 12 - Switch for Fan 1
const int PIN_BTN_FAN_2 = 13;   // GPIO 13 - Switch for Fan 2
const int PIN_BTN_LIGHT_1 = 14; // GPIO 14 - Switch for Light 1
const int PIN_BTN_LIGHT_2 = 25; // GPIO 25 - Switch for Light 2
const int PIN_BTN_LIGHT_3 = 26; // GPIO 26 - Switch for Light 3

// ACS712 Sensor Parameters
const float SENSITIVITY = 185.0; 
const float VREF = 3.3;          
const int ADC_RESOLUTION = 4095; 
const float VOLTAGE_AC = 220.0;  
const float POWER_FACTOR = 0.90; 

unsigned long lastUpdate = 0;
const unsigned long UPDATE_INTERVAL = 3000; 

// Button State Tracker Struct for Debouncing
struct SwitchButton {
  int pin;
  String deviceId;
  int lastDebouncedState;
  int lastFlickerState;
  unsigned long lastDebounceTime;
};

SwitchButton switches[] = {
  {PIN_BTN_FAN_1, "drawing_room_fan_1", HIGH, HIGH, 0},
  {PIN_BTN_FAN_2, "drawing_room_fan_2", HIGH, HIGH, 0},
  {PIN_BTN_LIGHT_1, "drawing_room_light_1", HIGH, HIGH, 0},
  {PIN_BTN_LIGHT_2, "drawing_room_light_2", HIGH, HIGH, 0},
  {PIN_BTN_LIGHT_3, "drawing_room_light_3", HIGH, HIGH, 0}
};
const int NUM_SWITCHES = 5;
const unsigned long DEBOUNCE_DELAY = 50; 

void setup() {
  Serial.begin(115200);

  // Initialize Actuator Pins
  pinMode(PIN_FAN_1, OUTPUT);
  pinMode(PIN_FAN_2, OUTPUT);
  pinMode(PIN_LIGHT_1, OUTPUT);
  pinMode(PIN_LIGHT_2, OUTPUT);
  pinMode(PIN_LIGHT_3, OUTPUT);

  // All actuators OFF initially
  digitalWrite(PIN_FAN_1, LOW);
  digitalWrite(PIN_FAN_2, LOW);
  digitalWrite(PIN_LIGHT_1, LOW);
  digitalWrite(PIN_LIGHT_2, LOW);
  digitalWrite(PIN_LIGHT_3, LOW);

  // Initialize Switch Pins with Internal Pull-Ups
  for (int i = 0; i < NUM_SWITCHES; i++) {
    pinMode(switches[i].pin, INPUT_PULLUP);
  }

  // Connect to Wi-Fi
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi Connected.");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // 1. Scan switches continuously
  checkPhysicalSwitches();

  // 2. Poll API database state & push sensor readings periodically
  if (WiFi.status() == WL_CONNECTED) {
    unsigned long currentMillis = millis();
    if (currentMillis - lastUpdate >= UPDATE_INTERVAL) {
      lastUpdate = currentMillis;
      
      syncDeviceStates();
      
      float currentRMS = readCurrentRMS();
      float powerWatts = currentRMS * VOLTAGE_AC * POWER_FACTOR;
      Serial.printf("[Sensor Data] Current: %.3f A | Power: %.1f W\n", currentRMS, powerWatts);
    }
  }
}

/**
 * Checks physical push button switches, debounces readings, and triggers HTTP toggle requests
 */
void checkPhysicalSwitches() {
  for (int i = 0; i < NUM_SWITCHES; i++) {
    int currentState = digitalRead(switches[i].pin);
    
    // Check if button state flickered
    if (currentState != switches[i].lastFlickerState) {
      switches[i].lastDebounceTime = millis();
      switches[i].lastFlickerState = currentState;
    }
    
    // If state is stable for at least DEBOUNCE_DELAY
    if ((millis() - switches[i].lastDebounceTime) > DEBOUNCE_DELAY) {
      // Toggle on transition from HIGH to LOW (button press)
      if (switches[i].lastDebouncedState == HIGH && currentState == LOW) {
        Serial.printf("[Switch Pressed] Actuating: %s\n", switches[i].deviceId.c_str());
        sendToggleRequest(switches[i].deviceId);
      }
      switches[i].lastDebouncedState = currentState;
    }
  }
}

/**
 * Sends a POST toggle request to the centralized state manager
 */
void sendToggleRequest(String deviceId) {
  if (WiFi.status() != WL_CONNECTED) return;
  
  HTTPClient http;
  String url = String(backendUrl) + "/" + deviceId + "/toggle";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  int httpCode = http.POST("{}");
  if (httpCode == HTTP_CODE_OK) {
    Serial.printf("[Cloud Sync] Toggled: %s\n", deviceId.c_str());
    syncDeviceStates(); // Sync immediately
  } else {
    Serial.printf("[Cloud Error] Failed to toggle %s. HTTP code: %d\n", deviceId.c_str(), httpCode);
  }
  http.end();
}

/**
 * Fetches current API database states to set output pin levels
 */
void syncDeviceStates() {
  HTTPClient http;
  http.begin(backendUrl);
  int httpCode = http.GET();
  
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    DynamicJsonDocument doc(4096);
    DeserializationError error = deserializeJson(doc, payload);
    
    if (!error) {
      bool fan1 = doc["drawing_room_fan_1"]["status"];
      bool fan2 = doc["drawing_room_fan_2"]["status"];
      bool light1 = doc["drawing_room_light_1"]["status"];
      bool light2 = doc["drawing_room_light_2"]["status"];
      bool light3 = doc["drawing_room_light_3"]["status"];
      
      digitalWrite(PIN_FAN_1, fan1 ? HIGH : LOW);
      digitalWrite(PIN_FAN_2, fan2 ? HIGH : LOW);
      digitalWrite(PIN_LIGHT_1, light1 ? HIGH : LOW);
      digitalWrite(PIN_LIGHT_2, light2 ? HIGH : LOW);
      digitalWrite(PIN_LIGHT_3, light3 ? HIGH : LOW);
    }
  }
  http.end();
}

/**
 * Reads ACS712 analog signals over 20ms and returns Root Mean Square (RMS) Amperes
 */
float readCurrentRMS() {
  float maxValue = 0;          
  float minValue = ADC_RESOLUTION; 
  unsigned long startTime = millis();
  
  while ((millis() - startTime) < 20) {
    int readValue = analogRead(PIN_ACS712);
    if (readValue > maxValue) maxValue = readValue;
    if (readValue < minValue) minValue = readValue;
  }
  
  float peakVoltage = ((maxValue - minValue) * VREF) / (2.0 * ADC_RESOLUTION);
  float voltageRMS = peakVoltage * 0.707;
  float currentRMS = (voltageRMS * 1000.0) / SENSITIVITY;
  
  if (currentRMS < 0.05) currentRMS = 0.0;
  return currentRMS;
}
