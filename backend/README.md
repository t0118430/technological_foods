# AgriTech Hydroponics Backend - Phase 1

Backend infrastructure for the AgriTech NFT Hydroponics automation system.

## Architecture

```
Arduino UNO R4 WiFi --HTTP POST--> API Server (server.py) ---> InfluxDB
                                                                   |
                                                                   v
                                                               Grafana
                                                            (dashboards)

Node-RED (flow automation) ---> InfluxDB
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| InfluxDB | 8086 | Time-series database |
| Grafana | 3000 | Dashboard visualization |
| Node-RED | 1880 | Visual flow programming |
| API Server | 3001 | HTTP API (runs outside Docker) |

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

2. Install API dependencies:
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
Endpoints:
  GET  /api/health      - Health check
  GET  /api/data/latest - Get latest reading from InfluxDB
  POST /api/data        - Save Arduino data to InfluxDB
  GET  /api/ac          - Get AC status
  POST /api/ac          - Control AC (power, temperature, mode)
  GET  /api/ac/auto     - Get auto control settings
  POST /api/ac/auto     - Set auto control settings
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

## HTTP API (REST)

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/data` | Submit sensor readings |
| GET | `/api/data/latest` | Get latest readings |
| GET | `/api/health` | Health check |
| GET | `/api/ac` | Get AC status |
| POST | `/api/ac` | Control AC (power, temp, mode) |
| GET | `/api/ac/auto` | Get auto control settings |
| POST | `/api/ac/auto` | Set auto control settings |

### POST /api/data

Submit sensor data from Arduino.

**Request:**

```http
POST /api/data HTTP/1.1
Host: your-server.com
Content-Type: application/json
Content-Length: 42

{"temperature": 25.5, "humidity": 60.0}
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `temperature` | float | Yes | Temperature in Celsius |
| `humidity` | float | Yes | Relative humidity (%) |
| `sensor_id` | string | No | Device identifier (default: "arduino_1") |
| `timestamp` | string | No | ISO 8601 timestamp (default: server time) |

**Extended Payload (optional fields):**

```json
{
    "temperature": 25.5,
    "humidity": 60.0,
    "sensor_id": "greenhouse_1",
    "timestamp": "2026-02-07T10:30:00Z",
    "ph": 6.2,
    "ec": 1.5,
    "water_temp": 22.0,
    "water_level": 80.0
}
```

**Response (Success - 201 Created):**

```json
{
    "status": "ok",
    "message": "Data received",
    "id": "abc123"
}
```

**Response (Error - 400 Bad Request):**

```json
{
    "status": "error",
    "message": "Missing required field: temperature"
}
```

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

#### GET /api/ac/auto - Get Auto Control Settings

```json
{
    "enabled": false,
    "max_temp": 28.0,
    "min_temp": 18.0,
    "target_temp": 24
}
```

#### POST /api/ac/auto - Set Auto Control

Enable automatic AC control based on sensor readings:

```json
{
    "enabled": true,
    "max_temp": 28.0,
    "min_temp": 20.0,
    "target_temp": 24
}
```

When enabled:
- AC turns **ON** (cooling mode) when temperature exceeds `max_temp`
- AC turns **OFF** when temperature drops below `min_temp`

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
- WiFi credentials are set in the sketch
- `API_HOST` points to your server IP
- `API_PORT` is `3001`

### Step 4: Verify Data Flow

Check the API server console — you should see:
```
[Arduino] Received: {'temperature': 25.5, 'humidity': 60.0}
Stored in InfluxDB: {'temperature': 25.5, 'humidity': 60.0}
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

## Grafana Dashboard

A pre-configured dashboard is available at:
`http://localhost:3000/d/hydroponics-overview`

The dashboard includes:
- pH level over time (with optimal range 5.8-6.5)
- EC level over time (with optimal range 1.2-2.5 mS/cm)
- Temperature graphs (water + air)
- Humidity monitoring
- Current value gauges with color-coded thresholds

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
- Alerting via email/SMS
