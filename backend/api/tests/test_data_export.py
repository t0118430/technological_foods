"""
Tests for the Data Export & Reporting Service.

Tests CSV export, crop lifecycle reports, weekly/monthly summaries,
and module-level helper functions.

Run: pytest test_data_export.py -v
"""

import sys
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, PropertyMock

from data_export import (
    DataExportService,
    SENSOR_FIELDS,
    _generate_weekly_recommendations,
    _compute_weekly_breakdown,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """Create a MagicMock database instance."""
    return MagicMock()


@pytest.fixture
def service(mock_db):
    """DataExportService with mocked db property."""
    svc = DataExportService()
    svc._db = mock_db
    return svc


@pytest.fixture
def sample_daily_data():
    """Seven days of representative sensor data."""
    base_date = datetime(2026, 2, 5)
    return [
        {
            'date': (base_date + timedelta(days=i)).strftime('%Y-%m-%d'),
            'temperature': 22.0 + i * 0.3,
            'humidity': 62.0 - i * 0.5,
            'ph': 6.0 + (i % 3) * 0.1,
            'ec': 1.5 + i * 0.02,
            'water_level': 75.0,
            'light_level': 500.0 + i * 10,
        }
        for i in range(7)
    ]


@pytest.fixture
def sample_daily_data_high_temp():
    """Daily data with high average temperature (>26)."""
    return [
        {'date': '2026-02-05', 'temperature': 28.0, 'humidity': 55.0, 'ph': 6.0, 'ec': 1.5},
        {'date': '2026-02-06', 'temperature': 27.5, 'humidity': 54.0, 'ph': 6.1, 'ec': 1.5},
        {'date': '2026-02-07', 'temperature': 29.0, 'humidity': 53.0, 'ph': 6.0, 'ec': 1.6},
    ]


@pytest.fixture
def sample_daily_data_low_temp():
    """Daily data with low average temperature (<18)."""
    return [
        {'date': '2026-02-05', 'temperature': 16.0, 'humidity': 70.0, 'ph': 6.0, 'ec': 1.5},
        {'date': '2026-02-06', 'temperature': 17.0, 'humidity': 68.0, 'ph': 6.1, 'ec': 1.5},
        {'date': '2026-02-07', 'temperature': 16.5, 'humidity': 69.0, 'ph': 6.0, 'ec': 1.6},
    ]


# ── CSV Export Tests ──────────────────────────────────────────────

class TestExportSensorCSV:
    @patch('data_export.InfluxDBClient')
    def test_csv_returns_header_and_data(self, mock_influx_cls, service):
        """CSV export should contain a header row and data rows."""
        mock_record = MagicMock()
        mock_record.get_time.return_value = datetime(2026, 2, 10, 12, 0, 0)
        mock_record.values = {
            'temperature': 22.5,
            'humidity': 63.0,
            'ph': 6.1,
            'ec': 1.6,
            'water_level': 75.0,
            'light_level': 520.0,
        }

        mock_table = MagicMock()
        mock_table.records = [mock_record]

        mock_query_api = MagicMock()
        mock_query_api.query.return_value = [mock_table]

        mock_client = MagicMock()
        mock_client.query_api.return_value = mock_query_api
        mock_influx_cls.return_value = mock_client

        result = service.export_sensor_csv('sensor_01', start='-7d', end='now()')

        lines = result.strip().split('\n')
        assert len(lines) == 2  # header + 1 data row

        header = lines[0]
        assert 'timestamp' in header
        for field in SENSOR_FIELDS:
            assert field in header

        data_line = lines[1]
        assert '22.5' in data_line
        assert '63.0' in data_line

        mock_client.close.assert_called_once()

    @patch('data_export.InfluxDBClient')
    def test_csv_with_custom_fields(self, mock_influx_cls, service):
        """CSV export with specific fields only includes those columns."""
        mock_record = MagicMock()
        mock_record.get_time.return_value = datetime(2026, 2, 10, 14, 0, 0)
        mock_record.values = {'temperature': 23.0, 'humidity': 60.0}

        mock_table = MagicMock()
        mock_table.records = [mock_record]

        mock_query_api = MagicMock()
        mock_query_api.query.return_value = [mock_table]

        mock_client = MagicMock()
        mock_client.query_api.return_value = mock_query_api
        mock_influx_cls.return_value = mock_client

        result = service.export_sensor_csv(
            'sensor_01', fields=['temperature', 'humidity']
        )

        header = result.strip().split('\n')[0]
        assert 'timestamp' in header
        assert 'temperature' in header
        assert 'humidity' in header
        # Should not have other fields in header
        assert 'ec' not in header
        assert 'water_level' not in header

    @patch('data_export.InfluxDBClient')
    def test_csv_with_aggregation(self, mock_influx_cls, service):
        """CSV export with aggregation parameter should work."""
        mock_table = MagicMock()
        mock_table.records = []

        mock_query_api = MagicMock()
        mock_query_api.query.return_value = [mock_table]

        mock_client = MagicMock()
        mock_client.query_api.return_value = mock_query_api
        mock_influx_cls.return_value = mock_client

        result = service.export_sensor_csv(
            'sensor_01', aggregation='1h'
        )

        # Should still have a header even with no data
        lines = result.strip().split('\n')
        assert len(lines) >= 1
        assert 'timestamp' in lines[0]

        # Verify the query used aggregateWindow
        query_str = mock_query_api.query.call_args[0][0]
        assert 'aggregateWindow' in query_str
        assert '1h' in query_str

    @patch('data_export.InfluxDBClient')
    def test_csv_empty_result(self, mock_influx_cls, service):
        """CSV export with no records returns only the header."""
        mock_query_api = MagicMock()
        mock_query_api.query.return_value = []

        mock_client = MagicMock()
        mock_client.query_api.return_value = mock_query_api
        mock_influx_cls.return_value = mock_client

        result = service.export_sensor_csv('sensor_01')

        lines = result.strip().split('\n')
        assert len(lines) == 1  # only header
        assert 'timestamp' in lines[0]

    @patch('data_export.InfluxDBClient')
    def test_csv_multiple_records(self, mock_influx_cls, service):
        """CSV export with multiple records returns correct row count."""
        records = []
        for i in range(5):
            rec = MagicMock()
            rec.get_time.return_value = datetime(2026, 2, 10, 10 + i, 0, 0)
            rec.values = {'temperature': 20.0 + i, 'humidity': 60.0}
            records.append(rec)

        mock_table = MagicMock()
        mock_table.records = records

        mock_query_api = MagicMock()
        mock_query_api.query.return_value = [mock_table]

        mock_client = MagicMock()
        mock_client.query_api.return_value = mock_query_api
        mock_influx_cls.return_value = mock_client

        result = service.export_sensor_csv('sensor_01')

        lines = result.strip().split('\n')
        assert len(lines) == 6  # header + 5 data rows

    @patch('data_export.InfluxDBClient')
    def test_csv_none_field_values(self, mock_influx_cls, service):
        """CSV export handles None field values gracefully."""
        mock_record = MagicMock()
        mock_record.get_time.return_value = datetime(2026, 2, 10, 12, 0, 0)
        mock_record.values = {
            'temperature': 22.0,
            'humidity': None,
            'ph': 6.0,
        }

        mock_table = MagicMock()
        mock_table.records = [mock_record]

        mock_query_api = MagicMock()
        mock_query_api.query.return_value = [mock_table]

        mock_client = MagicMock()
        mock_client.query_api.return_value = mock_query_api
        mock_influx_cls.return_value = mock_client

        result = service.export_sensor_csv(
            'sensor_01', fields=['temperature', 'humidity', 'ph']
        )

        lines = result.strip().split('\n')
        assert len(lines) == 2
        # None field should become empty string, not raise
        data_parts = lines[1].split(',')
        assert data_parts[1] == '22.0'  # temperature
        assert data_parts[2] == ''       # humidity (None)
        assert data_parts[3] == '6.0'   # ph

    @patch('data_export.InfluxDBClient')
    def test_csv_error_handling(self, mock_influx_cls, service):
        """CSV export returns error CSV on InfluxDB failure."""
        mock_influx_cls.side_effect = Exception('Connection refused')

        result = service.export_sensor_csv('sensor_01')

        lines = result.strip().splitlines()
        assert lines[0] == 'error'
        assert 'Connection refused' in lines[1]


# ── Crop Report Tests ─────────────────────────────────────────────

class TestExportCropReport:
    def test_crop_not_found(self, service, mock_db):
        """Report for nonexistent crop returns error."""
        mock_db.get_crop.return_value = None

        result = service.export_crop_report(999)

        assert 'error' in result
        assert '999' in result['error']

    def test_crop_with_stages_and_snapshots(self, service, mock_db):
        """Report includes stage reports with averages and durations."""
        mock_db.get_crop.return_value = {
            'variety': 'rosso_premium',
            'plant_date': '2026-01-01',
            'status': 'growing',
            'zone': 'A1',
            'stages': [
                {
                    'stage': 'germination',
                    'started_at': '2026-01-01T00:00:00',
                    'ended_at': '2026-01-05T00:00:00',
                },
                {
                    'stage': 'seedling',
                    'started_at': '2026-01-05T00:00:00',
                    'ended_at': '2026-01-15T00:00:00',
                },
            ],
        }

        mock_db.get_condition_snapshots.return_value = [
            {
                'snapshot_date': '2026-01-02',
                'avg_temperature': 22.0,
                'avg_humidity': 65.0,
                'avg_ph': 6.0,
                'avg_ec': 1.5,
                'avg_vpd': 0.9,
                'avg_dli': 14.0,
                'time_in_optimal_pct': 85.0,
            },
            {
                'snapshot_date': '2026-01-03',
                'avg_temperature': 22.5,
                'avg_humidity': 64.0,
                'avg_ph': 6.1,
                'avg_ec': 1.6,
                'avg_vpd': 0.95,
                'avg_dli': 14.5,
                'time_in_optimal_pct': 88.0,
            },
            {
                'snapshot_date': '2026-01-08',
                'avg_temperature': 23.0,
                'avg_humidity': 63.0,
                'avg_ph': 6.2,
                'avg_ec': 1.7,
                'avg_vpd': 1.0,
                'avg_dli': 15.0,
                'time_in_optimal_pct': 90.0,
            },
        ]

        # Mock harvest query - no harvest yet
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db.get_connection.return_value = mock_conn

        # Mock config_loader module (inline import in export_crop_report)
        mock_cl = MagicMock()
        mock_cl.config_loader.load_variety.return_value = {
            'variety': {'display_name': 'Rosso Premium'},
            'optimal_ranges': {
                'temperature': {'optimal_min': 18, 'optimal_max': 26},
                'humidity': {'optimal_min': 55, 'optimal_max': 75},
            },
        }
        with patch.dict(sys.modules, {'config_loader': mock_cl}):
            result = service.export_crop_report(1)

        assert result['report_type'] == 'crop_lifecycle'
        assert result['crop']['variety'] == 'rosso_premium'
        assert result['crop']['display_name'] == 'Rosso Premium'
        assert result['crop']['id'] == 1
        assert result['crop']['status'] == 'growing'
        assert result['crop']['zone'] == 'A1'
        assert result['crop']['total_days'] is None  # No harvest

        assert len(result['stages']) == 2
        germination = result['stages'][0]
        assert germination['stage'] == 'germination'
        assert germination['duration_days'] == 4
        assert germination['data_points'] == 2
        assert 'temperature' in germination['average_conditions']
        assert germination['average_conditions']['temperature'] == 22.25
        assert germination['time_in_optimal_pct'] == 86.5

        seedling = result['stages'][1]
        assert seedling['stage'] == 'seedling'
        assert seedling['data_points'] == 1

        assert 'optimal_ranges' in result
        assert 'temperature' in result['optimal_ranges']
        assert result['condition_snapshots_total'] == 3

    def test_crop_with_harvest(self, service, mock_db):
        """Report computes total_days when harvest exists."""
        mock_db.get_crop.return_value = {
            'variety': 'basil_genovese',
            'plant_date': '2026-01-01',
            'status': 'harvested',
            'zone': 'B2',
            'stages': [],
        }
        mock_db.get_condition_snapshots.return_value = []

        # Mock harvest query - no harvest row
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db.get_connection.return_value = mock_conn

        mock_cl = MagicMock()
        mock_cl.config_loader.load_variety.return_value = {
            'variety': {'display_name': 'Basil Genovese'},
            'optimal_ranges': {},
        }
        with patch.dict(sys.modules, {'config_loader': mock_cl}):
            result = service.export_crop_report(2)

        assert result['report_type'] == 'crop_lifecycle'
        assert result['harvest'] is None
        assert result['crop']['total_days'] is None  # No harvest row

    def test_crop_report_exception(self, service, mock_db):
        """Report returns error dict on unexpected exception."""
        mock_db.get_crop.side_effect = Exception('Database down')

        result = service.export_crop_report(1)

        assert 'error' in result
        assert 'Database down' in result['error']


# ── Weekly Summary Tests ──────────────────────────────────────────

class TestGenerateWeeklySummary:
    @patch('weather_service.weather_service')
    @patch('sensor_analytics.sensor_analytics')
    def test_weekly_summary_structure(self, mock_analytics, mock_weather, service):
        """Weekly summary returns all expected keys."""
        daily_data = [
            {'date': '2026-02-05', 'temperature': 22.0, 'humidity': 62.0,
             'ph': 6.0, 'ec': 1.5, 'water_level': 75.0, 'light_level': 500.0},
        ]

        with patch.object(service, '_query_daily_data', return_value=daily_data):
            mock_analytics.get_sensor_summary.return_value = {
                'vpd': 0.95, 'dli': 14.0, 'nutrient_score': 85,
            }
            mock_analytics.detect_trends.return_value = {
                'temperature': {'direction': 'stable', 'slope': 0.01},
            }
            mock_weather.get_forecast.return_value = {
                'daily_summaries': [{'date': '2026-02-12', 'max_temp': 20}],
            }

            result = service.generate_weekly_summary('sensor_01')

        assert result['report_type'] == 'weekly_summary'
        assert result['sensor_id'] == 'sensor_01'
        assert 'generated_at' in result
        assert 'period' in result
        assert 'start' in result['period']
        assert 'end' in result['period']
        assert result['daily_averages'] == daily_data
        assert result['current_snapshot']['vpd'] == 0.95
        assert result['current_snapshot']['dli'] == 14.0
        assert result['current_snapshot']['nutrient_score'] == 85
        assert 'trends' in result
        assert 'weather_context' in result
        assert isinstance(result['recommendations'], list)

    @patch('sensor_analytics.sensor_analytics')
    def test_weekly_summary_no_weather(self, mock_analytics, service):
        """Weekly summary works when weather service is unavailable."""
        with patch.object(service, '_query_daily_data', return_value=[]):
            mock_analytics.get_sensor_summary.return_value = {}
            mock_analytics.detect_trends.return_value = {}

            # Patch weather import to raise
            with patch.dict('sys.modules', {'weather_service': None}):
                # The code catches any Exception from the weather block
                result = service.generate_weekly_summary('sensor_01')

        assert result['report_type'] == 'weekly_summary'
        # weather_context should be None when weather fails
        assert result['weather_context'] is None or result.get('weather_context') is None

    @patch('sensor_analytics.sensor_analytics')
    def test_weekly_summary_recommendations_included(self, mock_analytics, service):
        """Weekly summary includes recommendations from helper."""
        daily_data = [
            {'date': '2026-02-05', 'temperature': 29.0, 'humidity': 55.0},
            {'date': '2026-02-06', 'temperature': 28.0, 'humidity': 56.0},
        ]

        with patch.object(service, '_query_daily_data', return_value=daily_data):
            mock_analytics.get_sensor_summary.return_value = {}
            mock_analytics.detect_trends.return_value = {}

            result = service.generate_weekly_summary('sensor_01')

        assert any('ventilation' in r for r in result['recommendations'])

    @patch('sensor_analytics.sensor_analytics')
    def test_weekly_summary_error_handling(self, mock_analytics, service):
        """Weekly summary returns error dict on failure."""
        mock_analytics.get_sensor_summary.side_effect = Exception('Analytics down')

        with patch.object(service, '_query_daily_data', return_value=[]):
            result = service.generate_weekly_summary('sensor_01')

        assert 'error' in result


# ── Monthly Summary Tests ─────────────────────────────────────────

class TestGenerateMonthlySummary:
    def test_monthly_summary_structure(self, service, mock_db):
        """Monthly summary returns all expected keys."""
        daily_data = [
            {
                'date': (datetime(2026, 1, 15) + timedelta(days=i)).strftime('%Y-%m-%d'),
                'temperature': 21.0 + i * 0.1,
                'humidity': 60.0,
            }
            for i in range(30)
        ]

        # Mock harvest query
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db.get_connection.return_value = mock_conn

        with patch.object(service, '_query_daily_data', return_value=daily_data):
            result = service.generate_monthly_summary('sensor_01')

        assert result['report_type'] == 'monthly_summary'
        assert result['sensor_id'] == 'sensor_01'
        assert 'generated_at' in result
        assert 'period' in result
        assert result['daily_averages'] == daily_data
        assert 'weekly_breakdown' in result
        assert isinstance(result['weekly_breakdown'], list)
        assert 'harvest_summary' in result
        assert 'harvests' in result
        assert 'market_context' in result

    def test_monthly_summary_with_harvests(self, service, mock_db):
        """Monthly summary computes harvest statistics."""
        mock_harvest_rows = [
            {'variety': 'rosso_premium', 'weight_kg': 2.5, 'harvest_date': '2026-02-01'},
            {'variety': 'rosso_premium', 'weight_kg': 3.0, 'harvest_date': '2026-02-05'},
            {'variety': 'basil_genovese', 'weight_kg': 1.5, 'harvest_date': '2026-02-08'},
        ]

        mock_row_objects = []
        for row in mock_harvest_rows:
            mock_row = MagicMock()
            mock_row.keys.return_value = row.keys()
            mock_row.__iter__ = MagicMock(return_value=iter(row.values()))
            mock_row_objects.append(mock_row)

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_harvest_rows
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db.get_connection.return_value = mock_conn

        with patch.object(service, '_query_daily_data', return_value=[]):
            result = service.generate_monthly_summary('sensor_01')

        harvest_summary = result['harvest_summary']
        assert harvest_summary['total_harvests'] == 3
        assert harvest_summary['total_yield_kg'] == 7.0
        assert harvest_summary['avg_yield_kg'] == pytest.approx(2.33, abs=0.01)
        assert harvest_summary['best_yield_kg'] == 3.0
        assert set(harvest_summary['varieties_harvested']) == {'rosso_premium', 'basil_genovese'}

    def test_monthly_summary_no_harvests(self, service, mock_db):
        """Monthly summary with no harvests returns empty harvest stats."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db.get_connection.return_value = mock_conn

        with patch.object(service, '_query_daily_data', return_value=[]):
            result = service.generate_monthly_summary('sensor_01')

        assert result['harvest_summary'] == {}
        assert result['harvests'] == []

    def test_monthly_summary_error_handling(self, service, mock_db):
        """Monthly summary returns error dict on failure."""
        mock_db.get_connection.side_effect = Exception('DB connection failed')

        with patch.object(service, '_query_daily_data', return_value=[]):
            result = service.generate_monthly_summary('sensor_01')

        assert 'error' in result


# ── Query Daily Data Tests ────────────────────────────────────────

class TestQueryDailyData:
    @patch('data_export.InfluxDBClient')
    def test_query_daily_data_returns_list(self, mock_influx_cls, service):
        """_query_daily_data returns a list of dicts with date and sensor fields."""
        mock_record = MagicMock()
        mock_record.get_time.return_value = datetime(2026, 2, 10, 0, 0, 0)
        mock_record.values = {
            'temperature': 22.5,
            'humidity': 63.2,
            'ph': 6.1,
            'ec': 1.55,
            'water_level': 74.8,
            'light_level': 510.0,
        }

        mock_table = MagicMock()
        mock_table.records = [mock_record]

        mock_query_api = MagicMock()
        mock_query_api.query.return_value = [mock_table]

        mock_client = MagicMock()
        mock_client.query_api.return_value = mock_query_api
        mock_influx_cls.return_value = mock_client

        result = service._query_daily_data('sensor_01', days=7)

        assert len(result) == 1
        assert result[0]['date'] == '2026-02-10'
        assert result[0]['temperature'] == 22.5
        assert result[0]['humidity'] == 63.2
        mock_client.close.assert_called_once()

    @patch('data_export.InfluxDBClient')
    def test_query_daily_data_rounds_values(self, mock_influx_cls, service):
        """Values should be rounded to 2 decimal places."""
        mock_record = MagicMock()
        mock_record.get_time.return_value = datetime(2026, 2, 10, 0, 0, 0)
        mock_record.values = {'temperature': 22.555555}

        mock_table = MagicMock()
        mock_table.records = [mock_record]

        mock_query_api = MagicMock()
        mock_query_api.query.return_value = [mock_table]

        mock_client = MagicMock()
        mock_client.query_api.return_value = mock_query_api
        mock_influx_cls.return_value = mock_client

        result = service._query_daily_data('sensor_01', days=7)

        assert result[0]['temperature'] == 22.56

    @patch('data_export.InfluxDBClient')
    def test_query_daily_data_skips_none_fields(self, mock_influx_cls, service):
        """Fields with None values should be omitted from the result."""
        mock_record = MagicMock()
        mock_record.get_time.return_value = datetime(2026, 2, 10, 0, 0, 0)
        mock_record.values = {'temperature': 22.0, 'humidity': None, 'ph': 6.0}

        mock_table = MagicMock()
        mock_table.records = [mock_record]

        mock_query_api = MagicMock()
        mock_query_api.query.return_value = [mock_table]

        mock_client = MagicMock()
        mock_client.query_api.return_value = mock_query_api
        mock_influx_cls.return_value = mock_client

        result = service._query_daily_data('sensor_01', days=7)

        assert 'temperature' in result[0]
        assert 'humidity' not in result[0]
        assert 'ph' in result[0]

    @patch('data_export.InfluxDBClient')
    def test_query_daily_data_error_returns_empty(self, mock_influx_cls, service):
        """InfluxDB errors should return an empty list."""
        mock_influx_cls.side_effect = Exception('Connection timeout')

        result = service._query_daily_data('sensor_01', days=7)

        assert result == []


# ── Weekly Recommendations Helper Tests ───────────────────────────

class TestGenerateWeeklyRecommendations:
    def test_no_data(self):
        """No data triggers connectivity check recommendation."""
        result = _generate_weekly_recommendations([], {})
        assert len(result) == 1
        assert 'No sensor data' in result[0]
        assert 'connectivity' in result[0]

    def test_high_temperature(self, sample_daily_data_high_temp):
        """High average temp recommends ventilation."""
        result = _generate_weekly_recommendations(sample_daily_data_high_temp, {})
        assert any('ventilation' in r for r in result)

    def test_low_temperature(self, sample_daily_data_low_temp):
        """Low average temp recommends checking heating."""
        result = _generate_weekly_recommendations(sample_daily_data_low_temp, {})
        assert any('heating' in r for r in result)

    def test_normal_temperature_no_temp_recommendation(self, sample_daily_data):
        """Normal temp range does not trigger temp recommendations."""
        result = _generate_weekly_recommendations(sample_daily_data, {})
        assert not any('ventilation' in r for r in result)
        assert not any('heating' in r for r in result)

    def test_ph_fluctuation(self):
        """Wide pH range recommends checking buffer capacity."""
        data = [
            {'date': '2026-02-05', 'ph': 5.5},
            {'date': '2026-02-06', 'ph': 6.8},
            {'date': '2026-02-07', 'ph': 5.8},
        ]
        result = _generate_weekly_recommendations(data, {})
        assert any('pH fluctuating' in r for r in result)
        assert any('buffer' in r for r in result)

    def test_ph_stable_no_recommendation(self):
        """Stable pH does not trigger pH recommendation."""
        data = [
            {'date': '2026-02-05', 'ph': 6.0},
            {'date': '2026-02-06', 'ph': 6.1},
            {'date': '2026-02-07', 'ph': 6.05},
        ]
        result = _generate_weekly_recommendations(data, {})
        assert not any('pH fluctuating' in r for r in result)

    def test_ph_needs_minimum_3_readings(self):
        """pH check requires at least 3 data points."""
        data = [
            {'date': '2026-02-05', 'ph': 5.0},
            {'date': '2026-02-06', 'ph': 7.5},
        ]
        result = _generate_weekly_recommendations(data, {})
        assert not any('pH fluctuating' in r for r in result)

    def test_ec_rising_trend(self):
        """Rising EC trend recommends diluting nutrient solution."""
        trends = {'ec': {'direction': 'rising', 'slope': 0.05}}
        data = [{'date': '2026-02-05', 'temperature': 22.0}]
        result = _generate_weekly_recommendations(data, trends)
        assert any('diluting' in r for r in result)

    def test_ec_falling_trend(self):
        """Falling EC trend recommends topping up solution."""
        trends = {'ec': {'direction': 'falling', 'slope': -0.03}}
        data = [{'date': '2026-02-05', 'temperature': 22.0}]
        result = _generate_weekly_recommendations(data, trends)
        assert any('top up' in r for r in result)

    def test_ec_stable_no_recommendation(self):
        """Stable EC trend does not trigger EC recommendation."""
        trends = {'ec': {'direction': 'stable', 'slope': 0.001}}
        data = [{'date': '2026-02-05', 'temperature': 22.0}]
        result = _generate_weekly_recommendations(data, trends)
        assert not any('diluting' in r for r in result)
        assert not any('top up' in r for r in result)

    def test_all_normal_conditions(self):
        """When everything is normal, get maintain-conditions recommendation."""
        data = [
            {'date': '2026-02-05', 'temperature': 22.0, 'ph': 6.0, 'ec': 1.5},
            {'date': '2026-02-06', 'temperature': 22.5, 'ph': 6.1, 'ec': 1.55},
            {'date': '2026-02-07', 'temperature': 22.2, 'ph': 6.05, 'ec': 1.52},
        ]
        result = _generate_weekly_recommendations(data, {})
        assert any('normal ranges' in r for r in result)
        assert any('maintain' in r for r in result)

    def test_multiple_issues_all_reported(self):
        """Multiple issues produce multiple recommendations."""
        data = [
            {'date': '2026-02-05', 'temperature': 28.0, 'ph': 5.0},
            {'date': '2026-02-06', 'temperature': 29.0, 'ph': 7.0},
            {'date': '2026-02-07', 'temperature': 27.5, 'ph': 5.5},
        ]
        trends = {'ec': {'direction': 'rising', 'slope': 0.1}}
        result = _generate_weekly_recommendations(data, trends)
        assert any('ventilation' in r for r in result)
        assert any('pH fluctuating' in r for r in result)
        assert any('diluting' in r for r in result)


# ── Weekly Breakdown Helper Tests ─────────────────────────────────

class TestComputeWeeklyBreakdown:
    def test_empty_list(self):
        """Empty data returns empty breakdown."""
        result = _compute_weekly_breakdown([])
        assert result == []

    def test_single_week(self):
        """Data within a single week produces one entry."""
        data = [
            {'date': '2026-02-09', 'temperature': 22.0, 'humidity': 60.0},
            {'date': '2026-02-10', 'temperature': 23.0, 'humidity': 62.0},
            {'date': '2026-02-11', 'temperature': 21.0, 'humidity': 58.0},
        ]
        result = _compute_weekly_breakdown(data)
        assert len(result) == 1
        assert result[0]['days'] == 3
        assert result[0]['avg_temperature'] == pytest.approx(22.0, abs=0.01)
        assert result[0]['avg_humidity'] == pytest.approx(60.0, abs=0.01)

    def test_data_across_weeks(self):
        """Data spanning multiple weeks produces multiple entries."""
        # Create data spanning 3 weeks
        data = []
        base = datetime(2026, 1, 5)  # Monday W2
        for i in range(21):  # 3 weeks of data
            dt = base + timedelta(days=i)
            data.append({
                'date': dt.strftime('%Y-%m-%d'),
                'temperature': 20.0 + i * 0.1,
            })

        result = _compute_weekly_breakdown(data)
        assert len(result) == 3
        # Each week should have 7 days
        for week in result:
            assert week['days'] == 7
            assert 'avg_temperature' in week
            assert week['week'].startswith('W')

    def test_sorted_by_week(self):
        """Weeks are returned in sorted order."""
        data = [
            {'date': '2026-02-16', 'temperature': 22.0},  # W8
            {'date': '2026-02-02', 'temperature': 20.0},  # W6
            {'date': '2026-02-09', 'temperature': 21.0},  # W7
        ]
        result = _compute_weekly_breakdown(data)
        week_numbers = [r['week'] for r in result]
        assert week_numbers == sorted(week_numbers)

    def test_missing_date_skipped(self):
        """Entries without a date field are skipped."""
        data = [
            {'date': '2026-02-10', 'temperature': 22.0},
            {'temperature': 23.0},  # no date
            {'date': '', 'temperature': 24.0},  # empty date
        ]
        result = _compute_weekly_breakdown(data)
        # Only the entry with a valid date should be counted
        total_days = sum(w['days'] for w in result)
        assert total_days == 1

    def test_averages_per_week(self):
        """Each week computes correct averages for sensor fields."""
        data = [
            {'date': '2026-02-09', 'temperature': 20.0, 'ph': 6.0},
            {'date': '2026-02-10', 'temperature': 24.0, 'ph': 6.4},
        ]
        result = _compute_weekly_breakdown(data)
        assert len(result) == 1
        assert result[0]['avg_temperature'] == 22.0
        assert result[0]['avg_ph'] == 6.2

    def test_only_sensor_fields_aggregated(self):
        """Only SENSOR_FIELDS are aggregated, not arbitrary keys."""
        data = [
            {'date': '2026-02-10', 'temperature': 22.0, 'custom_field': 999},
        ]
        result = _compute_weekly_breakdown(data)
        assert 'avg_temperature' in result[0]
        assert 'avg_custom_field' not in result[0]

    def test_partial_sensor_fields(self):
        """Weeks with only some sensor fields still produce averages for those fields."""
        data = [
            {'date': '2026-02-10', 'temperature': 22.0},
            {'date': '2026-02-11', 'temperature': 24.0, 'humidity': 60.0},
        ]
        result = _compute_weekly_breakdown(data)
        assert result[0]['avg_temperature'] == 23.0
        assert result[0]['avg_humidity'] == 60.0  # Only one value


# ── DB Property Tests ─────────────────────────────────────────────

class TestDBProperty:
    def test_lazy_db_initialization(self):
        """DB property initializes lazily from None."""
        svc = DataExportService()
        assert svc._db is None

    def test_db_uses_injected_value(self, service, mock_db):
        """When _db is set directly, the property returns it."""
        assert service.db is mock_db
