"""
Weather Service - Open-Meteo API integration for Algarve region.

Free API, no key required. 15-minute cache.
Provides outdoor weather, forecast, solar data, greenhouse correlation,
and growing conditions advisory.

API: https://api.open-meteo.com/v1/forecast
Coordinates: Faro/Algarve (lat=37.0194, lon=-7.9304)

Author: AgriTech Hydroponics
License: MIT
"""

import json
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from urllib.request import urlopen, Request
from urllib.error import URLError

logger = logging.getLogger('weather-service')

# Algarve coordinates (Faro area)
LATITUDE = 37.0194
LONGITUDE = -7.9304

# Cache TTL
CACHE_TTL_MINUTES = 15

# Open-Meteo base URL
BASE_URL = 'https://api.open-meteo.com/v1/forecast'


class WeatherService:
    """Weather data from Open-Meteo API with caching."""

    def __init__(self, lat: float = LATITUDE, lon: float = LONGITUDE):
        self.lat = lat
        self.lon = lon
        self._cache: Dict[str, Dict] = {}  # key -> {data, expires_at}

    def _cache_get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() < entry['expires_at']:
                return entry['data']
            del self._cache[key]
        return None

    def _cache_set(self, key: str, data: Any, ttl_minutes: int = CACHE_TTL_MINUTES):
        self._cache[key] = {
            'data': data,
            'expires_at': datetime.now() + timedelta(minutes=ttl_minutes),
        }

    def _fetch_api(self, params: Dict[str, str]) -> Optional[Dict]:
        """Fetch data from Open-Meteo API."""
        query = '&'.join(f'{k}={v}' for k, v in params.items())
        url = f'{BASE_URL}?latitude={self.lat}&longitude={self.lon}&{query}'

        try:
            req = Request(url, headers={'User-Agent': 'AgriTech-Hydroponics/1.0'})
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except URLError as e:
            logger.error(f"Open-Meteo API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Weather fetch error: {e}")
            return None

    # ── Current Weather ────────────────────────────────────────────

    def get_current_weather(self) -> Dict[str, Any]:
        """
        Get current outdoor conditions.

        Returns:
            Dict with temperature, humidity, VPD, precipitation, wind, cloud cover
        """
        cached = self._cache_get('current_weather')
        if cached:
            return cached

        data = self._fetch_api({
            'current': 'temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,'
                       'wind_direction_10m,cloud_cover,weather_code,apparent_temperature',
            'timezone': 'Europe/Lisbon',
        })

        if not data or 'current' not in data:
            return {'error': 'Failed to fetch weather data', 'source': 'open-meteo'}

        current = data['current']
        temp = current.get('temperature_2m', 0)
        humidity = current.get('relative_humidity_2m', 0)

        # Calculate outdoor VPD
        vpd = 0
        if temp and humidity:
            svp = 0.6108 * math.exp((17.27 * temp) / (temp + 237.3))
            vpd = round(svp * (1 - humidity / 100.0), 3)

        result = {
            'timestamp': current.get('time', datetime.now().isoformat()),
            'temperature_c': temp,
            'apparent_temperature_c': current.get('apparent_temperature', temp),
            'humidity_percent': humidity,
            'vpd_kpa': vpd,
            'precipitation_mm': current.get('precipitation', 0),
            'wind_speed_kmh': current.get('wind_speed_10m', 0),
            'wind_direction_deg': current.get('wind_direction_10m', 0),
            'cloud_cover_percent': current.get('cloud_cover', 0),
            'weather_code': current.get('weather_code', 0),
            'weather_description': _weather_code_to_text(current.get('weather_code', 0)),
            'source': 'open-meteo',
            'location': {'lat': self.lat, 'lon': self.lon, 'region': 'Algarve, Portugal'},
        }

        self._cache_set('current_weather', result)
        return result

    # ── Forecast ───────────────────────────────────────────────────

    def get_forecast(self, days: int = 3) -> Dict[str, Any]:
        """
        Get hourly forecast with agricultural parameters.

        Args:
            days: Number of forecast days (1-7)

        Returns:
            Dict with hourly forecast including ET0, solar radiation, soil temp
        """
        cached = self._cache_get(f'forecast_{days}')
        if cached:
            return cached

        data = self._fetch_api({
            'hourly': 'temperature_2m,relative_humidity_2m,precipitation_probability,'
                      'precipitation,cloud_cover,wind_speed_10m,'
                      'shortwave_radiation,et0_fao_evapotranspiration,'
                      'vapour_pressure_deficit,soil_temperature_6cm',
            'forecast_days': str(min(days, 7)),
            'timezone': 'Europe/Lisbon',
        })

        if not data or 'hourly' not in data:
            return {'error': 'Failed to fetch forecast', 'source': 'open-meteo'}

        hourly = data['hourly']
        times = hourly.get('time', [])

        forecast_hours = []
        for i, time_str in enumerate(times):
            forecast_hours.append({
                'time': time_str,
                'temperature_c': _safe_index(hourly.get('temperature_2m'), i),
                'humidity_percent': _safe_index(hourly.get('relative_humidity_2m'), i),
                'precipitation_probability': _safe_index(hourly.get('precipitation_probability'), i),
                'precipitation_mm': _safe_index(hourly.get('precipitation'), i),
                'cloud_cover_percent': _safe_index(hourly.get('cloud_cover'), i),
                'wind_speed_kmh': _safe_index(hourly.get('wind_speed_10m'), i),
                'solar_radiation_wm2': _safe_index(hourly.get('shortwave_radiation'), i),
                'et0_mm': _safe_index(hourly.get('et0_fao_evapotranspiration'), i),
                'vpd_kpa': _safe_index(hourly.get('vapour_pressure_deficit'), i),
                'soil_temperature_c': _safe_index(hourly.get('soil_temperature_6cm'), i),
            })

        # Daily summaries
        daily_summaries = _compute_daily_summaries(forecast_hours)

        result = {
            'forecast_days': days,
            'hourly': forecast_hours,
            'daily_summaries': daily_summaries,
            'source': 'open-meteo',
            'location': {'lat': self.lat, 'lon': self.lon, 'region': 'Algarve, Portugal'},
        }

        self._cache_set(f'forecast_{days}', result)
        return result

    # ── Solar Data ─────────────────────────────────────────────────

    def get_solar_data(self) -> Dict[str, Any]:
        """
        Get sunrise/sunset, daylight hours, solar radiation.
        Useful for supplemental lighting decisions.

        Returns:
            Dict with sunrise, sunset, daylight_hours, solar radiation, lighting advisory
        """
        cached = self._cache_get('solar_data')
        if cached:
            return cached

        data = self._fetch_api({
            'daily': 'sunrise,sunset,daylight_duration,shortwave_radiation_sum',
            'hourly': 'shortwave_radiation',
            'forecast_days': '1',
            'timezone': 'Europe/Lisbon',
        })

        if not data or 'daily' not in data:
            return {'error': 'Failed to fetch solar data', 'source': 'open-meteo'}

        daily = data['daily']
        sunrise = _safe_index(daily.get('sunrise'), 0)
        sunset = _safe_index(daily.get('sunset'), 0)
        daylight_seconds = _safe_index(daily.get('daylight_duration'), 0) or 0
        daylight_hours = round(daylight_seconds / 3600, 1)
        radiation_sum = _safe_index(daily.get('shortwave_radiation_sum'), 0) or 0

        # Hourly radiation for today
        hourly_radiation = []
        if 'hourly' in data:
            times = data['hourly'].get('time', [])
            rads = data['hourly'].get('shortwave_radiation', [])
            for i, t in enumerate(times):
                hourly_radiation.append({
                    'time': t,
                    'radiation_wm2': _safe_index(rads, i) or 0,
                })

        # Lighting advisory
        target_photoperiod = 14  # hours for lettuce
        supplemental_hours_needed = max(0, target_photoperiod - daylight_hours)

        if supplemental_hours_needed == 0:
            lighting_advisory = 'Natural daylight sufficient for target photoperiod'
        elif supplemental_hours_needed <= 2:
            lighting_advisory = f'Need {supplemental_hours_needed:.1f}h supplemental lighting (morning or evening)'
        else:
            lighting_advisory = f'Need {supplemental_hours_needed:.1f}h supplemental lighting — extend both morning and evening'

        result = {
            'date': datetime.now().date().isoformat(),
            'sunrise': sunrise,
            'sunset': sunset,
            'daylight_hours': daylight_hours,
            'solar_radiation_sum_mj': round(radiation_sum, 2),
            'hourly_radiation': hourly_radiation,
            'target_photoperiod_hours': target_photoperiod,
            'supplemental_hours_needed': round(supplemental_hours_needed, 1),
            'lighting_advisory': lighting_advisory,
            'source': 'open-meteo',
        }

        self._cache_set('solar_data', result)
        return result

    # ── Greenhouse Correlation ─────────────────────────────────────

    def get_greenhouse_correlation(self, indoor_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Compare indoor vs outdoor conditions.

        Args:
            indoor_data: Current indoor sensor readings
                         (temperature, humidity keys expected)

        Returns:
            Dict with temp differential, estimated HVAC load, efficiency metrics
        """
        outdoor = self.get_current_weather()
        if 'error' in outdoor:
            return {'error': 'Cannot fetch outdoor weather for correlation'}

        outdoor_temp = outdoor.get('temperature_c', 0)
        outdoor_humidity = outdoor.get('humidity_percent', 0)
        outdoor_vpd = outdoor.get('vpd_kpa', 0)

        result = {
            'outdoor': {
                'temperature_c': outdoor_temp,
                'humidity_percent': outdoor_humidity,
                'vpd_kpa': outdoor_vpd,
            },
            'timestamp': datetime.now().isoformat(),
        }

        if indoor_data:
            indoor_temp = indoor_data.get('temperature', 0)
            indoor_humidity = indoor_data.get('humidity', 0)

            # Calculate indoor VPD
            indoor_vpd = 0
            if indoor_temp and indoor_humidity:
                svp = 0.6108 * math.exp((17.27 * indoor_temp) / (indoor_temp + 237.3))
                indoor_vpd = round(svp * (1 - indoor_humidity / 100.0), 3)

            temp_diff = round(indoor_temp - outdoor_temp, 1)

            # HVAC load estimate (simplified)
            if temp_diff > 0:
                hvac_mode = 'heating'
                estimated_load = 'high' if temp_diff > 10 else 'medium' if temp_diff > 5 else 'low'
            elif temp_diff < -2:
                hvac_mode = 'cooling'
                estimated_load = 'high' if abs(temp_diff) > 10 else 'medium' if abs(temp_diff) > 5 else 'low'
            else:
                hvac_mode = 'passive'
                estimated_load = 'minimal'

            # Efficiency: how well is the greenhouse maintaining conditions?
            # Target: 22°C, 60% humidity
            temp_efficiency = max(0, 100 - abs(indoor_temp - 22) * 10)
            humidity_efficiency = max(0, 100 - abs(indoor_humidity - 60) * 2)
            overall_efficiency = round((temp_efficiency + humidity_efficiency) / 2, 1)

            result['indoor'] = {
                'temperature_c': indoor_temp,
                'humidity_percent': indoor_humidity,
                'vpd_kpa': indoor_vpd,
            }
            result['correlation'] = {
                'temp_differential_c': temp_diff,
                'hvac_mode': hvac_mode,
                'estimated_hvac_load': estimated_load,
                'greenhouse_efficiency_percent': overall_efficiency,
                'vpd_indoor_vs_outdoor': round(indoor_vpd - outdoor_vpd, 3),
            }

        return result

    # ── Growing Conditions Advisory ────────────────────────────────

    def get_growing_conditions_advisory(self, variety: str = None) -> Dict[str, Any]:
        """
        Weather-based growing advisory.

        Analyzes upcoming weather for heat waves, cold snaps,
        and suggests EC/watering adjustments.

        Args:
            variety: Optional variety name for specific thresholds

        Returns:
            Dict with advisories, alerts, and recommendations
        """
        forecast = self.get_forecast(days=3)
        if 'error' in forecast:
            return {'error': 'Cannot generate advisory without forecast data'}

        solar = self.get_solar_data()

        advisories = []
        alerts = []

        # Analyze daily summaries
        for day in forecast.get('daily_summaries', []):
            date = day.get('date', '')
            max_temp = day.get('max_temp', 0)
            min_temp = day.get('min_temp', 0)
            total_precip = day.get('total_precipitation', 0)
            avg_radiation = day.get('avg_radiation', 0)

            # Heat wave detection
            if max_temp and max_temp > 35:
                alerts.append({
                    'type': 'heat_wave',
                    'date': date,
                    'severity': 'high',
                    'message': f'Extreme heat expected ({max_temp:.0f}°C) - increase cooling/ventilation',
                    'actions': [
                        'Increase ventilation and shade cloth',
                        'Lower EC by 10-15% to reduce plant stress',
                        'Increase watering frequency',
                        'Monitor VPD closely',
                    ],
                })
            elif max_temp and max_temp > 30:
                advisories.append({
                    'type': 'warm_day',
                    'date': date,
                    'message': f'Warm day expected ({max_temp:.0f}°C) - monitor greenhouse temp',
                })

            # Cold snap detection
            if min_temp is not None and min_temp < 5:
                alerts.append({
                    'type': 'cold_snap',
                    'date': date,
                    'severity': 'high',
                    'message': f'Cold night expected ({min_temp:.0f}°C) - ensure heating active',
                    'actions': [
                        'Verify heating system operational',
                        'Close vents before sunset',
                        'Consider thermal blankets',
                        'Slightly increase EC for cold tolerance',
                    ],
                })
            elif min_temp is not None and min_temp < 10:
                advisories.append({
                    'type': 'cool_night',
                    'date': date,
                    'message': f'Cool night expected ({min_temp:.0f}°C) - reduce ventilation overnight',
                })

            # Heavy rain
            if total_precip and total_precip > 20:
                advisories.append({
                    'type': 'heavy_rain',
                    'date': date,
                    'message': f'Heavy rain expected ({total_precip:.0f}mm) - check drainage/humidity',
                })

            # Low radiation (cloudy)
            if avg_radiation is not None and avg_radiation < 100:
                advisories.append({
                    'type': 'low_light',
                    'date': date,
                    'message': 'Overcast conditions - consider supplemental lighting',
                })

        # Supplemental lighting from solar data
        if not solar.get('error'):
            supp_hours = solar.get('supplemental_hours_needed', 0)
            if supp_hours > 0:
                advisories.append({
                    'type': 'lighting',
                    'message': solar.get('lighting_advisory', ''),
                    'supplemental_hours': supp_hours,
                })

        result = {
            'generated_at': datetime.now().isoformat(),
            'variety': variety,
            'alerts': alerts,
            'advisories': advisories,
            'alert_count': len(alerts),
            'advisory_count': len(advisories),
            'source': 'open-meteo',
        }

        return result


# ── Helper functions ───────────────────────────────────────────────

def _safe_index(lst: Optional[list], idx: int, default=None):
    if lst is None or idx >= len(lst):
        return default
    return lst[idx]


def _weather_code_to_text(code: int) -> str:
    """Convert WMO weather code to readable text."""
    codes = {
        0: 'Clear sky',
        1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
        45: 'Foggy', 48: 'Depositing rime fog',
        51: 'Light drizzle', 53: 'Moderate drizzle', 55: 'Dense drizzle',
        61: 'Slight rain', 63: 'Moderate rain', 65: 'Heavy rain',
        71: 'Slight snow', 73: 'Moderate snow', 75: 'Heavy snow',
        80: 'Slight rain showers', 81: 'Moderate rain showers', 82: 'Violent rain showers',
        95: 'Thunderstorm', 96: 'Thunderstorm with slight hail', 99: 'Thunderstorm with heavy hail',
    }
    return codes.get(code, f'Unknown ({code})')


def _compute_daily_summaries(hourly: List[Dict]) -> List[Dict]:
    """Compute daily summaries from hourly forecast data."""
    days: Dict[str, List[Dict]] = {}
    for h in hourly:
        date = h.get('time', '')[:10]
        if date:
            days.setdefault(date, []).append(h)

    summaries = []
    for date, hours in sorted(days.items()):
        temps = [h['temperature_c'] for h in hours if h.get('temperature_c') is not None]
        humidities = [h['humidity_percent'] for h in hours if h.get('humidity_percent') is not None]
        precips = [h['precipitation_mm'] for h in hours if h.get('precipitation_mm') is not None]
        radiations = [h['solar_radiation_wm2'] for h in hours if h.get('solar_radiation_wm2') is not None]
        vpds = [h['vpd_kpa'] for h in hours if h.get('vpd_kpa') is not None]

        summaries.append({
            'date': date,
            'max_temp': round(max(temps), 1) if temps else None,
            'min_temp': round(min(temps), 1) if temps else None,
            'avg_temp': round(sum(temps) / len(temps), 1) if temps else None,
            'avg_humidity': round(sum(humidities) / len(humidities), 1) if humidities else None,
            'total_precipitation': round(sum(precips), 1) if precips else 0,
            'avg_radiation': round(sum(radiations) / len(radiations), 1) if radiations else None,
            'avg_vpd': round(sum(vpds) / len(vpds), 3) if vpds else None,
        })

    return summaries


# Global instance
weather_service = WeatherService()
