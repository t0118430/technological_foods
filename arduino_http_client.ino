#include "WiFiS3.h"
#include <Wire.h>
#include <DHT20.h>

// 1. WiFi Credentials
char ssid[] = "";
char pass[] = "";

// 2. Server Details (Your PC)
IPAddress serverIP(192, 168, 1, 168);
const int serverPort = 3000;

WiFiClient client;
int status = WL_IDLE_STATUS;

// DHT20 sensor (I2C)
DHT20 dht20;

// ── Simulated sensor state ────────────────────────────────────
float sim_ph = 6.2;
float sim_ec = 1.5;
float sim_water_level = 85.0;
float sim_light_level = 450.0;

float drift(float current, float step, float lo, float hi) {
  float delta = (random(-100, 101) / 100.0) * step;
  float next = current + delta;
  if (next < lo) next = lo + step;
  if (next > hi) next = hi - step;
  return next;
}

void setup() {
  Serial.begin(9600);
  while (!Serial);

  // Initialize I2C and DHT20
  Wire.begin();
  dht20.begin();
  Serial.println("DHT20 sensor initialized");

  // Seed RNG for simulated sensors
  randomSeed(analogRead(A1));

  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("Communication with WiFi module failed!");
    while (true);
  }

  // Connect to WiFi
  while (status != WL_CONNECTED) {
    Serial.print("Attempting to connect to SSID: ");
    Serial.println(ssid);
    status = WiFi.begin(ssid, pass);
    delay(10000);
  }
  Serial.println("Connected to WiFi");
  printWifiStatus();
}

void loop() {
  // Read from DHT20 sensor
  int readStatus = dht20.read();

  if (readStatus == DHT20_OK) {
    float temperature = dht20.getTemperature();
    float humidity = dht20.getHumidity();

    // Update simulated sensors
    sim_ph = drift(sim_ph, 0.05, 5.0, 7.5);
    sim_ec = drift(sim_ec, 0.03, 0.5, 3.0);
    sim_water_level -= random(0, 30) / 100.0;
    if (sim_water_level < 10.0) sim_water_level = 90.0;
    sim_light_level = drift(sim_light_level, 15.0, 100.0, 900.0);

    // Build JSON payload with ALL sensor fields
    String jsonPayload = "{";
    jsonPayload += "\"sensor_id\":\"arduino_1\",";
    jsonPayload += "\"temperature\":" + String(temperature, 1) + ",";
    jsonPayload += "\"humidity\":" + String(humidity, 1) + ",";
    jsonPayload += "\"ph\":" + String(sim_ph, 2) + ",";
    jsonPayload += "\"ec\":" + String(sim_ec, 2) + ",";
    jsonPayload += "\"water_level\":" + String(sim_water_level, 1) + ",";
    jsonPayload += "\"light_level\":" + String(sim_light_level, 1);
    jsonPayload += "}";

    Serial.print("Sending data: ");
    Serial.println(jsonPayload);

    if (client.connect(serverIP, serverPort)) {
      // Send HTTP POST request
      client.println("POST /api/data HTTP/1.1");
      client.println("Host: " + serverIP.toString());
      client.println("Content-Type: application/json");
      client.print("Content-Length: ");
      client.println(jsonPayload.length());
      client.println("Connection: close");
      client.println();
      client.println(jsonPayload);

      // Wait for response
      delay(500);
      Serial.println("Response:");
      while (client.available()) {
        char c = client.read();
        Serial.write(c);
      }

      client.stop();
      Serial.println("\n--- Request complete ---\n");

    } else {
      Serial.println("Connection failed!");
    }
  } else {
    Serial.print("DHT20 read error: ");
    Serial.println(readStatus);
  }

  // Wait 5 seconds before next reading
  delay(5000);
}

void printWifiStatus() {
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}
