#include <WiFiS3.h>
#include <Wire.h>
#include <DHT20.h>
#include "config.h"

#define LED_PIN 2
#define LIGHT_SENSOR_PIN A0  // Analog pin for LDR/light sensor (if connected)

// API paths
const char* API_PATH = "/api/data";
const char* CMD_PATH = "/api/commands?sensor_id=arduino_1";

WiFiClient client;
DHT20 dht;

// Timing
unsigned long lastSensorRead = 0;
unsigned long lastBlink = 0;
const unsigned long SENSOR_INTERVAL = 2000;
const unsigned long BLINK_INTERVAL = 300;

// LED state (controlled by server)
bool ledState = false;
bool shouldBlink = false;
bool ledOn = false;

// ── Simulated sensor state ────────────────────────────────────
// These hold drifting simulated values so readings look realistic
// over time (small random walk around a base value).
float sim_ph = 6.2;
float sim_ec = 1.5;
float sim_water_level = 85.0;  // percentage – slowly drains
float sim_light_level = 450.0; // lux

// Random walk helper: nudge a value within [lo, hi]
float drift(float current, float step, float lo, float hi) {
  float delta = (random(-100, 101) / 100.0) * step;
  float next = current + delta;
  if (next < lo) next = lo + step;
  if (next > hi) next = hi - step;
  return next;
}

void setup() {
  Wire.begin();
  Serial.begin(9600);
  dht.begin();

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  pinMode(LIGHT_SENSOR_PIN, INPUT);

  // Seed the RNG so simulated values vary between boots
  randomSeed(analogRead(A1));

  Serial.print("Connecting to WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" Connected!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

// ── Build JSON with ALL sensor fields ─────────────────────────
void sendToAPI(float temp, float humidity, float ph, float ec,
               float water_level, float light_level) {
  if (client.connect(API_HOST, API_PORT)) {
    String json = "{";
    json += "\"sensor_id\":\"arduino_1\",";
    json += "\"temperature\":" + String(temp, 2) + ",";
    json += "\"humidity\":"    + String(humidity, 2) + ",";
    json += "\"ph\":"          + String(ph, 2) + ",";
    json += "\"ec\":"          + String(ec, 2) + ",";
    json += "\"water_level\":" + String(water_level, 1) + ",";
    json += "\"light_level\":" + String(light_level, 1);
    json += "}";

    client.print("POST ");
    client.print(API_PATH);
    client.println(" HTTP/1.1");
    client.print("Host: ");
    client.println(API_HOST);
    client.println("Content-Type: application/json");
    client.print("X-API-Key: ");
    client.println(API_KEY);
    client.print("Content-Length: ");
    client.println(json.length());
    client.println("Connection: close");
    client.println();
    client.println(json);

    unsigned long timeout = millis();
    while (client.connected() && millis() - timeout < 3000) {
      if (client.available()) {
        char c = client.read();
        Serial.print(c);
      }
    }
    client.stop();
    Serial.println("\nData sent!");
  } else {
    Serial.println("Connection failed");
  }
}

void pollCommands() {
  if (client.connect(API_HOST, API_PORT)) {
    client.print("GET ");
    client.print(CMD_PATH);
    client.println(" HTTP/1.1");
    client.print("Host: ");
    client.println(API_HOST);
    client.print("X-API-Key: ");
    client.println(API_KEY);
    client.println("Connection: close");
    client.println();

    String response = "";
    unsigned long timeout = millis();
    while (client.connected() && millis() - timeout < 3000) {
      if (client.available()) {
        char c = client.read();
        response += c;
      }
    }
    client.stop();

    int bodyStart = response.indexOf("\r\n\r\n");
    if (bodyStart < 0) return;
    String body = response.substring(bodyStart + 4);

    int ledIdx = body.indexOf("\"led\"");
    if (ledIdx < 0) {
      shouldBlink = false;
      ledOn = false;
      return;
    }

    int valStart = body.indexOf("\"", ledIdx + 5) + 1;
    int valEnd = body.indexOf("\"", valStart);
    if (valStart <= 0 || valEnd <= 0) return;
    String ledCmd = body.substring(valStart, valEnd);

    Serial.print("LED command: ");
    Serial.println(ledCmd);

    if (ledCmd == "blink") {
      shouldBlink = true;
      ledOn = false;
    } else if (ledCmd == "on") {
      shouldBlink = false;
      ledOn = true;
    } else {
      shouldBlink = false;
      ledOn = false;
    }
  }
}

void loop() {
  unsigned long now = millis();

  if (now - lastSensorRead >= SENSOR_INTERVAL) {
    lastSensorRead = now;

    // ── Real sensors ──────────────────────────────────────────
    dht.read();
    float temp = dht.getTemperature();
    float hum  = dht.getHumidity();

    // ── Simulated sensors (random walk) ───────────────────────
    // pH: hydroponics optimal 5.5 – 7.0, drift ±0.05 per cycle
    sim_ph = drift(sim_ph, 0.05, 5.0, 7.5);

    // EC: nutrient solution 0.5 – 3.0 mS/cm, drift ±0.03
    sim_ec = drift(sim_ec, 0.03, 0.5, 3.0);

    // Water level: drains slowly (bias downward), refill at 10%
    sim_water_level -= random(0, 30) / 100.0;  // drain 0.00–0.29% per cycle
    if (sim_water_level < 10.0) sim_water_level = 90.0; // simulate refill

    // Light level: 200–800 lux range, drift ±15
    sim_light_level = drift(sim_light_level, 15.0, 100.0, 900.0);

    // ── Send everything ───────────────────────────────────────
    sendToAPI(temp, hum, sim_ph, sim_ec, sim_water_level, sim_light_level);
    pollCommands();

    // Serial debug – full payload
    Serial.print("{\"temperature\":");
    Serial.print(temp);
    Serial.print(",\"humidity\":");
    Serial.print(hum);
    Serial.print(",\"ph\":");
    Serial.print(sim_ph, 2);
    Serial.print(",\"ec\":");
    Serial.print(sim_ec, 2);
    Serial.print(",\"water_level\":");
    Serial.print(sim_water_level, 1);
    Serial.print(",\"light_level\":");
    Serial.print(sim_light_level, 1);
    Serial.println("}");
  }

  // ── LED control (from server commands) ──────────────────────
  if (shouldBlink && (now - lastBlink >= BLINK_INTERVAL)) {
    lastBlink = now;
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState ? HIGH : LOW);
  } else if (ledOn) {
    digitalWrite(LED_PIN, HIGH);
  } else if (!shouldBlink) {
    digitalWrite(LED_PIN, LOW);
  }
}
