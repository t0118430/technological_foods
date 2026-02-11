
# AgriTech Hydroponics Backend - Phase 1

Backend infrastructure for the AgriTech NFT Hydroponics automation system.

## Architecture

```
Arduino UNO R4 WiFi
    │
    ├── POST /api/data ──────► API Server (server.py :3001)
    │   (X-API-Key header)          │
    │                               ├── Write to InfluxDB ──► Grafana
    │                               │
    │                               └── Rule Engine (config server)
    │                                       │
    │                                       ├── Evaluate rules
    │                                       ├── Queue Arduino commands
    │                                       ├── Trigger AC actions ──► Haier hOn API
    │                                       └── Trigger notifications ──► Notification Service
    │                                                                        ├── Console
    │                                                                        ├── WhatsApp (Twilio)
    │                                                                        ├── SMS (Twilio)
    │                                                                        └── Email (SMTP)
    │
    └── GET /api/commands ◄──── Pending commands (led, pump, etc.)
```

The **Config Server** (rule engine) is the central decision-maker. All thresholds, conditions, and actions are configurable at runtime via API — no Arduino redeployment needed.

## Services

| Service | Port | Description |
|---------|------|-------------|
| InfluxDB | 8086 | Time-series database (sensor data) |
| PostgreSQL | 5432 | Relational database (7 schemas: core, iot, crop, business, alert, bi, audit) |
| Redis | 6379 | Cache layer (latest readings, rate limiting) |
| Grafana | 3000 | Dashboard visualization (15 dashboards, 3 folders) |
| Node-RED | 1880 | Visual flow programming |
| API Server | 3001 | HTTP API + Config Server (runs outside Docker) |

## Quick Start

### Prerequisites

- Docker Desktop installed
- Docker Compose (included with Docker Desktop)
- Python 3.x installed

### Setup

1. Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

2. Copy `arduino/temp_hum_light_sending_api/config.h.example` to `config.h` and fill in your WiFi credentials and API key:
```bash
cp arduino/temp_hum_light_sending_api/config.h.example arduino/temp_hum_light_sending_api/config.h
```

3. Install API dependencies:
```bash
pip install -r api/requirements.txt
```

### Start the Backend

```bash
cd backend
docker-compose up -d
```

### Start the API Server

```bash
cd backend/api
python server.py
```

You should see:
```
Server running at http://0.0.0.0:3001
Swagger UI:  http://localhost:3001/api/docs
Endpoints:
  GET    /api/docs                - Swagger UI
  GET    /api/openapi.json        - OpenAPI spec
  GET    /api/health              - Health check
  GET    /api/data/latest         - Get latest reading from InfluxDB
  POST   /api/data                - Save Arduino data + evaluate rules
  GET    /api/ac                  - Get AC status
  POST   /api/ac                  - Control AC (power, temperature, mode)
  GET    /api/rules               - List all rules (config server)
  POST   /api/rules               - Create a rule
  PUT    /api/rules/{id}          - Update a rule
  DELETE /api/rules/{id}          - Delete a rule
  GET    /api/commands            - Arduino polls for commands
  GET    /api/notifications       - Notification status & history
  POST   /api/notifications/test  - Send test alert
```

### Check Status

```bash
docker-compose ps
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f influxdb
```

### Stop the Backend

```bash
docker-compose down

# To also remove data volumes:
docker-compose down -v
```

## Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | See `.env` (GRAFANA_USER / GRAFANA_PASSWORD) |
| InfluxDB | http://localhost:8086 | See `.env` (INFLUXDB_USERNAME / INFLUXDB_PASSWORD) |
| Node-RED | http://localhost:1880 | (no auth by default) |

## Authentication

All API endpoints (except `/api/health`) require an `X-API-Key` header. Set `API_KEY` in your `.env` file and use the same key in the Arduino `config.h`.

```bash
# Example request with API key
curl -H "X-API-Key: agritech-secret-key-2026" http://localhost:3001/api/rules
```

If `API_KEY` is empty or not set in `.env`, authentication is disabled (backwards compatible).

### Arduino Config (`config.h`)

WiFi credentials, server IP, and the API key are stored in `config.h` (gitignored). Copy from the example:

```bash
cp arduino/temp_hum_light_sending_api/config.h.example arduino/temp_hum_light_sending_api/config.h
```

```c
#define WIFI_SSID "your-wifi-ssid"
#define WIFI_PASS "your-wifi-password"
#define API_HOST  "192.168.1.130"
#define API_PORT  3001
#define API_KEY   "your-api-key-here"
```

### Postman Collection

Import `AgriTech_API.postman_collection.json` into Postman. Set the `api_key` and `base_url` collection variables before testing.

## Swagger / API Docs

Interactive API documentation is served directly from the API server — no extra tools needed.

| URL | Description |
|-----|-------------|
| [http://localhost:3001/api/docs](http://localhost:3001/api/docs) | Swagger UI — browse and test all endpoints |
| [http://localhost:3001/api/openapi.json](http://localhost:3001/api/openapi.json) | OpenAPI 3.0 spec (JSON) |

Both endpoints are **public** (no API key required). Open `/api/docs` in your browser after starting the server.

To authenticate in Swagger UI, click the **Authorize** button (lock icon) and enter your `API_KEY` value.

## HTTP API (REST)

### Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/docs` | No | Swagger UI |
| GET | `/api/openapi.json` | No | OpenAPI 3.0 spec |
| GET | `/api/health` | No | Health check |
| POST | `/api/data` | Yes | Submit sensor readings + evaluate rules |
| GET | `/api/data/latest` | Yes | Get latest readings from InfluxDB |
| GET | `/api/ac` | Yes | Get AC status |
| POST | `/api/ac` | Yes | Control AC (power, temp, mode) |
| GET | `/api/rules` | Yes | List all rules (config server) |
| POST | `/api/rules` | Yes | Create a new rule |
| PUT | `/api/rules/{id}` | Yes | Update a rule |
| DELETE | `/api/rules/{id}` | Yes | Delete a rule |
| GET | `/api/commands` | Yes | Arduino polls for pending commands |
| GET | `/api/notifications` | Yes | Notification channel status & alert history |
| POST | `/api/notifications/test` | Yes | Fire a test alert through all channels |

### POST /api/data

Submit sensor data from Arduino. The server stores the data in InfluxDB and evaluates all rules from the config server.

**Request:**

```http
POST /api/data HTTP/1.1
Content-Type: application/json

{"temperature": 25.5, "humidity": 60.0}
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `temperature` | float | Yes | Temperature in Celsius |
| `humidity` | float | Yes | Relative humidity (%) |
| `sensor_id` | string | No | Device identifier (default: "arduino_1") |

**Extended Payload (optional fields):**

```json
{
    "temperature": 25.5,
    "humidity": 60.0,
    "sensor_id": "greenhouse_1",
    "ph": 6.2,
    "ec": 1.5,
    "water_temp": 22.0,
    "water_level": 80.0
}
```

**Response (201 Created):**

```json
{
    "status": "saved",
    "data": {"temperature": 25.5, "humidity": 60.0},
    "triggered_rules": ["led_high_temp"]
}
```

The `triggered_rules` field shows which rules fired based on the sensor data.

### AC Control Endpoints (Haier hOn)

Control your Haier AC unit via the hOn API.

**Setup:** Add your Haier hOn credentials to `.env`:
```
HON_EMAIL=your-email@example.com
HON_PASSWORD=your-password
```

#### GET /api/ac - Get AC Status

```json
{
    "available": true,
    "power": true,
    "target_temp": 24,
    "current_temp": 26.5,
    "mode": "cool",
    "fan_speed": "auto"
}
```

#### POST /api/ac - Control AC

```json
{
    "power": true,
    "temperature": 24,
    "mode": "cool"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `power` | bool | Turn AC on/off |
| `temperature` | int | Target temperature (16-30) |
| `mode` | string | `auto`, `cool`, `heat`, `fan`, `dry` |

## Config Server (Rule Engine)

The config server centralizes all decision logic. Instead of hardcoding thresholds in the Arduino sketch or the server, all rules are stored in `rules_config.json` and are editable via API at runtime.

### How It Works

1. Arduino sends sensor data via `POST /api/data`
2. The rule engine evaluates all enabled rules against the data
3. For **arduino** actions: commands are queued and the Arduino picks them up via `GET /api/commands`
4. For **ac** actions: the server calls the Haier hOn API directly

### Rule Structure

```json
{
    "id": "ac_cooling",
    "name": "AC Auto Cooling",
    "enabled": true,
    "sensor": "temperature",
    "condition": "above",
    "threshold": 28.0,
    "action": {"type": "ac", "command": "cool", "target_temp": 24}
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `name` | string | Human-readable name |
| `enabled` | bool | Whether the rule is active |
| `sensor` | string | Which sensor field to evaluate (`temperature`, `humidity`, `ph`, etc.) |
| `condition` | string | `above` or `below` |
| `threshold` | float | The threshold value |
| `action` | object | What to do when the rule fires |

### Action Types

**Arduino actions** — queued for polling:
```json
{"type": "arduino", "command": "led_blink"}
{"type": "arduino", "command": "led_on"}
{"type": "arduino", "command": "led_off"}
```

**AC actions** — executed immediately:
```json
{"type": "ac", "command": "cool", "target_temp": 24}
{"type": "ac", "command": "heat", "target_temp": 22}
{"type": "ac", "command": "off"}
```

**Notification actions** — sent through all available channels:
```json
{"type": "notify", "severity": "critical", "message": "Temperature too high"}
{"type": "notify", "severity": "warning", "message": "Humidity too low"}
```

### Default Rules

The system ships with 13 rules in `rules_config.json`:

**AC & LED rules:**

| Rule | Condition | Action |
|------|-----------|--------|
| `ac_cooling` | temperature > 28°C | AC on, cool mode, 24°C |
| `ac_shutoff` | temperature < 18°C | AC off |
| `led_high_temp` | temperature > 16°C | LED blink |
| `led_high_humidity` | humidity > 60% | LED blink |

**Hydroponic notification alerts:**

| Rule | Condition | Severity | Alert |
|------|-----------|----------|-------|
| `notify_high_temp` | temperature > 30°C | critical | Temperature too high |
| `notify_low_temp` | temperature < 15°C | warning | Temperature too low |
| `notify_high_humidity` | humidity > 80% | warning | Humidity too high — risk of mold |
| `notify_low_humidity` | humidity < 40% | warning | Humidity too low |
| `notify_high_ph` | pH > 7.0 | critical | pH too alkaline — nutrient lockout risk |
| `notify_low_ph` | pH < 5.5 | critical | pH too acidic — root damage risk |
| `notify_high_ec` | EC > 2.5 mS/cm | warning | EC too high — nutrient burn risk |
| `notify_low_ec` | EC < 0.8 mS/cm | warning | EC too low — nutrient deficiency |
| `notify_low_water` | water_level < 20% | critical | Water level critically low |

### API Examples

**List all rules:**
```bash
curl -H "X-API-Key: $API_KEY" http://localhost:3001/api/rules
```

**Get a specific rule:**
```bash
curl -H "X-API-Key: $API_KEY" http://localhost:3001/api/rules/ac_cooling
```

**Update a threshold (no Arduino redeploy needed):**
```bash
curl -X PUT http://localhost:3001/api/rules/notify_high_temp \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"threshold": 28.0}'
```

**Create a new rule:**
```bash
curl -X POST http://localhost:3001/api/rules \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "notify_water_temp",
    "name": "Alert: Water Temperature High",
    "sensor": "water_temp",
    "condition": "above",
    "threshold": 28.0,
    "action": {"type": "notify", "severity": "warning", "message": "Water temperature too high for roots"}
  }'
```

**Delete a rule:**
```bash
curl -X DELETE -H "X-API-Key: $API_KEY" http://localhost:3001/api/rules/notify_water_temp
```

**Arduino polls for commands:**
```bash
curl -H "X-API-Key: $API_KEY" http://localhost:3001/api/commands?sensor_id=arduino_1
# Response: {"commands": {"led": "blink"}}
```

### Testing the Rule Engine

Run the test suite:
```bash
cd backend/api
pip install pytest
pytest test_rule_engine.py test_notification_service.py -v
```

The test suite (46 tests) covers:
- Rule evaluation (above/below thresholds, boundary values)
- Disabled rules are skipped
- Arduino command queue (queuing, clearing after poll, default LED off)
- Independent command queues per sensor_id
- CRUD operations (create, update, delete, validation)
- Persistence (rules survive server restart)
- Notification channels (console, stubs for WhatsApp/SMS/email)
- Cooldown logic (prevents alert spam)
- Alert history tracking
- Rule engine integration with notify actions

## Notification Service

The notification service sends alerts when sensor data breaches rule thresholds. It uses a **channel-agnostic architecture** — add new channels without changing any existing code.

### How It Works

1. Rule engine detects a threshold breach (e.g. `temperature > 30`)
2. If the rule's action type is `"notify"`, the notification service is called
3. The service sends the alert through **all available channels**
4. A per-rule **cooldown** (default: 15 minutes) prevents repeated alerts

### Available Channels

| Channel | Status | Configuration |
|---------|--------|---------------|
| Console | Active | Always available — prints alerts to server log |
| WhatsApp | Stub | Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM/TO` in `.env` |
| SMS | Stub | Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_SMS_FROM/TO` in `.env` |
| Email | Stub | Set `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `ALERT_EMAIL_TO` in `.env` |

Channels become available automatically when their credentials are configured — no code changes needed.

### Endpoints

**Fire a test alert** (bypasses cooldown):
```bash
curl -X POST -H "X-API-Key: $API_KEY" http://localhost:3001/api/notifications/test
```

**Check notification status and recent alerts:**
```bash
curl -H "X-API-Key: $API_KEY" http://localhost:3001/api/notifications
```

Response:
```json
{
  "channels": [
    {"name": "console", "available": true},
    {"name": "whatsapp", "available": false},
    {"name": "sms", "available": false},
    {"name": "email", "available": false}
  ],
  "cooldown_seconds": 900,
  "recent_alerts": [
    {
      "timestamp": "2026-02-08T15:30:00",
      "rule_id": "notify_high_temp",
      "severity": "critical",
      "message": "Temperature too high for hydroponics",
      "sensor_data": {"temperature": 33.0, "humidity": 85.0}
    }
  ]
}
```

### Quick Test with Postman

1. Import `AgriTech_API.postman_collection.json`
2. Set `api_key` and `base_url` in collection variables
3. Run **"Send Sensor Data (trigger alerts)"** — sends critical values that breach multiple thresholds
4. Run **"Test Alert (all channels)"** — fires a test directly
5. Run **"Get Notification Status & History"** — verify alerts were recorded

### Cooldown

To prevent alert spam (Arduino sends data every 2 seconds), each rule has a cooldown period. After an alert fires, the same rule won't alert again until the cooldown expires.

Configure via `.env`:
```
NOTIFICATION_COOLDOWN=900  # seconds (default: 15 minutes)
```

### Adding a New Channel

Create a class that implements `NotificationChannel` in `notification_service.py`:

```python
class SlackChannel(NotificationChannel):
    @property
    def name(self) -> str:
        return "slack"

    def send(self, subject: str, body: str) -> bool:
        # Your Slack webhook logic here
        return True

    def is_available(self) -> bool:
        return bool(os.getenv('SLACK_WEBHOOK_URL'))
```

Then add it to the `NotificationService` default channels list.

## Step-by-Step: Arduino Data to Database

Complete guide to get sensor data from Arduino into InfluxDB.

### Prerequisites

- Docker Desktop installed and running
- Python 3.x installed
- Arduino UNO R4 WiFi with sensor (DHT11/DHT20)
- USB cable to connect Arduino

### Step 1: Start Docker Containers

```bash
cd backend
docker-compose up -d
```

Verify all containers are running:
```bash
docker ps
```

You should see:
- `agritech-influxdb` (InfluxDB database on port 8086)
- `agritech-postgres` (PostgreSQL database on port 5432)
- `agritech-redis` (Redis cache on port 6379)
- `agritech-grafana` (Dashboard on port 3000)
- `agritech-nodered` (Node-RED flow automation on port 1880)

### Step 2: Start the API Server

```bash
cd backend/api
python server.py
```

The server starts on port 3001 and receives HTTP POST requests from Arduino.

### Step 3: Upload Arduino Sketch

Upload the sketch from `arduino/temp_hum_light_sending_api/temp_hum_light_sending_api.ino` using the Arduino IDE.

Make sure:
- Board: **Arduino UNO R4 WiFi**
- Port: The correct COM port for your board
- `config.h` exists with your WiFi credentials, server IP, and API key (copy from `config.h.example`)

### Step 4: Verify Data Flow

Check the API server console — you should see:
```
[Arduino] Received: {'temperature': 25.5, 'humidity': 60.0} | Rules triggered: 1
```

### Step 5: Query Data in InfluxDB

**Option A: Web UI**
1. Open http://localhost:8086
2. Login with credentials from `.env` (INFLUXDB_USERNAME / INFLUXDB_PASSWORD)
3. Go to **Data Explorer**
4. Select bucket `hydroponics`
5. Run query

**Option B: Command Line**
```bash
docker exec -it agritech-influxdb influx query \
  'from(bucket:"hydroponics") |> range(start: -1h)' \
  --org "$INFLUXDB_ORG" \
  --token "$INFLUXDB_TOKEN"
```

### Step 6: View in Grafana

1. Open http://localhost:3000
2. Login with credentials from `.env` (GRAFANA_USER / GRAFANA_PASSWORD)
3. Go to Dashboards > Browse
4. Open the hydroponics dashboard

## Grafana Dashboards

15 pre-configured dashboards are provisioned across 3 folders with 2 datasources (InfluxDB + PostgreSQL):

### Production (7 dashboards)
| Dashboard | URL | Panels | Data Source |
|-----------|-----|--------|-------------|
| Hydroponics Overview | `/d/hydroponics-overview` | 8 | InfluxDB |
| Greenhouse Realtime | `/d/greenhouse-realtime` | 16 | InfluxDB |
| Crop Lifecycle | `/d/crop-lifecycle` | 10 | PostgreSQL |
| Yield & Harvest | `/d/yield-harvest` | 10 | PostgreSQL |
| Alerts & Rule Engine | `/d/alerts-rule-engine` | 10 | PostgreSQL |
| Environment & Weather | `/d/environment-weather` | 10 | InfluxDB |
| Sensor Health | `/d/sensor-health` | 10 | Both |

### Business (4 dashboards)
| Dashboard | URL | Panels | Data Source |
|-----------|-----|--------|-------------|
| SaaS Revenue | `/d/saas-revenue` | 14 | PostgreSQL |
| Client Health | `/d/client-health` | 10 | PostgreSQL |
| Site Visits | `/d/site-visits` | 10 | PostgreSQL |
| Market Intelligence | `/d/market-intelligence` | 8 | InfluxDB + text |

### DevOps (4 dashboards)
| Dashboard | URL | Panels | Data Source |
|-----------|-----|--------|-------------|
| ETL & Data Pipeline | `/d/etl-pipeline` | 10 | PostgreSQL |
| API Performance | `/d/api-performance` | 2 | Stub (needs middleware) |
| Docker Resources | `/d/docker-resources` | 2 | Stub (needs cAdvisor) |
| CI/CD Pipeline | `/d/cicd-pipeline` | 2 | Stub (needs GitHub integration) |

Dashboard files are in `grafana/dashboards/{production,business,devops}/`.

## Data Retention

InfluxDB is configured with default retention policies. For Phase 1 (90 days of data), the default settings are sufficient.

To configure custom retention:
```bash
docker exec -it agritech-influxdb influx bucket update \
    --name hydroponics \
    --retention 90d
```

## Troubleshooting

### API Server not receiving data

1. Check the API server is running: `python server.py`
2. Verify Arduino is connected to WiFi (check Serial Monitor)
3. Verify `API_HOST` in the Arduino sketch matches your server IP
4. Check firewall is not blocking port 3001

### No data in Grafana

1. Check if API server logs show incoming data
2. Verify InfluxDB has data:
```bash
docker exec -it agritech-influxdb influx query \
    'from(bucket:"hydroponics") |> range(start: -1h) |> limit(n:10)'
```

### Arduino Uno R4 WiFi — Upload Fails ("Device unsupported")

The Uno R4 WiFi uses a **Renesas RA4M1** chip. If you see:

```
"C:\...\bossac\1.9.1-arduino5/bossac" --port=COM9 ...
Device unsupported
Failed uploading: uploading error: exit status 1
```

**Most common cause: another process is holding the COM port open.** The Arduino IDE cannot send the 1200bps reset signal if the serial port is locked by another program.

**Fix (check in this order):**

1. **Close anything using the COM port:**
   - Close Arduino IDE Serial Monitor
   - Kill any Python process holding the port:
     ```bash
     tasklist | grep -i python
     taskkill //PID <pid> //F
     ```
2. **Verify board selection** — In **Tools > Board**, make sure you selected **Arduino UNO R4 Boards > Arduino UNO R4 WiFi** (not "Arduino AVR Boards > Arduino Uno")
3. **Reinstall the board package** — **Tools > Board Manager** > search `UNO R4` > remove "Arduino UNO R4 Boards" > close IDE > reopen > install it again (latest version)
4. **Verify the fix** — Enable verbose upload (**File > Preferences > Show verbose output during: Upload**) and check the upload command in the output

### Arduino Uno R4 WiFi — Wrong COM Port

The Uno R4 WiFi connects over USB. In Device Manager, look for **USB Serial Device** entries (e.g. COM3, COM9), not Bluetooth or legacy ports.

| Port Type | Example | Is it the Arduino? |
|-----------|---------|-------------------|
| USB Serial Device | COM3, COM9 | Yes (one of these) |
| Standard Serial over Bluetooth | COM5, COM6 | No |
| Communications Port | COM1 | No |

To identify which USB port is the Arduino: unplug the board, see which COM port disappears, plug it back in.

### Arduino Uno R4 WiFi — Upload Still Fails After Closing Serial

If the COM port is free but upload still fails:

1. **Double-tap the RESET button** on the board to force bootloader mode (LED will pulse)
2. A new COM port may appear — select it in **Tools > Port**
3. Click **Upload** immediately (bootloader mode times out after ~10s)
4. Try a different USB cable — some cables are charge-only (no data lines)
5. **Check the COM port** — The Arduino may change COM port after each reconnect. Open Device Manager, unplug the board, see which port disappears, plug it back, note the new port, and select it in **Tools > Port**

### Arduino Uno R4 WiFi — COM Port Changes on Every Reconnect

Windows may assign a different COM port each time the Arduino reconnects.

**To assign a fixed COM port:**

1. Open **Device Manager**
2. Right-click the Arduino's **USB Serial Device** (e.g. COM9)
3. **Properties > Port Settings > Advanced**
4. Choose a fixed COM port number (e.g. COM9)
5. Click OK and restart the Arduino

### DHT11 Library on Uno R4 WiFi

The `Arduino_SensorKit` library does **not** support the Uno R4 WiFi (`renesas_uno` architecture). Use the **DHT sensor library** by Adafruit instead:

1. **Library Manager** > install "DHT sensor library" (by Adafruit)
2. **Library Manager** > install "Adafruit Unified Sensor" (dependency)

```cpp
#include <DHT.h>

#define DHT_PIN 3
#define DHT_TYPE DHT11

DHT dht(DHT_PIN, DHT_TYPE);

void setup() {
  Serial.begin(9600);
  dht.begin();
}

void loop() {
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }

  Serial.print("Temperature = ");
  Serial.print(temperature);
  Serial.println(" C");
  Serial.print("Humidity = ");
  Serial.print(humidity);
  Serial.println(" %");
  delay(2000);
}
```

### Reset everything

```bash
docker-compose down -v
docker-compose up -d
```

## Next Steps (Phase 2)

For Phase 2 with Siemens LOGO! PLC, you'll add:
- Modbus TCP integration
- Industrial sensor support (4-20mA)
- Node-RED automation flows
- Real notification channels (WhatsApp via Twilio, Email via SMTP)
- Additional sensors (pH probe, EC meter, water level sensor)
