"""
Database Schema and ORM for Growth Stage Management.

Hybrid approach:
- InfluxDB: Sensor data (time-series)
- SQLite/PostgreSQL: Crops, stages, history (relational)

Backend switch via DB_BACKEND env var:
- DB_BACKEND=sqlite  (default) - Original SQLite backend
- DB_BACKEND=postgres          - PostgreSQL via pg_database.py

Author: AgriTech Hydroponics
License: MIT
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger('database')

# Database backend selection
DB_BACKEND = os.getenv('DB_BACKEND', 'sqlite').lower()

# Database path (SQLite)
DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'agritech.db'
DB_PATH.parent.mkdir(exist_ok=True)


class Database:
    """SQLite database manager for crop tracking and growth stages."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return dict-like rows
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_database(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Crops table - tracks individual crop batches
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS crops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    variety TEXT NOT NULL,
                    plant_date DATE NOT NULL,
                    expected_harvest_date DATE,
                    actual_harvest_date DATE,
                    status TEXT DEFAULT 'active',
                    zone TEXT DEFAULT 'main',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Growth stages table - tracks stage transitions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS growth_stages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crop_id INTEGER NOT NULL,
                    stage TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    ended_at TIMESTAMP,
                    expected_duration_days INTEGER,
                    conditions_met BOOLEAN DEFAULT 0,
                    FOREIGN KEY (crop_id) REFERENCES crops(id)
                )
            ''')

            # Stage conditions table - optimal conditions per stage
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stage_conditions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    variety TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    parameter TEXT NOT NULL,
                    optimal_min REAL,
                    optimal_max REAL,
                    critical_min REAL,
                    critical_max REAL,
                    unit TEXT,
                    notes TEXT,
                    UNIQUE(variety, stage, parameter)
                )
            ''')

            # Harvest records - tracks yield and quality
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS harvests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crop_id INTEGER NOT NULL,
                    harvest_date DATE NOT NULL,
                    weight_kg REAL,
                    quality_grade TEXT,
                    market_value REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (crop_id) REFERENCES crops(id)
                )
            ''')

            # Sensor calibration log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS calibrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_type TEXT NOT NULL,
                    calibration_date TIMESTAMP NOT NULL,
                    next_due_date DATE,
                    performed_by TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # System events log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    severity TEXT,
                    message TEXT,
                    data JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_crops_status ON crops(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_crops_variety ON crops(variety)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stages_crop ON growth_stages(crop_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)')

            conn.commit()
            logger.info("Database initialized successfully")

    def create_crop(self, variety: str, plant_date: str = None, zone: str = 'main',
                   notes: str = None) -> int:
        """
        Create a new crop batch.

        Args:
            variety: Variety name (e.g., 'rosso_premium', 'curly_green')
            plant_date: Plant date (ISO format, defaults to today)
            zone: Growing zone identifier
            notes: Additional notes

        Returns:
            Crop ID
        """
        if plant_date is None:
            plant_date = datetime.now().date().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO crops (variety, plant_date, zone, notes)
                VALUES (?, ?, ?, ?)
            ''', (variety, plant_date, zone, notes))

            crop_id = cursor.lastrowid

            # Initialize first stage (seedling)
            cursor.execute('''
                INSERT INTO growth_stages (crop_id, stage, started_at)
                VALUES (?, 'seedling', ?)
            ''', (crop_id, datetime.now().isoformat()))

            conn.commit()
            logger.info(f"Created crop {crop_id}: {variety} planted on {plant_date}")

            return crop_id

    def get_active_crops(self) -> List[Dict[str, Any]]:
        """Get all active crops with current stage."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT
                    c.*,
                    gs.stage as current_stage,
                    gs.started_at as stage_started,
                    gs.expected_duration_days
                FROM crops c
                LEFT JOIN growth_stages gs ON c.id = gs.crop_id
                WHERE c.status = 'active' AND gs.ended_at IS NULL
                ORDER BY c.plant_date DESC
            ''')

            return [dict(row) for row in cursor.fetchall()]

    def get_crop(self, crop_id: int) -> Optional[Dict[str, Any]]:
        """Get crop details with stage history."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get crop info
            cursor.execute('SELECT * FROM crops WHERE id = ?', (crop_id,))
            crop = cursor.fetchone()

            if not crop:
                return None

            crop_dict = dict(crop)

            # Get stage history
            cursor.execute('''
                SELECT * FROM growth_stages
                WHERE crop_id = ?
                ORDER BY started_at
            ''', (crop_id,))

            crop_dict['stages'] = [dict(row) for row in cursor.fetchall()]

            return crop_dict

    def advance_stage(self, crop_id: int, new_stage: str, notes: str = None) -> bool:
        """
        Advance crop to next growth stage.

        Args:
            crop_id: Crop ID
            new_stage: New stage name (vegetative, maturity, harvested)
            notes: Optional notes about transition

        Returns:
            Success status
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # End current stage
            cursor.execute('''
                UPDATE growth_stages
                SET ended_at = ?
                WHERE crop_id = ? AND ended_at IS NULL
            ''', (datetime.now().isoformat(), crop_id))

            # Start new stage
            cursor.execute('''
                INSERT INTO growth_stages (crop_id, stage, started_at)
                VALUES (?, ?, ?)
            ''', (crop_id, new_stage, datetime.now().isoformat()))

            # Update crop status if harvested
            if new_stage == 'harvested':
                cursor.execute('''
                    UPDATE crops
                    SET status = 'harvested', actual_harvest_date = ?, updated_at = ?
                    WHERE id = ?
                ''', (datetime.now().date().isoformat(), datetime.now().isoformat(), crop_id))

            conn.commit()
            logger.info(f"Crop {crop_id} advanced to stage: {new_stage}")

            return True

    def get_current_stage(self, crop_id: int) -> Optional[Dict[str, Any]]:
        """Get current growth stage for a crop."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM growth_stages
                WHERE crop_id = ? AND ended_at IS NULL
                LIMIT 1
            ''', (crop_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def check_stage_advancement(self) -> List[Dict[str, Any]]:
        """
        Check if any crops should advance to next stage based on time.

        Returns:
            List of crops ready to advance
        """
        ready_to_advance = []

        active_crops = self.get_active_crops()

        for crop in active_crops:
            variety = crop['variety']
            current_stage = crop['current_stage']
            stage_started = datetime.fromisoformat(crop['stage_started'])
            days_in_stage = (datetime.now() - stage_started).days

            # Load variety config to get expected stage duration
            from config_loader import config_loader
            config = config_loader.load_variety(variety)
            stages = config.get('growth_stages', {})

            stage_info = stages.get(current_stage, {})
            expected_days_str = stage_info.get('days', '0-999')

            # Parse expected days (e.g., "14-35" → max 35)
            if '-' in expected_days_str:
                _, max_days = expected_days_str.split('-')
                max_days = int(max_days)
            else:
                max_days = int(expected_days_str)

            if days_in_stage >= max_days:
                # Determine next stage
                next_stage = None
                if current_stage == 'seedling':
                    next_stage = 'vegetative'
                elif current_stage == 'vegetative':
                    next_stage = 'maturity'

                if next_stage:
                    ready_to_advance.append({
                        'crop_id': crop['id'],
                        'variety': variety,
                        'current_stage': current_stage,
                        'next_stage': next_stage,
                        'days_in_stage': days_in_stage,
                        'expected_max_days': max_days
                    })

        return ready_to_advance

    def record_harvest(self, crop_id: int, weight_kg: float, quality_grade: str,
                      market_value: float = None, notes: str = None) -> int:
        """Record harvest data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO harvests (crop_id, harvest_date, weight_kg, quality_grade, market_value, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (crop_id, datetime.now().date().isoformat(), weight_kg, quality_grade, market_value, notes))

            harvest_id = cursor.lastrowid

            # Mark crop as harvested
            self.advance_stage(crop_id, 'harvested', notes=f"Harvest recorded: {weight_kg}kg")

            conn.commit()
            logger.info(f"Harvest recorded for crop {crop_id}: {weight_kg}kg, grade {quality_grade}")

            return harvest_id

    def record_calibration(self, sensor_type: str, next_due_days: int = 30,
                          performed_by: str = None, notes: str = None) -> int:
        """Record sensor calibration."""
        calibration_date = datetime.now()
        next_due = (calibration_date + timedelta(days=next_due_days)).date()

        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO calibrations (sensor_type, calibration_date, next_due_date, performed_by, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (sensor_type, calibration_date.isoformat(), next_due.isoformat(), performed_by, notes))

            calibration_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Calibration recorded for {sensor_type}, next due: {next_due}")
            return calibration_id

    def get_due_calibrations(self) -> List[Dict[str, Any]]:
        """Get sensors that need calibration."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT sensor_type, MAX(calibration_date) as last_calibration, next_due_date
                FROM calibrations
                GROUP BY sensor_type
                HAVING next_due_date <= date('now')
                ORDER BY next_due_date
            ''')

            return [dict(row) for row in cursor.fetchall()]

    def log_event(self, event_type: str, message: str, severity: str = 'info',
                 data: Dict[str, Any] = None):
        """Log system event."""
        import json

        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO events (event_type, severity, message, data)
                VALUES (?, ?, ?, ?)
            ''', (event_type, severity, message, json.dumps(data) if data else None))

            conn.commit()


# Global instance - switches based on DB_BACKEND env var
if DB_BACKEND == 'postgres':
    try:
        from pg_database import get_pg_database
        db = get_pg_database()
        logger.info("Using PostgreSQL database backend")
    except Exception as e:
        logger.warning(f"PostgreSQL backend failed, falling back to SQLite: {e}")
        db = Database()
else:
    db = Database()
    logger.info("Using SQLite database backend")
