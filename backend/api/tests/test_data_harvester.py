"""
Tests for the Data Harvester module.

Unit tests for all sources (mocked HTTP, tmp_path SQLite),
scheduler registration/start/stop/status, CSV imports,
and rule engine compound rule evaluation.

Run: pytest test_data_harvester.py -v
"""

import json
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory

from harvester.data_harvester import DataSource, HarvestScheduler
from harvester.weather_source import WeatherSource
from harvester.solar_source import SolarSource
from harvester.electricity_source import ElectricitySource
from harvester.market_price_source import MarketPriceSource
from harvester.tourism_source import TourismSource
from rules.rule_engine import RuleEngine


# ── Mock HTTP responses ───────────────────────────────────────

MOCK_WEATHER_RESPONSE = {
    'current': {
        'time': '2026-02-11T14:00',
        'temperature_2m': 18.5,
        'relative_humidity_2m': 65,
        'wind_speed_10m': 12.3,
        'precipitation': 0.0,
        'cloud_cover': 30,
        'pressure_msl': 1018.5,
        'uv_index': 3.2,
    },
    'hourly': {
        'time': [f'2026-02-11T{h:02d}:00' for h in range(24)],
        'temperature_2m': [15 + h * 0.5 for h in range(24)],
        'relative_humidity_2m': [70 - h for h in range(24)],
        'wind_speed_10m': [10 + h * 0.2 for h in range(24)],
        'precipitation_probability': [5 * (h % 4) for h in range(24)],
        'uv_index': [0 if h < 6 or h > 20 else h - 5 for h in range(24)],
        'direct_radiation': [0 if h < 6 or h > 20 else (h - 5) * 50 for h in range(24)],
    },
}

MOCK_SOLAR_RESPONSE = {
    'results': {
        'sunrise': '2026-02-11T07:30:00+00:00',
        'sunset': '2026-02-11T18:00:00+00:00',
        'solar_noon': '2026-02-11T12:45:00+00:00',
        'day_length': 37800,  # 10.5 hours in seconds
        'civil_twilight_begin': '2026-02-11T07:05:00+00:00',
        'civil_twilight_end': '2026-02-11T18:25:00+00:00',
    },
    'status': 'OK',
}


# ── DataSource ABC Tests ─────────────────────────────────────

class TestDataSourceABC(unittest.TestCase):
    def test_cannot_instantiate_abc(self):
        with self.assertRaises(TypeError):
            DataSource()

    def test_http_get_json_convenience(self):
        """Test that _http_get_json is a static method available to subclasses."""
        self.assertTrue(callable(DataSource._http_get_json))
        self.assertTrue(callable(DataSource._http_get_text))


# ── HarvestScheduler Tests ───────────────────────────────────

class TestHarvestScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = HarvestScheduler()

    def test_register_source(self):
        mock_source = MagicMock(spec=DataSource)
        mock_source.name = 'test'
        mock_source.interval_seconds = 60
        mock_source.is_available.return_value = True

        self.scheduler.register(mock_source)
        status = self.scheduler.get_status()

        self.assertEqual(status['source_count'], 1)
        self.assertIn('test', status['sources'])
        self.assertTrue(status['sources']['test']['available'])

    def test_start_stop(self):
        mock_source = MagicMock(spec=DataSource)
        mock_source.name = 'test'
        mock_source.interval_seconds = 3600
        mock_source.is_available.return_value = True

        self.scheduler.register(mock_source)
        self.scheduler.start()
        self.assertTrue(self.scheduler.get_status()['running'])

        self.scheduler.stop()
        self.assertFalse(self.scheduler.get_status()['running'])

    def test_harvest_now(self):
        mock_source = MagicMock(spec=DataSource)
        mock_source.name = 'test'
        mock_source.interval_seconds = 60
        mock_source.is_available.return_value = True
        mock_source.harvest.return_value = {
            'source': 'test',
            'status': 'ok',
            'timestamp': '2026-02-11T00:00:00',
        }

        self.scheduler.register(mock_source)
        results = self.scheduler.harvest_now('test')

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], 'ok')
        mock_source.harvest.assert_called_once()

    def test_harvest_now_all(self):
        for name in ('a', 'b', 'c'):
            src = MagicMock(spec=DataSource)
            src.name = name
            src.interval_seconds = 60
            src.is_available.return_value = True
            src.harvest.return_value = {'source': name, 'status': 'ok', 'timestamp': ''}
            self.scheduler.register(src)

        results = self.scheduler.harvest_now()
        self.assertEqual(len(results), 3)

    def test_get_source(self):
        mock_source = MagicMock(spec=DataSource)
        mock_source.name = 'test'
        mock_source.interval_seconds = 60
        mock_source.is_available.return_value = True

        self.scheduler.register(mock_source)
        self.assertIs(self.scheduler.get_source('test'), mock_source)
        self.assertIsNone(self.scheduler.get_source('nonexistent'))


# ── WeatherSource Tests ──────────────────────────────────────

class TestWeatherSource(unittest.TestCase):
    def setUp(self):
        self.mock_write = MagicMock()
        self.source = WeatherSource(influx_write_api=self.mock_write, influx_bucket='test')

    @patch.object(DataSource, '_http_get_json', return_value=MOCK_WEATHER_RESPONSE)
    def test_fetch(self, mock_http):
        data = self.source.fetch()
        self.assertIn('current', data)
        self.assertIn('hourly', data)
        self.assertEqual(data['current']['temperature_2m'], 18.5)

    @patch.object(DataSource, '_http_get_json', return_value=MOCK_WEATHER_RESPONSE)
    def test_store(self, mock_http):
        data = self.source.fetch()
        self.source.store(data)
        # 1 current + 24 forecast = 25 writes
        self.assertTrue(self.mock_write.write.call_count >= 1)

    @patch.object(DataSource, '_http_get_json', return_value=MOCK_WEATHER_RESPONSE)
    def test_get_current_summary(self, mock_http):
        self.source.fetch()
        summary = self.source.get_current_summary()
        self.assertEqual(summary['temperature_c'], 18.5)
        self.assertEqual(summary['humidity_pct'], 65)
        self.assertEqual(summary['location']['name'], 'Algarve')

    @patch.object(DataSource, '_http_get_json', return_value=MOCK_WEATHER_RESPONSE)
    def test_get_forecast_summary(self, mock_http):
        self.source.fetch()
        forecast = self.source.get_forecast_summary()
        self.assertEqual(len(forecast), 24)
        self.assertIn('temperature_c', forecast[0])

    @patch.object(DataSource, '_http_get_json', return_value=MOCK_WEATHER_RESPONSE)
    def test_get_external_context(self, mock_http):
        self.source.fetch()
        ctx = self.source.get_external_context()
        self.assertEqual(ctx['temperature'], 18.5)
        self.assertFalse(ctx['is_hot'])
        self.assertFalse(ctx['is_cold'])
        self.assertFalse(ctx['is_rainy'])

    def test_no_data_summary(self):
        summary = self.source.get_current_summary()
        self.assertEqual(summary['status'], 'no_data')


# ── SolarSource Tests ────────────────────────────────────────

class TestSolarSource(unittest.TestCase):
    def setUp(self):
        self.mock_write = MagicMock()
        self.source = SolarSource(influx_write_api=self.mock_write, influx_bucket='test')

    @patch.object(DataSource, '_http_get_json', return_value=MOCK_SOLAR_RESPONSE)
    def test_fetch(self, mock_http):
        data = self.source.fetch()
        self.assertIn('sunrise', data)
        self.assertIn('sunset', data)
        self.assertEqual(data['day_length'], 37800)

    @patch.object(DataSource, '_http_get_json', return_value=MOCK_SOLAR_RESPONSE)
    def test_store(self, mock_http):
        data = self.source.fetch()
        self.source.store(data)
        self.mock_write.write.assert_called_once()

    @patch.object(DataSource, '_http_get_json', return_value=MOCK_SOLAR_RESPONSE)
    def test_get_day_length(self, mock_http):
        self.source.fetch()
        hours = self.source.get_day_length_hours()
        self.assertAlmostEqual(hours, 10.5, places=1)

    @patch.object(DataSource, '_http_get_json', return_value=MOCK_SOLAR_RESPONSE)
    def test_get_external_context(self, mock_http):
        self.source.fetch()
        ctx = self.source.get_external_context()
        self.assertAlmostEqual(ctx['day_length_hours'], 10.5, places=1)
        self.assertFalse(ctx['is_long_day'])
        self.assertFalse(ctx['is_short_day'])

    def test_no_data_summary(self):
        summary = self.source.get_solar_summary()
        self.assertEqual(summary['status'], 'no_data')


# ── ElectricitySource Tests ──────────────────────────────────

class TestElectricitySource(unittest.TestCase):
    def setUp(self):
        self.mock_write = MagicMock()
        self.source = ElectricitySource(influx_write_api=self.mock_write, influx_bucket='test')

    def test_no_data_summary(self):
        summary = self.source.get_price_summary()
        self.assertEqual(summary['status'], 'no_data')

    def test_store_prices(self):
        data = {
            'source': 'test',
            'date': '20260211',
            'prices': [
                {'hour': h, 'price_eur_mwh': 50 + h * 2, 'price_eur_kwh': (50 + h * 2) / 1000}
                for h in range(1, 25)
            ],
        }
        self.source._last_prices = data['prices']
        self.source._last_date = data['date']
        self.source.store(data)
        self.assertEqual(self.mock_write.write.call_count, 24)

    def test_get_cheapest_hours(self):
        self.source._last_prices = [
            {'hour': h, 'price_eur_mwh': 100 - h * 3, 'price_eur_kwh': (100 - h * 3) / 1000}
            for h in range(1, 25)
        ]
        cheapest = self.source.get_cheapest_hours(3)
        self.assertEqual(len(cheapest), 3)
        # Highest hour numbers should be cheapest (100 - h*3)
        self.assertTrue(cheapest[0]['price_eur_mwh'] < cheapest[1]['price_eur_mwh'])

    def test_get_external_context(self):
        self.source._last_prices = [
            {'hour': h, 'price_eur_mwh': 50 + h, 'price_eur_kwh': (50 + h) / 1000}
            for h in range(1, 25)
        ]
        ctx = self.source.get_external_context()
        self.assertIn('is_cheap_hour', ctx)
        self.assertIn('cheapest_hours', ctx)


# ── MarketPriceSource Tests ──────────────────────────────────

class TestMarketPriceSource(unittest.TestCase):
    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / 'test.db'
        self.source = MarketPriceSource(db_path=self.db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_add_price(self):
        row_id = self.source.add_price('basil', 'loule', 12.50)
        self.assertIsNotNone(row_id)
        self.assertGreater(row_id, 0)

    def test_add_price_invalid_produce(self):
        with self.assertRaises(ValueError):
            self.source.add_price('unknown_produce', 'loule', 10.0)

    def test_add_price_invalid_market(self):
        with self.assertRaises(ValueError):
            self.source.add_price('basil', 'unknown_market', 10.0)

    def test_get_latest_prices(self):
        self.source.add_price('basil', 'loule', 12.50, '2026-01-01')
        self.source.add_price('basil', 'loule', 13.00, '2026-02-01')
        prices = self.source.get_latest_prices('basil')
        self.assertEqual(len(prices), 1)
        self.assertEqual(prices[0]['price_per_kg'], 13.0)

    def test_import_csv(self):
        csv_text = (
            "produce_type,market_id,price_per_kg,price_date,notes\n"
            "basil,loule,12.50,2026-01-15,Fresh\n"
            "arugula,faro,8.00,2026-01-15,Organic\n"
            "mint,olhao,15.00,2026-01-15,Premium\n"
        )
        count = self.source.import_csv(csv_text)
        self.assertEqual(count, 3)
        prices = self.source.get_latest_prices()
        self.assertEqual(len(prices), 3)

    def test_stale_data_detection(self):
        self.source.add_price('basil', 'loule', 12.50, '2025-01-01')
        stale = self.source._check_stale_data()
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]['produce_type'], 'basil')

    def test_price_summary_empty(self):
        summary = self.source.get_price_summary()
        self.assertEqual(summary['status'], 'no_data')

    def test_harvest(self):
        self.source.add_price('basil', 'loule', 12.50, '2025-01-01')
        result = self.source.harvest()
        self.assertEqual(result['status'], 'ok')


# ── TourismSource Tests ──────────────────────────────────────

class TestTourismSource(unittest.TestCase):
    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / 'test.db'
        self.source = TourismSource(db_path=self.db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_default_seeding(self):
        """Test that default seasonality is seeded on first init."""
        current = self.source.get_current_index()
        self.assertIn('seasonal_index', current)
        self.assertGreater(current['seasonal_index'], 0)

    def test_get_demand_forecast(self):
        forecast = self.source.get_demand_forecast(3)
        self.assertEqual(len(forecast), 3)
        for entry in forecast:
            self.assertIn('month', entry)
            self.assertIn('seasonal_index', entry)

    def test_import_csv(self):
        csv_text = (
            "year,month,arrivals,occupancy_rate,seasonal_index\n"
            "2026,7,500000,92.5,185\n"
            "2026,8,600000,98.0,210\n"
        )
        count = self.source.import_csv(csv_text)
        self.assertEqual(count, 2)

    def test_get_tourism_summary(self):
        summary = self.source.get_tourism_summary()
        self.assertIn('current', summary)
        self.assertIn('demand_level', summary)
        self.assertIn('forecast_3_months', summary)
        self.assertIn('recommendation', summary)

    def test_external_context(self):
        ctx = self.source.get_external_context()
        self.assertIn('seasonal_index', ctx)
        self.assertIn('is_high_season', ctx)
        self.assertIn('demand_level', ctx)

    def test_harvest(self):
        result = self.source.harvest()
        self.assertEqual(result['status'], 'ok')


# ── Compound Rule Evaluation Tests ───────────────────────────

class TestCompoundRules(unittest.TestCase):
    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        rules_file = Path(self.tmpdir.name) / 'rules.json'
        rules_file.write_text(json.dumps({'rules': []}))
        self.engine = RuleEngine(rules_file=rules_file)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_basic_rule_still_works(self):
        """Existing rules work without external_data."""
        self.engine.create_rule({
            'id': 'temp_high',
            'sensor': 'temperature',
            'condition': 'above',
            'threshold': 28.0,
            'action': {'type': 'notify', 'message': 'Too hot'},
        })
        triggered = self.engine.evaluate({'temperature': 30.0})
        self.assertEqual(len(triggered), 1)
        self.assertEqual(triggered[0]['rule_id'], 'temp_high')

    def test_compound_rule_both_conditions_met(self):
        """Compound rule fires when both sensor AND external conditions are met."""
        self.engine.create_rule({
            'id': 'smart_ac',
            'sensor': 'temperature',
            'condition': 'above',
            'threshold': 28.0,
            'external_condition': {
                'source_field': 'electricity.is_cheap_hour',
                'condition': 'equals',
                'threshold': True,
            },
            'action': {'type': 'ac', 'command': 'cool', 'target_temp': 24},
        })

        external = {'electricity': {'is_cheap_hour': True}}
        triggered = self.engine.evaluate({'temperature': 30.0}, external_data=external)
        self.assertEqual(len(triggered), 1)
        self.assertEqual(triggered[0]['rule_id'], 'smart_ac')

    def test_compound_rule_external_condition_not_met(self):
        """Compound rule does NOT fire when external condition fails."""
        self.engine.create_rule({
            'id': 'smart_ac',
            'sensor': 'temperature',
            'condition': 'above',
            'threshold': 28.0,
            'external_condition': {
                'source_field': 'electricity.is_cheap_hour',
                'condition': 'equals',
                'threshold': True,
            },
            'action': {'type': 'ac', 'command': 'cool', 'target_temp': 24},
        })

        external = {'electricity': {'is_cheap_hour': False}}
        triggered = self.engine.evaluate({'temperature': 30.0}, external_data=external)
        self.assertEqual(len(triggered), 0)

    def test_compound_rule_sensor_condition_not_met(self):
        """Compound rule does NOT fire when sensor condition fails."""
        self.engine.create_rule({
            'id': 'smart_ac',
            'sensor': 'temperature',
            'condition': 'above',
            'threshold': 28.0,
            'external_condition': {
                'source_field': 'electricity.is_cheap_hour',
                'condition': 'equals',
                'threshold': True,
            },
            'action': {'type': 'ac', 'command': 'cool', 'target_temp': 24},
        })

        external = {'electricity': {'is_cheap_hour': True}}
        triggered = self.engine.evaluate({'temperature': 25.0}, external_data=external)
        self.assertEqual(len(triggered), 0)

    def test_compound_rule_above_condition(self):
        """External condition with 'above' works."""
        self.engine.create_rule({
            'id': 'weather_hot',
            'sensor': 'temperature',
            'condition': 'above',
            'threshold': 28.0,
            'external_condition': {
                'source_field': 'weather.temperature',
                'condition': 'above',
                'threshold': 30,
            },
            'action': {'type': 'notify', 'message': 'Both inside and outside are hot'},
        })

        external = {'weather': {'temperature': 35}}
        triggered = self.engine.evaluate({'temperature': 30.0}, external_data=external)
        self.assertEqual(len(triggered), 1)

        external = {'weather': {'temperature': 25}}
        triggered = self.engine.evaluate({'temperature': 30.0}, external_data=external)
        self.assertEqual(len(triggered), 0)

    def test_compound_rule_missing_external_data(self):
        """Compound rule skips when external data is missing."""
        self.engine.create_rule({
            'id': 'smart_ac',
            'sensor': 'temperature',
            'condition': 'above',
            'threshold': 28.0,
            'external_condition': {
                'source_field': 'electricity.is_cheap_hour',
                'condition': 'equals',
                'threshold': True,
            },
            'action': {'type': 'ac', 'command': 'cool', 'target_temp': 24},
        })

        # No external data at all
        triggered = self.engine.evaluate({'temperature': 30.0}, external_data=None)
        self.assertEqual(len(triggered), 0)

    def test_rule_without_external_condition_ignores_external_data(self):
        """Rules without external_condition work even when external_data is provided."""
        self.engine.create_rule({
            'id': 'simple_rule',
            'sensor': 'temperature',
            'condition': 'above',
            'threshold': 28.0,
            'action': {'type': 'notify', 'message': 'Hot'},
        })

        external = {'electricity': {'is_cheap_hour': False}}
        triggered = self.engine.evaluate({'temperature': 30.0}, external_data=external)
        self.assertEqual(len(triggered), 1)

    def test_get_nested_helper(self):
        """Test dot-notation nested access helper."""
        data = {'weather': {'temperature': 18.5, 'wind': {'speed': 12}}}
        self.assertEqual(RuleEngine._get_nested(data, 'weather.temperature'), 18.5)
        self.assertEqual(RuleEngine._get_nested(data, 'weather.wind.speed'), 12)
        self.assertIsNone(RuleEngine._get_nested(data, 'weather.missing'))
        self.assertIsNone(RuleEngine._get_nested(data, 'nonexistent.path'))


if __name__ == '__main__':
    unittest.main()
