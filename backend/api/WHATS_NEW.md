# What's New: AI Improvements Phase 2

**Branch**: `ai-improvements-2`
**Date**: 2026-02-12

---

## Summary

Five priorities delivered in this session: architecture cleanup, expanded test coverage, full API documentation, smarter notification filtering, and a new business digest system.

**Test suite**: 348 passing &rarr; **482 passing** (+134 new tests)

---

## P1: Architecture — Redis Removed

The three-tier data layer (InfluxDB + PostgreSQL + Redis) has been simplified to **two tiers**. Redis was used as a cache for latest sensor readings in `query_latest()`, but InfluxDB `last()` queries on localhost are sub-second, making the cache layer unnecessary overhead.

### What Changed

| File | Change |
|---|---|
| `server.py` | Removed Redis import block, cache write in `write_to_influx()`, cache check in `query_latest()` |
| `db/pg_database.py` | Removed `RedisCache` class (96 lines), `import redis`, cache usage in `get_dashboard()` |
| `db/__init__.py` | Removed `RedisCache` from exports |
| `docker-compose.yml` | Removed `redis` service and `redis-data` volume |
| `docker-compose.pi.yml` | Removed `redis` service override and bind-mount volume |
| `README.md` | Updated architecture diagram, tech stack, service count (5 &rarr; 4) |

### Docker Services (now 4)

```
InfluxDB (:8086) | PostgreSQL (:5432) | Grafana (:3000) | Node-RED (:1880)
```

### Data Flow (simplified)

```
Arduino POST /api/data --> server.py --> InfluxDB (hot)
                                    --> PostgreSQL (lifecycle/BI)

GET /api/data/latest --> InfluxDB last() query (sub-second)
```

---

## P2: Test Coverage Expansion

Three new test files covering previously untested modules:

| Test File | Module | Tests | Coverage |
|---|---|---|---|
| `test_crop_intelligence.py` | `crop_intelligence.py` | 43 | Correlations, recommendations, yield prediction, health scoring, helpers |
| `test_data_export.py` | `data_export.py` | 45 | CSV export, crop reports, weekly/monthly summaries, recommendation helpers, weekly breakdown |
| `test_market_data_service.py` | `market_data_service.py` | 48 | Market prices, seasonal demand, update operations, planting recommendations |

### Test Patterns Used

- **Lazy imports**: Modules that use `from X import Y` inside method bodies need `sys.modules` patching:
  ```python
  with patch.dict(sys.modules, {'config_loader': mock_module}):
      result = service.export_crop_report(1)
  ```
- **Direct property injection**: For classes with lazy `self._db` or `self._config_loader`:
  ```python
  svc = DataExportService()
  svc._db = MagicMock()
  ```
- **Windows compatibility**: Use `splitlines()` instead of `split('\n')` for CSV output.

### Running the New Tests

```bash
cd backend/api

# All new tests
python -m pytest tests/test_crop_intelligence.py tests/test_data_export.py tests/test_market_data_service.py -v

# Full suite (excludes known broken integration tests)
python -m pytest tests/ -q --ignore=tests/test_business_dashboard.py --ignore=tests/test_integration.py --ignore=tests/test_integration_notifications.py
```

---

## P3: OpenAPI Spec — Full API Documentation

The `openapi.json` spec was expanded from **12 paths** to **65 paths** with **75 operations** across **18 tags**.

### Coverage by Domain

| Tag | Paths | Operations |
|---|---|---|
| Core | 4 | 5 |
| AC Control | 1 | 2 |
| Rules | 2 | 4 |
| Commands | 1 | 1 |
| Notifications | 3 | 4 |
| Escalation | 1 | 1 |
| Crops | 9 | 11 |
| Business | 2 | 3 |
| Calibrations | 2 | 2 |
| Sensor Drift | 3 | 3 |
| Sensor Analytics | 6 | 6 |
| Weather | 5 | 5 |
| Market Data | 2 | 3 |
| Crop Intelligence | 4 | 4 |
| Export & Reports | 4 | 4 |
| Site Visits | 6 | 9 |
| ETL | 2 | 2 |
| Data Harvester | 9 | 11 |

### Accessing the Docs

```
Swagger UI:  http://localhost:3001/api/docs
Raw spec:    http://localhost:3001/api/openapi.json
```

---

## P4: Sensor/Zone Filtering on Snapshot Notifications

### Problem

`query_latest()` accepted a `sensor_id` parameter but never used it in the InfluxDB query. The `/api/notifications/test-real` endpoint always queried all sensors and listed all crops.

### Fix

1. **`query_latest(sensor_id)`** now filters by `sensor_id` tag in the Flux query
2. **`POST /api/notifications/test-real`** accepts `sensor_id` and `zone` parameters (body or query string)
3. Active crop list is filtered by zone when provided

### API Usage

```bash
# Filter by sensor and zone
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"sensor_id": "arduino_2", "zone": "A1"}' \
  http://localhost:3001/api/notifications/test-real

# Or via query parameters
curl -X POST \
  "http://localhost:3001/api/notifications/test-real?sensor_id=arduino_2&zone=A1"
```

### Response Changes

```json
{
  "status": "test_sent_with_real_data",
  "sensor_id": "arduino_2",
  "zone": "A1",
  "sensor_data": { ... },
  "available_crops": [ /* filtered by zone */ ],
  "channels": [ ... ]
}
```

---

## P5: Business Digest with Private ntfy Channel

A new business digest service generates periodic business reports with configurable tone and sends them to a dedicated private ntfy topic.

### Tones

| Tone | Priority | Style |
|---|---|---|
| `aggressive` | 4 (high) | Growth targets, missed opportunities, urgency |
| `medium` | 3 (default) | Balanced metrics, progress, next steps |
| `optimist` | 2 (low) | Highlights wins, positive trends, momentum |

### Configuration

Add to `.env`:
```env
NTFY_BUSINESS_TOPIC=agritech-business    # Separate from sensor alerts
NTFY_TOKEN=your-token                     # Optional: auth for private topics
```

### API Endpoints

```bash
# Generate digest (preview, no send)
curl "http://localhost:3001/api/business/digest?tone=aggressive"

# Generate and send via ntfy
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"tone": "optimist"}' \
  http://localhost:3001/api/business/digest
```

### Sample Digest (medium tone)

```
**Business Digest** — 2026-02-12 14:30

Clients: 5 | MRR: 750.0 | Growth: 15.0%

**Revenue**
- MRR: 750.0
- Total this month: 900.0
- Projected annual: 10800.0

**Tier Breakdown**
- bronze: 3 clients, 147.0/mo
- silver: 1 clients, 199.0/mo
- gold: 1 clients, 399.0/mo

**Crops**
- Active: 12
- Harvests this month: 2 (avg 1.8 kg)
- Stages: vegetative: 4, seedling: 3, germination: 5

**Opportunities (2)**
- Total potential value: 550
- Healthy client — pitch Silver tier (+150)
- Faro Sunday Market (+400)

---
Review dashboard for full details.
```

### New Files

| File | Purpose |
|---|---|
| `business/business_digest.py` | Digest generation, formatting, ntfy sending |
| `tests/test_business_digest.py` | 25 tests: generation, tone formatting, ntfy sending, error handling |

---

## Files Modified (Summary)

| File | Lines Changed | Reason |
|---|---|---|
| `server.py` | +30 / -20 | Redis removal, sensor/zone filtering, digest endpoints, import |
| `db/pg_database.py` | -100 | RedisCache class + cache usage removed |
| `db/__init__.py` | -1 | RedisCache import removed |
| `docker-compose.yml` | -10 | Redis service + volume removed |
| `docker-compose.pi.yml` | -25 | Redis service override + volume removed |
| `README.md` | ~10 | Architecture, tech stack, service count |
| `openapi.json` | +3000 | 53 new endpoint definitions |
| `business/__init__.py` | +1 | business_digest import |

## New Files

| File | Tests |
|---|---|
| `tests/test_crop_intelligence.py` | 43 |
| `tests/test_data_export.py` | 45 |
| `tests/test_market_data_service.py` | 48 |
| `tests/test_business_digest.py` | 25 |
| `business/business_digest.py` | — |

---

## Pre-existing Test Failures (unchanged)

These 4 tests fail before and after changes — not caused by this work:

| Test | Issue |
|---|---|
| `test_sensor_analytics::test_vpd_known_value_25c_50pct` | Float rounding precision |
| `test_sensor_analytics::test_stddev` | Float precision mismatch |
| `test_client_manager::test_health_score_decrease` | Logic/assertion mismatch |
| `test_client_manager::test_health_score_clamped_to_zero` | Logic/assertion mismatch |
