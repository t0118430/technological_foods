"""
Weather Source - Open-Meteo API for external weather data.

Fetches current conditions + 7-day hourly forecast for Algarve region.
Stores as InfluxDB measurements: weather_external (current) + weather_forecast (hourly).
Free API, no key required.

Author: AgriTech Hydroponics
License: MIT
"""

import os
import logging
from datetime import datetime
from typing import Any, Dict

from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS

from .data_harvester import DataSource

logger = logging.getLogger('weather-source')

# Algarve defaults (Faro area)
DEFAULT_LAT = float(os.getenv('HARVEST_WEATHER_LAT', '37.0194'))
DEFAULT_LON = float(os.getenv('HARVEST_WEATHER_LON', '-7.9304'))
DEFAULT_INTERVAL = int(os.getenv('HARVEST_WEATHER_INTERVAL', '900'))  # 15 min

OPEN_METEO_BASE = 'https://api.open-meteo.com/v1/forecast'


class WeatherSource(DataSource):
    """Fetches weather from Open-Meteo (free, no API key)."""

    def __init__(self, influx_write_api=None, influx_bucket: str = None,
                 lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON):
        self._write_api = influx_write_api
        self._bucket = influx_bucket or os.getenv('INFLUXDB_BUCKET', 'hydroponics')
        self._lat = lat
        self._lon = lon
        self._last_data: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        return 'weather'

    @property
    def interval_seconds(self) -> int:
        return DEFAULT_INTERVAL

    def is_available(self) -> bool:
        return self._write_api is not None

    def fetch(self) -> Dict[str, Any]:
        """Fetch current weather + 7-day hourly forecast from Open-Meteo."""
        url = (
            f"{OPEN_METEO_BASE}?"
            f"latitude={self._lat}&longitude={self._lon}"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,"
            f"precipitation,cloud_cover,pressure_msl,uv_index"
            f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,"
            f"precipitation_probability,uv_index,direct_radiation"
            f"&timezone=Europe%2FLisbon&forecast_days=7"
        )
        data = self._http_get_json(url)
        self._last_data = data
        return data

    def store(self, data: Dict[str, Any]) -> None:
        """Write current conditions and forecast to InfluxDB."""
        if not self._write_api:
            return

        # Store current conditions
        current = data.get('current', {})
        if current:
            point = (
                Point('weather_external')
                .tag('source', 'open_meteo')
                .tag('location', 'algarve')
                .field('temperature', float(current.get('temperature_2m', 0)))
                .field('humidity', float(current.get('relative_humidity_2m', 0)))
                .field('wind_speed', float(current.get('wind_speed_10m', 0)))
                .field('precipitation', float(current.get('precipitation', 0)))
                .field('cloud_cover', float(current.get('cloud_cover', 0)))
                .field('pressure', float(current.get('pressure_msl', 0)))
                .field('uv_index', float(current.get('uv_index', 0)))
            )
            self._write_api.write(bucket=self._bucket, record=point)

        # Store hourly forecast (next 48 hours to avoid flooding)
        hourly = data.get('hourly', {})
        times = hourly.get('time', [])
        for i, t in enumerate(times[:48]):
            point = (
                Point('weather_forecast')
                .tag('source', 'open_meteo')
                .tag('location', 'algarve')
                .tag('forecast_hour', str(i))
                .field('temperature', float(hourly.get('temperature_2m', [0])[i] or 0))
                .field('humidity', float(hourly.get('relative_humidity_2m', [0])[i] or 0))
                .field('wind_speed', float(hourly.get('wind_speed_10m', [0])[i] or 0))
                .field('rain_probability', float(hourly.get('precipitation_probability', [0])[i] or 0))
                .field('uv_index', float(hourly.get('uv_index', [0])[i] or 0))
                .field('solar_radiation', float(hourly.get('direct_radiation', [0])[i] or 0))
                .field('forecast_time', t)
            )
            self._write_api.write(bucket=self._bucket, record=point)

        logger.info(f"Stored weather: current + {min(len(times), 48)} forecast hours")

    # ── Convenience methods for API/rule engine ────────────────

    def get_current_summary(self) -> Dict[str, Any]:
        """Return latest current weather data for API responses."""
        current = self._last_data.get('current', {})
        if not current:
            return {'status': 'no_data', 'message': 'No weather data yet. Waiting for first harvest.'}
        return {
            'temperature_c': current.get('temperature_2m'),
            'humidity_pct': current.get('relative_humidity_2m'),
            'wind_speed_kmh': current.get('wind_speed_10m'),
            'precipitation_mm': current.get('precipitation'),
            'cloud_cover_pct': current.get('cloud_cover'),
            'pressure_hpa': current.get('pressure_msl'),
            'uv_index': current.get('uv_index'),
            'timestamp': current.get('time'),
            'location': {'lat': self._lat, 'lon': self._lon, 'name': 'Algarve'},
        }

    def get_forecast_summary(self) -> list:
        """Return next 24 hours of forecast for API/rule engine."""
        hourly = self._last_data.get('hourly', {})
        times = hourly.get('time', [])
        forecast = []
        for i, t in enumerate(times[:24]):
            forecast.append({
                'time': t,
                'temperature_c': hourly.get('temperature_2m', [None])[i],
                'humidity_pct': hourly.get('relative_humidity_2m', [None])[i],
                'wind_speed_kmh': hourly.get('wind_speed_10m', [None])[i],
                'rain_probability_pct': hourly.get('precipitation_probability', [None])[i],
                'uv_index': hourly.get('uv_index', [None])[i],
                'solar_radiation_wm2': hourly.get('direct_radiation', [None])[i],
            })
        return forecast

    def get_external_context(self) -> Dict[str, Any]:
        """Build context dict for rule engine compound rules."""
        current = self._last_data.get('current', {})
        return {
            'temperature': current.get('temperature_2m'),
            'humidity': current.get('relative_humidity_2m'),
            'wind_speed': current.get('wind_speed_10m'),
            'precipitation': current.get('precipitation'),
            'cloud_cover': current.get('cloud_cover'),
            'uv_index': current.get('uv_index'),
            'is_hot': (current.get('temperature_2m') or 0) > 30,
            'is_cold': (current.get('temperature_2m') or 0) < 10,
            'is_rainy': (current.get('precipitation') or 0) > 0.5,
        }
