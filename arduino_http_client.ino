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

void setup() {
  Serial.begin(9600);
  while (!Serial);

  // Initialize I2C and DHT20
  Wire.begin();
  dht20.begin();
  Serial.println("DHT20 sensor initialized");

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

    // Build JSON payload
    String jsonPayload = "{";
    jsonPayload += "\"temperature\":" + String(temperature, 1) + ",";
    jsonPayload += "\"humidity\":" + String(humidity, 1);
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
