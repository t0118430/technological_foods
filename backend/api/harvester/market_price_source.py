"""
Market Price Source - Produce market prices (manual entry + CSV import).

Creates a market_prices SQLite table for tracking produce prices across
Algarve markets and restaurant clients.
Scheduled check detects stale data (>7 days) and logs warning.

Author: AgriTech Hydroponics
License: MIT
"""

import csv
import io
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from .data_harvester import DataSource

logger = logging.getLogger('market-price-source')

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'agritech.db'
DB_PATH.parent.mkdir(exist_ok=True)

# Supported produce types
PRODUCE_TYPES = ['rosso_lettuce', 'basil', 'arugula', 'mint', 'cherry_tomato']

# Known markets
MARKETS = {
    'loule': 'Mercado de Loule',
    'olhao': 'Mercado de Olhao',
    'faro': 'Mercado de Faro',
    'lagos_restaurants': 'Restaurants Lagos',
    'albufeira_restaurants': 'Restaurants Albufeira',
    'vilamoura_restaurants': 'Restaurants Vilamoura',
}

STALE_DAYS = 7


class MarketPriceSource(DataSource):
    """Manual/CSV market price tracking via SQLite."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_table()

    @property
    def name(self) -> str:
        return 'market_prices'

    @property
    def interval_seconds(self) -> int:
        return 86400  # 24 hours - just checks for stale data

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
        """Create market_prices table if it doesn't exist."""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS market_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    produce_type TEXT NOT NULL,
                    market_id TEXT NOT NULL,
                    price_per_kg REAL NOT NULL,
                    price_date DATE NOT NULL,
                    source TEXT DEFAULT 'manual',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_market_prices_produce
                ON market_prices(produce_type, price_date DESC)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_market_prices_market
                ON market_prices(market_id, price_date DESC)
            ''')

    def fetch(self) -> Dict[str, Any]:
        """Check for stale data and return current status."""
        stale = self._check_stale_data()
        return {'stale_items': stale, 'checked_at': datetime.utcnow().isoformat()}

    def store(self, data: Dict[str, Any]) -> None:
        """Log warnings for stale data (no external fetch to store)."""
        stale = data.get('stale_items', [])
        if stale:
            for item in stale:
                logger.warning(
                    f"Stale market price: {item['produce_type']} at {item['market_id']} "
                    f"last updated {item['days_ago']} days ago"
                )

    def _check_stale_data(self) -> List[Dict[str, Any]]:
        """Find produce/market combos with no price data in the last STALE_DAYS."""
        cutoff = (datetime.utcnow() - timedelta(days=STALE_DAYS)).strftime('%Y-%m-%d')
        stale = []

        with self._get_connection() as conn:
            # Get distinct produce/market combos that have ever had data
            rows = conn.execute('''
                SELECT produce_type, market_id, MAX(price_date) as last_date
                FROM market_prices
                GROUP BY produce_type, market_id
                HAVING MAX(price_date) < ?
            ''', (cutoff,)).fetchall()

            for row in rows:
                days_ago = (datetime.utcnow() - datetime.strptime(row['last_date'], '%Y-%m-%d')).days
                stale.append({
                    'produce_type': row['produce_type'],
                    'market_id': row['market_id'],
                    'last_date': row['last_date'],
                    'days_ago': days_ago,
                })

        return stale

    # ── CRUD methods for API routes ────────────────────────────

    def add_price(self, produce_type: str, market_id: str, price_per_kg: float,
                  price_date: str = None, source: str = 'manual', notes: str = None) -> int:
        """Add a single price entry. Returns row ID."""
        if produce_type not in PRODUCE_TYPES:
            raise ValueError(f"Unknown produce type: {produce_type}. Valid: {PRODUCE_TYPES}")
        if market_id not in MARKETS:
            raise ValueError(f"Unknown market: {market_id}. Valid: {list(MARKETS.keys())}")

        price_date = price_date or datetime.utcnow().strftime('%Y-%m-%d')

        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO market_prices (produce_type, market_id, price_per_kg, price_date, source, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (produce_type, market_id, price_per_kg, price_date, source, notes))
            return cursor.lastrowid

    def import_csv(self, csv_text: str) -> int:
        """Import prices from CSV text. Expected columns: produce_type, market_id, price_per_kg, price_date, notes.
        Returns number of rows imported."""
        reader = csv.DictReader(io.StringIO(csv_text))
        count = 0

        with self._get_connection() as conn:
            for row in reader:
                produce_type = row.get('produce_type', '').strip()
                market_id = row.get('market_id', '').strip()
                price_str = row.get('price_per_kg', '').strip()
                price_date = row.get('price_date', '').strip() or datetime.utcnow().strftime('%Y-%m-%d')
                notes = row.get('notes', '').strip()

                if not produce_type or not market_id or not price_str:
                    continue

                try:
                    price_per_kg = float(price_str)
                except ValueError:
                    continue

                conn.execute('''
                    INSERT INTO market_prices (produce_type, market_id, price_per_kg, price_date, source, notes)
                    VALUES (?, ?, ?, ?, 'csv_import', ?)
                ''', (produce_type, market_id, price_per_kg, price_date, notes))
                count += 1

        logger.info(f"Imported {count} market price entries from CSV")
        return count

    def get_latest_prices(self, produce_type: str = None) -> List[Dict[str, Any]]:
        """Get latest price for each produce/market combo. Optionally filter by produce."""
        with self._get_connection() as conn:
            if produce_type:
                rows = conn.execute('''
                    SELECT mp.* FROM market_prices mp
                    INNER JOIN (
                        SELECT produce_type, market_id, MAX(price_date) as max_date
                        FROM market_prices
                        WHERE produce_type = ?
                        GROUP BY produce_type, market_id
                    ) latest ON mp.produce_type = latest.produce_type
                        AND mp.market_id = latest.market_id
                        AND mp.price_date = latest.max_date
                    ORDER BY mp.produce_type, mp.market_id
                ''', (produce_type,)).fetchall()
            else:
                rows = conn.execute('''
                    SELECT mp.* FROM market_prices mp
                    INNER JOIN (
                        SELECT produce_type, market_id, MAX(price_date) as max_date
                        FROM market_prices
                        GROUP BY produce_type, market_id
                    ) latest ON mp.produce_type = latest.produce_type
                        AND mp.market_id = latest.market_id
                        AND mp.price_date = latest.max_date
                    ORDER BY mp.produce_type, mp.market_id
                ''').fetchall()

            return [dict(row) for row in rows]

    def get_price_summary(self) -> Dict[str, Any]:
        """Return market price summary for API responses."""
        prices = self.get_latest_prices()
        if not prices:
            return {
                'status': 'no_data',
                'message': 'No market prices yet. Add via POST /api/harvester/market-prices.',
                'supported_produce': PRODUCE_TYPES,
                'supported_markets': MARKETS,
            }
        stale = self._check_stale_data()
        return {
            'prices': prices,
            'stale_warnings': stale,
            'supported_produce': PRODUCE_TYPES,
            'supported_markets': MARKETS,
        }
