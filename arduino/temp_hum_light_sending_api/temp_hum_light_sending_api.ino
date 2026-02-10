#include <WiFiS3.h>
#include <Wire.h>
#include <DHT20.h>
#include "config.h"

#define LED_PIN 2

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

void setup() {
  Wire.begin();
  Serial.begin(9600);
  dht.begin();

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

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

void sendToAPI(float temp, float humidity) {
  if (client.connect(API_HOST, API_PORT)) {
    String json = "{\"temperature\":";
    json += String(temp, 2);
    json += ",\"humidity\":";
    json += String(humidity, 2);
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

    dht.read();
    float temp = dht.getTemperature();
    float hum = dht.getHumidity();

    sendToAPI(temp, hum);
    pollCommands();

    Serial.print("{\"temperature\":");
    Serial.print(temp);
    Serial.print(",\"humidity\":");
    Serial.print(hum);
    Serial.println("}");
  }

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
