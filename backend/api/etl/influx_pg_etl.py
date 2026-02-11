"""
InfluxDB → PostgreSQL ETL Data Processor.

Bridges the gap between InfluxDB downsampled buckets (hydroponics_hourly,
hydroponics_daily) and PostgreSQL BI tables (bi.hourly_sensor_agg,
bi.daily_sensor_agg).

Data flow:
  Arduino → POST /api/data → InfluxDB "hydroponics" → Flux tasks → hourly/daily buckets
                                                                         │
                                                           [THIS ETL] ◄──┘
                                                                │
                                                                ▼
                                                    PostgreSQL bi.* tables

Author: AgriTech Hydroponics
License: MIT
"""

import os
import json
import logging
import threading
from datetime import datetime, date, timedelta, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger('influx-pg-etl')

# InfluxDB config
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', '')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', '')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'hydroponics')

# ETL config
ETL_HOURLY_INTERVAL = int(os.getenv('ETL_HOURLY_INTERVAL_MINUTES', '65'))
ETL_DAILY_HOUR = int(os.getenv('ETL_DAILY_HOUR', '1'))
ETL_HOURLY_RETENTION_DAYS = int(os.getenv('ETL_HOURLY_RETENTION_DAYS', '90'))
ETL_CONDITION_CALC_ENABLED = os.getenv('ETL_CONDITION_CALC_ENABLED', 'true').lower() == 'true'

try:
    from influxdb_client import InfluxDBClient
    HAS_INFLUX = True
except ImportError:
    HAS_INFLUX = False
    logger.warning("influxdb_client not installed. ETL unavailable.")

try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    logger.warning("psycopg2 not installed. ETL unavailable.")


@dataclass
class SensorMapping:
    """Maps an InfluxDB (sensor_tag, field) pair to a PostgreSQL sensor row."""
    influx_sensor_tag: str    # e.g. "arduino_1"
    influx_field: str         # e.g. "temperature"
    pg_sensor_id: int         # iot.sensors.id
    pg_zone_id: Optional[int] # core.zones.id
    sensor_type_name: str     # e.g. "DHT20_TEMPERATURE"


class InfluxPgEtlProcessor:
    """
    ETL processor that reads downsampled data from InfluxDB hourly/daily buckets
    and writes it into PostgreSQL BI tables.
    """

    # InfluxDB _field → PostgreSQL iot.sensor_types.name
    FIELD_TO_SENSOR_TYPE = {
        'temperature': 'DHT20_TEMPERATURE',
        'humidity': 'DHT20_HUMIDITY',
        'ph': 'PH_SENSOR',
        'ec': 'EC_SENSOR',
        'water_level': 'WATER_LEVEL',
        'water_temp': 'WATER_TEMP',
        'light': 'LIGHT_LUX',
    }

    # Fields for which we compute optimal/critical condition percentages
    CONDITION_FIELDS = {'temperature', 'humidity', 'ph', 'ec'}

    def __init__(self):
        self.influx_client = None
        self.query_api = None
        self.pg_pool = None
        self._sensor_mappings: Dict[Tuple[str, str], SensorMapping] = {}
        self._scheduler_running = False
        self._scheduler_timer: Optional[threading.Timer] = None
        self._initialized = False
        self._init()

    def _init(self):
        """Initialize connections to InfluxDB and PostgreSQL."""
        if not HAS_INFLUX or not HAS_PSYCOPG2:
            logger.warning("ETL dependencies missing, processor unavailable")
            return

        try:
            self.influx_client = InfluxDBClient(
                url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG
            )
            self.query_api = self.influx_client.query_api()
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            return

        try:
            self.pg_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=5,
                host=os.getenv('PG_HOST', 'localhost'),
                port=int(os.getenv('PG_PORT', '5432')),
                dbname=os.getenv('PG_DATABASE', 'agritech'),
                user=os.getenv('PG_USER', 'agritech'),
                password=os.getenv('PG_PASSWORD', 'CHANGE_ME'),
            )
            self._initialized = True
            logger.info("ETL processor initialized (InfluxDB + PostgreSQL)")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")

    # ── PostgreSQL helpers ──────────────────────────────────

    def _pg_fetchone(self, conn, query, params=None):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def _pg_fetchall(self, conn, query, params=None):
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]

    def _pg_execute(self, conn, query, params=None):
        with conn.cursor() as cur:
            cur.execute(query, params)

    # ── Sensor Mapping ──────────────────────────────────────

    def _load_sensor_mappings(self):
        """Query PostgreSQL to build the (sensor_tag, field) → sensor_id lookup."""
        if not self._initialized:
            return

        conn = self.pg_pool.getconn()
        try:
            rows = self._pg_fetchall(conn, """
                SELECT
                    s.id AS sensor_id,
                    d.device_code AS sensor_tag,
                    st.name AS sensor_type_name,
                    s.sensor_code,
                    d.facility_id
                FROM iot.sensors s
                JOIN iot.devices d ON s.device_id = d.id
                JOIN iot.sensor_types st ON s.sensor_type_id = st.id
                WHERE s.status = 'active'
            """)

            # Build reverse lookup: sensor_type_name → influx field
            type_to_field = {v: k for k, v in self.FIELD_TO_SENSOR_TYPE.items()}

            self._sensor_mappings = {}
            for row in rows:
                influx_field = type_to_field.get(row['sensor_type_name'])
                if influx_field:
                    # Try to find zone for this device's facility
                    zone_row = self._pg_fetchone(conn, """
                        SELECT id FROM core.zones
                        WHERE facility_id = %s LIMIT 1
                    """, (row['facility_id'],))
                    zone_id = zone_row['id'] if zone_row else None

                    key = (row['sensor_tag'], influx_field)
                    self._sensor_mappings[key] = SensorMapping(
                        influx_sensor_tag=row['sensor_tag'],
                        influx_field=influx_field,
                        pg_sensor_id=row['sensor_id'],
                        pg_zone_id=zone_id,
                        sensor_type_name=row['sensor_type_name'],
                    )

            logger.info(f"Loaded {len(self._sensor_mappings)} sensor mappings")
        finally:
            self.pg_pool.putconn(conn)

    def _ensure_sensor_exists(self, sensor_tag: str, influx_field: str) -> Optional[SensorMapping]:
        """
        Auto-register a device + sensor in PostgreSQL if not found.
        Bootstrap case: first ETL run with empty iot.sensors table.
        """
        key = (sensor_tag, influx_field)
        if key in self._sensor_mappings:
            return self._sensor_mappings[key]

        sensor_type_name = self.FIELD_TO_SENSOR_TYPE.get(influx_field)
        if not sensor_type_name:
            return None

        conn = self.pg_pool.getconn()
        conn.autocommit = False
        try:
            # Get sensor type id
            st_row = self._pg_fetchone(conn,
                "SELECT id FROM iot.sensor_types WHERE name = %s", (sensor_type_name,))
            if not st_row:
                conn.rollback()
                return None

            # Find or create device
            dev_row = self._pg_fetchone(conn,
                "SELECT id, facility_id FROM iot.devices WHERE device_code = %s", (sensor_tag,))
            if not dev_row:
                # Get default facility
                fac_row = self._pg_fetchone(conn,
                    "SELECT id FROM core.facilities ORDER BY id LIMIT 1")
                if not fac_row:
                    conn.rollback()
                    return None

                self._pg_execute(conn, """
                    INSERT INTO iot.devices (facility_id, device_code, device_type, status)
                    VALUES (%s, %s, 'arduino_mkr_nb_1500', 'online')
                """, (fac_row['id'], sensor_tag))
                dev_row = self._pg_fetchone(conn,
                    "SELECT id, facility_id FROM iot.devices WHERE device_code = %s", (sensor_tag,))

            # Find or create sensor
            sensor_code = f"{sensor_tag}_{influx_field}"
            s_row = self._pg_fetchone(conn,
                "SELECT id FROM iot.sensors WHERE device_id = %s AND sensor_code = %s",
                (dev_row['id'], sensor_code))
            if not s_row:
                self._pg_execute(conn, """
                    INSERT INTO iot.sensors (device_id, sensor_type_id, sensor_code, status)
                    VALUES (%s, %s, %s, 'active')
                """, (dev_row['id'], st_row['id'], sensor_code))
                s_row = self._pg_fetchone(conn,
                    "SELECT id FROM iot.sensors WHERE device_id = %s AND sensor_code = %s",
                    (dev_row['id'], sensor_code))

            conn.commit()

            # Get zone
            zone_row = self._pg_fetchone(conn, """
                SELECT id FROM core.zones
                WHERE facility_id = %s LIMIT 1
            """, (dev_row['facility_id'],))
            zone_id = zone_row['id'] if zone_row else None

            mapping = SensorMapping(
                influx_sensor_tag=sensor_tag,
                influx_field=influx_field,
                pg_sensor_id=s_row['id'],
                pg_zone_id=zone_id,
                sensor_type_name=sensor_type_name,
            )
            self._sensor_mappings[key] = mapping
            logger.info(f"Auto-registered sensor: {sensor_tag}/{influx_field} → pg sensor_id={s_row['id']}")
            return mapping

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to auto-register sensor {sensor_tag}/{influx_field}: {e}")
            return None
        finally:
            self.pg_pool.putconn(conn)

    # ── Watermarks ──────────────────────────────────────────

    def _get_watermark(self, key: str) -> Optional[datetime]:
        """Read last-processed timestamp from core.system_config."""
        conn = self.pg_pool.getconn()
        try:
            row = self._pg_fetchone(conn,
                "SELECT value FROM core.system_config WHERE key = %s", (key,))
            if row and row['value']:
                ts = row['value'].get('timestamp')
                if ts:
                    return datetime.fromisoformat(ts)
            return None
        finally:
            self.pg_pool.putconn(conn)

    def _set_watermark(self, key: str, ts: datetime):
        """Write last-processed timestamp to core.system_config."""
        conn = self.pg_pool.getconn()
        conn.autocommit = False
        try:
            value = json.dumps({'timestamp': ts.isoformat(), 'updated_at': datetime.now(timezone.utc).isoformat()})
            self._pg_execute(conn, """
                INSERT INTO core.system_config (key, value, description)
                VALUES (%s, %s::jsonb, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (key, value, f"ETL watermark for {key}"))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to set watermark {key}: {e}")
        finally:
            self.pg_pool.putconn(conn)

    # ── Hourly ETL ──────────────────────────────────────────

    def process_hourly(self, lookback_hours: int = 3, dry_run: bool = False) -> Dict[str, Any]:
        """
        Query hydroponics_hourly bucket → insert into bi.hourly_sensor_agg.

        Returns summary dict with rows_processed count.
        """
        if not self._initialized:
            return {'error': 'ETL not initialized', 'rows': 0}

        self._load_sensor_mappings()

        # Determine start time from watermark or lookback
        watermark = self._get_watermark('etl_hourly_watermark')
        if watermark:
            start = watermark - timedelta(minutes=30)  # overlap for safety
        else:
            start = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        bucket = f"{INFLUXDB_BUCKET}_hourly"
        query = f'''
        from(bucket: "{bucket}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
          |> yield(name: "hourly_avg")
        '''

        # Also get min, max, count
        query_min = f'''
        from(bucket: "{bucket}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> aggregateWindow(every: 1h, fn: min, createEmpty: false)
          |> yield(name: "hourly_min")
        '''

        query_max = f'''
        from(bucket: "{bucket}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> aggregateWindow(every: 1h, fn: max, createEmpty: false)
          |> yield(name: "hourly_max")
        '''

        query_count = f'''
        from(bucket: "{bucket}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> aggregateWindow(every: 1h, fn: count, createEmpty: false)
          |> yield(name: "hourly_count")
        '''

        try:
            avg_tables = self.query_api.query(query)
            min_tables = self.query_api.query(query_min)
            max_tables = self.query_api.query(query_max)
            count_tables = self.query_api.query(query_count)
        except Exception as e:
            logger.error(f"Hourly ETL: InfluxDB query failed: {e}")
            # Fallback: try querying the raw bucket with aggregation
            return self._process_hourly_from_raw(start, dry_run)

        # Index results by (sensor_tag, field, hour)
        avg_data = self._index_influx_records(avg_tables)
        min_data = self._index_influx_records(min_tables)
        max_data = self._index_influx_records(max_tables)
        count_data = self._index_influx_records(count_tables)

        rows = 0
        latest_ts = start
        conn = self.pg_pool.getconn()
        conn.autocommit = False

        try:
            for key, avg_val in avg_data.items():
                sensor_tag, field_name, hour_start = key

                if field_name not in self.FIELD_TO_SENSOR_TYPE:
                    continue

                mapping = self._ensure_sensor_exists(sensor_tag, field_name)
                if not mapping:
                    continue

                min_val = min_data.get(key, avg_val)
                max_val = max_data.get(key, avg_val)
                count_val = count_data.get(key, 1)

                if dry_run:
                    logger.info(f"[DRY RUN] hourly: sensor={mapping.pg_sensor_id} "
                                f"hour={hour_start} avg={avg_val:.2f}")
                    rows += 1
                    continue

                self._pg_execute(conn, """
                    INSERT INTO bi.hourly_sensor_agg
                        (sensor_id, zone_id, hour_start, avg_value, min_value,
                         max_value, stddev_value, reading_count)
                    VALUES (%s, %s, %s, %s, %s, %s, NULL, %s)
                    ON CONFLICT (sensor_id, hour_start) DO UPDATE SET
                        avg_value = EXCLUDED.avg_value,
                        min_value = EXCLUDED.min_value,
                        max_value = EXCLUDED.max_value,
                        reading_count = EXCLUDED.reading_count
                """, (mapping.pg_sensor_id, mapping.pg_zone_id,
                      hour_start, avg_val, min_val, max_val, count_val))

                rows += 1
                if hour_start > latest_ts:
                    latest_ts = hour_start

            if not dry_run:
                conn.commit()
                self._set_watermark('etl_hourly_watermark', latest_ts)

        except Exception as e:
            conn.rollback()
            logger.error(f"Hourly ETL: PostgreSQL write failed: {e}")
            return {'error': str(e), 'rows': rows}
        finally:
            self.pg_pool.putconn(conn)

        logger.info(f"Hourly ETL complete: {rows} rows processed")
        return {'rows': rows, 'latest_ts': latest_ts.isoformat()}

    def _process_hourly_from_raw(self, start: datetime, dry_run: bool) -> Dict[str, Any]:
        """Fallback: query the raw hydroponics bucket and aggregate ourselves."""
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> filter(fn: (r) =>
              r._field == "temperature" or r._field == "humidity" or
              r._field == "ph" or r._field == "ec" or
              r._field == "water_level" or r._field == "water_temp" or
              r._field == "light"
          )
          |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
          |> yield(name: "hourly_avg")
        '''
        query_min = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> filter(fn: (r) =>
              r._field == "temperature" or r._field == "humidity" or
              r._field == "ph" or r._field == "ec" or
              r._field == "water_level" or r._field == "water_temp" or
              r._field == "light"
          )
          |> aggregateWindow(every: 1h, fn: min, createEmpty: false)
          |> yield(name: "hourly_min")
        '''
        query_max = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> filter(fn: (r) =>
              r._field == "temperature" or r._field == "humidity" or
              r._field == "ph" or r._field == "ec" or
              r._field == "water_level" or r._field == "water_temp" or
              r._field == "light"
          )
          |> aggregateWindow(every: 1h, fn: max, createEmpty: false)
          |> yield(name: "hourly_max")
        '''
        query_count = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> filter(fn: (r) =>
              r._field == "temperature" or r._field == "humidity" or
              r._field == "ph" or r._field == "ec" or
              r._field == "water_level" or r._field == "water_temp" or
              r._field == "light"
          )
          |> aggregateWindow(every: 1h, fn: count, createEmpty: false)
          |> yield(name: "hourly_count")
        '''

        try:
            avg_tables = self.query_api.query(query)
            min_tables = self.query_api.query(query_min)
            max_tables = self.query_api.query(query_max)
            count_tables = self.query_api.query(query_count)
        except Exception as e:
            logger.error(f"Hourly ETL fallback: InfluxDB query failed: {e}")
            return {'error': str(e), 'rows': 0}

        avg_data = self._index_influx_records(avg_tables)
        min_data = self._index_influx_records(min_tables)
        max_data = self._index_influx_records(max_tables)
        count_data = self._index_influx_records(count_tables)

        rows = 0
        latest_ts = start
        conn = self.pg_pool.getconn()
        conn.autocommit = False

        try:
            for key, avg_val in avg_data.items():
                sensor_tag, field_name, hour_start = key

                if field_name not in self.FIELD_TO_SENSOR_TYPE:
                    continue

                mapping = self._ensure_sensor_exists(sensor_tag, field_name)
                if not mapping:
                    continue

                min_val = min_data.get(key, avg_val)
                max_val = max_data.get(key, avg_val)
                count_val = count_data.get(key, 1)

                if dry_run:
                    logger.info(f"[DRY RUN] hourly (raw fallback): sensor={mapping.pg_sensor_id} "
                                f"hour={hour_start} avg={avg_val:.2f}")
                    rows += 1
                    continue

                self._pg_execute(conn, """
                    INSERT INTO bi.hourly_sensor_agg
                        (sensor_id, zone_id, hour_start, avg_value, min_value,
                         max_value, stddev_value, reading_count)
                    VALUES (%s, %s, %s, %s, %s, %s, NULL, %s)
                    ON CONFLICT (sensor_id, hour_start) DO UPDATE SET
                        avg_value = EXCLUDED.avg_value,
                        min_value = EXCLUDED.min_value,
                        max_value = EXCLUDED.max_value,
                        reading_count = EXCLUDED.reading_count
                """, (mapping.pg_sensor_id, mapping.pg_zone_id,
                      hour_start, avg_val, min_val, max_val, count_val))

                rows += 1
                if hour_start > latest_ts:
                    latest_ts = hour_start

            if not dry_run:
                conn.commit()
                self._set_watermark('etl_hourly_watermark', latest_ts)

        except Exception as e:
            conn.rollback()
            logger.error(f"Hourly ETL fallback: PostgreSQL write failed: {e}")
            return {'error': str(e), 'rows': rows}
        finally:
            self.pg_pool.putconn(conn)

        logger.info(f"Hourly ETL (raw fallback) complete: {rows} rows processed")
        return {'rows': rows, 'latest_ts': latest_ts.isoformat(), 'source': 'raw_bucket_fallback'}

    # ── Daily ETL ───────────────────────────────────────────

    def process_daily(self, lookback_days: int = 2, dry_run: bool = False) -> Dict[str, Any]:
        """
        Query hydroponics_daily bucket → insert into bi.daily_sensor_agg.

        For CONDITION_FIELDS, also computes optimal/critical time percentages
        by querying raw InfluxDB data against growth stage ranges.
        """
        if not self._initialized:
            return {'error': 'ETL not initialized', 'rows': 0}

        self._load_sensor_mappings()

        watermark = self._get_watermark('etl_daily_watermark')
        if watermark:
            start = watermark - timedelta(days=1)
        else:
            start = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        bucket = f"{INFLUXDB_BUCKET}_daily"
        query = f'''
        from(bucket: "{bucket}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
          |> yield(name: "daily_avg")
        '''
        query_min = f'''
        from(bucket: "{bucket}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> aggregateWindow(every: 1d, fn: min, createEmpty: false)
          |> yield(name: "daily_min")
        '''
        query_max = f'''
        from(bucket: "{bucket}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> aggregateWindow(every: 1d, fn: max, createEmpty: false)
          |> yield(name: "daily_max")
        '''
        query_count = f'''
        from(bucket: "{bucket}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> aggregateWindow(every: 1d, fn: count, createEmpty: false)
          |> yield(name: "daily_count")
        '''

        try:
            avg_tables = self.query_api.query(query)
            min_tables = self.query_api.query(query_min)
            max_tables = self.query_api.query(query_max)
            count_tables = self.query_api.query(query_count)
        except Exception as e:
            logger.error(f"Daily ETL: InfluxDB query failed: {e}")
            return self._process_daily_from_raw(start, dry_run)

        avg_data = self._index_influx_records(avg_tables)
        min_data = self._index_influx_records(min_tables)
        max_data = self._index_influx_records(max_tables)
        count_data = self._index_influx_records(count_tables)

        rows = 0
        latest_ts = start
        conn = self.pg_pool.getconn()
        conn.autocommit = False

        try:
            for key, avg_val in avg_data.items():
                sensor_tag, field_name, day_start = key

                if field_name not in self.FIELD_TO_SENSOR_TYPE:
                    continue

                mapping = self._ensure_sensor_exists(sensor_tag, field_name)
                if not mapping:
                    continue

                min_val = min_data.get(key, avg_val)
                max_val = max_data.get(key, avg_val)
                count_val = count_data.get(key, 1)
                metric_date = day_start.date() if hasattr(day_start, 'date') else day_start

                # Compute condition percentages for relevant fields
                optimal_pct = None
                critical_pct = None
                if ETL_CONDITION_CALC_ENABLED and field_name in self.CONDITION_FIELDS:
                    optimal_pct, critical_pct = self._compute_condition_percentages(
                        sensor_tag, field_name, metric_date
                    )

                if dry_run:
                    logger.info(f"[DRY RUN] daily: sensor={mapping.pg_sensor_id} "
                                f"date={metric_date} avg={avg_val:.2f} "
                                f"optimal={optimal_pct}% critical={critical_pct}%")
                    rows += 1
                    continue

                self._pg_execute(conn, """
                    INSERT INTO bi.daily_sensor_agg
                        (sensor_id, zone_id, metric_date, avg_value, min_value,
                         max_value, stddev_value, reading_count,
                         time_in_optimal_pct, time_in_critical_pct)
                    VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s, %s)
                    ON CONFLICT (sensor_id, metric_date) DO UPDATE SET
                        avg_value = EXCLUDED.avg_value,
                        min_value = EXCLUDED.min_value,
                        max_value = EXCLUDED.max_value,
                        reading_count = EXCLUDED.reading_count,
                        time_in_optimal_pct = EXCLUDED.time_in_optimal_pct,
                        time_in_critical_pct = EXCLUDED.time_in_critical_pct
                """, (mapping.pg_sensor_id, mapping.pg_zone_id,
                      metric_date, avg_val, min_val, max_val, count_val,
                      optimal_pct, critical_pct))

                rows += 1
                if day_start > latest_ts:
                    latest_ts = day_start

            if not dry_run:
                conn.commit()
                self._set_watermark('etl_daily_watermark', latest_ts)

        except Exception as e:
            conn.rollback()
            logger.error(f"Daily ETL: PostgreSQL write failed: {e}")
            return {'error': str(e), 'rows': rows}
        finally:
            self.pg_pool.putconn(conn)

        logger.info(f"Daily ETL complete: {rows} rows processed")
        return {'rows': rows, 'latest_ts': latest_ts.isoformat()}

    def _process_daily_from_raw(self, start: datetime, dry_run: bool) -> Dict[str, Any]:
        """Fallback: query raw bucket with daily aggregation."""
        field_filter = ' or '.join(
            f'r._field == "{f}"' for f in self.FIELD_TO_SENSOR_TYPE.keys()
        )
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> filter(fn: (r) => {field_filter})
          |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
          |> yield(name: "daily_avg")
        '''
        query_min = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> filter(fn: (r) => {field_filter})
          |> aggregateWindow(every: 1d, fn: min, createEmpty: false)
          |> yield(name: "daily_min")
        '''
        query_max = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> filter(fn: (r) => {field_filter})
          |> aggregateWindow(every: 1d, fn: max, createEmpty: false)
          |> yield(name: "daily_max")
        '''
        query_count = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {start.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> filter(fn: (r) => {field_filter})
          |> aggregateWindow(every: 1d, fn: count, createEmpty: false)
          |> yield(name: "daily_count")
        '''

        try:
            avg_tables = self.query_api.query(query)
            min_tables = self.query_api.query(query_min)
            max_tables = self.query_api.query(query_max)
            count_tables = self.query_api.query(query_count)
        except Exception as e:
            logger.error(f"Daily ETL fallback: InfluxDB query failed: {e}")
            return {'error': str(e), 'rows': 0}

        avg_data = self._index_influx_records(avg_tables)
        min_data = self._index_influx_records(min_tables)
        max_data = self._index_influx_records(max_tables)
        count_data = self._index_influx_records(count_tables)

        rows = 0
        latest_ts = start
        conn = self.pg_pool.getconn()
        conn.autocommit = False

        try:
            for key, avg_val in avg_data.items():
                sensor_tag, field_name, day_start = key

                if field_name not in self.FIELD_TO_SENSOR_TYPE:
                    continue

                mapping = self._ensure_sensor_exists(sensor_tag, field_name)
                if not mapping:
                    continue

                min_val = min_data.get(key, avg_val)
                max_val = max_data.get(key, avg_val)
                count_val = count_data.get(key, 1)
                metric_date = day_start.date() if hasattr(day_start, 'date') else day_start

                optimal_pct = None
                critical_pct = None
                if ETL_CONDITION_CALC_ENABLED and field_name in self.CONDITION_FIELDS:
                    optimal_pct, critical_pct = self._compute_condition_percentages(
                        sensor_tag, field_name, metric_date
                    )

                if dry_run:
                    logger.info(f"[DRY RUN] daily (raw fallback): sensor={mapping.pg_sensor_id} "
                                f"date={metric_date} avg={avg_val:.2f}")
                    rows += 1
                    continue

                self._pg_execute(conn, """
                    INSERT INTO bi.daily_sensor_agg
                        (sensor_id, zone_id, metric_date, avg_value, min_value,
                         max_value, stddev_value, reading_count,
                         time_in_optimal_pct, time_in_critical_pct)
                    VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s, %s)
                    ON CONFLICT (sensor_id, metric_date) DO UPDATE SET
                        avg_value = EXCLUDED.avg_value,
                        min_value = EXCLUDED.min_value,
                        max_value = EXCLUDED.max_value,
                        reading_count = EXCLUDED.reading_count,
                        time_in_optimal_pct = EXCLUDED.time_in_optimal_pct,
                        time_in_critical_pct = EXCLUDED.time_in_critical_pct
                """, (mapping.pg_sensor_id, mapping.pg_zone_id,
                      metric_date, avg_val, min_val, max_val, count_val,
                      optimal_pct, critical_pct))

                rows += 1
                if day_start > latest_ts:
                    latest_ts = day_start

            if not dry_run:
                conn.commit()
                self._set_watermark('etl_daily_watermark', latest_ts)

        except Exception as e:
            conn.rollback()
            logger.error(f"Daily ETL fallback: PostgreSQL write failed: {e}")
            return {'error': str(e), 'rows': rows}
        finally:
            self.pg_pool.putconn(conn)

        logger.info(f"Daily ETL (raw fallback) complete: {rows} rows processed")
        return {'rows': rows, 'latest_ts': latest_ts.isoformat(), 'source': 'raw_bucket_fallback'}

    # ── Condition Percentage Calculation ────────────────────

    def _compute_condition_percentages(self, sensor_tag: str, field_name: str,
                                        metric_date: date) -> Tuple[Optional[float], Optional[float]]:
        """
        Query raw InfluxDB data for a day, compare against growth stage
        optimal ranges from crop.growth_stage_definitions.

        Returns (optimal_pct, critical_pct) or (None, None) if no data/ranges.
        """
        # Get optimal ranges from active crop batches
        ranges = self._get_optimal_ranges(field_name)
        if not ranges:
            return None, None

        # Query raw readings for this sensor+field+day
        day_start = datetime(metric_date.year, metric_date.month, metric_date.day,
                             tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)

        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {day_start.strftime("%Y-%m-%dT%H:%M:%SZ")},
                   stop: {day_end.strftime("%Y-%m-%dT%H:%M:%SZ")})
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> filter(fn: (r) => r.sensor_id == "{sensor_tag}")
          |> filter(fn: (r) => r._field == "{field_name}")
        '''

        try:
            tables = self.query_api.query(query)
        except Exception as e:
            logger.debug(f"Condition calc query failed for {sensor_tag}/{field_name}: {e}")
            return None, None

        values = []
        for table in tables:
            for record in table.records:
                val = record.get_value()
                if isinstance(val, (int, float)):
                    values.append(val)

        if not values:
            return None, None

        # Use widest optimal range across all active batches
        opt_min = min(r['opt_min'] for r in ranges)
        opt_max = max(r['opt_max'] for r in ranges)

        # Critical = >20% beyond optimal range
        range_width = opt_max - opt_min
        critical_margin = range_width * 0.2
        crit_min = opt_min - critical_margin
        crit_max = opt_max + critical_margin

        total = len(values)
        in_optimal = sum(1 for v in values if opt_min <= v <= opt_max)
        in_critical = sum(1 for v in values if v < crit_min or v > crit_max)

        optimal_pct = round((in_optimal / total) * 100, 2)
        critical_pct = round((in_critical / total) * 100, 2)

        return optimal_pct, critical_pct

    def _get_optimal_ranges(self, field_name: str) -> List[Dict[str, float]]:
        """Get optimal ranges for a field from active crop growth stage definitions."""
        field_column_map = {
            'temperature': ('optimal_temp_min', 'optimal_temp_max'),
            'humidity': ('optimal_humidity_min', 'optimal_humidity_max'),
            'ph': ('optimal_ph_min', 'optimal_ph_max'),
            'ec': ('optimal_ec_min', 'optimal_ec_max'),
        }

        columns = field_column_map.get(field_name)
        if not columns:
            return []

        col_min, col_max = columns
        conn = self.pg_pool.getconn()
        try:
            rows = self._pg_fetchall(conn, f"""
                SELECT gsd.{col_min} AS opt_min, gsd.{col_max} AS opt_max
                FROM crop.batches b
                JOIN crop.batch_stages bs ON bs.batch_id = b.id
                    AND bs.ended_at IS NULL
                JOIN crop.growth_stage_definitions gsd ON gsd.id = bs.stage_def_id
                WHERE b.status = 'active'
                    AND gsd.{col_min} IS NOT NULL
                    AND gsd.{col_max} IS NOT NULL
            """)
            return [{'opt_min': float(r['opt_min']), 'opt_max': float(r['opt_max'])} for r in rows]
        except Exception as e:
            logger.debug(f"Failed to get optimal ranges for {field_name}: {e}")
            return []
        finally:
            self.pg_pool.putconn(conn)

    # ── Helpers ─────────────────────────────────────────────

    def _index_influx_records(self, tables) -> Dict[tuple, float]:
        """
        Index InfluxDB query results into a dict keyed by (sensor_tag, field, time).
        """
        result = {}
        for table in tables:
            for record in table.records:
                sensor_tag = record.values.get('sensor_id', 'unknown')
                field_name = record.get_field()
                time = record.get_time()
                value = record.get_value()
                if isinstance(value, (int, float)):
                    result[(sensor_tag, field_name, time)] = float(value)
        return result

    # ── Cleanup ─────────────────────────────────────────────

    def cleanup_old_hourly(self, retention_days: int = None) -> Dict[str, Any]:
        """Delete hourly aggregates older than retention period."""
        if not self._initialized:
            return {'error': 'ETL not initialized', 'deleted': 0}

        if retention_days is None:
            retention_days = ETL_HOURLY_RETENTION_DAYS

        conn = self.pg_pool.getconn()
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM bi.hourly_sensor_agg
                    WHERE hour_start < NOW() - INTERVAL '%s days'
                """, (retention_days,))
                deleted = cur.rowcount
            conn.commit()
            logger.info(f"Cleanup: deleted {deleted} hourly rows older than {retention_days} days")
            return {'deleted': deleted, 'retention_days': retention_days}
        except Exception as e:
            conn.rollback()
            logger.error(f"Cleanup failed: {e}")
            return {'error': str(e), 'deleted': 0}
        finally:
            self.pg_pool.putconn(conn)

    # ── Full Cycle ──────────────────────────────────────────

    def run_full_cycle(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run hourly + daily ETL + cleanup."""
        results = {}
        results['hourly'] = self.process_hourly(dry_run=dry_run)
        results['daily'] = self.process_daily(dry_run=dry_run)
        if not dry_run:
            results['cleanup'] = self.cleanup_old_hourly()
        return results

    # ── Backfill ────────────────────────────────────────────

    def backfill(self, days: int = 30, dry_run: bool = False) -> Dict[str, Any]:
        """Backfill historical data for the specified number of days."""
        results = {}
        results['hourly'] = self.process_hourly(lookback_hours=days * 24, dry_run=dry_run)
        results['daily'] = self.process_daily(lookback_days=days, dry_run=dry_run)
        return results

    # ── Status ──────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return ETL status: watermarks, row counts, connection health."""
        status = {
            'initialized': self._initialized,
            'scheduler_running': self._scheduler_running,
            'influx_connected': False,
            'pg_connected': False,
            'sensor_mappings': len(self._sensor_mappings),
            'watermarks': {},
            'row_counts': {},
        }

        # Check InfluxDB
        if self.influx_client:
            try:
                health = self.influx_client.health()
                status['influx_connected'] = health.status == 'pass'
            except Exception:
                pass

        # Check PostgreSQL and get counts
        if self.pg_pool:
            try:
                conn = self.pg_pool.getconn()
                try:
                    status['pg_connected'] = True

                    # Watermarks
                    for key in ('etl_hourly_watermark', 'etl_daily_watermark'):
                        row = self._pg_fetchone(conn,
                            "SELECT value FROM core.system_config WHERE key = %s", (key,))
                        if row:
                            status['watermarks'][key] = row['value']

                    # Row counts
                    for table, label in [
                        ('bi.hourly_sensor_agg', 'hourly_rows'),
                        ('bi.daily_sensor_agg', 'daily_rows'),
                    ]:
                        row = self._pg_fetchone(conn, f"SELECT COUNT(*) AS cnt FROM {table}")
                        status['row_counts'][label] = row['cnt'] if row else 0

                finally:
                    self.pg_pool.putconn(conn)
            except Exception as e:
                status['pg_error'] = str(e)

        return status

    # ── Background Scheduler ────────────────────────────────

    def start_background_scheduler(self):
        """Start a background timer loop for periodic ETL runs."""
        if self._scheduler_running:
            logger.warning("ETL scheduler already running")
            return

        self._scheduler_running = True
        logger.info(f"ETL background scheduler started "
                    f"(hourly every {ETL_HOURLY_INTERVAL}min, daily at {ETL_DAILY_HOUR:02d}:30)")
        self._schedule_hourly()

    def stop_background_scheduler(self):
        """Stop the background scheduler."""
        self._scheduler_running = False
        if self._scheduler_timer:
            self._scheduler_timer.cancel()
            self._scheduler_timer = None
        logger.info("ETL background scheduler stopped")

    def _schedule_hourly(self):
        """Schedule the next hourly ETL run."""
        if not self._scheduler_running:
            return

        def _run():
            if not self._scheduler_running:
                return
            try:
                logger.info("ETL scheduler: running hourly cycle")
                self.process_hourly()

                # Check if it's time for daily run
                now = datetime.now()
                if now.hour == ETL_DAILY_HOUR and now.minute < ETL_HOURLY_INTERVAL:
                    logger.info("ETL scheduler: running daily cycle")
                    self.process_daily()
                    self.cleanup_old_hourly()
            except Exception as e:
                logger.error(f"ETL scheduler error: {e}")
            finally:
                self._schedule_hourly()

        self._scheduler_timer = threading.Timer(ETL_HOURLY_INTERVAL * 60, _run)
        self._scheduler_timer.daemon = True
        self._scheduler_timer.start()


# ── Module-level singleton ──────────────────────────────────
etl_processor = InfluxPgEtlProcessor()
