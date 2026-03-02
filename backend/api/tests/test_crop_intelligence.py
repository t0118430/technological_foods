"""
Tests for Crop Intelligence Service.

Tests condition-harvest correlation, growth optimization recommendations,
yield prediction, crop health scoring, and helper functions.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from contextlib import contextmanager

from crop_intelligence import (
    CropIntelligence,
    _format_batch,
    _generate_correlation_insights,
    _range_pct,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def ci():
    """CropIntelligence instance with mocked db and config_loader."""
    instance = CropIntelligence()
    instance._db = MagicMock()
    instance._config_loader = MagicMock()
    return instance


@pytest.fixture
def mock_conn():
    """Create a mock connection with a cursor that returns sqlite3.Row-like dicts."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


@pytest.fixture
def sample_variety_config():
    """Sample variety config as returned by config_loader.load_variety()."""
    return {
        'optimal_ranges': {
            'temperature': {
                'optimal_min': 20.0,
                'optimal_max': 24.0,
                'critical_min': 15.0,
                'critical_max': 30.0,
            },
            'humidity': {
                'optimal_min': 55.0,
                'optimal_max': 75.0,
                'critical_min': 40.0,
                'critical_max': 90.0,
            },
            'ph': {
                'optimal_min': 5.8,
                'optimal_max': 6.5,
                'critical_min': 5.0,
                'critical_max': 7.5,
            },
            'ec': {
                'optimal_min': 1.2,
                'optimal_max': 2.0,
                'critical_min': 0.5,
                'critical_max': 3.0,
            },
        },
        'growth_stages': {
            'seedling': {'ec_range': '0.8-1.2', 'duration_days': 7},
            'vegetative': {'ec_range': '1.2-1.8', 'duration_days': 14},
            'maturity': {'ec_range': '1.5-2.0', 'duration_days': 7},
        },
    }


def _make_row_dict(data):
    """Create a mock sqlite3.Row-like object that supports dict() and key access."""
    row = MagicMock()
    row.keys.return_value = list(data.keys())
    row.__getitem__ = lambda self, key: data[key]
    row.__contains__ = lambda self, key: key in data
    row.__iter__ = lambda self: iter(data)

    # Support dict(row) via iteration over keys
    def _dict_side_effect():
        return data.copy()
    # Make dict(row) work: MagicMock with __iter__ over key-value pairs
    row.__iter__ = lambda self: iter(data.keys())
    row.keys = lambda: data.keys()

    # Patch so dict(row) works properly
    type(row).__iter__ = lambda self: iter(data.keys())
    type(row).__getitem__ = lambda self, key: data[key]
    type(row).__contains__ = lambda self, key: key in data

    return row


# ── Helper Function Tests ─────────────────────────────────────────

class TestRangePct:
    """Test _range_pct helper."""

    def test_within_optimal_returns_1(self):
        """Value within optimal range should return 1.0."""
        assert _range_pct(22.0, 20.0, 24.0, 15.0, 30.0) == 1.0

    def test_at_optimal_min_boundary(self):
        """Value exactly at optimal_min should return 1.0."""
        assert _range_pct(20.0, 20.0, 24.0, 15.0, 30.0) == 1.0

    def test_at_optimal_max_boundary(self):
        """Value exactly at optimal_max should return 1.0."""
        assert _range_pct(24.0, 20.0, 24.0, 15.0, 30.0) == 1.0

    def test_below_critical_min_returns_0(self):
        """Value below critical_min should return 0.0."""
        assert _range_pct(10.0, 20.0, 24.0, 15.0, 30.0) == 0.0

    def test_above_critical_max_returns_0(self):
        """Value above critical_max should return 0.0."""
        assert _range_pct(35.0, 20.0, 24.0, 15.0, 30.0) == 0.0

    def test_between_critical_min_and_optimal_min(self):
        """Value between critical_min and optimal_min returns partial score (0..0.7)."""
        result = _range_pct(17.5, 20.0, 24.0, 15.0, 30.0)
        assert 0.0 < result < 0.7
        # 17.5 is halfway between 15.0 and 20.0 => (17.5 - 15) / (20 - 15) * 0.7 = 0.35
        assert abs(result - 0.35) < 0.01

    def test_between_optimal_max_and_critical_max(self):
        """Value between optimal_max and critical_max returns partial score (0..0.7)."""
        result = _range_pct(27.0, 20.0, 24.0, 15.0, 30.0)
        assert 0.0 < result < 0.7
        # 27.0: (30 - 27) / (30 - 24) * 0.7 = 0.5 * 0.7 = 0.35
        assert abs(result - 0.35) < 0.01

    def test_at_critical_min_boundary(self):
        """Value exactly at critical_min should return 0.0 (bottom of warning range)."""
        result = _range_pct(15.0, 20.0, 24.0, 15.0, 30.0)
        # (15 - 15) / (20 - 15) * 0.7 = 0
        assert result == 0.0

    def test_at_critical_max_boundary(self):
        """Value exactly at critical_max should return 0.0 (top of warning range)."""
        result = _range_pct(30.0, 20.0, 24.0, 15.0, 30.0)
        # (30 - 30) / (30 - 24) * 0.7 = 0
        assert result == 0.0


class TestFormatBatch:
    """Test _format_batch helper."""

    def test_full_batch(self):
        """Full batch dict should format correctly."""
        batch = {
            'crop_id': 1,
            'plant_date': '2025-01-01',
            'weight_kg': 2.5,
            'quality_grade': 'premium',
            'avg_temp': 22.0,
            'avg_humidity': 65.0,
            'avg_ph': 6.1,
            'avg_ec': 1.6,
            'avg_vpd': 0.95,
            'avg_dli': 14.0,
            'avg_optimal_pct': 85.0,
        }
        result = _format_batch(batch)

        assert result['crop_id'] == 1
        assert result['plant_date'] == '2025-01-01'
        assert result['weight_kg'] == 2.5
        assert result['quality_grade'] == 'premium'
        assert result['conditions']['avg_temperature'] == 22.0
        assert result['conditions']['avg_humidity'] == 65.0
        assert result['conditions']['avg_ph'] == 6.1
        assert result['conditions']['avg_ec'] == 1.6
        assert result['conditions']['avg_vpd'] == 0.95
        assert result['conditions']['avg_dli'] == 14.0
        assert result['conditions']['time_in_optimal_pct'] == 85.0

    def test_partial_batch(self):
        """Batch with missing fields should return None for missing keys."""
        batch = {'crop_id': 2, 'weight_kg': 1.0}
        result = _format_batch(batch)

        assert result['crop_id'] == 2
        assert result['weight_kg'] == 1.0
        assert result['plant_date'] is None
        assert result['quality_grade'] is None
        assert result['conditions']['avg_temperature'] is None

    def test_empty_batch(self):
        """Empty batch dict should return all None values."""
        result = _format_batch({})
        assert result['crop_id'] is None
        assert result['conditions']['avg_temperature'] is None


class TestGenerateCorrelationInsights:
    """Test _generate_correlation_insights helper."""

    def test_single_batch_returns_not_enough_data(self):
        """Fewer than 2 batches should yield 'need more batches' insight."""
        batches = [{'avg_temp': 22.0, 'avg_optimal_pct': 80.0}]
        insights = _generate_correlation_insights(batches, 'rosso_premium')
        assert len(insights) == 1
        assert 'more harvested batches' in insights[0].lower()

    def test_empty_batches(self):
        """Empty batch list should yield 'need more batches' insight."""
        insights = _generate_correlation_insights([], 'rosso_premium')
        assert len(insights) == 1
        assert 'more harvested batches' in insights[0].lower()

    def test_temperature_insight_warmer(self):
        """Should generate insight when best batch grew warmer."""
        batches = [
            {'avg_temp': 24.0, 'avg_optimal_pct': None, 'avg_vpd': None},
            {'avg_temp': 20.0, 'avg_optimal_pct': None, 'avg_vpd': None},
        ]
        insights = _generate_correlation_insights(batches, 'rosso_premium')
        temp_insights = [i for i in insights if 'warmer' in i]
        assert len(temp_insights) == 1
        assert '4.0' in temp_insights[0]

    def test_temperature_insight_cooler(self):
        """Should generate insight when best batch grew cooler."""
        batches = [
            {'avg_temp': 20.0, 'avg_optimal_pct': None, 'avg_vpd': None},
            {'avg_temp': 24.0, 'avg_optimal_pct': None, 'avg_vpd': None},
        ]
        insights = _generate_correlation_insights(batches, 'rosso_premium')
        temp_insights = [i for i in insights if 'cooler' in i]
        assert len(temp_insights) == 1

    def test_no_temp_insight_when_diff_small(self):
        """Should not generate temperature insight when diff < 1 degree."""
        batches = [
            {'avg_temp': 22.5, 'avg_optimal_pct': None, 'avg_vpd': None},
            {'avg_temp': 22.0, 'avg_optimal_pct': None, 'avg_vpd': None},
        ]
        insights = _generate_correlation_insights(batches, 'rosso_premium')
        temp_insights = [i for i in insights if 'warmer' in i or 'cooler' in i]
        assert len(temp_insights) == 0

    def test_optimal_time_insight(self):
        """Should generate insight about time in optimal conditions."""
        batches = [
            {'avg_temp': 22.0, 'avg_optimal_pct': 90.0, 'avg_vpd': None},
            {'avg_temp': 22.0, 'avg_optimal_pct': 60.0, 'avg_vpd': None},
        ]
        insights = _generate_correlation_insights(batches, 'rosso_premium')
        optimal_insights = [i for i in insights if 'optimal conditions' in i]
        assert len(optimal_insights) == 1


# ── Condition-Harvest Correlation Tests ───────────────────────────

class TestGetConditionHarvestCorrelation:
    """Test get_condition_harvest_correlation method."""

    def test_no_data_returns_insufficient(self, ci, mock_conn):
        """No harvested crops should return insufficient_data status."""
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        result = ci.get_condition_harvest_correlation('rosso_premium')

        assert result['variety'] == 'rosso_premium'
        assert result['status'] == 'insufficient_data'
        assert result['batches_analyzed'] == 0

    def test_with_data_returns_correlation(self, ci, mock_conn):
        """With harvest data, should return full correlation result."""
        conn, cursor = mock_conn

        row1 = _make_row_dict({
            'crop_id': 1,
            'plant_date': '2025-01-01',
            'weight_kg': 3.0,
            'quality_grade': 'premium',
            'market_value': 15.0,
            'avg_temp': 22.5,
            'avg_humidity': 65.0,
            'avg_ph': 6.1,
            'avg_ec': 1.6,
            'avg_vpd': 0.95,
            'avg_dli': 14.0,
            'avg_optimal_pct': 85.0,
        })
        row2 = _make_row_dict({
            'crop_id': 2,
            'plant_date': '2025-02-01',
            'weight_kg': 2.0,
            'quality_grade': 'standard',
            'market_value': 8.0,
            'avg_temp': 20.0,
            'avg_humidity': 60.0,
            'avg_ph': 5.9,
            'avg_ec': 1.4,
            'avg_vpd': 1.1,
            'avg_dli': 12.0,
            'avg_optimal_pct': 65.0,
        })
        cursor.fetchall.return_value = [row1, row2]

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        result = ci.get_condition_harvest_correlation('rosso_premium')

        assert result['variety'] == 'rosso_premium'
        assert result['batches_analyzed'] == 2
        assert 'yield_statistics' in result
        assert result['yield_statistics']['avg_yield_kg'] == 2.5
        assert result['yield_statistics']['best_yield_kg'] == 3.0
        assert result['yield_statistics']['worst_yield_kg'] == 2.0
        assert 'average_conditions' in result
        assert result['best_batch'] is not None
        assert result['best_batch']['crop_id'] == 1
        assert result['worst_batch'] is not None
        assert result['worst_batch']['crop_id'] == 2
        assert 'insights' in result

    def test_single_batch_no_worst(self, ci, mock_conn):
        """Single batch should have best_batch but worst_batch should be None."""
        conn, cursor = mock_conn

        row = _make_row_dict({
            'crop_id': 1,
            'plant_date': '2025-01-01',
            'weight_kg': 2.5,
            'quality_grade': 'premium',
            'market_value': 12.0,
            'avg_temp': 22.0,
            'avg_humidity': 65.0,
            'avg_ph': 6.0,
            'avg_ec': 1.5,
            'avg_vpd': 0.9,
            'avg_dli': 13.0,
            'avg_optimal_pct': 80.0,
        })
        cursor.fetchall.return_value = [row]

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        result = ci.get_condition_harvest_correlation('rosso_premium')

        assert result['batches_analyzed'] == 1
        assert result['best_batch'] is not None
        assert result['worst_batch'] is None

    def test_exception_returns_error(self, ci):
        """Database exceptions should return error dict."""
        @contextmanager
        def failing_conn():
            raise RuntimeError("DB failure")
            yield  # noqa - unreachable but needed for generator

        ci._db.get_connection = failing_conn

        result = ci.get_condition_harvest_correlation('rosso_premium')

        assert result['variety'] == 'rosso_premium'
        assert 'error' in result


# ── Growth Optimization Recommendations Tests ─────────────────────

class TestGetGrowthOptimizationRecommendations:
    """Test get_growth_optimization_recommendations method."""

    def test_crop_not_found(self, ci):
        """Non-existent crop should return error."""
        ci._db.get_crop.return_value = None

        result = ci.get_growth_optimization_recommendations(999)

        assert 'error' in result
        assert '999' in result['error']

    def test_crop_with_recommendations(self, ci, mock_conn, sample_variety_config):
        """Crop with out-of-range conditions should produce recommendations."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {
            'variety': 'rosso_premium',
            'status': 'active',
            'stages': [
                {'stage': 'seedling', 'started_at': '2025-01-01T00:00:00', 'ended_at': '2025-01-07T00:00:00'},
                {'stage': 'vegetative', 'started_at': '2025-01-07T00:00:00', 'ended_at': None},
            ],
        }

        ci._config_loader.load_variety.return_value = sample_variety_config

        # Latest snapshot with temperature too low, EC too high
        snapshot = _make_row_dict({
            'avg_temperature': 18.0,  # Below optimal_min 20.0
            'avg_humidity': 65.0,     # Within optimal
            'avg_ph': 6.1,           # Within optimal
            'avg_ec': 2.5,           # Above optimal_max 2.0
            'avg_vpd': 0.95,
            'avg_dli': 14.0,
            'time_in_optimal_pct': 60.0,
        })
        cursor.fetchone.return_value = snapshot

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        # Mock the correlation call used for historical best
        with patch.object(ci, 'get_condition_harvest_correlation', return_value={
            'average_conditions': {'avg_temp': 22.0},
        }):
            result = ci.get_growth_optimization_recommendations(1)

        assert result['crop_id'] == 1
        assert result['variety'] == 'rosso_premium'
        assert result['current_stage'] == 'vegetative'
        assert result['recommendation_count'] >= 2  # temperature + ec at least

        # Check temperature recommendation exists
        temp_recs = [r for r in result['recommendations'] if r['parameter'] == 'temperature']
        assert len(temp_recs) == 1
        assert 'Increase' in temp_recs[0]['action']

        # Check EC recommendation exists
        ec_recs = [r for r in result['recommendations'] if r['parameter'] == 'ec']
        assert len(ec_recs) == 1
        assert 'Decrease' in ec_recs[0]['action']

    def test_crop_in_optimal_conditions(self, ci, mock_conn, sample_variety_config):
        """Crop within all optimal ranges should have no recommendations."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {
            'variety': 'rosso_premium',
            'status': 'active',
            'stages': [
                {'stage': 'vegetative', 'started_at': '2025-01-07T00:00:00', 'ended_at': None},
            ],
        }

        ci._config_loader.load_variety.return_value = sample_variety_config

        snapshot = _make_row_dict({
            'avg_temperature': 22.0,
            'avg_humidity': 65.0,
            'avg_ph': 6.1,
            'avg_ec': 1.5,
            'avg_vpd': 0.95,
            'avg_dli': 14.0,
            'time_in_optimal_pct': 90.0,
        })
        cursor.fetchone.return_value = snapshot

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        with patch.object(ci, 'get_condition_harvest_correlation', return_value={
            'average_conditions': {},
        }):
            result = ci.get_growth_optimization_recommendations(1)

        assert result['recommendation_count'] == 0
        assert result['recommendations'] == []

    def test_no_snapshot_no_recommendations(self, ci, mock_conn, sample_variety_config):
        """No condition snapshot should yield empty recommendations."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {
            'variety': 'rosso_premium',
            'status': 'active',
            'stages': [],
        }

        ci._config_loader.load_variety.return_value = sample_variety_config
        cursor.fetchone.return_value = None

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        with patch.object(ci, 'get_condition_harvest_correlation', return_value={
            'average_conditions': {},
        }):
            result = ci.get_growth_optimization_recommendations(1)

        assert result['recommendation_count'] == 0

    def test_critical_priority_below_critical_min(self, ci, mock_conn, sample_variety_config):
        """Value below critical_min should yield high priority recommendation."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {
            'variety': 'rosso_premium',
            'status': 'active',
            'stages': [
                {'stage': 'vegetative', 'started_at': '2025-01-07T00:00:00', 'ended_at': None},
            ],
        }

        ci._config_loader.load_variety.return_value = sample_variety_config

        snapshot = _make_row_dict({
            'avg_temperature': 12.0,  # Below critical_min 15.0
            'avg_humidity': 65.0,
            'avg_ph': 6.1,
            'avg_ec': 1.5,
            'avg_vpd': 0.95,
            'avg_dli': 14.0,
            'time_in_optimal_pct': 30.0,
        })
        cursor.fetchone.return_value = snapshot

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        with patch.object(ci, 'get_condition_harvest_correlation', return_value={
            'average_conditions': {},
        }):
            result = ci.get_growth_optimization_recommendations(1)

        temp_recs = [r for r in result['recommendations'] if r['parameter'] == 'temperature']
        assert len(temp_recs) == 1
        assert temp_recs[0]['priority'] == 'high'

    def test_stage_specific_ec_recommendation(self, ci, mock_conn, sample_variety_config):
        """EC outside stage-specific range should generate stage-specific rec."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {
            'variety': 'rosso_premium',
            'status': 'active',
            'stages': [
                {'stage': 'seedling', 'started_at': '2025-01-01T00:00:00', 'ended_at': None},
            ],
        }

        ci._config_loader.load_variety.return_value = sample_variety_config

        # EC 1.5 is within general optimal (1.2-2.0) but outside seedling range (0.8-1.2)
        snapshot = _make_row_dict({
            'avg_temperature': 22.0,
            'avg_humidity': 65.0,
            'avg_ph': 6.1,
            'avg_ec': 1.5,
            'avg_vpd': 0.95,
            'avg_dli': 14.0,
            'time_in_optimal_pct': 80.0,
        })
        cursor.fetchone.return_value = snapshot

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        with patch.object(ci, 'get_condition_harvest_correlation', return_value={
            'average_conditions': {},
        }):
            result = ci.get_growth_optimization_recommendations(1)

        stage_ec_recs = [r for r in result['recommendations'] if r['parameter'] == 'ec_stage_specific']
        assert len(stage_ec_recs) == 1
        assert 'seedling' in stage_ec_recs[0]['action']


# ── Yield Prediction Tests ────────────────────────────────────────

class TestPredictYield:
    """Test predict_yield method."""

    def test_crop_not_found(self, ci):
        """Non-existent crop should return error."""
        ci._db.get_crop.return_value = None

        result = ci.predict_yield(999)

        assert 'error' in result
        assert '999' in result['error']

    def test_no_historical_data(self, ci, mock_conn):
        """No historical harvests should return insufficient_data."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {'variety': 'rosso_premium'}
        cursor.fetchall.return_value = []

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        result = ci.predict_yield(1)

        assert result['crop_id'] == 1
        assert result['variety'] == 'rosso_premium'
        assert result['status'] == 'insufficient_data'

    def test_with_historical_data_no_conditions(self, ci, mock_conn):
        """Historical data but no condition snapshots should predict with factor 1.0."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {'variety': 'rosso_premium'}

        # First call: fetchall for historical harvests
        historical = [
            (2.0, 'premium'),
            (2.5, 'standard'),
            (3.0, 'premium'),
        ]
        # Second call: fetchone for condition snapshots (None = no data)
        cursor.fetchall.return_value = historical
        cursor.fetchone.return_value = (None,)

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        result = ci.predict_yield(1)

        assert result['crop_id'] == 1
        assert result['variety'] == 'rosso_premium'
        assert result['historical_avg_yield_kg'] == 2.5
        assert result['adjustment_factor'] == 1.0
        assert result['predicted_yield_kg'] == 2.5
        assert result['confidence'] == 'low'  # 3 batches < 5
        assert result['predicted_quality'] == 'premium'  # most common
        assert result['historical_batches'] == 3

    def test_with_conditions_adjustment(self, ci, mock_conn):
        """Condition data should adjust the predicted yield."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {'variety': 'rosso_premium'}

        historical = [(2.0, 'standard')] * 10
        cursor.fetchall.return_value = historical
        # avg_optimal_pct = 75.0 => factor = 0.7 + (75/100)*0.4 = 0.7 + 0.3 = 1.0
        cursor.fetchone.return_value = (75.0,)

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        result = ci.predict_yield(1)

        assert result['adjustment_factor'] == 1.0
        assert result['optimal_time_percent'] == 75.0
        assert result['confidence'] == 'high'  # 10 batches >= 10

    def test_high_optimal_boosts_yield(self, ci, mock_conn):
        """100% optimal time should boost yield by 1.1x."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {'variety': 'rosso_premium'}

        historical = [(2.0, 'standard')] * 6
        cursor.fetchall.return_value = historical
        cursor.fetchone.return_value = (100.0,)

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        result = ci.predict_yield(1)

        # factor = 0.7 + (100/100) * 0.4 = 1.1
        assert result['adjustment_factor'] == 1.1
        assert result['predicted_yield_kg'] == round(2.0 * 1.1, 2)
        assert result['confidence'] == 'medium'  # 6 batches: 5 <= n < 10

    def test_low_optimal_reduces_yield(self, ci, mock_conn):
        """Low optimal time should reduce yield below base."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {'variety': 'rosso_premium'}

        historical = [(2.0, 'standard')] * 5
        cursor.fetchall.return_value = historical
        # Use 25.0% (non-zero to avoid falsy check in source)
        cursor.fetchone.return_value = (25.0,)

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        result = ci.predict_yield(1)

        # factor = 0.7 + (25/100) * 0.4 = 0.7 + 0.1 = 0.8
        assert result['adjustment_factor'] == 0.8
        assert result['predicted_yield_kg'] == round(2.0 * 0.8, 2)

    def test_zero_optimal_treated_as_no_data(self, ci, mock_conn):
        """0% optimal time is falsy so treated as no condition data (factor=1.0)."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {'variety': 'rosso_premium'}

        historical = [(2.0, 'standard')] * 5
        cursor.fetchall.return_value = historical
        cursor.fetchone.return_value = (0.0,)

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        result = ci.predict_yield(1)

        # 0.0 is falsy, so avg_optimal_pct becomes None => factor stays 1.0
        assert result['adjustment_factor'] == 1.0
        assert result['optimal_time_percent'] is None

    def test_exception_returns_error(self, ci):
        """Exceptions should be caught and return error dict."""
        ci._db.get_crop.side_effect = RuntimeError("DB error")

        result = ci.predict_yield(1)

        assert result['crop_id'] == 1
        assert 'error' in result


# ── Crop Health Score Tests ───────────────────────────────────────

class TestGetCropHealthScore:
    """Test get_crop_health_score method."""

    def test_crop_not_found(self, ci):
        """Non-existent crop should return error."""
        ci._db.get_crop.return_value = None

        result = ci.get_crop_health_score(999)

        assert 'error' in result
        assert '999' in result['error']

    def test_no_snapshots_returns_no_data(self, ci, mock_conn):
        """No condition snapshots should return no_data status."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {'variety': 'rosso_premium'}
        cursor.fetchall.return_value = []

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        result = ci.get_crop_health_score(1)

        assert result['crop_id'] == 1
        assert result['variety'] == 'rosso_premium'
        assert result['status'] == 'no_data'
        assert result['score'] is None

    def test_healthy_score(self, ci, mock_conn, sample_variety_config):
        """All values within optimal range should produce healthy score."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {'variety': 'rosso_premium'}
        ci._config_loader.load_variety.return_value = sample_variety_config

        snapshot = _make_row_dict({
            'avg_temperature': 22.0,  # Within 20-24
            'avg_humidity': 65.0,     # Within 55-75
            'avg_ph': 6.1,           # Within 5.8-6.5
            'avg_ec': 1.6,           # Within 1.2-2.0
            'avg_vpd': 0.95,         # No range defined in sample config
            'avg_dli': 14.0,
            'time_in_optimal_pct': 90.0,
        })
        cursor.fetchall.return_value = [snapshot]

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        result = ci.get_crop_health_score(1)

        assert result['crop_id'] == 1
        # temp=25, humidity=15, ph=25, ec=25 => 90 total (vpd has no range in our config)
        assert result['score'] == 90.0
        assert result['status'] == 'healthy'
        assert result['snapshots_analyzed'] == 1
        assert result['time_in_optimal_pct'] == 90.0

        # Check parameter statuses are all optimal
        for param in ['temperature', 'humidity', 'ph', 'ec']:
            assert result['parameter_scores'][param]['status'] == 'optimal'

    def test_warning_score(self, ci, mock_conn, sample_variety_config):
        """Values in warning range should produce warning status."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {'variety': 'rosso_premium'}
        ci._config_loader.load_variety.return_value = sample_variety_config

        # Temperature and pH in warning range
        snapshot = _make_row_dict({
            'avg_temperature': 17.5,  # Between critical_min 15 and optimal_min 20
            'avg_humidity': 65.0,     # Within optimal
            'avg_ph': 5.4,           # Between critical_min 5.0 and optimal_min 5.8
            'avg_ec': 1.6,           # Within optimal
            'avg_vpd': None,
            'avg_dli': None,
            'time_in_optimal_pct': 50.0,
        })
        cursor.fetchall.return_value = [snapshot]

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        result = ci.get_crop_health_score(1)

        assert result['score'] < 90.0
        assert result['parameter_scores']['temperature']['status'] == 'warning'
        assert result['parameter_scores']['ph']['status'] == 'warning'
        assert result['parameter_scores']['humidity']['status'] == 'optimal'
        assert result['parameter_scores']['ec']['status'] == 'optimal'

    def test_critical_score(self, ci, mock_conn, sample_variety_config):
        """Values outside critical range should produce critical status."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {'variety': 'rosso_premium'}
        ci._config_loader.load_variety.return_value = sample_variety_config

        # Everything below critical
        snapshot = _make_row_dict({
            'avg_temperature': 10.0,  # Below critical_min 15.0
            'avg_humidity': 30.0,     # Below critical_min 40.0
            'avg_ph': 4.0,           # Below critical_min 5.0
            'avg_ec': 0.2,           # Below critical_min 0.5
            'avg_vpd': None,
            'avg_dli': None,
            'time_in_optimal_pct': 5.0,
        })
        cursor.fetchall.return_value = [snapshot]

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        result = ci.get_crop_health_score(1)

        assert result['score'] == 0.0
        assert result['status'] == 'critical'
        for param in ['temperature', 'humidity', 'ph', 'ec']:
            assert result['parameter_scores'][param]['status'] == 'critical'

    def test_multiple_snapshots_averaged(self, ci, mock_conn, sample_variety_config):
        """Multiple snapshots should be averaged for scoring."""
        conn, cursor = mock_conn

        ci._db.get_crop.return_value = {'variety': 'rosso_premium'}
        ci._config_loader.load_variety.return_value = sample_variety_config

        snap1 = _make_row_dict({
            'avg_temperature': 21.0,
            'avg_humidity': 60.0,
            'avg_ph': 6.0,
            'avg_ec': 1.5,
            'avg_vpd': None,
            'avg_dli': None,
            'time_in_optimal_pct': 80.0,
        })
        snap2 = _make_row_dict({
            'avg_temperature': 23.0,
            'avg_humidity': 70.0,
            'avg_ph': 6.2,
            'avg_ec': 1.7,
            'avg_vpd': None,
            'avg_dli': None,
            'time_in_optimal_pct': 90.0,
        })
        cursor.fetchall.return_value = [snap1, snap2]

        @contextmanager
        def fake_conn():
            yield conn

        ci._db.get_connection = fake_conn

        result = ci.get_crop_health_score(1)

        assert result['snapshots_analyzed'] == 2
        assert result['time_in_optimal_pct'] == 85.0  # avg of 80 and 90
        # All averages within optimal -> healthy
        assert result['status'] == 'healthy'

    def test_exception_returns_error(self, ci):
        """Exceptions should return error dict."""
        ci._db.get_crop.side_effect = RuntimeError("DB error")

        result = ci.get_crop_health_score(1)

        assert result['crop_id'] == 1
        assert 'error' in result
