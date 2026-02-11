# InfluxDB -> PostgreSQL ETL Data Processor

## What It Does

Sensor data arrives from Arduino via `POST /api/data` and gets written to InfluxDB. Two Flux tasks already downsample into `hydroponics_hourly` and `hydroponics_daily` buckets. The ETL bridges the gap by copying those aggregates into PostgreSQL BI tables for dashboards and analytics.

```
Arduino -> POST /api/data -> InfluxDB "hydroponics" -> Flux tasks -> hourly/daily buckets
                                                                          |
                                                            [ETL] <-------+
                                                              |
                                                              v
                                                  PostgreSQL bi.* tables
                                                  (hourly_sensor_agg, daily_sensor_agg)
```

---

## Architecture

### Three-Layer Data Flow

| Layer | Store | Purpose |
|-------|-------|---------|
| Hot | InfluxDB + Redis | Real-time sensor readings, sub-second queries |
| Warm | PostgreSQL `bi.*` | Hourly/daily aggregates for dashboards & BI |
| Cold | PostgreSQL `bi.daily_*` | Permanent daily records, trend analysis |

### Sensor Mapping

Each InfluxDB `(sensor_tag, _field)` pair maps to a distinct `iot.sensors` row in PostgreSQL:

| InfluxDB `_field` | PostgreSQL `iot.sensor_types.name` | Unit |
|---|---|---|
| temperature | DHT20_TEMPERATURE | C |
| humidity | DHT20_HUMIDITY | % |
| ph | PH_SENSOR | pH |
| ec | EC_SENSOR | mS/cm |
| water_level | WATER_LEVEL | % |
| water_temp | WATER_TEMP | C |
| light | LIGHT_LUX | lux |

---

## Setup

### 1. Prerequisites

Docker services must be running (InfluxDB, PostgreSQL, Redis):

```bash
docker compose up -d
```

Seed the database if not already done:

```bash
cd backend/tools
python seed_varieties.py
```

### 2. Environment Variables

Add these to your `backend/.env` (all have defaults):

```env
# ETL (InfluxDB -> PostgreSQL BI tables)
ETL_ENABLED=false                    # Set to true for background scheduler
ETL_HOURLY_INTERVAL_MINUTES=65       # How often to run hourly ETL
ETL_DAILY_HOUR=1                     # Hour (0-23) to run daily ETL
ETL_HOURLY_RETENTION_DAYS=90         # Delete hourly data older than this
ETL_CONDITION_CALC_ENABLED=true      # Compute optimal/critical % for daily
```

### 3. Schema Update

If your PostgreSQL database was created before this feature, run this SQL to add the unique index needed for idempotent daily upserts:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_daily_sensor_metric
    ON bi.daily_sensor_agg (sensor_id, metric_date);
```

If you're starting fresh, `init.sql` already includes this index.

---

## Usage

### CLI Tool (`backend/tools/run_etl.py`)

The CLI is the primary way to run ETL manually or via cron.

```bash
cd backend/tools

# Process latest hourly aggregates (default: last 3 hours)
python run_etl.py hourly

# Process latest daily aggregates (default: last 2 days)
python run_etl.py daily

# Full cycle: hourly + daily + cleanup old data
python run_etl.py full

# Backfill 30 days of historical data
python run_etl.py backfill --days 30

# Purge hourly data older than 90 days
python run_etl.py cleanup

# Check ETL status, watermarks, row counts
python run_etl.py status
```

#### Dry Run Mode

All write commands support `--dry-run` to preview without writing:

```bash
python run_etl.py hourly --dry-run
python run_etl.py backfill --days 7 --dry-run
```

#### Custom Lookback

```bash
python run_etl.py hourly --hours 12     # Look back 12 hours
python run_etl.py daily --days 7        # Look back 7 days
python run_etl.py cleanup --retention-days 60  # Custom retention
```

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/etl/status` | Public | ETL status, watermarks, row counts, connection health |
| POST | `/api/etl/run` | API key | Trigger ETL manually |

#### GET /api/etl/status

```bash
curl http://localhost:3001/api/etl/status
```

Response:
```json
{
  "initialized": true,
  "scheduler_running": false,
  "influx_connected": true,
  "pg_connected": true,
  "sensor_mappings": 7,
  "watermarks": {
    "etl_hourly_watermark": {"timestamp": "2026-02-11T14:00:00+00:00"},
    "etl_daily_watermark": {"timestamp": "2026-02-11T00:00:00+00:00"}
  },
  "row_counts": {
    "hourly_rows": 168,
    "daily_rows": 14
  }
}
```

#### POST /api/etl/run

```bash
# Full cycle (default)
curl -X POST http://localhost:3001/api/etl/run \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"command": "full"}'

# Just hourly
curl -X POST http://localhost:3001/api/etl/run \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"command": "hourly"}'

# Backfill with dry run
curl -X POST http://localhost:3001/api/etl/run \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"command": "backfill", "days": 14, "dry_run": true}'
```

Available commands: `hourly`, `daily`, `full`, `cleanup`, `backfill`.

### Background Scheduler

Set `ETL_ENABLED=true` in `.env` and restart the server. The ETL will run automatically:

- **Hourly cycle** every 65 minutes (configurable via `ETL_HOURLY_INTERVAL_MINUTES`)
- **Daily cycle** at 01:30 (configurable via `ETL_DAILY_HOUR`)
- **Cleanup** runs after daily cycle

The scheduler appears in the server startup banner:

```
ETL (InfluxDB -> PostgreSQL):
  GET    /api/etl/status           - ETL status & watermarks
  POST   /api/etl/run              - Manual ETL trigger (API key required)
  -> Background scheduler RUNNING
```

### Cron Alternative

For production, you can use cron instead of the background scheduler:

```cron
# Hourly ETL every hour at minute 5
5 * * * * cd /path/to/backend/tools && python run_etl.py hourly >> /var/log/etl.log 2>&1

# Daily ETL at 01:30
30 1 * * * cd /path/to/backend/tools && python run_etl.py daily >> /var/log/etl.log 2>&1

# Cleanup weekly on Sunday at 03:00
0 3 * * 0 cd /path/to/backend/tools && python run_etl.py cleanup >> /var/log/etl.log 2>&1
```

---

## How It Works

### Hourly ETL

1. Query `hydroponics_hourly` InfluxDB bucket for avg/min/max/count per (sensor, field, hour)
2. If the hourly bucket doesn't exist, falls back to aggregating from the raw `hydroponics` bucket
3. Map each `(sensor_tag, field)` to a PostgreSQL `iot.sensors.id`
4. Upsert into `bi.hourly_sensor_agg` using `ON CONFLICT (sensor_id, hour_start) DO UPDATE`
5. Update watermark in `core.system_config`

### Daily ETL

1. Query `hydroponics_daily` InfluxDB bucket (fallback: raw bucket with daily aggregation)
2. For condition fields (temperature, humidity, ph, ec):
   - Query raw InfluxDB data for the day
   - Compare each reading against `crop.growth_stage_definitions` optimal ranges
   - Compute `time_in_optimal_pct` and `time_in_critical_pct`
3. Upsert into `bi.daily_sensor_agg` using `ON CONFLICT (sensor_id, metric_date) DO UPDATE`
4. Update watermark

### Condition Percentage Calculation

For temperature, humidity, pH, and EC, the ETL computes how much time sensors spent in optimal vs critical ranges:

- **Optimal %** = readings within the growth stage's defined optimal range
- **Critical %** = readings more than 20% beyond the optimal range boundaries
- Ranges come from `crop.growth_stage_definitions` for all active crop batches
- The widest range across active batches is used (most permissive)

### Sensor Auto-Registration

On first run with an empty `iot.sensors` table, the ETL automatically:

1. Creates a device in `iot.devices` for each unique `sensor_tag` (e.g., `arduino_1`)
2. Creates sensor entries in `iot.sensors` for each `(device, field)` pair
3. Links them to the correct `iot.sensor_types` entry

This means the ETL works out of the box without manual sensor setup.

### Watermarks

The ETL tracks progress using watermarks stored in `core.system_config`:

| Key | Purpose |
|-----|---------|
| `etl_hourly_watermark` | Last processed hourly timestamp |
| `etl_daily_watermark` | Last processed daily timestamp |

Watermarks prevent reprocessing the same data. On each run, the ETL starts from the watermark (with a small overlap for safety) rather than scanning everything.

### Idempotency

Both hourly and daily inserts use `ON CONFLICT ... DO UPDATE`, so it's safe to:

- Re-run the same time period multiple times
- Overlap lookback windows
- Run backfill over already-processed data
- Have the scheduler and CLI running at the same time

No duplicates will be created.

---

## Verification

### Quick Smoke Test

```bash
# 1. Make sure Docker services are running
docker compose up -d

# 2. Send some sensor data
curl -X POST http://localhost:3001/api/data \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"temperature": 22.5, "humidity": 55, "ph": 6.1, "ec": 1.4, "water_level": 80, "water_temp": 20.1, "light": 12000}'

# 3. Wait a moment, then run hourly ETL
cd backend/tools
python run_etl.py hourly

# 4. Check status
python run_etl.py status

# 5. Verify no duplicates by running again
python run_etl.py hourly

# 6. Check the API status endpoint
curl http://localhost:3001/api/etl/status
```

### Verify PostgreSQL Data

```sql
-- Check hourly aggregates
SELECT * FROM bi.hourly_sensor_agg ORDER BY hour_start DESC LIMIT 10;

-- Check daily aggregates
SELECT * FROM bi.daily_sensor_agg ORDER BY metric_date DESC LIMIT 10;

-- Check watermarks
SELECT * FROM core.system_config WHERE key LIKE 'etl_%';

-- Check auto-registered sensors
SELECT s.id, s.sensor_code, st.name, d.device_code
FROM iot.sensors s
JOIN iot.sensor_types st ON s.sensor_type_id = st.id
JOIN iot.devices d ON s.device_id = d.id;
```

---

## Files

| File | Purpose |
|------|---------|
| `backend/api/influx_pg_etl.py` | ETL processor class (core logic) |
| `backend/tools/run_etl.py` | CLI entry point for manual/cron execution |
| `backend/api/pg_database.py` | PostgreSQL abstraction (modified: daily upsert) |
| `backend/sql/init.sql` | Schema (modified: unique index on daily_sensor_agg) |
| `backend/api/server.py` | HTTP server (modified: ETL endpoints + scheduler) |
| `backend/.env.example` | Environment variables template |

---

## Troubleshooting

### ETL shows "not initialized"

Check that PostgreSQL and InfluxDB are reachable:

```bash
# Test PostgreSQL
psql -h localhost -U agritech -d agritech -c "SELECT 1"

# Test InfluxDB
curl http://localhost:8086/health
```

### "InfluxDB query failed" with fallback to raw bucket

This is normal if the `hydroponics_hourly` / `hydroponics_daily` Flux task buckets haven't been created yet. The ETL falls back to aggregating from the raw `hydroponics` bucket automatically.

### Zero rows processed

- Verify sensor data exists in InfluxDB: check Grafana or query InfluxDB directly
- Check the lookback window: use `--hours 24` or `--days 7` for a wider range
- Run with `--dry-run` to see what would be processed

### Duplicate key violation on daily_sensor_agg

Run the unique index migration:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_daily_sensor_metric
    ON bi.daily_sensor_agg (sensor_id, metric_date);
```

### Condition percentages are NULL

- Check `ETL_CONDITION_CALC_ENABLED=true` in `.env`
- Ensure active crop batches exist (run `seed_varieties.py` + create a crop via API)
- Condition % only applies to: temperature, humidity, ph, ec
