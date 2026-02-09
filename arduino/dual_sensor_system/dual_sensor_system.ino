/*
 * AgriTech Dual Sensor Redundancy System
 *
 * Hardware:
 * - Arduino UNO R4 WiFi
 * - 2x DHT20 sensors (I2C addresses: 0x38 primary, 0x39 secondary)
 * - LED on pin 2 for status indication
 *
 * Purpose:
 * - Compare readings from two sensors
 * - Detect sensor drift automatically
 * - Provide redundancy and early failure detection
 * - Send drift alerts to server for business intelligence
 *
 * Business Value:
 * - Never lose data due to single sensor failure
 * - Predict sensor failures before they happen
 * - Reduce crop loss from bad sensor readings
 * - Justify higher service fees with reliability
 */

#include <WiFiS3.h>
#include <Wire.h>
#include "DFRobot_DHT20.h"  // DHT20 library
#include "config.h"  // WiFi credentials, API settings

// ── DHT20 Sensors ─────────────────────────────────────────────

DFRobot_DHT20 dht20_primary;    // Primary sensor (address 0x38)
DFRobot_DHT20 dht20_secondary;  // Secondary sensor (address 0x39)

// If both sensors use same I2C address (0x38), use I2C multiplexer
// Or manually connect to different I2C buses if available

// ── Configuration ─────────────────────────────────────────────

#define LED_PIN 2
#define SENSOR_INTERVAL 2000  // 2 seconds between readings

// Drift thresholds (from business intelligence analysis)
#define TEMP_DRIFT_WARNING 0.5    // °C - Medium quality sensor tolerance
#define TEMP_DRIFT_CRITICAL 2.0   // °C - Cheap sensor tolerance
#define HUMIDITY_DRIFT_WARNING 2.0  // % - Medium tolerance
#define HUMIDITY_DRIFT_CRITICAL 5.0 // % - Cheap tolerance

// ── WiFi Client ───────────────────────────────────────────────

WiFiClient client;

// ── Sensor Status ─────────────────────────────────────────────

struct SensorReading {
  float temperature;
  float humidity;
  bool valid;
  unsigned long timestamp;
};

SensorReading primary_reading;
SensorReading secondary_reading;

struct DriftStatus {
  float temp_drift_percent;
  float humidity_drift_percent;
  bool temp_warning;
  bool temp_critical;
  bool humidity_warning;
  bool humidity_critical;
  String status;  // "healthy", "degraded", "failing"
};

DriftStatus current_drift;

// ── Setup ─────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000);  // Wait max 3s for serial

  Serial.println(F("\n=== AgriTech Dual Sensor System ==="));
  Serial.println(F("Initializing..."));

  // LED setup
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // I2C setup
  Wire.begin();

  // Initialize primary sensor (0x38)
  Serial.print(F("Initializing primary sensor (0x38)..."));
  dht20_primary.begin();
  delay(1000);
  if (dht20_primary.begin() == 0) {
    Serial.println(F(" OK"));
  } else {
    Serial.println(F(" FAILED"));
  }

  // Initialize secondary sensor
  // NOTE: If using same I2C address, you need I2C multiplexer (TCA9548A)
  // For now, we'll simulate secondary sensor for testing
  Serial.print(F("Initializing secondary sensor..."));
  // dht20_secondary.begin(0x39);  // If different address available
  Serial.println(F(" OK (using same sensor for demo)"));

  // WiFi connection
  Serial.print(F("Connecting to WiFi: "));
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(F("\nWiFi Connected!"));
    Serial.print(F("IP: "));
    Serial.println(WiFi.localIP());
    blinkLED(3, 200);  // Success indicator
  } else {
    Serial.println(F("\nWiFi Connection Failed!"));
    Serial.println(F("Check config.h settings"));
    blinkLED(10, 100);  // Error indicator
  }

  Serial.println(F("\n=== System Ready ===\n"));
}

// ── Main Loop ─────────────────────────────────────────────────

void loop() {
  // Read both sensors
  primary_reading = readPrimarySensor();
  secondary_reading = readSecondarySensor();

  // Calculate drift
  if (primary_reading.valid && secondary_reading.valid) {
    current_drift = calculateDrift(primary_reading, secondary_reading);

    // Display readings
    displayReadings();

    // Send to server
    sendDualSensorData();

    // Update LED status
    updateStatusLED();
  } else {
    Serial.println(F("⚠️  Sensor read error - retrying..."));
    blinkLED(2, 100);
  }

  delay(SENSOR_INTERVAL);
}

// ── Read Primary Sensor ───────────────────────────────────────

SensorReading readPrimarySensor() {
  SensorReading reading;
  reading.timestamp = millis();
  reading.valid = false;

  // Read from DHT20
  reading.temperature = dht20_primary.getTemperature();
  reading.humidity = dht20_primary.getHumidity() * 100;  // Convert to percentage

  // Validate reading
  if (reading.temperature > -40 && reading.temperature < 80 &&
      reading.humidity >= 0 && reading.humidity <= 100) {
    reading.valid = true;
  }

  return reading;
}

// ── Read Secondary Sensor ─────────────────────────────────────

SensorReading readSecondarySensor() {
  SensorReading reading;
  reading.timestamp = millis();
  reading.valid = false;

  // For demo: Add small random variation to simulate different sensor
  // In production, read from actual second sensor
  reading.temperature = dht20_primary.getTemperature() + random(-10, 10) / 10.0;
  reading.humidity = (dht20_primary.getHumidity() * 100) + random(-20, 20) / 10.0;

  // In production with actual second sensor:
  // reading.temperature = dht20_secondary.getTemperature();
  // reading.humidity = dht20_secondary.getHumidity() * 100;

  // Validate reading
  if (reading.temperature > -40 && reading.temperature < 80 &&
      reading.humidity >= 0 && reading.humidity <= 100) {
    reading.valid = true;
  }

  return reading;
}

// ── Calculate Drift ───────────────────────────────────────────

DriftStatus calculateDrift(SensorReading primary, SensorReading secondary) {
  DriftStatus drift;

  // Temperature drift (absolute difference)
  float temp_diff = abs(primary.temperature - secondary.temperature);
  drift.temp_drift_percent = (temp_diff / primary.temperature) * 100;

  // Humidity drift (absolute difference)
  float humidity_diff = abs(primary.humidity - secondary.humidity);
  drift.humidity_drift_percent = (humidity_diff / primary.humidity) * 100;

  // Determine warning/critical levels
  drift.temp_warning = (temp_diff >= TEMP_DRIFT_WARNING);
  drift.temp_critical = (temp_diff >= TEMP_DRIFT_CRITICAL);
  drift.humidity_warning = (humidity_diff >= HUMIDITY_DRIFT_WARNING);
  drift.humidity_critical = (humidity_diff >= HUMIDITY_DRIFT_CRITICAL);

  // Overall status
  if (drift.temp_critical || drift.humidity_critical) {
    drift.status = "failing";
  } else if (drift.temp_warning || drift.humidity_warning) {
    drift.status = "degraded";
  } else {
    drift.status = "healthy";
  }

  return drift;
}

// ── Display Readings ──────────────────────────────────────────

void displayReadings() {
  Serial.println(F("┌─────────────────────────────────────────┐"));
  Serial.println(F("│     DUAL SENSOR COMPARISON              │"));
  Serial.println(F("├─────────────────────────────────────────┤"));

  // Primary sensor
  Serial.print(F("│ PRIMARY:   "));
  Serial.print(primary_reading.temperature, 1);
  Serial.print(F("°C  "));
  Serial.print(primary_reading.humidity, 1);
  Serial.println(F("%     │"));

  // Secondary sensor
  Serial.print(F("│ SECONDARY: "));
  Serial.print(secondary_reading.temperature, 1);
  Serial.print(F("°C  "));
  Serial.print(secondary_reading.humidity, 1);
  Serial.println(F("%     │"));

  Serial.println(F("├─────────────────────────────────────────┤"));

  // Drift analysis
  Serial.print(F("│ TEMP DRIFT:  "));
  Serial.print(abs(primary_reading.temperature - secondary_reading.temperature), 2);
  Serial.print(F("°C ("));
  Serial.print(current_drift.temp_drift_percent, 1);
  Serial.print(F("%)"));
  if (current_drift.temp_critical) {
    Serial.println(F("  🔴 CRITICAL"));
  } else if (current_drift.temp_warning) {
    Serial.println(F("  🟡 WARNING"));
  } else {
    Serial.println(F("  ✅ OK"));
  }

  Serial.print(F("│ HUM. DRIFT:  "));
  Serial.print(abs(primary_reading.humidity - secondary_reading.humidity), 2);
  Serial.print(F("% ("));
  Serial.print(current_drift.humidity_drift_percent, 1);
  Serial.print(F("%)"));
  if (current_drift.humidity_critical) {
    Serial.println(F("  🔴 CRITICAL"));
  } else if (current_drift.humidity_warning) {
    Serial.println(F("  🟡 WARNING"));
  } else {
    Serial.println(F("  ✅ OK"));
  }

  Serial.println(F("├─────────────────────────────────────────┤"));

  // Overall status
  Serial.print(F("│ STATUS: "));
  if (current_drift.status == "healthy") {
    Serial.println(F("✅ HEALTHY - Both sensors accurate │"));
  } else if (current_drift.status == "degraded") {
    Serial.println(F("🟡 DEGRADED - Calibration needed   │"));
  } else {
    Serial.println(F("🔴 FAILING - Sensor replacement!   │"));
  }

  Serial.println(F("└─────────────────────────────────────────┘\n"));
}

// ── Send Data to Server ───────────────────────────────────────

void sendDualSensorData() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("⚠️  WiFi disconnected - skipping upload"));
    return;
  }

  // Build JSON payload
  String json = "{";
  json += "\"sensor_id\":\"" + String(SENSOR_ID) + "\",";
  json += "\"primary\":{";
  json += "\"temperature\":" + String(primary_reading.temperature, 2) + ",";
  json += "\"humidity\":" + String(primary_reading.humidity, 2);
  json += "},";
  json += "\"secondary\":{";
  json += "\"temperature\":" + String(secondary_reading.temperature, 2) + ",";
  json += "\"humidity\":" + String(secondary_reading.humidity, 2);
  json += "},";
  json += "\"drift\":{";
  json += "\"temp_diff\":" + String(abs(primary_reading.temperature - secondary_reading.temperature), 2) + ",";
  json += "\"humidity_diff\":" + String(abs(primary_reading.humidity - secondary_reading.humidity), 2) + ",";
  json += "\"status\":\"" + current_drift.status + "\"";
  json += "}";
  json += "}";

  // HTTP POST request
  if (client.connect(API_HOST, API_PORT)) {
    client.println("POST /api/sensors/dual HTTP/1.1");
    client.print("Host: ");
    client.println(API_HOST);
    client.println("Content-Type: application/json");
    client.print("X-API-Key: ");
    client.println(API_KEY);
    client.print("Content-Length: ");
    client.println(json.length());
    client.println();
    client.println(json);

    // Wait for response
    unsigned long timeout = millis();
    while (client.available() == 0) {
      if (millis() - timeout > 5000) {
        Serial.println(F("⏱️  Server timeout"));
        client.stop();
        return;
      }
    }

    // Read response
    while (client.available()) {
      String line = client.readStringUntil('\r');
      if (line.indexOf("200") >= 0) {
        Serial.println(F("✅ Data sent successfully"));
      }
    }

    client.stop();
  } else {
    Serial.println(F("❌ Connection to server failed"));
  }
}

// ── Update Status LED ─────────────────────────────────────────

void updateStatusLED() {
  if (current_drift.status == "healthy") {
    digitalWrite(LED_PIN, HIGH);  // Solid on = healthy
  } else if (current_drift.status == "degraded") {
    // Slow blink = warning
    digitalWrite(LED_PIN, (millis() / 1000) % 2);
  } else {
    // Fast blink = critical
    digitalWrite(LED_PIN, (millis() / 250) % 2);
  }
}

// ── Utility: Blink LED ────────────────────────────────────────

void blinkLED(int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(delayMs);
    digitalWrite(LED_PIN, LOW);
    delay(delayMs);
  }
}
