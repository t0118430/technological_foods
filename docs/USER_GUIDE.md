# AgriTech Hydroponics — User Guide

> Complete guide for product owners, operators, and anyone using the AgriTech NFT Hydroponics platform.

---

## Table of Contents

1. [Platform Overview](#1-platform-overview)
2. [Getting Started](#2-getting-started)
3. [Daily Operations](#3-daily-operations)
4. [Crop Management](#4-crop-management)
5. [Sensor Monitoring & Analytics](#5-sensor-monitoring--analytics)
6. [Alert & Notification System](#6-alert--notification-system)
7. [Rule Engine](#7-rule-engine)
8. [Weather & External Data](#8-weather--external-data)
9. [Business & SaaS](#9-business--saas)
10. [Reports & Data Export](#10-reports--data-export)
11. [Dashboards Guide](#11-dashboards-guide)
12. [Sensor Calibration](#12-sensor-calibration)
13. [ETL Pipeline](#13-etl-pipeline)
14. [Troubleshooting](#14-troubleshooting)
15. [API Quick Reference](#15-api-quick-reference)

---

## 1. Platform Overview

### What the System Does

The AgriTech platform monitors your NFT hydroponic greenhouse 24/7. Arduino sensors measure temperature, humidity, pH, EC (electrical conductivity), water level, water temperature, and light. The data flows to a central API server which stores it, evaluates rules, sends alerts, and tracks crop progress from germination to harvest.

### Data Flow

```
  Sensors (Arduino)                External Sources
  temp, humidity, pH,              weather, electricity,
  EC, water level, light           solar, market prices
        │                                │
        │ Every 2 seconds                │ Scheduled intervals
        ▼                                ▼
  ┌──────────────────────────────────────────┐
  │           API Server (:3001)             │
  │                                          │
  │  1. Store in InfluxDB (real-time)        │
  │  2. Evaluate rules → trigger actions     │
  │  3. Update crop stages                   │
  │  4. Cache latest in Redis                │
  │  5. ETL → PostgreSQL (hourly/daily)      │
  └──────────────────────────────────────────┘
        │              │              │
        ▼              ▼              ▼
   InfluxDB       PostgreSQL       Redis
   (sensor        (crops, BI,      (latest
    history)       business)       readings)
        │              │
        └──────┬───────┘
               ▼
         Grafana (15 dashboards)
```

### Key URLs

| Service | URL | Purpose |
|---|---|---|
| API Server | http://localhost:3001 | REST API |
| Swagger UI | http://localhost:3001/api/docs | Interactive API docs |
| Grafana | http://localhost:3000 | Dashboards |
| InfluxDB | http://localhost:8086 | Time-series database |
| Node-RED | http://localhost:1880 | Flow automation |
| Business Dashboard | http://localhost:3001/business | Business HTML UI |
| Site Visits | http://localhost:3001/site-visits | Site visits HTML UI |

---

## 2. Getting Started

### Prerequisites

- **Docker Desktop** installed and running
- **Python 3.x** installed
- A `.env` file configured (copy from `.env.example`)

### First-Time Setup

**Step 1 — Start Docker services:**
```bash
cd backend
docker-compose up -d
```

Verify all 5 containers are running:
```bash
docker ps
```

You should see: `agritech-influxdb`, `agritech-postgres`, `agritech-redis`, `agritech-grafana`, `agritech-nodered`.

**Step 2 — Install API dependencies:**
```bash
cd backend/api
pip install -r requirements.txt
```

**Step 3 — Start the API server:**
```bash
python server.py
```

The server prints all available endpoints on startup. Look for:
```
Server running at http://0.0.0.0:3001
Swagger UI:  http://localhost:3001/api/docs
```

**Step 4 — Verify the system:**
```bash
# Health check (no API key needed)
curl http://localhost:3001/api/health

# Check sensor analytics (API key required)
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/analytics/summary
```

### Authentication

All API endpoints except health, docs, and a few public UIs require an `X-API-Key` header. The key is set in your `.env` file as `API_KEY`.

```bash
# All authenticated requests use this pattern:
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/...
```

Public endpoints (no key needed): `/`, `/api/health`, `/api/docs`, `/api/openapi.json`, `/business`, `/site-visits`, `/api/etl/status`, `/api/site-visits/*`, `/api/help`.

---

## 3. Daily Operations

### Morning Checklist

1. **Check system health:**
   ```bash
   curl http://localhost:3001/api/health
   ```

2. **Review latest sensor readings:**
   ```bash
   curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/data/latest
   ```

3. **Check active alerts:**
   ```bash
   curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/escalation
   ```

4. **Review crop dashboard:**
   ```bash
   curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/dashboard
   ```

5. **Check weather advisory:**
   ```bash
   curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/weather/advisory
   ```

### Normal Sensor Ranges (NFT Hydroponics)

| Sensor | Optimal Range | Warning | Critical |
|---|---|---|---|
| Temperature | 18–28 °C | < 15 or > 30 °C | < 10 or > 35 °C |
| Humidity | 40–80 % | < 40 or > 80 % | < 30 or > 90 % |
| pH | 5.5–7.0 | < 5.5 or > 7.0 | < 5.0 or > 7.5 |
| EC | 0.8–2.5 mS/cm | < 0.8 or > 2.5 | < 0.5 or > 3.0 |
| Water Level | > 20 % | < 20 % | < 10 % |
| Water Temp | 18–24 °C | < 16 or > 26 °C | < 14 or > 28 °C |

### What to Watch For

- **VPD (Vapor Pressure Deficit):** Ideal range 0.4–1.6 kPa. Check via `/api/analytics/vpd`
- **DLI (Daily Light Integral):** Target depends on crop variety. Check via `/api/analytics/dli`
- **Trends:** Look for sustained upward/downward trends at `/api/analytics/trends`
- **Anomalies:** Unusual readings flagged at `/api/analytics/anomalies`

---

## 4. Crop Management

### Supported Varieties

| Variety | Code | Flowering/Fruiting Stages |
|---|---|---|
| Rosso Premium (lettuce) | `rosso_premium` | No |
| Curly Green (lettuce) | `curly_green` | No |
| Arugula Rocket | `arugula_rocket` | No |
| Basil Genovese | `basil_genovese` | No |
| Mint Spearmint | `mint_spearmint` | No |
| Cherry Tomato | `tomato_cherry` | Yes |

### Growth Stages

All varieties follow this progression:

```
germination → seedling → transplant → vegetative → [flowering*] → [fruiting*] → maturity → harvest_ready
```

*Flowering and fruiting stages apply only to `tomato_cherry` and other fruit-bearing varieties.

Each stage has variety-specific optimal conditions (temperature, humidity, EC, light hours) and a minimum duration before auto-advancement.

### Register a New Crop Batch

```bash
curl -X POST http://localhost:3001/api/crops \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "variety": "rosso_premium",
    "batch_name": "Batch 2026-Q1",
    "quantity": 50,
    "notes": "NFT channel A"
  }'
```

Response includes the `crop_id` you will use for all subsequent operations.

### Monitor Crop Progress

```bash
# Get crop details and stage history
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/crops/1

# Get stage-specific optimal conditions
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/crops/1/conditions

# Get stage-specific monitoring rules
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/crops/1/rules

# Full crop dashboard (all active crops)
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/dashboard
```

### Advance to Next Stage

Stages auto-advance when the minimum duration is met. To manually advance:

```bash
curl -X POST http://localhost:3001/api/crops/1/advance \
  -H "X-API-Key: YOUR_KEY"
```

### Record a Harvest

```bash
curl -X POST http://localhost:3001/api/crops/1/harvest \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "weight_grams": 2500,
    "quality_score": 8,
    "notes": "Good color, slightly smaller heads than expected"
  }'
```

### Harvest Analytics

```bash
# Performance metrics across all harvests
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/harvest/analytics
```

Returns average yields, quality scores, and variety comparisons.

### Crop Intelligence

```bash
# Condition-to-harvest correlations (what conditions produce best yields)
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/intelligence/correlations

# Optimization recommendations for a specific crop
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/intelligence/recommendations/1

# Yield prediction based on current conditions
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/intelligence/predict/1

# Crop health score (0-100)
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/intelligence/health/1
```

---

## 5. Sensor Monitoring & Analytics

### Real-Time Readings

```bash
# Latest sensor data from InfluxDB
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/data/latest
```

Returns the most recent values for temperature, humidity, pH, EC, water level, water temperature, and light.

### Full Analytics Snapshot

```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/analytics/summary
```

Returns VPD, DLI, trends, and anomalies in a single response.

### VPD (Vapor Pressure Deficit)

VPD combines temperature and humidity into a single metric that indicates how hard plants need to work to transpire.

```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/analytics/vpd
```

| VPD Range | Classification | Meaning |
|---|---|---|
| < 0.4 kPa | Too low | Risk of mold, poor transpiration |
| 0.4–0.8 kPa | Propagation | Good for seedlings and clones |
| 0.8–1.2 kPa | Vegetative | Ideal for growth phase |
| 1.2–1.6 kPa | Flowering | Good for flowering/fruiting |
| > 1.6 kPa | Too high | Plant stress, stomata close |

### DLI (Daily Light Integral)

DLI measures total photosynthetically active light received over 24 hours.

```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/analytics/dli
```

Returns current DLI progress and projected daily total based on the trend.

### Trend Detection

```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/analytics/trends
```

Shows trend direction (rising, falling, stable) for each sensor over the recent window.

### Anomaly Detection

```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/analytics/anomalies
```

Flags readings that deviate significantly from expected patterns (sudden spikes, unusual values).

### Historical Data

```bash
# Last 24 hours, hourly aggregation
curl -H "X-API-Key: YOUR_KEY" "http://localhost:3001/api/analytics/history?hours=24&aggregation=1h"

# Last 7 days, daily aggregation
curl -H "X-API-Key: YOUR_KEY" "http://localhost:3001/api/analytics/history?hours=168&aggregation=1d"
```

---

## 6. Alert & Notification System

### How Alerts Work

1. Arduino sends sensor data every ~2 seconds via `POST /api/data`
2. The rule engine evaluates all enabled rules against the data
3. When a threshold is breached, a notification is sent through all configured channels
4. A cooldown period (default: 15 minutes) prevents repeated alerts for the same rule

### 4 Escalation Levels

The system uses progressive escalation. If an issue persists and no action is taken:

| Level | Name | Wait Time | Priority | Action |
|---|---|---|---|---|
| 1 | PREVENTIVE | — | 3 | First alert with advisory |
| 2 | WARNING | 5 min | 4 | Repeated alert, situation persisting |
| 3 | CRITICAL | 10 min | 4 | Urgent alert, immediate action needed |
| 4 | URGENT | 15 min | 5 | Maximum priority, all channels |

Escalation is intelligent: it detects if you have taken action (e.g., AC turned on) and can de-escalate or confirm resolution automatically.

### Notification Channels

| Channel | Setup | Description |
|---|---|---|
| **Console** | Always active | Prints to server log |
| **ntfy** | Set `NTFY_TOPIC` in `.env` | Push notifications to phone/desktop |
| **WhatsApp** | Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM/TO` | Via Twilio |
| **SMS** | Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_SMS_FROM/TO` | Via Twilio |
| **Email** | Set `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `ALERT_EMAIL_TO` | Via SMTP |

Channels are auto-detected. Configure the credentials in `.env` and they activate automatically.

### Setting Up ntfy (Recommended for Mobile)

1. Install the ntfy app on your phone (Android/iOS)
2. Subscribe to your topic (e.g., `agritech-alerts`)
3. Add to `.env`:
   ```
   NTFY_TOPIC=agritech-alerts
   ```
4. Restart the server — alerts now push to your phone

### Checking Alert Status

```bash
# Current notification channel status and recent alerts
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/notifications

# Alert escalation status and active alerts
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/escalation
```

### Testing Alerts

```bash
# Send test alert with default data
curl -X POST -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/notifications/test

# Send test alert with real sensor data
curl -X POST -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/notifications/test-real
```

---

## 7. Rule Engine

### How Rules Work

The rule engine is the central decision-maker. Each rule watches a sensor value and triggers an action when a threshold is crossed. Rules are stored in `rules_config.json` and editable via API at runtime — no Arduino redeployment needed.

### Default Rules (13)

The system ships with rules for:

**AC & LED automation:**
- `ac_cooling` — Temperature > 28°C → AC on, cool mode, 24°C
- `ac_shutoff` — Temperature < 18°C → AC off
- `led_high_temp` — Temperature > 16°C → LED blink
- `led_high_humidity` — Humidity > 60% → LED blink

**Alert notifications:**
- `notify_high_temp` — Temperature > 30°C → Critical alert
- `notify_low_temp` — Temperature < 15°C → Warning
- `notify_high_humidity` — Humidity > 80% → Warning (mold risk)
- `notify_low_humidity` — Humidity < 40% → Warning
- `notify_high_ph` — pH > 7.0 → Critical (nutrient lockout)
- `notify_low_ph` — pH < 5.5 → Critical (root damage)
- `notify_high_ec` — EC > 2.5 → Warning (nutrient burn)
- `notify_low_ec` — EC < 0.8 → Warning (nutrient deficiency)
- `notify_low_water` — Water level < 20% → Critical

### List All Rules

```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/rules
```

### Create a New Rule

```bash
curl -X POST http://localhost:3001/api/rules \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "notify_water_temp_high",
    "name": "Alert: Water Temperature High",
    "enabled": true,
    "sensor": "water_temp",
    "condition": "above",
    "threshold": 26.0,
    "action": {
      "type": "notify",
      "severity": "warning",
      "message": "Water temperature too high for roots"
    }
  }'
```

### Update a Rule Threshold

```bash
curl -X PUT http://localhost:3001/api/rules/notify_high_temp \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"threshold": 29.0}'
```

### Delete a Rule

```bash
curl -X DELETE -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/rules/notify_water_temp_high
```

### Action Types

**Arduino actions** — queued for Arduino to pick up via `GET /api/commands`:
```json
{"type": "arduino", "command": "led_blink"}
{"type": "arduino", "command": "led_on"}
{"type": "arduino", "command": "led_off"}
```

**AC actions** — executed immediately via Haier hOn API:
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

### Compound Weather Rules

You can create rules that respond to weather data harvested from external APIs. For example, if the forecast shows extreme heat, pre-cool the greenhouse:

```bash
curl -X POST http://localhost:3001/api/rules \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "ac_precool_forecast",
    "name": "Pre-cool before heat wave",
    "enabled": true,
    "sensor": "temperature",
    "condition": "above",
    "threshold": 26.0,
    "action": {"type": "ac", "command": "cool", "target_temp": 22}
  }'
```

---

## 8. Weather & External Data

### Weather Endpoints

All weather data comes from the Open-Meteo API (free, no key required), targeted at the Algarve region.

```bash
# Current outdoor conditions
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/weather/current

# 3-day forecast
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/weather/forecast

# Solar data (sunrise, sunset, day length)
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/weather/solar

# Indoor vs outdoor comparison
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/weather/correlation

# Growing conditions advisory
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/weather/advisory
```

### Indoor vs Outdoor Correlation

The `/api/weather/correlation` endpoint compares your greenhouse readings with outdoor weather. This helps identify:
- How well insulation is performing
- Whether ventilation is needed
- How outdoor temperature swings affect indoor conditions

### Growing Advisory

The `/api/weather/advisory` endpoint combines indoor conditions, weather forecast, and crop data to generate actionable advice (e.g., "High temperatures forecast for tomorrow — consider pre-cooling overnight").

### Data Harvester

The data harvester runs on a schedule and collects external data from multiple sources:

| Source | Data | Storage | Frequency |
|---|---|---|---|
| **Weather** | Temperature, humidity, wind, rain | InfluxDB | Every 15 min |
| **Electricity** | OMIE spot prices, cheapest hours | InfluxDB | Hourly |
| **Solar** | Sunrise, sunset, day length, UV | InfluxDB | Daily |
| **Market Prices** | Produce prices per kg | PostgreSQL | Manual/CSV import |
| **Tourism** | Tourism index (affects demand) | PostgreSQL | Manual/CSV import |

```bash
# Status of all harvester sources
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/harvester/status

# Trigger manual harvest (all sources)
curl -X POST -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/harvester/trigger

# Trigger specific source
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"source": "weather"}' \
  http://localhost:3001/api/harvester/trigger
```

### Market Prices

```bash
# Get latest market prices
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/harvester/market-prices

# Add a price entry
curl -X POST http://localhost:3001/api/harvester/market-prices \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"product": "lettuce", "price_per_kg": 2.50, "source": "local_market"}'

# Import prices from CSV
curl -X POST http://localhost:3001/api/harvester/market-prices/import \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: text/csv" \
  --data-binary @prices.csv
```

### Seasonal Demand

```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/market/demand
```

Returns demand multipliers by month and product, useful for planning planting schedules.

---

## 9. Business & SaaS

### Overview

The business module supports a multi-tenant SaaS model where you can manage clients, subscriptions, and revenue tracking. This is the foundation for offering monitoring-as-a-service to other growers.

### Client Management

Access the visual business dashboard at http://localhost:3001/business (no API key needed).

### Subscription Tiers

| Tier | Monthly Price | Alert Types | Data Retention | Support |
|---|---|---|---|---|
| **Bronze** | €49 | Critical only | 7 days | Email |
| **Silver** | €199 | All alerts | 30 days | Email + Chat |
| **Gold** | €499 | Full escalation | 90 days | Priority + Phone |
| **Platinum** | €799 | All + predictive | 180 days | 24/7 Dedicated |

### Business Dashboard API

```bash
# Business intelligence dashboard (MRR, clients, metrics)
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/business/dashboard
```

### Site Visits

The site visits module tracks field visits to client greenhouses.

Access the visual UI at http://localhost:3001/site-visits (no API key needed).

```bash
# List all visits (paginated)
curl -H "X-API-Key: YOUR_KEY" "http://localhost:3001/api/site-visits?page=1&per_page=20"

# Visit analytics
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/site-visits/dashboard

# Create a visit
curl -X POST http://localhost:3001/api/site-visits \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Quinta da Horta",
    "visit_type": "installation",
    "notes": "Initial sensor setup",
    "follow_up_required": true,
    "follow_up_notes": "Check calibration after 48h"
  }'

# Mark follow-up as done
curl -X POST -H "X-API-Key: YOUR_KEY" \
  http://localhost:3001/api/site-visits/1/complete-follow-up

# Export all visits (for CSV)
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/site-visits/export
```

### Market Intelligence

```bash
# Market prices for local produce
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/market/prices

# Seasonal demand multipliers
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/market/demand

# Tourism index (affects local market demand)
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/harvester/tourism
```

---

## 10. Reports & Data Export

### CSV Export

Download sensor data as CSV for spreadsheet analysis:

```bash
# Export last 24 hours of sensor data
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:3001/api/export/sensor-csv?hours=24" \
  -o sensor_data.csv

# Export last 7 days
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:3001/api/export/sensor-csv?hours=168" \
  -o sensor_week.csv
```

### Crop Lifecycle Report

Generate a full lifecycle report for a specific crop batch:

```bash
curl -H "X-API-Key: YOUR_KEY" \
  http://localhost:3001/api/export/crop-report/1
```

Returns: variety info, stage history with timestamps, conditions during each stage, harvest results, and quality scores.

### Weekly Summary

```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/reports/weekly
```

Includes: sensor averages, alert counts, crop stage changes, harvest totals, and condition trends for the past 7 days.

### Monthly Summary

```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/reports/monthly
```

Includes: monthly averages, yield totals, variety comparisons, alert patterns, and business metrics.

---

## 11. Dashboards Guide

### Grafana Dashboards

Access Grafana at http://localhost:3000. Credentials are in your `.env` file (`GRAFANA_USER` / `GRAFANA_PASSWORD`).

All 15 dashboards are auto-provisioned — no manual setup needed.

#### Production Dashboards (7)

| Dashboard | URL | What It Shows |
|---|---|---|
| **Hydroponics Overview** | `/d/hydroponics-overview` | High-level summary of all sensors, 8 panels |
| **Greenhouse Realtime** | `/d/greenhouse-realtime` | Live sensor gauges and time-series, 16 panels |
| **Crop Lifecycle** | `/d/crop-lifecycle` | Active crops, growth stages, stage durations, 10 panels |
| **Yield & Harvest** | `/d/yield-harvest` | Harvest weights, quality scores, variety comparison, 10 panels |
| **Alerts & Rule Engine** | `/d/alerts-rule-engine` | Alert history, rule triggers, escalation status, 10 panels |
| **Environment & Weather** | `/d/environment-weather` | Indoor/outdoor comparison, weather trends, 10 panels |
| **Sensor Health** | `/d/sensor-health` | Sensor uptime, drift detection, calibration status, 10 panels |

#### Business Dashboards (4)

| Dashboard | URL | What It Shows |
|---|---|---|
| **SaaS Revenue** | `/d/saas-revenue` | MRR, ARR, client counts, revenue by tier, 14 panels |
| **Client Health** | `/d/client-health` | Client status, sensor counts, alert frequency, 10 panels |
| **Site Visits** | `/d/site-visits` | Visit history, follow-up tracking, analytics, 10 panels |
| **Market Intelligence** | `/d/market-intelligence` | Produce prices, demand trends, tourism index, 8 panels |

#### DevOps Dashboards (4)

| Dashboard | URL | What It Shows |
|---|---|---|
| **ETL & Data Pipeline** | `/d/etl-pipeline` | ETL status, row counts, watermarks, processing times, 10 panels |
| **API Performance** | `/d/api-performance` | Request latency, error rates (requires middleware) |
| **Docker Resources** | `/d/docker-resources` | Container CPU/memory (requires cAdvisor) |
| **CI/CD Pipeline** | `/d/cicd-pipeline` | Build status, deploy frequency (requires GitHub integration) |

Dashboard JSON files are in `grafana/dashboards/{production,business,devops}/`.

### HTML Dashboards

| Dashboard | URL | Description |
|---|---|---|
| **Business Dashboard** | http://localhost:3001/business | Client management, revenue metrics, SaaS overview |
| **Site Visits** | http://localhost:3001/site-visits | Field visit scheduling, tracking, and analytics |

These are served directly from the API server — no separate frontend needed.

---

## 12. Sensor Calibration

### Why Calibrate

pH and EC sensors drift over time. Regular calibration ensures accurate readings. The system tracks when each sensor was last calibrated and alerts you when calibration is due.

### Record a Calibration

```bash
curl -X POST http://localhost:3001/api/calibrations \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_id": "ph_probe_1",
    "sensor_type": "ph",
    "calibration_value": 7.0,
    "reference_value": 7.0,
    "notes": "Calibrated with pH 7.0 buffer solution"
  }'
```

### Check Due Calibrations

```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/calibrations/due
```

Returns a list of sensors that are due or overdue for calibration.

### Drift Detection

The system monitors sensor readings for signs of drift (gradual shift from expected values):

```bash
# Overall drift status
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/sensors/drift/status

# Drift trend for a specific sensor
curl -H "X-API-Key: YOUR_KEY" http://localhost:3001/api/sensors/drift/ph_probe_1
```

### Dual Sensor Support

For critical measurements, you can run two sensors and the system detects discrepancies:

```bash
curl -X POST http://localhost:3001/api/sensors/dual \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_id": "greenhouse_1",
    "temperature": 25.5,
    "humidity": 60.0,
    "temperature_2": 25.3,
    "humidity_2": 59.8
  }'
```

---

## 13. ETL Pipeline

### What ETL Does

The ETL (Extract, Transform, Load) pipeline moves data from InfluxDB (real-time) to PostgreSQL (analytics). It runs on two schedules:

- **Hourly:** Aggregates sensor readings into hourly averages, min, max per sensor
- **Daily:** Computes daily summaries, condition percentages, and BI metrics

### Check ETL Status

```bash
# Public endpoint (no API key needed)
curl http://localhost:3001/api/etl/status
```

Returns: last run times, watermarks (how far processing has reached), row counts, and error status.

### Enable Background ETL

Set in your `.env` file:
```
ETL_ENABLED=true
```

Restart the server — the background scheduler starts automatically and runs hourly/daily cycles.

### Manual ETL Trigger

```bash
curl -X POST http://localhost:3001/api/etl/run \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"cycle": "hourly"}'
```

Options: `"hourly"`, `"daily"`, `"full"` (both).

### CLI Alternative

For cron jobs or manual runs:

```bash
cd backend/tools

# Run hourly ETL
python run_etl.py --hourly

# Run daily ETL
python run_etl.py --daily

# Full cycle
python run_etl.py --full

# Backfill (re-process historical data)
python run_etl.py --backfill --days 30

# Dry run (no changes)
python run_etl.py --hourly --dry-run
```

---

## 14. Troubleshooting

### API Server Won't Start

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | Missing dependencies | `pip install -r requirements.txt` |
| `Connection refused` to InfluxDB | Docker not running | `docker-compose up -d` |
| Port 3001 in use | Another process | Kill the process or change `HTTP_PORT` in `.env` |

### No Sensor Data

| Symptom | Cause | Fix |
|---|---|---|
| No data in `/api/data/latest` | Arduino not connected | Check Serial Monitor for WiFi connection |
| Arduino sends but no data stored | Wrong API key | Match `API_KEY` in `.env` and `config.h` |
| Data in InfluxDB but not Grafana | Datasource config | Check Grafana datasource points to correct InfluxDB URL |

### Alerts Not Arriving

| Symptom | Cause | Fix |
|---|---|---|
| No alerts at all | All rules disabled | Check `GET /api/rules` — ensure rules have `"enabled": true` |
| Alert fires but no notification | No channels configured | Check `GET /api/notifications` for channel availability |
| Same alert not re-firing | Cooldown active | Wait 15 minutes or adjust `NOTIFICATION_COOLDOWN` in `.env` |
| ntfy not working | Wrong topic | Verify `NTFY_TOPIC` in `.env` matches your subscription |

### Crop Issues

| Symptom | Cause | Fix |
|---|---|---|
| Crop not advancing | Not enough time | Each stage has a minimum duration — check `/api/crops/{id}` |
| Wrong variety config | Variety not seeded | Run `python backend/tools/seed_varieties.py` |
| Stage-specific rules not applying | Crop not in expected stage | Check current stage at `/api/crops/{id}` |

### Docker Services

```bash
# Check all containers
docker ps

# Restart a specific service
docker-compose restart grafana

# View logs
docker-compose logs -f influxdb

# Reset everything (WARNING: deletes all data)
docker-compose down -v && docker-compose up -d
```

### Common InfluxDB Issues

```bash
# Verify data exists
docker exec -it agritech-influxdb influx query \
  'from(bucket:"hydroponics") |> range(start: -1h) |> limit(n:5)' \
  --org "$INFLUXDB_ORG" --token "$INFLUXDB_TOKEN"
```

### ETL Issues

| Symptom | Cause | Fix |
|---|---|---|
| ETL shows "not initialized" | PostgreSQL not ready | Check `docker ps` for postgres container |
| Zero rows processed | No new data since watermark | Check InfluxDB has data in the expected time range |
| Duplicate key errors | Re-running same period | ETL is idempotent — duplicates are handled via upserts |

---

## 15. API Quick Reference

All endpoints require `X-API-Key` header unless marked as **Public**.

### Core

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check **[Public]** |
| GET | `/api/docs` | Swagger UI **[Public]** |
| GET | `/api/openapi.json` | OpenAPI spec **[Public]** |
| GET | `/api/help` | Dashboard help JSON **[Public]** |
| POST | `/api/data` | Submit sensor readings |
| GET | `/api/data/latest` | Latest sensor readings |

### AC Control

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/ac` | Get AC status |
| POST | `/api/ac` | Control AC (power, temp, mode) |

### Rules & Commands

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/rules` | List all rules |
| GET | `/api/rules/{id}` | Get specific rule |
| POST | `/api/rules` | Create a rule |
| PUT | `/api/rules/{id}` | Update a rule |
| DELETE | `/api/rules/{id}` | Delete a rule |
| GET | `/api/commands` | Arduino command polling |

### Notifications & Escalation

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/notifications` | Channel status & alert history |
| POST | `/api/notifications/test` | Send test alert (default data) |
| POST | `/api/notifications/test-real` | Send test alert (real sensor data) |
| GET | `/api/escalation` | Escalation status & active alerts |

### Crop Management

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/crops` | Create new crop batch |
| GET | `/api/crops` | List active crops |
| GET | `/api/crops/{id}` | Crop details & stage history |
| GET | `/api/crops/{id}/conditions` | Stage-specific optimal conditions |
| GET | `/api/crops/{id}/rules` | Stage-specific monitoring rules |
| POST | `/api/crops/{id}/advance` | Manually advance stage |
| POST | `/api/crops/{id}/harvest` | Record harvest |
| GET | `/api/dashboard` | Crop dashboard (all crops) |
| GET | `/api/harvest/analytics` | Harvest performance metrics |

### Sensor Analytics

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/analytics/summary` | Full analytics snapshot |
| GET | `/api/analytics/vpd` | Current VPD |
| GET | `/api/analytics/dli` | DLI progress |
| GET | `/api/analytics/trends` | Trend detection |
| GET | `/api/analytics/anomalies` | Anomaly detection |
| GET | `/api/analytics/history` | Historical data with aggregation |

### Weather & Market

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/weather/current` | Current outdoor weather |
| GET | `/api/weather/forecast` | 3-day forecast |
| GET | `/api/weather/solar` | Sunrise/sunset/day length |
| GET | `/api/weather/correlation` | Indoor vs outdoor comparison |
| GET | `/api/weather/advisory` | Growing conditions advisory |
| GET | `/api/market/prices` | Market prices |
| POST | `/api/market/prices` | Update market prices |
| GET | `/api/market/demand` | Seasonal demand multipliers |

### Crop Intelligence

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/intelligence/correlations` | Condition-to-harvest correlations |
| GET | `/api/intelligence/recommendations/{id}` | Optimization recommendations |
| GET | `/api/intelligence/predict/{id}` | Yield prediction |
| GET | `/api/intelligence/health/{id}` | Crop health score |

### Data Export & Reports

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/export/sensor-csv` | CSV download (`?hours=24`) |
| GET | `/api/export/crop-report/{id}` | Crop lifecycle report |
| GET | `/api/reports/weekly` | Weekly summary |
| GET | `/api/reports/monthly` | Monthly summary |

### Calibration & Drift

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/calibrations` | Record sensor calibration |
| GET | `/api/calibrations/due` | Sensors needing calibration |
| GET | `/api/sensors/drift/status` | Drift detection status |
| GET | `/api/sensors/drift/{sensor_id}` | Drift trend for sensor |
| POST | `/api/sensors/dual` | Dual sensor reading |

### Site Visits

| Method | Endpoint | Description |
|---|---|---|
| GET | `/site-visits` | Backoffice HTML UI **[Public]** |
| GET | `/api/site-visits` | List visits (paginated) **[Public]** |
| GET | `/api/site-visits/dashboard` | Visit analytics **[Public]** |
| GET | `/api/site-visits/clients` | Client list **[Public]** |
| GET | `/api/site-visits/export` | Export all visits **[Public]** |
| GET | `/api/site-visits/{id}` | Single visit detail **[Public]** |
| POST | `/api/site-visits` | Create visit |
| PUT | `/api/site-visits/{id}` | Update visit |
| DELETE | `/api/site-visits/{id}` | Delete visit |
| POST | `/api/site-visits/{id}/complete-follow-up` | Mark follow-up done |

### ETL Pipeline

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/etl/status` | ETL status & watermarks **[Public]** |
| POST | `/api/etl/run` | Manual ETL trigger |

### Data Harvester

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/harvester/status` | All sources status |
| GET | `/api/harvester/weather` | Weather summary |
| GET | `/api/harvester/electricity` | Electricity prices |
| GET | `/api/harvester/solar` | Solar data |
| GET | `/api/harvester/market-prices` | Produce prices |
| GET | `/api/harvester/tourism` | Tourism index |
| POST | `/api/harvester/trigger` | Manual harvest |
| POST | `/api/harvester/market-prices` | Add price entry |
| POST | `/api/harvester/market-prices/import` | Import prices CSV |
| POST | `/api/harvester/tourism/import` | Import tourism CSV |

### Business

| Method | Endpoint | Description |
|---|---|---|
| GET | `/business` | Business dashboard HTML UI **[Public]** |
| GET | `/api/business/dashboard` | Business intelligence API |
