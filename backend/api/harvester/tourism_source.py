"""
Tourism Source - Seasonal tourism index for Algarve.

Creates a tourism_index SQLite table with monthly seasonality data.
Seeds default Algarve seasonality pattern on first run.
Supports CSV import for real INE (Instituto Nacional de Estatistica) data.

Author: AgriTech Hydroponics
License: MIT
"""

import csv
import io
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from contextlib import contextmanager

from .data_harvester import DataSource

logger = logging.getLogger('tourism-source')

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'agritech.db'
DB_PATH.parent.mkdir(exist_ok=True)

# Default Algarve seasonality index (100 = average month)
# Based on typical tourism patterns: low winter, peak summer
DEFAULT_SEASONALITY = {
    1: 30,    # January
    2: 35,    # February
    3: 50,    # March
    4: 70,    # April (Easter)
    5: 90,    # May
    6: 130,   # June
    7: 180,   # July
    8: 200,   # August (peak)
    9: 140,   # September
    10: 80,   # October
    11: 40,   # November
    12: 45,   # December (Christmas)
}


class TourismSource(DataSource):
    """Tourism seasonal index tracking via SQLite."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_table()

    @property
    def name(self) -> str:
        return 'tourism'

    @property
    def interval_seconds(self) -> int:
        return 86400  # 24 hours - seasonal data doesn't change often

    def is_available(self) -> bool:
        return True  # SQLite is always available

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_table(self):
        """Create tourism_index table and seed defaults if empty."""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tourism_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    arrivals INTEGER,
                    occupancy_rate REAL,
                    seasonal_index INTEGER NOT NULL,
                    region TEXT DEFAULT 'algarve',
                    source TEXT DEFAULT 'default',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(year, month, region)
                )
            ''')

            # Seed defaults for current year if empty
            count = conn.execute('SELECT COUNT(*) FROM tourism_index').fetchone()[0]
            if count == 0:
                self._seed_defaults(conn)

    def _seed_defaults(self, conn):
        """Seed default seasonality data for current year."""
        year = datetime.utcnow().year
        for month, index in DEFAULT_SEASONALITY.items():
            conn.execute('''
                INSERT OR IGNORE INTO tourism_index (year, month, seasonal_index, region, source)
                VALUES (?, ?, ?, 'algarve', 'default')
            ''', (year, month, index))
        logger.info(f"Seeded default tourism seasonality for {year}")

    def fetch(self) -> Dict[str, Any]:
        """Return current month's tourism data."""
        now = datetime.utcnow()
        return {
            'current_index': self.get_current_index(),
            'month': now.month,
            'year': now.year,
            'checked_at': now.isoformat(),
        }

    def store(self, data: Dict[str, Any]) -> None:
        """Log current tourism index (no external data to store)."""
        idx = data.get('current_index', {})
        if idx:
            logger.info(f"Tourism index for {data.get('year')}-{data.get('month'):02d}: {idx.get('seasonal_index')}")

    # ── Query methods ──────────────────────────────────────────

    def get_current_index(self) -> Dict[str, Any]:
        """Get the tourism index for the current month."""
        now = datetime.utcnow()
        with self._get_connection() as conn:
            row = conn.execute('''
                SELECT * FROM tourism_index
                WHERE year = ? AND month = ? AND region = 'algarve'
                ORDER BY id DESC LIMIT 1
            ''', (now.year, now.month)).fetchone()

            if row:
                return dict(row)

            # Fallback to default seasonality
            return {
                'year': now.year,
                'month': now.month,
                'seasonal_index': DEFAULT_SEASONALITY.get(now.month, 100),
                'source': 'default_fallback',
            }

    def get_demand_forecast(self, months_ahead: int = 3) -> List[Dict[str, Any]]:
        """Get tourism demand forecast for the next N months."""
        now = datetime.utcnow()
        forecast = []

        for i in range(months_ahead):
            month = ((now.month - 1 + i) % 12) + 1
            year = now.year + ((now.month - 1 + i) // 12)

            with self._get_connection() as conn:
                row = conn.execute('''
                    SELECT * FROM tourism_index
                    WHERE year = ? AND month = ? AND region = 'algarve'
                    ORDER BY id DESC LIMIT 1
                ''', (year, month)).fetchone()

                if row:
                    forecast.append(dict(row))
                else:
                    # Use default seasonality
                    forecast.append({
                        'year': year,
                        'month': month,
                        'seasonal_index': DEFAULT_SEASONALITY.get(month, 100),
                        'source': 'default',
                    })

        return forecast

    def get_tourism_summary(self) -> Dict[str, Any]:
        """Return tourism data for API responses."""
        current = self.get_current_index()
        forecast = self.get_demand_forecast(3)

        # Demand level classification
        idx = current.get('seasonal_index', 100)
        if idx >= 150:
            demand_level = 'high'
        elif idx >= 80:
            demand_level = 'medium'
        else:
            demand_level = 'low'

        return {
            'current': current,
            'demand_level': demand_level,
            'forecast_3_months': forecast,
            'recommendation': self._get_recommendation(idx),
        }

    def _get_recommendation(self, index: int) -> str:
        """Production planning recommendation based on tourism index."""
        if index >= 150:
            return "High season - maximize production, premium pricing possible"
        elif index >= 80:
            return "Moderate demand - standard production levels"
        else:
            return "Low season - reduce production, focus on preservation/local markets"

    # ── CSV Import ─────────────────────────────────────────────

    def import_csv(self, csv_text: str) -> int:
        """Import tourism data from CSV. Expected columns: year, month, arrivals, occupancy_rate, seasonal_index.
        Returns number of rows imported."""
        reader = csv.DictReader(io.StringIO(csv_text))
        count = 0

        with self._get_connection() as conn:
            for row in reader:
                try:
                    year = int(row.get('year', '').strip())
                    month = int(row.get('month', '').strip())
                    seasonal_index = int(row.get('seasonal_index', '').strip())
                except (ValueError, AttributeError):
                    continue

                arrivals = None
                if row.get('arrivals', '').strip():
                    try:
                        arrivals = int(row['arrivals'].strip())
                    except ValueError:
                        pass

                occupancy_rate = None
                if row.get('occupancy_rate', '').strip():
                    try:
                        occupancy_rate = float(row['occupancy_rate'].strip())
                    except ValueError:
                        pass

                conn.execute('''
                    INSERT OR REPLACE INTO tourism_index
                    (year, month, arrivals, occupancy_rate, seasonal_index, region, source)
                    VALUES (?, ?, ?, ?, ?, 'algarve', 'csv_import')
                ''', (year, month, arrivals, occupancy_rate, seasonal_index))
                count += 1

        logger.info(f"Imported {count} tourism index entries from CSV")
        return count

    def get_external_context(self) -> Dict[str, Any]:
        """Build context dict for rule engine compound rules."""
        current = self.get_current_index()
        idx = current.get('seasonal_index', 100)
        return {
            'seasonal_index': idx,
            'is_high_season': idx >= 150,
            'is_low_season': idx < 80,
            'demand_level': 'high' if idx >= 150 else ('medium' if idx >= 80 else 'low'),
        }
