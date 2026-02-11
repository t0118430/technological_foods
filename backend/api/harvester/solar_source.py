"""
Solar Source - Sunrise/Sunset times from sunrise-sunset.org API.

Fetches daily solar times for Algarve region.
Stores as InfluxDB measurement: solar_times.
Free API, no key required.

Author: AgriTech Hydroponics
License: MIT
"""

import os
import logging
from datetime import datetime
from typing import Any, Dict

from influxdb_client import Point

from .data_harvester import DataSource

logger = logging.getLogger('solar-source')

DEFAULT_LAT = float(os.getenv('HARVEST_WEATHER_LAT', '37.0194'))
DEFAULT_LON = float(os.getenv('HARVEST_WEATHER_LON', '-7.9304'))
DEFAULT_INTERVAL = int(os.getenv('HARVEST_SOLAR_INTERVAL', '21600'))  # 6 hours

SUNRISE_SUNSET_API = 'https://api.sunrise-sunset.org/json'


class SolarSource(DataSource):
    """Fetches sunrise/sunset times from sunrise-sunset.org (free, no API key)."""

    def __init__(self, influx_write_api=None, influx_bucket: str = None,
                 lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON):
        self._write_api = influx_write_api
        self._bucket = influx_bucket or os.getenv('INFLUXDB_BUCKET', 'hydroponics')
        self._lat = lat
        self._lon = lon
        self._last_data: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        return 'solar'

    @property
    def interval_seconds(self) -> int:
        return DEFAULT_INTERVAL

    def is_available(self) -> bool:
        return self._write_api is not None

    def fetch(self) -> Dict[str, Any]:
        """Fetch today's sunrise/sunset from sunrise-sunset.org."""
        url = (
            f"{SUNRISE_SUNSET_API}?"
            f"lat={self._lat}&lng={self._lon}&formatted=0"
        )
        data = self._http_get_json(url)
        results = data.get('results', {})
        self._last_data = results
        return results

    def store(self, data: Dict[str, Any]) -> None:
        """Write solar times to InfluxDB."""
        if not self._write_api:
            return

        day_length_str = data.get('day_length', '0')
        # day_length comes as seconds (int) when formatted=0
        if isinstance(day_length_str, (int, float)):
            day_length_hours = round(float(day_length_str) / 3600, 2)
        else:
            day_length_hours = 0.0

        point = (
            Point('solar_times')
            .tag('location', 'algarve')
            .field('sunrise', data.get('sunrise', ''))
            .field('sunset', data.get('sunset', ''))
            .field('solar_noon', data.get('solar_noon', ''))
            .field('day_length_hours', day_length_hours)
            .field('civil_twilight_begin', data.get('civil_twilight_begin', ''))
            .field('civil_twilight_end', data.get('civil_twilight_end', ''))
        )
        self._write_api.write(bucket=self._bucket, record=point)
        logger.info(f"Stored solar times: sunrise={data.get('sunrise')}, day_length={day_length_hours}h")

    # ── Convenience methods for API/rule engine ────────────────

    def get_day_length_hours(self) -> float:
        """Return current day length in hours for light schedule planning."""
        day_length = self._last_data.get('day_length', 0)
        if isinstance(day_length, (int, float)):
            return round(float(day_length) / 3600, 2)
        return 0.0

    def get_solar_summary(self) -> Dict[str, Any]:
        """Return solar data for API responses."""
        if not self._last_data:
            return {'status': 'no_data', 'message': 'No solar data yet. Waiting for first harvest.'}
        return {
            'sunrise': self._last_data.get('sunrise'),
            'sunset': self._last_data.get('sunset'),
            'solar_noon': self._last_data.get('solar_noon'),
            'day_length_hours': self.get_day_length_hours(),
            'civil_twilight_begin': self._last_data.get('civil_twilight_begin'),
            'civil_twilight_end': self._last_data.get('civil_twilight_end'),
            'location': {'lat': self._lat, 'lon': self._lon, 'name': 'Algarve'},
        }

    def get_external_context(self) -> Dict[str, Any]:
        """Build context dict for rule engine compound rules."""
        return {
            'day_length_hours': self.get_day_length_hours(),
            'is_long_day': self.get_day_length_hours() > 14,
            'is_short_day': self.get_day_length_hours() < 10,
        }
