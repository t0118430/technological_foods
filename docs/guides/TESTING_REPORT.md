# Testing Report — What to Test and How

**Date**: 2026-02-12
**Branch**: `ai-improvements-2`
**Current state**: 482 passing, 4 pre-existing failures

This report covers every testable feature in the system, organized by testing method: automated unit tests (pytest), manual API tests (curl), and live integration tests.

---

## 1. Automated Unit Tests (pytest)

These run without any infrastructure — no InfluxDB, no PostgreSQL, no ntfy. All dependencies are mocked.

### How to Run

```bash
cd backend/api

# Full suite (recommended)
python -m pytest tests/ -v --ignore=tests/test_integration.py --ignore=tests/test_integration_notifications.py --ignore=tests/test_business_dashboard.py

# Quick summary
python -m pytest tests/ -q --ignore=tests/test_integration.py --ignore=tests/test_integration_notifications.py --ignore=tests/test_business_dashboard.py

# Single module
python -m pytest tests/test_crop_intelligence.py -v

# With coverage
python -m pytest tests/ --cov=. --cov-report=html --ignore=tests/test_integration.py --ignore=tests/test_integration_notifications.py --ignore=tests/test_business_dashboard.py
```

### Test Files and What They Cover

| Test File | Module | Tests | What It Verifies |
|---|---|---|---|
| `test_rule_engine.py` | `rules/rule_engine.py` | Rule CRUD, evaluation, threshold triggers, preventive margins, Arduino commands |
| `test_notification_service.py` | `notifications/notification_service.py` | Channel dispatch, cooldown, severity formatting, history |
| `test_alert_escalation.py` | `notifications/alert_escalation.py` | Escalation levels, timing, priority mapping |
| `test_multi_channel_notifier.py` | `notifications/multi_channel_notifier.py` | Alert level routing, channel selection |
| `test_config_loader.py` | `crops/config_loader.py` | Variety config loading, growth stage definitions |
| `test_growth_stages.py` | `crops/growth_stage_manager.py` | Stage advancement, conditions, auto-advance logic |
| `test_sensor_analytics.py` | `sensor_analytics.py` | VPD calculation, DLI, trend detection, anomaly detection, helpers |
| `test_crop_intelligence.py` | `crop_intelligence.py` | Harvest correlations, optimization recommendations, yield prediction, health scoring |
| `test_data_export.py` | `data_export.py` | CSV export, crop lifecycle reports, weekly/monthly summaries, recommendation helpers |
| `test_market_data_service.py` | `market_data_service.py` | Market prices, seasonal demand, price updates, planting recommendations |
| `test_business_digest.py` | `business/business_digest.py` | Digest generation, 3 tones, ntfy sending, error handling |
| `test_client_manager.py` | `business/client_manager.py` | Client CRUD, health scoring, tier management |
| `test_data_harvester.py` | `harvester/` | Weather, electricity, solar, market price, tourism data sources |
| `test_drift_detection.py` | `sensors/drift_detection_service.py` | Drift analysis, dual sensor comparison, alert thresholds |
| `test_preventive_alerts.py` | `rules/` + `notifications/` | Warning margin evaluation, preventive vs critical classification |

### Expected Output

```
482 passed, 4 failed

# The 4 failures are pre-existing:
FAILED test_sensor_analytics::TestVPD::test_vpd_known_value_25c_50pct   (float rounding)
FAILED test_sensor_analytics::TestHelpers::test_stddev                  (float precision)
FAILED test_client_manager::TestHealthScore::test_health_score_decrease  (logic mismatch)
FAILED test_client_manager::TestHealthScore::test_health_score_clamped   (logic mismatch)
```

---

## 2. API Endpoint Tests (curl)

These require the server running: `python server.py` (port 3001).
Some also require Docker services (InfluxDB, PostgreSQL).

### 2.1 Core Health & Data

```bash
# Health check (no auth required)
curl http://localhost:3001/api/health

# Post sensor data
curl -X POST -H "Content-Type: application/json" \
  -d '{"temperature":24.5,"humidity":62,"ph":6.1,"ec":1.5,"water_level":75,"light":3000,"sensor_id":"arduino_1"}' \
  http://localhost:3001/api/data

# Get latest readings (now filtered by sensor_id)
curl "http://localhost:3001/api/data/latest?sensor_id=arduino_1"
```

**Verify**: 200 OK, data written to InfluxDB, latest returns last reading.

### 2.2 Sensor Analytics

```bash
# Summary (VPD, DLI, nutrient score)
curl "http://localhost:3001/api/analytics/summary?sensor_id=arduino_1"

# VPD calculation
curl "http://localhost:3001/api/analytics/vpd?sensor_id=arduino_1"

# DLI calculation
curl "http://localhost:3001/api/analytics/dli?sensor_id=arduino_1"

# Trend detection
curl "http://localhost:3001/api/analytics/trends?sensor_id=arduino_1"

# Anomaly detection
curl "http://localhost:3001/api/analytics/anomalies?sensor_id=arduino_1"

# Sensor history with time range
curl "http://localhost:3001/api/analytics/history?sensor_id=arduino_1&field=temperature&start=-24h"
```

**Verify**: Each returns computed metrics from InfluxDB data. Empty data returns graceful defaults.

### 2.3 Crop Lifecycle

```bash
# List active crops
curl http://localhost:3001/api/crops

# Create a crop batch
curl -X POST -H "Content-Type: application/json" \
  -d '{"variety":"rosso_premium","zone":"main"}' \
  http://localhost:3001/api/crops

# Get crop details
curl http://localhost:3001/api/crops/1

# Get current conditions for a crop
curl http://localhost:3001/api/crops/1/conditions

# Advance growth stage
curl -X POST http://localhost:3001/api/crops/1/advance

# Record harvest
curl -X POST -H "Content-Type: application/json" \
  -d '{"weight_kg":2.5,"quality":"A","notes":"Good batch"}' \
  http://localhost:3001/api/crops/1/harvest

# Dashboard summary
curl http://localhost:3001/api/dashboard
```

**Verify**: Crop created in DB, stages advance correctly, harvest recorded, dashboard aggregates all crops.

### 2.4 Crop Intelligence

```bash
# Condition-harvest correlations
curl http://localhost:3001/api/intelligence/correlations

# Growth optimization recommendations
curl http://localhost:3001/api/intelligence/recommendations/1

# Yield prediction
curl http://localhost:3001/api/intelligence/predict/1

# Crop health score
curl http://localhost:3001/api/intelligence/health/1
```

**Verify**: Returns analysis based on stored crop/snapshot data. Handles "no data" gracefully with `insufficient_data` status.

### 2.5 Notification System

```bash
# Notification status (channels, cooldowns, history)
curl http://localhost:3001/api/notifications

# Test alert with dummy data
curl -X POST http://localhost:3001/api/notifications/test

# Test alert with real sensor data + sensor/zone filtering
curl -X POST -H "Content-Type: application/json" \
  -d '{"sensor_id":"arduino_1","zone":"main","crop_id":1}' \
  http://localhost:3001/api/notifications/test-real

# Escalation status
curl http://localhost:3001/api/escalation
```

**Verify**:
- `test` sends to all configured channels (check ntfy app)
- `test-real` uses live InfluxDB data, filtered by sensor_id
- When `zone` is provided, `available_crops` list is filtered
- Response includes `sensor_id` and `zone` fields

### 2.6 Rule Engine

```bash
# List all rules
curl http://localhost:3001/api/rules

# Create a rule
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "id":"test_temp_high","sensor":"temperature","condition":"above",
    "threshold":30,"warning_margin":2,
    "action":{"type":"notify","severity":"critical","message":"Temp too high!"},
    "preventive_message":"Approaching temp limit"
  }' \
  http://localhost:3001/api/rules

# Update a rule
curl -X PUT -H "Content-Type: application/json" \
  -d '{"threshold":28}' \
  http://localhost:3001/api/rules/test_temp_high

# Delete a rule
curl -X DELETE http://localhost:3001/api/rules/test_temp_high
```

**Verify**: CRUD operations work. Post sensor data above threshold and verify notification fires.

### 2.7 Weather Service

```bash
curl http://localhost:3001/api/weather/current
curl http://localhost:3001/api/weather/forecast
curl http://localhost:3001/api/weather/solar
curl http://localhost:3001/api/weather/correlation
curl http://localhost:3001/api/weather/advisory
```

**Verify**: Returns weather data from Open-Meteo. Advisory combines weather + crop recommendations.

### 2.8 Market Data

```bash
# Get prices with seasonal adjustments
curl http://localhost:3001/api/market/prices

# Get seasonal demand curve (12 months)
curl http://localhost:3001/api/market/demand

# Update prices
curl -X POST -H "Content-Type: application/json" \
  -d '{"products":{"rosso_premium":{"price":12.0}}}' \
  http://localhost:3001/api/market/prices
```

**Verify**: Prices include seasonal multiplier based on current month. Demand shows peak Jul/Aug (3.0x).

### 2.9 Data Export & Reports

```bash
# CSV download (sensor data)
curl -o sensor_data.csv \
  "http://localhost:3001/api/export/sensor-csv?sensor_id=arduino_1&start=-7d"

# Crop lifecycle report
curl http://localhost:3001/api/export/crop-report/1

# Weekly summary
curl "http://localhost:3001/api/reports/weekly?sensor_id=arduino_1"

# Monthly summary
curl "http://localhost:3001/api/reports/monthly?sensor_id=arduino_1"
```

**Verify**: CSV has header + data rows. Weekly includes recommendations, weather context. Monthly includes harvest stats, market context.

### 2.10 Business Dashboard & Digest

```bash
# Full business dashboard (all KPIs)
curl http://localhost:3001/api/business/dashboard

# Business digest — preview (GET)
curl "http://localhost:3001/api/business/digest?tone=aggressive"
curl "http://localhost:3001/api/business/digest?tone=medium"
curl "http://localhost:3001/api/business/digest?tone=optimist"

# Business digest — generate and send via ntfy (POST)
curl -X POST -H "Content-Type: application/json" \
  -d '{"tone":"medium"}' \
  http://localhost:3001/api/business/digest
```

**Verify**:
- Dashboard returns: `business_overview`, `revenue_metrics`, `crop_status`, `sensor_health`, `client_health`, `local_market_data`, `weather_correlation`, `opportunities`, `alerts_summary`
- GET digest returns `formatted_message` without sending
- POST digest returns `ntfy_sent: true` if `NTFY_BUSINESS_TOPIC` is configured
- Different tones produce different message framing:
  - `aggressive`: "below target", "action needed", "execute today"
  - `medium`: balanced KPI summary
  - `optimist`: "growing!", "keep it up!"

### 2.11 Site Visits

```bash
# List visits
curl http://localhost:3001/api/site-visits

# Create visit
curl -X POST -H "Content-Type: application/json" \
  -d '{"client_id":1,"visit_type":"maintenance","scheduled_date":"2026-02-15"}' \
  http://localhost:3001/api/site-visits

# Visit dashboard
curl http://localhost:3001/api/site-visits/dashboard

# Client visit history
curl http://localhost:3001/api/site-visits/clients

# Export
curl http://localhost:3001/api/site-visits/export
```

### 2.12 Calibration

```bash
# Record calibration
curl -X POST -H "Content-Type: application/json" \
  -d '{"sensor_type":"ph","calibration_date":"2026-02-12","next_due":"2026-03-12","notes":"2-point buffer"}' \
  http://localhost:3001/api/calibrations

# Check due calibrations
curl http://localhost:3001/api/calibrations/due
```

### 2.13 ETL Pipeline

```bash
# Pipeline status
curl http://localhost:3001/api/etl/status

# Trigger manual run
curl -X POST http://localhost:3001/api/etl/run
```

**Verify**: Status shows last run time and success/failure. Manual trigger processes InfluxDB -> PostgreSQL aggregation.

### 2.14 Data Harvester

```bash
# Harvester status
curl http://localhost:3001/api/harvester/status

# Individual sources
curl http://localhost:3001/api/harvester/weather
curl http://localhost:3001/api/harvester/electricity
curl http://localhost:3001/api/harvester/solar
curl http://localhost:3001/api/harvester/market-prices
curl http://localhost:3001/api/harvester/tourism

# Manual trigger
curl -X POST http://localhost:3001/api/harvester/trigger
```

### 2.15 Drift Detection

```bash
# Overall drift status
curl http://localhost:3001/api/sensors/drift/status

# Specific sensor drift trend
curl http://localhost:3001/api/sensors/drift/arduino_1

# Submit dual sensor reading
curl -X POST -H "Content-Type: application/json" \
  -d '{"primary":{"temperature":24.5,"humidity":62},"secondary":{"temperature":24.3,"humidity":61.5},"sensor_id":"arduino_1"}' \
  http://localhost:3001/api/sensors/dual
```

### 2.16 OpenAPI Spec

```bash
# Raw spec (machine-readable)
curl http://localhost:3001/api/openapi.json | python -m json.tool | head -20

# Swagger UI (browser)
# Open: http://localhost:3001/api/docs
```

**Verify**: Spec loads in Swagger UI, all 65 paths listed, try-it-out works for public endpoints.

---

## 3. Live Integration Tests

These test real-world flows with actual infrastructure running.

### 3.1 Sensor Data Pipeline (Arduino -> InfluxDB -> Grafana)

**Prerequisites**: Docker services running (`docker-compose up -d`)

```bash
# 1. Post simulated sensor reading
curl -X POST -H "Content-Type: application/json" \
  -d '{"temperature":25.0,"humidity":63,"ph":6.0,"ec":1.5,"water_level":80,"light":3500,"sensor_id":"arduino_1"}' \
  http://localhost:3001/api/data

# 2. Verify in InfluxDB
curl "http://localhost:3001/api/data/latest?sensor_id=arduino_1"

# 3. Check Grafana dashboard
# Open: http://localhost:3000/d/hydroponics-overview
```

**Verify**: Data appears in InfluxDB within 1 second. Grafana panels refresh with new data point.

### 3.2 Alert Pipeline (Data -> Rule -> Notification)

```bash
# 1. Create a temperature rule
curl -X POST -H "Content-Type: application/json" \
  -d '{"id":"integration_test","sensor":"temperature","condition":"above","threshold":28,"action":{"type":"notify","severity":"warning","message":"Integration test alert"}}' \
  http://localhost:3001/api/rules

# 2. Post data above threshold
curl -X POST -H "Content-Type: application/json" \
  -d '{"temperature":30.5,"humidity":60,"sensor_id":"arduino_1"}' \
  http://localhost:3001/api/data

# 3. Check notification was sent
curl http://localhost:3001/api/notifications
# -> recent_alerts should include the triggered rule

# 4. Check phone for ntfy notification

# 5. Cleanup
curl -X DELETE http://localhost:3001/api/rules/integration_test
```

### 3.3 Crop Lifecycle (Create -> Grow -> Harvest)

```bash
# 1. Create crop
curl -X POST -H "Content-Type: application/json" \
  -d '{"variety":"basil_genovese","zone":"main"}' \
  http://localhost:3001/api/crops

# 2. Check current stage (should be germination)
curl http://localhost:3001/api/crops/1

# 3. Advance to seedling
curl -X POST http://localhost:3001/api/crops/1/advance

# 4. Check health score
curl http://localhost:3001/api/intelligence/health/1

# 5. Record harvest
curl -X POST -H "Content-Type: application/json" \
  -d '{"weight_kg":1.2,"quality":"A"}' \
  http://localhost:3001/api/crops/1/harvest

# 6. Check report
curl http://localhost:3001/api/export/crop-report/1
```

### 3.4 Business Digest via ntfy

**Prerequisites**: `NTFY_BUSINESS_TOPIC` set in `.env`

```bash
# 1. Send aggressive digest
curl -X POST -H "Content-Type: application/json" \
  -d '{"tone":"aggressive"}' \
  http://localhost:3001/api/business/digest

# 2. Send optimist digest
curl -X POST -H "Content-Type: application/json" \
  -d '{"tone":"optimist"}' \
  http://localhost:3001/api/business/digest

# 3. Check ntfy app for 2 notifications on the business topic
```

**Verify**: Two separate notifications received on the business ntfy topic. Aggressive has priority 4 (high), optimist has priority 2 (low). Content framing matches tone.

### 3.5 Weekly/Monthly Report Generation

```bash
# Requires sensor data in InfluxDB for the past 7/30 days

# Weekly report
curl "http://localhost:3001/api/reports/weekly?sensor_id=arduino_1"

# Monthly report
curl "http://localhost:3001/api/reports/monthly?sensor_id=arduino_1"
```

**Verify**:
- Weekly: `daily_averages` array, `current_snapshot` with VPD/DLI, `trends`, `weather_context`, `recommendations`
- Monthly: `weekly_breakdown` array, `harvest_summary` with yield stats, `market_context`

---

## 4. What Is NOT Testable (and Why)

| Feature | Why |
|---|---|
| Redis removal | It's a deletion — nothing to test, just verify Docker has 4 services |
| OpenAPI spec content | Validated as JSON, verified 65 paths. Swagger UI confirms rendering |
| AC control (Haier hOn) | Requires physical AC unit + Haier cloud credentials |
| WhatsApp/SMS channels | Stubs only — require Twilio account |
| Email channel | Stub only — requires SMTP server |
| Arduino hardware | Physical device, sensors, WiFi connection |
| Multi-location VPN | Requires WireGuard network between sites |
| Grafana provisioning | Visual — manually verify dashboards load at `:3000` |

---

## 5. Quick Validation Checklist

After deploying this branch, run these commands to confirm everything works:

```bash
cd backend/api

# 1. Unit tests (no infrastructure needed)
python -m pytest tests/ -q \
  --ignore=tests/test_integration.py \
  --ignore=tests/test_integration_notifications.py \
  --ignore=tests/test_business_dashboard.py
# Expected: 482 passed, 4 failed

# 2. Start server (needs Docker services)
docker-compose up -d
python server.py &

# 3. Health check
curl http://localhost:3001/api/health
# Expected: {"status":"healthy",...}

# 4. Post test data
curl -X POST -H "Content-Type: application/json" \
  -d '{"temperature":24,"humidity":62,"ph":6.0,"ec":1.5,"water_level":80,"light":3000,"sensor_id":"arduino_1"}' \
  http://localhost:3001/api/data

# 5. Verify sensor_id filtering works
curl "http://localhost:3001/api/data/latest?sensor_id=arduino_1"

# 6. Test notification with zone filter
curl -X POST -H "Content-Type: application/json" \
  -d '{"sensor_id":"arduino_1","zone":"main"}' \
  http://localhost:3001/api/notifications/test-real

# 7. Business digest preview
curl "http://localhost:3001/api/business/digest?tone=medium"

# 8. OpenAPI spec loads
curl -s http://localhost:3001/api/openapi.json | python -c "import sys,json; d=json.load(sys.stdin); print(f'Paths: {len(d[\"paths\"])}')"
# Expected: Paths: 65

# 9. Swagger UI
echo "Open http://localhost:3001/api/docs in browser"
```

If all 9 steps pass, the deployment is healthy.
