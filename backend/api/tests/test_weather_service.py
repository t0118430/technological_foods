"""
Tests for Weather Service and Market Data Service.

Tests caching, data parsing, advisory generation, and market price management.
"""

import pytest
import math
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from weather_service import WeatherService, _weather_code_to_text, _compute_daily_summaries, _safe_index
from market_data_service import MarketDataService, SEASONAL_DEMAND, DEFAULT_PRICES


# ── Weather Service Tests ──────────────────────────────────────────

class TestWeatherService:
    @pytest.fixture
    def ws(self):
        return WeatherService()

    def test_initialization(self, ws):
        assert ws.lat == 37.0194
        assert ws.lon == -7.9304
        assert ws._cache == {}

    def test_cache_set_and_get(self, ws):
        ws._cache_set('test_key', {'temp': 25})
        result = ws._cache_get('test_key')
        assert result == {'temp': 25}

    def test_cache_expiry(self, ws):
        ws._cache['expired'] = {
            'data': {'temp': 20},
            'expires_at': datetime.now() - timedelta(minutes=1),
        }
        result = ws._cache_get('expired')
        assert result is None

    def test_cache_miss(self, ws):
        result = ws._cache_get('nonexistent')
        assert result is None

    @patch.object(WeatherService, '_fetch_api')
    def test_get_current_weather_success(self, mock_fetch, ws):
        mock_fetch.return_value = {
            'current': {
                'time': '2026-02-11T14:00',
                'temperature_2m': 18.5,
                'relative_humidity_2m': 65,
                'precipitation': 0,
                'wind_speed_10m': 12,
                'wind_direction_10m': 180,
                'cloud_cover': 30,
                'weather_code': 2,
                'apparent_temperature': 17.0,
            }
        }

        result = ws.get_current_weather()
        assert result['temperature_c'] == 18.5
        assert result['humidity_percent'] == 65
        assert result['vpd_kpa'] > 0
        assert result['weather_description'] == 'Partly cloudy'
        assert result['source'] == 'open-meteo'

    @patch.object(WeatherService, '_fetch_api')
    def test_get_current_weather_cached(self, mock_fetch, ws):
        mock_fetch.return_value = {
            'current': {
                'time': '2026-02-11T14:00',
                'temperature_2m': 18.5,
                'relative_humidity_2m': 65,
                'precipitation': 0,
                'wind_speed_10m': 12,
                'wind_direction_10m': 180,
                'cloud_cover': 30,
                'weather_code': 0,
                'apparent_temperature': 17.0,
            }
        }

        ws.get_current_weather()
        ws.get_current_weather()  # Should use cache
        assert mock_fetch.call_count == 1

    @patch.object(WeatherService, '_fetch_api')
    def test_get_current_weather_api_failure(self, mock_fetch, ws):
        mock_fetch.return_value = None
        result = ws.get_current_weather()
        assert 'error' in result

    @patch.object(WeatherService, '_fetch_api')
    def test_get_forecast(self, mock_fetch, ws):
        mock_fetch.return_value = {
            'hourly': {
                'time': ['2026-02-11T00:00', '2026-02-11T01:00'],
                'temperature_2m': [15.0, 14.5],
                'relative_humidity_2m': [70, 72],
                'precipitation_probability': [10, 20],
                'precipitation': [0, 0],
                'cloud_cover': [50, 60],
                'wind_speed_10m': [10, 12],
                'shortwave_radiation': [0, 0],
                'et0_fao_evapotranspiration': [0, 0],
                'vapour_pressure_deficit': [0.5, 0.4],
                'soil_temperature_6cm': [12, 11.5],
            }
        }

        result = ws.get_forecast(days=1)
        assert len(result['hourly']) == 2
        assert 'daily_summaries' in result
        assert result['source'] == 'open-meteo'

    @patch.object(WeatherService, '_fetch_api')
    def test_get_solar_data(self, mock_fetch, ws):
        mock_fetch.return_value = {
            'daily': {
                'sunrise': ['2026-02-11T07:30'],
                'sunset': ['2026-02-11T18:00'],
                'daylight_duration': [37800],  # 10.5 hours
                'shortwave_radiation_sum': [15.5],
            },
            'hourly': {
                'time': ['2026-02-11T12:00'],
                'shortwave_radiation': [500],
            },
        }

        result = ws.get_solar_data()
        assert result['daylight_hours'] == 10.5
        assert result['supplemental_hours_needed'] == 3.5
        assert 'lighting_advisory' in result

    @patch.object(WeatherService, '_fetch_api')
    def test_greenhouse_correlation_no_indoor(self, mock_fetch, ws):
        mock_fetch.return_value = {
            'current': {
                'time': '2026-02-11T14:00',
                'temperature_2m': 16.0,
                'relative_humidity_2m': 60,
                'precipitation': 0,
                'wind_speed_10m': 10,
                'wind_direction_10m': 0,
                'cloud_cover': 50,
                'weather_code': 2,
                'apparent_temperature': 15.0,
            }
        }

        result = ws.get_greenhouse_correlation()
        assert 'outdoor' in result
        assert 'correlation' not in result  # No indoor data provided

    @patch.object(WeatherService, '_fetch_api')
    def test_greenhouse_correlation_with_indoor(self, mock_fetch, ws):
        mock_fetch.return_value = {
            'current': {
                'time': '2026-02-11T14:00',
                'temperature_2m': 16.0,
                'relative_humidity_2m': 60,
                'precipitation': 0,
                'wind_speed_10m': 10,
                'wind_direction_10m': 0,
                'cloud_cover': 50,
                'weather_code': 0,
                'apparent_temperature': 15.0,
            }
        }

        result = ws.get_greenhouse_correlation(
            indoor_data={'temperature': 22.0, 'humidity': 65.0}
        )
        assert 'correlation' in result
        assert result['correlation']['temp_differential_c'] == 6.0
        assert result['correlation']['hvac_mode'] == 'heating'

    @patch.object(WeatherService, '_fetch_api')
    def test_growing_advisory_heat_wave(self, mock_fetch, ws):
        # Mock forecast with extreme heat
        mock_fetch.return_value = {
            'hourly': {
                'time': ['2026-07-15T12:00', '2026-07-15T15:00'],
                'temperature_2m': [36.0, 38.0],
                'relative_humidity_2m': [30, 25],
                'precipitation_probability': [0, 0],
                'precipitation': [0, 0],
                'cloud_cover': [10, 5],
                'wind_speed_10m': [15, 20],
                'shortwave_radiation': [800, 900],
                'et0_fao_evapotranspiration': [0.5, 0.6],
                'vapour_pressure_deficit': [3.0, 3.5],
                'soil_temperature_6cm': [28, 29],
            }
        }

        # Also mock solar data fetch
        ws._cache_set('solar_data', {
            'supplemental_hours_needed': 0,
            'lighting_advisory': 'Natural daylight sufficient',
        })

        result = ws.get_growing_conditions_advisory()
        heat_alerts = [a for a in result['alerts'] if a['type'] == 'heat_wave']
        assert len(heat_alerts) > 0


# ── Helper Tests ───────────────────────────────────────────────────

class TestWeatherHelpers:
    def test_weather_code_clear(self):
        assert _weather_code_to_text(0) == 'Clear sky'

    def test_weather_code_rain(self):
        assert _weather_code_to_text(63) == 'Moderate rain'

    def test_weather_code_unknown(self):
        assert 'Unknown' in _weather_code_to_text(999)

    def test_safe_index_valid(self):
        assert _safe_index([1, 2, 3], 1) == 2

    def test_safe_index_out_of_bounds(self):
        assert _safe_index([1, 2], 5) is None

    def test_safe_index_none_list(self):
        assert _safe_index(None, 0) is None

    def test_compute_daily_summaries(self):
        hourly = [
            {'time': '2026-02-11T10:00', 'temperature_c': 18, 'humidity_percent': 60,
             'precipitation_mm': 0, 'solar_radiation_wm2': 400, 'vpd_kpa': 0.8},
            {'time': '2026-02-11T14:00', 'temperature_c': 22, 'humidity_percent': 55,
             'precipitation_mm': 0, 'solar_radiation_wm2': 600, 'vpd_kpa': 1.2},
        ]
        summaries = _compute_daily_summaries(hourly)
        assert len(summaries) == 1
        assert summaries[0]['max_temp'] == 22
        assert summaries[0]['min_temp'] == 18


# ── Market Data Service Tests ─────────────────────────────────────

class TestMarketDataService:
    @pytest.fixture
    def mds(self, tmp_path):
        """Market data service with temp file path."""
        import market_data_service
        original_file = market_data_service.MARKET_DATA_FILE
        market_data_service.MARKET_DATA_FILE = tmp_path / 'test_prices.json'
        service = MarketDataService()
        yield service
        market_data_service.MARKET_DATA_FILE = original_file

    def test_default_prices_loaded(self, mds):
        assert len(mds.prices) > 0
        assert 'lettuce_rosso_premium' in mds.prices

    def test_get_market_prices(self, mds):
        result = mds.get_market_prices()
        assert 'products' in result
        assert 'categories' in result
        assert result['source'] == 'curated_algarve'
        assert len(result['products']) == len(DEFAULT_PRICES)

    def test_seasonal_price_adjustment(self, mds):
        result = mds.get_market_prices()
        month = datetime.now().month
        multiplier = SEASONAL_DEMAND[month]['multiplier']

        rosso = next(p for p in result['products'] if p['id'] == 'lettuce_rosso_premium')
        expected = round(10.00 * multiplier, 2)
        assert rosso['seasonal_price_per_kg'] == expected

    def test_get_seasonal_demand(self, mds):
        result = mds.get_seasonal_demand()
        assert 'current_month' in result
        assert 'monthly' in result
        assert len(result['monthly']) == 12
        assert 'planning' in result
        assert result['planning']['peak_multiplier'] == 3.0

    def test_update_market_prices_existing(self, mds):
        result = mds.update_market_prices({
            'products': {
                'lettuce_rosso_premium': {'price_per_kg': 12.00}
            }
        })
        assert result['status'] == 'updated'
        assert mds.prices['lettuce_rosso_premium']['price_per_kg'] == 12.00

    def test_update_market_prices_new_product(self, mds):
        result = mds.update_market_prices({
            'products': {
                'microgreens_sunflower': {
                    'name': 'Microgreens Girassol',
                    'price_per_kg': 30.00,
                    'category': 'microgreens',
                }
            }
        })
        assert result['status'] == 'updated'
        assert 'microgreens_sunflower' in mds.prices

    def test_update_no_products(self, mds):
        result = mds.update_market_prices({})
        assert 'error' in result

    def test_seasonal_demand_peak_months(self):
        peak = [m for m, d in SEASONAL_DEMAND.items() if d['multiplier'] >= 2.0]
        assert 7 in peak  # July
        assert 8 in peak  # August
