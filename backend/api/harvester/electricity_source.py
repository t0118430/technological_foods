"""
Electricity Source - OMIE Day-Ahead Prices for Portugal.

Fetches Portugal hourly electricity prices from OMIE public data.
Fallback to ENTSO-E Transparency Platform (requires free API key).
Stores as InfluxDB measurement: electricity_price.

Author: AgriTech Hydroponics
License: MIT
"""

import csv
import io
import os
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from influxdb_client import Point

from .data_harvester import DataSource

logger = logging.getLogger('electricity-source')

DEFAULT_INTERVAL = int(os.getenv('HARVEST_ELECTRICITY_INTERVAL', '3600'))  # 1 hour
ENTSOE_TOKEN = os.getenv('ENTSOE_API_TOKEN', '')

# OMIE public CSV endpoint for Portugal day-ahead prices
# Format: https://www.omie.es/sites/default/files/dados/NUEVA_SECCION/MERCADOS/1_precio_horario_del_mercado_diario_YYYYMMDD.csv
OMIE_BASE = 'https://www.omie.es/sites/default/files/dados/NUEVA_SECCION/MERCADOS'


class ElectricitySource(DataSource):
    """Fetches Portugal electricity prices from OMIE (free public CSV)."""

    def __init__(self, influx_write_api=None, influx_bucket: str = None):
        self._write_api = influx_write_api
        self._bucket = influx_bucket or os.getenv('INFLUXDB_BUCKET', 'hydroponics')
        self._last_prices: List[Dict[str, Any]] = []
        self._last_date: str = ''

    @property
    def name(self) -> str:
        return 'electricity'

    @property
    def interval_seconds(self) -> int:
        return DEFAULT_INTERVAL

    def is_available(self) -> bool:
        return self._write_api is not None

    def fetch(self) -> Dict[str, Any]:
        """Fetch today's hourly prices from OMIE. Falls back to ENTSO-E if OMIE fails."""
        today = datetime.utcnow().strftime('%Y%m%d')

        try:
            prices = self._fetch_omie(today)
            self._last_prices = prices
            self._last_date = today
            return {'source': 'omie', 'date': today, 'prices': prices}
        except Exception as e:
            logger.warning(f"OMIE fetch failed: {e}")

        # Fallback: try yesterday (OMIE publishes day-ahead, today may not exist yet)
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y%m%d')
        try:
            prices = self._fetch_omie(yesterday)
            self._last_prices = prices
            self._last_date = yesterday
            return {'source': 'omie', 'date': yesterday, 'prices': prices}
        except Exception as e2:
            logger.warning(f"OMIE yesterday fetch failed: {e2}")

        # Fallback to ENTSO-E if token configured
        if ENTSOE_TOKEN:
            try:
                prices = self._fetch_entsoe(today)
                self._last_prices = prices
                self._last_date = today
                return {'source': 'entsoe', 'date': today, 'prices': prices}
            except Exception as e3:
                logger.warning(f"ENTSO-E fetch failed: {e3}")

        raise RuntimeError("All electricity price sources failed")

    def _fetch_omie(self, date_str: str) -> List[Dict[str, Any]]:
        """Parse OMIE daily price CSV for Portugal column."""
        url = f"{OMIE_BASE}/1_precio_horario_del_mercado_diario_{date_str}.csv"
        text = self._http_get_text(url)

        prices = []
        reader = csv.reader(io.StringIO(text), delimiter=';')
        header_found = False

        for row in reader:
            if not row or len(row) < 5:
                continue
            # Look for the header row containing "Portugal"
            if not header_found:
                if any('portugal' in cell.lower() for cell in row):
                    header_found = True
                continue
            # Parse data rows: hour, spain_price, portugal_price, ...
            try:
                hour = int(row[0].strip())
                # Portugal price is typically in column index 2 or the second price column
                # OMIE format: Hour;Spain;Portugal;...
                pt_price_str = row[2].strip().replace(',', '.')
                price_eur_mwh = float(pt_price_str)
                prices.append({
                    'hour': hour,
                    'price_eur_mwh': price_eur_mwh,
                    'price_eur_kwh': round(price_eur_mwh / 1000, 6),
                })
            except (ValueError, IndexError):
                continue

        if not prices:
            raise ValueError(f"No Portugal prices found in OMIE CSV for {date_str}")

        return prices

    def _fetch_entsoe(self, date_str: str) -> List[Dict[str, Any]]:
        """Fetch from ENTSO-E Transparency Platform (XML API)."""
        # Portugal bidding zone: 10YPT-REN------W
        domain = '10YPT-REN------W'
        period_start = f"{date_str}0000"
        period_end = f"{date_str}2300"
        url = (
            f"https://web-api.tp.entsoe.eu/api?"
            f"securityToken={ENTSOE_TOKEN}"
            f"&documentType=A44"
            f"&in_Domain={domain}&out_Domain={domain}"
            f"&periodStart={period_start}&periodEnd={period_end}"
        )
        # ENTSO-E returns XML; do a simple parse for price values
        text = self._http_get_text(url)

        prices = []
        hour = 1
        # Simple XML extraction: look for <price.amount> tags
        import re
        for match in re.finditer(r'<price\.amount>([^<]+)</price\.amount>', text):
            price_eur_mwh = float(match.group(1))
            prices.append({
                'hour': hour,
                'price_eur_mwh': price_eur_mwh,
                'price_eur_kwh': round(price_eur_mwh / 1000, 6),
            })
            hour += 1

        if not prices:
            raise ValueError(f"No prices found in ENTSO-E response for {date_str}")

        return prices

    def store(self, data: Dict[str, Any]) -> None:
        """Write hourly prices to InfluxDB."""
        if not self._write_api:
            return

        source = data.get('source', 'unknown')
        date = data.get('date', '')
        prices = data.get('prices', [])

        for p in prices:
            point = (
                Point('electricity_price')
                .tag('source', source)
                .tag('market', 'portugal')
                .tag('date', date)
                .field('hour', p['hour'])
                .field('price_eur_mwh', p['price_eur_mwh'])
                .field('price_eur_kwh', p['price_eur_kwh'])
            )
            self._write_api.write(bucket=self._bucket, record=point)

        logger.info(f"Stored {len(prices)} hourly prices from {source} for {date}")

    # ── Convenience methods for API/rule engine ────────────────

    def get_current_price(self) -> Optional[Dict[str, Any]]:
        """Return the price for the current hour."""
        if not self._last_prices:
            return None
        current_hour = datetime.now().hour + 1  # OMIE uses 1-24
        for p in self._last_prices:
            if p['hour'] == current_hour:
                return p
        return self._last_prices[0] if self._last_prices else None

    def get_cheapest_hours(self, n: int = 6) -> List[Dict[str, Any]]:
        """Return the N cheapest hours today, sorted by price."""
        if not self._last_prices:
            return []
        sorted_prices = sorted(self._last_prices, key=lambda p: p['price_eur_mwh'])
        return sorted_prices[:n]

    def get_price_summary(self) -> Dict[str, Any]:
        """Return price summary for API responses."""
        if not self._last_prices:
            return {'status': 'no_data', 'message': 'No electricity price data yet.'}

        current = self.get_current_price()
        cheapest = self.get_cheapest_hours(6)
        cheapest_hours = [p['hour'] for p in cheapest]
        current_hour = datetime.now().hour + 1

        return {
            'date': self._last_date,
            'current_hour': current_hour,
            'current_price': current,
            'cheapest_6_hours': cheapest,
            'is_cheap_hour': current_hour in cheapest_hours,
            'daily_min': min(p['price_eur_mwh'] for p in self._last_prices),
            'daily_max': max(p['price_eur_mwh'] for p in self._last_prices),
            'daily_avg': round(sum(p['price_eur_mwh'] for p in self._last_prices) / len(self._last_prices), 2),
            'all_hours': self._last_prices,
        }

    def get_external_context(self) -> Dict[str, Any]:
        """Build context dict for rule engine compound rules."""
        current = self.get_current_price()
        cheapest = self.get_cheapest_hours(6)
        cheapest_hours = [p['hour'] for p in cheapest]
        current_hour = datetime.now().hour + 1

        return {
            'current_price_eur_mwh': current['price_eur_mwh'] if current else None,
            'current_price_eur_kwh': current['price_eur_kwh'] if current else None,
            'is_cheap_hour': current_hour in cheapest_hours,
            'cheapest_hours': cheapest_hours,
        }
