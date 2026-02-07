#include <WiFiS3.h>
#include "Arduino_SensorKit.h"

#define DHTPIN 3
#define Environment Environment_I2C
#define LED_PIN 2

// WiFi credentials
const char* WIFI_SSID = "DIGIFIBRA-EPdQ";
const char* WIFI_PASS = "XQPNXHxGAUPF";

// API endpoint
const char* API_HOST = "192.168.1.130";
const int API_PORT = 3001;
const char* API_PATH = "/api/data";

WiFiClient client;

// Thresholds
const float TEMP_THRESHOLD = 16.0;
const float HUMIDITY_THRESHOLD = 60.0;

// Timing
unsigned long lastSensorRead = 0;
unsigned long lastBlink = 0;
const unsigned long SENSOR_INTERVAL = 2000;
const unsigned long BLINK_INTERVAL = 300;

bool ledState = false;
bool shouldBlink = false;

void setup() {
  Wire.begin();
  Serial.begin(9600);
  
  // Connect to WiFi
  Serial.print("Connecting to WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" Connected!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
  
  Environment.begin();
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
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
    client.print("Content-Length: ");
    client.println(json.length());
    client.println("Connection: close");
    client.println();
    client.println(json);
    
    // Wait for response
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

void loop() {
  unsigned long now = millis();
  
  if (now - lastSensorRead >= SENSOR_INTERVAL) {
    lastSensorRead = now;
    
    float temp = Environment.readTemperature();
    float hum = Environment.readHumidity();
    
    shouldBlink = (temp >= TEMP_THRESHOLD) || (hum > HUMIDITY_THRESHOLD);
    
    if (!shouldBlink) {
      digitalWrite(LED_PIN, LOW);
      ledState = false;
    }
    
    sendToAPI(temp, hum);
    
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
  }
}
