"""
PostgreSQL Database Abstraction Layer with Connection Pooling.

Professional data layer for the three-tier architecture:
- PostgreSQL: Crop lifecycle, clients, operational queries, BI
- InfluxDB: Real-time sensor time-series (handled separately)
- Redis: Latest readings cache, dashboard refresh

Author: AgriTech Hydroponics
License: MIT
"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from decimal import Decimal

logger = logging.getLogger('pg-database')

try:
    import psycopg2
    import psycopg2.pool
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    logger.warning("psycopg2 not installed. PostgreSQL backend unavailable.")

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    logger.warning("redis not installed. Redis caching unavailable.")


def _json_serial(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


class RedisCache:
    """Redis cache wrapper for latest sensor readings and dashboard data."""

    def __init__(self):
        self.client = None
        self.available = False
        self._connect()

    def _connect(self):
        if not HAS_REDIS:
            return
        try:
            host = os.getenv('REDIS_HOST', 'localhost')
            port = int(os.getenv('REDIS_PORT', '6379'))
            self.client = redis.Redis(host=host, port=port, decode_responses=True)
            self.client.ping()
            self.available = True
            logger.info(f"Redis connected at {host}:{port}")
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            self.available = False

    def set_latest_reading(self, sensor_id: str, data: Dict[str, Any], ttl: int = 30):
        """Cache latest sensor reading with TTL."""
        if not self.available:
            return
        try:
            key = f"latest:{sensor_id}"
            self.client.setex(key, ttl, json.dumps(data, default=_json_serial))
        except Exception as e:
            logger.debug(f"Redis set error: {e}")

    def get_latest_reading(self, sensor_id: str) -> Optional[Dict[str, Any]]:
        """Get cached latest reading."""
        if not self.available:
            return None
        try:
            key = f"latest:{sensor_id}"
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.debug(f"Redis get error: {e}")
            return None

    def get_all_latest_readings(self) -> Dict[str, Any]:
        """Get all cached latest readings."""
        if not self.available:
            return {}
        try:
            keys = self.client.keys("latest:*")
            result = {}
            for key in keys:
                sensor_id = key.replace("latest:", "")
                data = self.client.get(key)
                if data:
                    result[sensor_id] = json.loads(data)
            return result
        except Exception as e:
            logger.debug(f"Redis scan error: {e}")
            return {}

    def set_cached(self, key: str, data: Any, ttl: int = 60):
        """Generic cache set."""
        if not self.available:
            return
        try:
            self.client.setex(f"cache:{key}", ttl, json.dumps(data, default=_json_serial))
        except Exception:
            pass

    def get_cached(self, key: str) -> Optional[Any]:
        """Generic cache get."""
        if not self.available:
            return None
        try:
            data = self.client.get(f"cache:{key}")
            return json.loads(data) if data else None
        except Exception:
            return None


class PostgresDatabase:
    """PostgreSQL database manager with connection pooling for crop lifecycle and BI."""

    def __init__(self):
        self.pool = None
        self.available = False
        self.cache = RedisCache()
        self._connect()

    def _connect(self):
        if not HAS_PSYCOPG2:
            return
        try:
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                host=os.getenv('PG_HOST', 'localhost'),
                port=int(os.getenv('PG_PORT', '5432')),
                dbname=os.getenv('PG_DATABASE', 'agritech'),
                user=os.getenv('PG_USER', 'agritech'),
                password=os.getenv('PG_PASSWORD', 'CHANGE_ME'),
            )
            self.available = True
            logger.info("PostgreSQL connection pool initialized")
        except Exception as e:
            logger.warning(f"PostgreSQL not available: {e}")
            self.available = False

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool."""
        conn = self.pool.getconn()
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self.pool.putconn(conn)

    def _fetchone(self, conn, query, params=None) -> Optional[Dict[str, Any]]:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def _fetchall(self, conn, query, params=None) -> List[Dict[str, Any]]:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def _execute(self, conn, query, params=None):
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur

    # ── Crop Varieties ────────────────────────────────────

    def get_varieties(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            return self._fetchall(conn, "SELECT * FROM crop.varieties ORDER BY name")

    def get_variety_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            return self._fetchone(conn,
                "SELECT * FROM crop.varieties WHERE code = %s", (code,))

    def get_stage_definitions(self, variety_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            return self._fetchall(conn, """
                SELECT * FROM crop.growth_stage_definitions
                WHERE variety_id = %s ORDER BY stage_order
            """, (variety_id,))

    # ── Crop Batches ──────────────────────────────────────

    def create_crop(self, variety: str, plant_date: str = None,
                    zone: str = 'main', notes: str = None,
                    plant_count: int = None, seed_lot: str = None) -> int:
        """Create a new crop batch with initial stage."""
        if plant_date is None:
            plant_date = date.today().isoformat()

        with self.get_connection() as conn:
            # Look up variety
            variety_row = self._fetchone(conn,
                "SELECT id FROM crop.varieties WHERE code = %s", (variety,))
            if not variety_row:
                raise ValueError(f"Unknown variety: {variety}")
            variety_id = variety_row['id']

            # Look up zone
            zone_row = self._fetchone(conn,
                "SELECT id FROM core.zones WHERE name = %s", (zone,))
            zone_id = zone_row['id'] if zone_row else None

            # Generate batch code
            cur = self._execute(conn,
                "SELECT crop.generate_batch_code(%s) AS code", (variety,))
            batch_code = cur.fetchone()[0]

            # Get first stage definition
            first_stage = self._fetchone(conn, """
                SELECT id FROM crop.growth_stage_definitions
                WHERE variety_id = %s ORDER BY stage_order LIMIT 1
            """, (variety_id,))

            # Calculate expected harvest
            last_stage = self._fetchone(conn, """
                SELECT COALESCE(SUM(max_days), 60) AS total_days
                FROM crop.growth_stage_definitions WHERE variety_id = %s
            """, (variety_id,))
            total_days = last_stage['total_days'] if last_stage else 60
            expected_harvest = (datetime.fromisoformat(plant_date) + timedelta(days=int(total_days))).date()

            # Insert batch
            cur = self._execute(conn, """
                INSERT INTO crop.batches (batch_code, variety_id, zone_id, plant_date,
                    expected_harvest_date, plant_count, seed_lot, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (batch_code, variety_id, zone_id, plant_date,
                  expected_harvest, plant_count, seed_lot, notes))
            batch_id = cur.fetchone()[0]

            # Insert initial stage
            if first_stage:
                self._execute(conn, """
                    INSERT INTO crop.batch_stages (batch_id, stage_def_id, started_at)
                    VALUES (%s, %s, %s)
                """, (batch_id, first_stage['id'], datetime.now()))

            # Log event
            self._execute(conn, """
                INSERT INTO audit.events (event_type, severity, entity_type, entity_id, message, data)
                VALUES ('crop_created', 'info', 'batch', %s, %s, %s)
            """, (batch_id, f"New {variety} crop planted",
                  json.dumps({'variety': variety, 'zone': zone, 'batch_code': batch_code})))

            logger.info(f"Created batch {batch_code} (id={batch_id}): {variety}")
            return batch_id

    def get_active_crops(self) -> List[Dict[str, Any]]:
        """Get all active crops with current stage."""
        with self.get_connection() as conn:
            return self._fetchall(conn, """
                SELECT
                    b.id, b.batch_code, v.code AS variety, b.plant_date,
                    b.expected_harvest_date, b.status, b.plant_count,
                    z.name AS zone,
                    gsd.stage_name AS current_stage,
                    bs.started_at AS stage_started,
                    gsd.max_days AS expected_duration_days,
                    gsd.optimal_temp_min, gsd.optimal_temp_max,
                    gsd.optimal_ec_min, gsd.optimal_ec_max,
                    gsd.light_hours
                FROM crop.batches b
                JOIN crop.varieties v ON b.variety_id = v.id
                LEFT JOIN core.zones z ON b.zone_id = z.id
                LEFT JOIN crop.batch_stages bs ON b.id = bs.batch_id AND bs.ended_at IS NULL
                LEFT JOIN crop.growth_stage_definitions gsd ON bs.stage_def_id = gsd.id
                WHERE b.status = 'active'
                ORDER BY b.plant_date DESC
            """)

    def get_crop(self, crop_id: int) -> Optional[Dict[str, Any]]:
        """Get crop details with stage history."""
        with self.get_connection() as conn:
            crop = self._fetchone(conn, """
                SELECT b.*, v.code AS variety, v.name AS variety_name,
                       z.name AS zone
                FROM crop.batches b
                JOIN crop.varieties v ON b.variety_id = v.id
                LEFT JOIN core.zones z ON b.zone_id = z.id
                WHERE b.id = %s
            """, (crop_id,))
            if not crop:
                return None

            stages = self._fetchall(conn, """
                SELECT bs.*, gsd.stage_name AS stage, gsd.stage_order
                FROM crop.batch_stages bs
                JOIN crop.growth_stage_definitions gsd ON bs.stage_def_id = gsd.id
                WHERE bs.batch_id = %s
                ORDER BY bs.started_at
            """, (crop_id,))

            crop['stages'] = stages
            return crop

    def get_current_stage(self, crop_id: int) -> Optional[Dict[str, Any]]:
        """Get the current active stage for a crop."""
        with self.get_connection() as conn:
            return self._fetchone(conn, """
                SELECT bs.*, gsd.stage_name AS stage, gsd.stage_order
                FROM crop.batch_stages bs
                JOIN crop.growth_stage_definitions gsd ON bs.stage_def_id = gsd.id
                WHERE bs.batch_id = %s AND bs.ended_at IS NULL
                LIMIT 1
            """, (crop_id,))

    def advance_stage(self, crop_id: int, new_stage: str, notes: str = None,
                      auto: bool = False) -> bool:
        """Advance crop to next growth stage."""
        with self.get_connection() as conn:
            # Get batch info
            batch = self._fetchone(conn, """
                SELECT b.variety_id FROM crop.batches b WHERE b.id = %s
            """, (crop_id,))
            if not batch:
                return False

            # Find the new stage definition
            new_stage_def = self._fetchone(conn, """
                SELECT id FROM crop.growth_stage_definitions
                WHERE variety_id = %s AND stage_name = %s
            """, (batch['variety_id'], new_stage))
            if not new_stage_def:
                return False

            # End current stage
            self._execute(conn, """
                UPDATE crop.batch_stages SET ended_at = NOW()
                WHERE batch_id = %s AND ended_at IS NULL
            """, (crop_id,))

            # Start new stage
            self._execute(conn, """
                INSERT INTO crop.batch_stages (batch_id, stage_def_id, started_at, auto_advanced, notes)
                VALUES (%s, %s, NOW(), %s, %s)
            """, (crop_id, new_stage_def['id'], auto, notes))

            # If harvested, update batch status
            if new_stage in ('harvested', 'harvest_ready'):
                self._execute(conn, """
                    UPDATE crop.batches
                    SET status = CASE WHEN %s = 'harvested' THEN 'harvested' ELSE status END,
                        actual_harvest_date = CASE WHEN %s = 'harvested' THEN CURRENT_DATE ELSE actual_harvest_date END,
                        updated_at = NOW()
                    WHERE id = %s
                """, (new_stage, new_stage, crop_id))

            logger.info(f"Batch {crop_id} advanced to stage: {new_stage}")
            return True

    def check_stage_advancement(self) -> List[Dict[str, Any]]:
        """Check if any crops should auto-advance based on time."""
        with self.get_connection() as conn:
            return self._fetchall(conn, """
                SELECT
                    b.id AS crop_id,
                    v.code AS variety,
                    gsd.stage_name AS current_stage,
                    EXTRACT(EPOCH FROM (NOW() - bs.started_at)) / 86400 AS days_in_stage,
                    gsd.max_days AS expected_max_days,
                    next_gsd.stage_name AS next_stage,
                    next_gsd.id AS next_stage_def_id
                FROM crop.batches b
                JOIN crop.varieties v ON b.variety_id = v.id
                JOIN crop.batch_stages bs ON b.id = bs.batch_id AND bs.ended_at IS NULL
                JOIN crop.growth_stage_definitions gsd ON bs.stage_def_id = gsd.id
                LEFT JOIN crop.growth_stage_definitions next_gsd
                    ON next_gsd.variety_id = v.id AND next_gsd.stage_order = gsd.stage_order + 1
                WHERE b.status = 'active'
                    AND gsd.max_days IS NOT NULL
                    AND EXTRACT(EPOCH FROM (NOW() - bs.started_at)) / 86400 >= gsd.max_days
                    AND next_gsd.id IS NOT NULL
            """)

    # ── Harvests ──────────────────────────────────────────

    def record_harvest(self, crop_id: int, weight_kg: float, quality_grade: str,
                       market_price_per_kg: float = None, destination: str = None,
                       notes: str = None) -> int:
        """Record harvest data and compute BI metrics."""
        total_revenue = None
        if market_price_per_kg and weight_kg:
            total_revenue = round(market_price_per_kg * weight_kg, 2)

        with self.get_connection() as conn:
            cur = self._execute(conn, """
                INSERT INTO crop.harvests (batch_id, harvest_date, weight_kg, quality_grade,
                    market_price_per_kg, total_revenue, destination, notes)
                VALUES (%s, CURRENT_DATE, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (crop_id, weight_kg, quality_grade, market_price_per_kg,
                  total_revenue, destination, notes))
            harvest_id = cur.fetchone()[0]

            # Advance to harvested stage
            self.advance_stage(crop_id, 'harvested',
                               notes=f"Harvest recorded: {weight_kg}kg")

            # Compute BI performance
            self._execute(conn, "SELECT bi.compute_batch_performance(%s)", (crop_id,))

            logger.info(f"Harvest recorded for batch {crop_id}: {weight_kg}kg, grade {quality_grade}")
            return harvest_id

    # ── Calibrations ──────────────────────────────────────

    def record_calibration(self, sensor_type: str, next_due_days: int = 30,
                           performed_by: str = None, notes: str = None) -> int:
        """Record sensor calibration (finds sensor by type name)."""
        with self.get_connection() as conn:
            # Find sensor by type name
            sensor = self._fetchone(conn, """
                SELECT s.id FROM iot.sensors s
                JOIN iot.sensor_types st ON s.sensor_type_id = st.id
                WHERE LOWER(st.name) LIKE %s AND s.status = 'active'
                LIMIT 1
            """, (f"%{sensor_type.lower()}%",))

            if not sensor:
                # Create a calibration log entry anyway via audit
                self._execute(conn, """
                    INSERT INTO audit.events (event_type, severity, message, data)
                    VALUES ('calibration', 'info', %s, %s)
                """, (f"Calibration recorded for {sensor_type}",
                      json.dumps({'sensor_type': sensor_type, 'performed_by': performed_by})))
                return -1

            next_due = (datetime.now() + timedelta(days=next_due_days)).date()

            cur = self._execute(conn, """
                INSERT INTO iot.calibrations (sensor_id, calibration_date, next_due_date,
                    performed_by, notes)
                VALUES (%s, NOW(), %s, %s, %s)
                RETURNING id
            """, (sensor['id'], next_due, performed_by, notes))

            cal_id = cur.fetchone()[0]

            # Update sensor calibration dates
            self._execute(conn, """
                UPDATE iot.sensors SET last_calibration_date = CURRENT_DATE,
                    next_calibration_date = %s WHERE id = %s
            """, (next_due, sensor['id']))

            return cal_id

    def get_due_calibrations(self) -> List[Dict[str, Any]]:
        """Get sensors that need calibration."""
        with self.get_connection() as conn:
            return self._fetchall(conn, """
                SELECT s.id, s.sensor_code, st.name AS sensor_type,
                       s.last_calibration_date, s.next_calibration_date
                FROM iot.sensors s
                JOIN iot.sensor_types st ON s.sensor_type_id = st.id
                WHERE st.calibration_required = TRUE
                  AND s.status = 'active'
                  AND (s.next_calibration_date IS NULL OR s.next_calibration_date <= CURRENT_DATE)
                ORDER BY s.next_calibration_date NULLS FIRST
            """)

    # ── Events ────────────────────────────────────────────

    def log_event(self, event_type: str, message: str, severity: str = 'info',
                  data: Dict[str, Any] = None):
        """Log system event to audit schema."""
        with self.get_connection() as conn:
            self._execute(conn, """
                INSERT INTO audit.events (event_type, severity, message, data)
                VALUES (%s, %s, %s, %s)
            """, (event_type, severity, message,
                  json.dumps(data, default=_json_serial) if data else None))

    # ── Business / Clients ────────────────────────────────

    def get_client(self, client_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            return self._fetchone(conn,
                "SELECT * FROM business.clients WHERE id = %s", (client_id,))

    def create_client(self, name: str, email: str, company_name: str = None,
                      phone: str = None, tier: str = 'bronze') -> int:
        with self.get_connection() as conn:
            start_date = date.today()
            end_date = start_date + timedelta(days=365)
            cur = self._execute(conn, """
                INSERT INTO business.clients (name, company_name, email, phone,
                    subscription_tier, subscription_start_date, subscription_end_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (name, company_name, email, phone, tier, start_date, end_date))
            return cur.fetchone()[0]

    # ── BI: Hourly Aggregation ────────────────────────────

    def insert_hourly_aggregate(self, sensor_id: int, zone_id: int,
                                 hour_start: datetime, avg_val: float,
                                 min_val: float, max_val: float,
                                 stddev_val: float, count: int):
        """Insert hourly sensor aggregate from InfluxDB data."""
        with self.get_connection() as conn:
            self._execute(conn, """
                INSERT INTO bi.hourly_sensor_agg
                    (sensor_id, zone_id, hour_start, avg_value, min_value,
                     max_value, stddev_value, reading_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (sensor_id, hour_start) DO UPDATE SET
                    avg_value = EXCLUDED.avg_value,
                    min_value = EXCLUDED.min_value,
                    max_value = EXCLUDED.max_value,
                    stddev_value = EXCLUDED.stddev_value,
                    reading_count = EXCLUDED.reading_count
            """, (sensor_id, zone_id, hour_start, avg_val, min_val,
                  max_val, stddev_val, count))

    def insert_daily_aggregate(self, sensor_id: int, zone_id: int,
                                metric_date: date, avg_val: float,
                                min_val: float, max_val: float,
                                stddev_val: float, count: int,
                                optimal_pct: float = None, critical_pct: float = None):
        """Insert daily sensor aggregate."""
        with self.get_connection() as conn:
            self._execute(conn, """
                INSERT INTO bi.daily_sensor_agg
                    (sensor_id, zone_id, metric_date, avg_value, min_value,
                     max_value, stddev_value, reading_count,
                     time_in_optimal_pct, time_in_critical_pct)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (sensor_id, zone_id, metric_date, avg_val, min_val,
                  max_val, stddev_val, count, optimal_pct, critical_pct))

    # ── Site Visits ───────────────────────────────────────

    def create_site_visit(self, data: Dict[str, Any]) -> int:
        """Create a new site visit record."""
        with self.get_connection() as conn:
            row = self._fetchone(conn, """
                INSERT INTO business.site_visits (
                    visit_date, inspector_name, client_id, facility_name,
                    visit_type, zones_inspected, crop_batches_checked,
                    sensor_readings_snapshot, observations, issues_found,
                    actions_taken, follow_up_required, follow_up_date,
                    follow_up_notes, overall_rating, photo_notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                data.get('visit_date', date.today().isoformat()),
                data['inspector_name'],
                data.get('client_id'),
                data.get('facility_name', ''),
                data['visit_type'],
                psycopg2.extras.Json(data.get('zones_inspected', [])),
                psycopg2.extras.Json(data.get('crop_batches_checked', [])),
                psycopg2.extras.Json(data.get('sensor_readings_snapshot', {})),
                data.get('observations', ''),
                psycopg2.extras.Json(data.get('issues_found', [])),
                data.get('actions_taken', ''),
                bool(data.get('follow_up_required', False)),
                data.get('follow_up_date'),
                data.get('follow_up_notes', ''),
                data.get('overall_rating', 3),
                data.get('photo_notes', ''),
            ))
            return row['id']

    def get_site_visit(self, visit_id: int) -> Optional[Dict[str, Any]]:
        """Get a single site visit by ID with client name."""
        with self.get_connection() as conn:
            return self._fetchone(conn, """
                SELECT sv.*, c.name AS client_name
                FROM business.site_visits sv
                LEFT JOIN business.clients c ON sv.client_id = c.id
                WHERE sv.id = %s
            """, (visit_id,))

    def update_site_visit(self, visit_id: int, data: Dict[str, Any]) -> bool:
        """Update an existing site visit. Only updates fields present in data."""
        allowed = {
            'visit_date', 'inspector_name', 'client_id', 'facility_name',
            'visit_type', 'zones_inspected', 'crop_batches_checked',
            'sensor_readings_snapshot', 'observations', 'issues_found',
            'actions_taken', 'follow_up_required', 'follow_up_date',
            'follow_up_notes', 'follow_up_completed', 'overall_rating', 'photo_notes'
        }
        json_fields = {'zones_inspected', 'crop_batches_checked', 'sensor_readings_snapshot', 'issues_found'}

        sets = []
        values = []
        for key, value in data.items():
            if key not in allowed:
                continue
            if key in json_fields and isinstance(value, (list, dict)):
                value = psycopg2.extras.Json(value)
            if key == 'follow_up_required':
                value = bool(value)
            sets.append(f"{key} = %s")
            values.append(value)

        if not sets:
            return False

        sets.append("updated_at = NOW()")
        values.append(visit_id)

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE business.site_visits SET {', '.join(sets)} WHERE id = %s",
                    values
                )
                return cur.rowcount > 0

    def delete_site_visit(self, visit_id: int) -> bool:
        """Delete a site visit record."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM business.site_visits WHERE id = %s", (visit_id,))
                return cur.rowcount > 0

    def list_site_visits(self, filters: Dict[str, Any] = None,
                         page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """List site visits with filtering, sorting, and pagination."""
        filters = filters or {}
        where_clauses = []
        params = []

        if filters.get('visit_type'):
            where_clauses.append("sv.visit_type = %s")
            params.append(filters['visit_type'])

        if filters.get('inspector_name'):
            where_clauses.append("sv.inspector_name ILIKE %s")
            params.append(f"%{filters['inspector_name']}%")

        if filters.get('date_from'):
            where_clauses.append("sv.visit_date >= %s")
            params.append(filters['date_from'])

        if filters.get('date_to'):
            where_clauses.append("sv.visit_date <= %s")
            params.append(filters['date_to'])

        if filters.get('follow_up') == 'pending':
            where_clauses.append("sv.follow_up_required = TRUE AND sv.follow_up_completed = FALSE")
        elif filters.get('follow_up') == 'completed':
            where_clauses.append("sv.follow_up_required = TRUE AND sv.follow_up_completed = TRUE")

        if filters.get('search'):
            where_clauses.append(
                "(sv.inspector_name ILIKE %s OR sv.observations ILIKE %s OR sv.facility_name ILIKE %s)")
            search_term = f"%{filters['search']}%"
            params.extend([search_term, search_term, search_term])

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        sort_col = filters.get('sort', 'visit_date')
        sort_dir = 'ASC' if filters.get('sort_dir', 'desc').lower() == 'asc' else 'DESC'
        allowed_sorts = {'visit_date', 'inspector_name', 'visit_type', 'overall_rating', 'created_at'}
        if sort_col not in allowed_sorts:
            sort_col = 'visit_date'

        with self.get_connection() as conn:
            count_row = self._fetchone(conn,
                f"SELECT COUNT(*) AS total FROM business.site_visits sv{where_sql}", params)
            total = count_row['total']

            offset = (page - 1) * per_page
            visits = self._fetchall(conn, f"""
                SELECT sv.*, c.name AS client_name
                FROM business.site_visits sv
                LEFT JOIN business.clients c ON sv.client_id = c.id
                {where_sql}
                ORDER BY sv.{sort_col} {sort_dir}, sv.id ASC
                LIMIT %s OFFSET %s
            """, params + [per_page, offset])

            return {
                'visits': visits,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': max(1, -(-total // per_page)),
            }

    def get_site_visits_dashboard(self) -> Dict[str, Any]:
        """Return KPIs, chart data, recent activity, and top clients."""
        with self.get_connection() as conn:
            total = self._fetchone(conn,
                "SELECT COUNT(*) AS c FROM business.site_visits")['c']

            this_month = self._fetchone(conn, """
                SELECT COUNT(*) AS c FROM business.site_visits
                WHERE visit_date >= date_trunc('month', CURRENT_DATE)
            """)['c']

            last_month = self._fetchone(conn, """
                SELECT COUNT(*) AS c FROM business.site_visits
                WHERE visit_date >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
                  AND visit_date < date_trunc('month', CURRENT_DATE)
            """)['c']

            pending_followups = self._fetchone(conn, """
                SELECT COUNT(*) AS c FROM business.site_visits
                WHERE follow_up_required = TRUE AND follow_up_completed = FALSE
            """)['c']

            avg_rating = self._fetchone(conn,
                "SELECT COALESCE(AVG(overall_rating), 0) AS avg FROM business.site_visits"
            )['avg']

            monthly_data = self._fetchall(conn, """
                SELECT to_char(visit_date, 'YYYY-MM') AS month, COUNT(*) AS count
                FROM business.site_visits
                WHERE visit_date >= CURRENT_DATE - INTERVAL '6 months'
                GROUP BY month
                ORDER BY month
            """)

            type_data = self._fetchall(conn, """
                SELECT visit_type AS type, COUNT(*) AS count
                FROM business.site_visits
                GROUP BY visit_type
                ORDER BY count DESC
            """)

            rating_data = self._fetchall(conn, """
                SELECT overall_rating AS rating, COUNT(*) AS count
                FROM business.site_visits
                GROUP BY overall_rating
                ORDER BY overall_rating
            """)

            recent = self._fetchall(conn, """
                SELECT sv.*, c.name AS client_name
                FROM business.site_visits sv
                LEFT JOIN business.clients c ON sv.client_id = c.id
                ORDER BY sv.created_at DESC
                LIMIT 10
            """)

            top_clients = self._fetchall(conn, """
                SELECT c.id, c.name AS company_name, c.health_score,
                       COUNT(sv.id) AS visit_count,
                       MAX(sv.visit_date) AS last_visit
                FROM business.site_visits sv
                JOIN business.clients c ON sv.client_id = c.id
                GROUP BY c.id, c.name, c.health_score
                ORDER BY visit_count DESC
                LIMIT 10
            """)

            inspectors = self._fetchall(conn, """
                SELECT DISTINCT inspector_name
                FROM business.site_visits
                ORDER BY inspector_name
            """)

            return {
                'kpis': {
                    'total_visits': total,
                    'visits_this_month': this_month,
                    'visits_last_month': last_month,
                    'month_delta': this_month - last_month,
                    'pending_followups': pending_followups,
                    'avg_rating': round(float(avg_rating), 1),
                },
                'charts': {
                    'monthly': [{'month': r['month'], 'count': r['count']} for r in monthly_data],
                    'by_type': [{'type': r['type'], 'count': r['count']} for r in type_data],
                    'ratings': [{'rating': r['rating'], 'count': r['count']} for r in rating_data],
                },
                'recent_activity': recent,
                'top_clients': top_clients,
                'inspectors': [r['inspector_name'] for r in inspectors],
            }

    def get_site_visits_clients(self) -> List[Dict[str, Any]]:
        """Get active clients for site visit form dropdown."""
        with self.get_connection() as conn:
            return self._fetchall(conn, """
                SELECT id, name AS company_name, subscription_tier, health_score
                FROM business.clients
                WHERE status = 'active'
                ORDER BY name
            """)

    def get_site_visits_export(self) -> List[Dict[str, Any]]:
        """Return all visits flat for CSV export."""
        with self.get_connection() as conn:
            return self._fetchall(conn, """
                SELECT sv.*, c.name AS client_name
                FROM business.site_visits sv
                LEFT JOIN business.clients c ON sv.client_id = c.id
                ORDER BY sv.visit_date DESC
            """)

    def complete_site_visit_follow_up(self, visit_id: int) -> bool:
        """Mark a site visit follow-up as completed."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE business.site_visits
                    SET follow_up_completed = TRUE, updated_at = NOW()
                    WHERE id = %s AND follow_up_required = TRUE
                """, (visit_id,))
                return cur.rowcount > 0

    # ── Dashboard ─────────────────────────────────────────

    def get_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive crop dashboard data."""
        cached = self.cache.get_cached("dashboard")
        if cached:
            return cached

        active_crops = self.get_active_crops()

        stage_summary = {}
        variety_summary = {}
        for crop in active_crops:
            stage = crop.get('current_stage', 'unknown')
            variety = crop.get('variety', 'unknown')
            stage_summary[stage] = stage_summary.get(stage, 0) + 1
            variety_summary[variety] = variety_summary.get(variety, 0) + 1

        ready_to_advance = self.check_stage_advancement()
        due_calibrations = self.get_due_calibrations()

        alerts = []
        if ready_to_advance:
            alerts.append({
                'type': 'stage_advancement_due',
                'count': len(ready_to_advance),
                'crops': ready_to_advance
            })
        if due_calibrations:
            alerts.append({
                'type': 'calibration_due',
                'sensors': due_calibrations
            })

        dashboard = {
            'total_active_crops': len(active_crops),
            'crops': active_crops,
            'stage_summary': stage_summary,
            'variety_summary': variety_summary,
            'alerts': alerts
        }

        self.cache.set_cached("dashboard", dashboard, ttl=30)
        return dashboard

    def get_harvest_analytics(self) -> Dict[str, Any]:
        """Get harvest analytics and performance metrics."""
        with self.get_connection() as conn:
            variety_stats = self._fetchall(conn, """
                SELECT v.code AS variety, COUNT(*) AS count,
                       AVG(h.weight_kg) AS avg_weight,
                       AVG(h.total_revenue) AS avg_value
                FROM crop.harvests h
                JOIN crop.batches b ON h.batch_id = b.id
                JOIN crop.varieties v ON b.variety_id = v.id
                GROUP BY v.code
            """)

            recent = self._fetchall(conn, """
                SELECT h.*, v.code AS variety, b.plant_date, b.batch_code
                FROM crop.harvests h
                JOIN crop.batches b ON h.batch_id = b.id
                JOIN crop.varieties v ON b.variety_id = v.id
                ORDER BY h.harvest_date DESC
                LIMIT 10
            """)

            return {
                'by_variety': variety_stats,
                'recent_harvests': recent
            }

    # ── Alert Writes ──────────────────────────────────────

    def write_alert(self, rule_id: int = None, device_id: int = None,
                    sensor_id: int = None, severity: str = 'warning',
                    title: str = '', message: str = '',
                    current_value: float = None, threshold: float = None) -> int:
        """Write alert to PostgreSQL alert schema."""
        with self.get_connection() as conn:
            cur = self._execute(conn, """
                INSERT INTO alert.alerts (rule_id, device_id, sensor_id, severity,
                    title, message, current_value, threshold_violated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (rule_id, device_id, sensor_id, severity,
                  title, message, current_value, threshold))
            return cur.fetchone()[0]

    # ── Zones ─────────────────────────────────────────────

    def get_zones(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            return self._fetchall(conn,
                "SELECT * FROM core.zones ORDER BY name")

    def close(self):
        """Close the connection pool."""
        if self.pool:
            self.pool.closeall()
            logger.info("PostgreSQL connection pool closed")


# Singleton - lazy initialization
_pg_db = None


def get_pg_database() -> PostgresDatabase:
    """Get or create the PostgreSQL database singleton."""
    global _pg_db
    if _pg_db is None:
        _pg_db = PostgresDatabase()
    return _pg_db
