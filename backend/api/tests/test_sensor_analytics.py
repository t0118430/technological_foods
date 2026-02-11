"""
Tests for Sensor Analytics Engine.

Tests VPD, DLI, nutrient scoring, anomaly detection, trend detection, moving averages.
"""

import math
import pytest
from datetime import datetime, timedelta
from sensor_analytics import SensorAnalytics, _mean, _stddev, _linear_regression_slope, _range_score


@pytest.fixture
def analytics():
    return SensorAnalytics()


@pytest.fixture
def loaded_analytics():
    """Analytics engine pre-loaded with 100 readings."""
    sa = SensorAnalytics()
    for i in range(100):
        data = {
            'temperature': 22.0 + (i % 5) * 0.1,
            'humidity': 60.0 + (i % 3) * 0.5,
            'ph': 6.0 + (i % 4) * 0.05,
            'ec': 1.5 + (i % 3) * 0.1,
            'water_level': 75.0,
            'light_level': 500.0,
        }
        sa.ingest_reading(data, 'test_sensor')
    return sa


# ── VPD Tests ──────────────────────────────────────────────────────

class TestVPD:
    def test_vpd_known_value_25c_50pct(self, analytics):
        """VPD at 25°C, 50% RH should be ~1.58 kPa."""
        result = analytics.calculate_vpd(25.0, 50.0)
        # SVP at 25°C = 0.6108 * exp(17.27 * 25 / (25 + 237.3)) = 3.167 kPa
        # VPD = 3.167 * (1 - 0.5) = 1.584 kPa
        assert 1.5 < result['vpd_kpa'] < 1.7
        assert result['classification'] == 'too_high'

    def test_vpd_known_value_22c_65pct(self, analytics):
        """VPD at 22°C, 65% RH - typical optimal conditions."""
        result = analytics.calculate_vpd(22.0, 65.0)
        # SVP at 22°C = 0.6108 * exp(17.27*22/(22+237.3)) = 2.643
        # VPD = 2.643 * 0.35 = 0.925
        assert 0.8 <= result['vpd_kpa'] <= 1.2
        assert result['classification'] == 'optimal'

    def test_vpd_high_humidity_low_vpd(self, analytics):
        """Very high humidity should give low VPD."""
        result = analytics.calculate_vpd(20.0, 95.0)
        assert result['vpd_kpa'] < 0.4
        assert result['classification'] == 'too_low'

    def test_vpd_low_humidity_high_vpd(self, analytics):
        """Low humidity should give high VPD."""
        result = analytics.calculate_vpd(30.0, 30.0)
        assert result['vpd_kpa'] > 1.6
        assert result['classification'] == 'too_high'

    def test_vpd_optimal_range_present(self, analytics):
        result = analytics.calculate_vpd(22.0, 65.0)
        assert result['optimal_range'] == {'min': 0.8, 'max': 1.2}

    def test_vpd_risk_none_when_optimal(self, analytics):
        result = analytics.calculate_vpd(22.0, 65.0)
        assert result['risk'] is None


# ── DLI Tests ──────────────────────────────────────────────────────

class TestDLI:
    def test_dli_accumulation(self, analytics):
        """DLI should increase with light readings."""
        for _ in range(10):
            analytics.ingest_reading({'light_level': 500.0}, 'dli_test')

        result = analytics.calculate_dli('dli_test')
        assert result['current_dli'] >= 0
        assert 'projected_dli' in result
        assert result['unit'] == 'mol/m2/day'

    def test_dli_no_data(self, analytics):
        result = analytics.calculate_dli('nonexistent')
        assert result['current_dli'] == 0
        assert result['classification'] == 'no_data'

    def test_dli_classification(self, analytics):
        """Test DLI classification ranges."""
        # Manually set accumulated light
        analytics.daily_light['test'] = {
            'date': datetime.now().date().isoformat(),
            'readings': [{'ppfd': 100, 'timestamp': datetime.now()}],
            'total_ppfd_seconds': 15_000_000,  # 15 mol/m2/day
        }
        result = analytics.calculate_dli('test')
        assert result['classification'] == 'optimal'


# ── Nutrient Score Tests ───────────────────────────────────────────

class TestNutrientScore:
    def test_perfect_score(self, analytics):
        """Optimal pH and EC should give 100."""
        result = analytics.calculate_nutrient_score(6.0, 1.6)
        assert result['score'] == 100
        assert result['ph_status'] == 'optimal'
        assert result['ec_status'] == 'optimal'
        assert result['recommendations'] == []

    def test_low_ph(self, analytics):
        result = analytics.calculate_nutrient_score(5.0, 1.6)
        assert result['score'] < 100
        assert result['ph_status'] == 'critical'
        assert any('pH too low' in r for r in result['recommendations'])

    def test_high_ec(self, analytics):
        result = analytics.calculate_nutrient_score(6.0, 3.0)
        assert result['score'] < 100
        assert result['ec_status'] == 'critical'
        assert any('EC too high' in r for r in result['recommendations'])

    def test_warning_range(self, analytics):
        """Values in warning range (between critical and optimal)."""
        result = analytics.calculate_nutrient_score(5.6, 1.0)
        assert result['ph_status'] == 'warning'
        assert result['ec_status'] == 'warning'
        assert 0 < result['score'] < 100

    def test_both_critical(self, analytics):
        result = analytics.calculate_nutrient_score(4.0, 4.0)
        assert result['score'] == 0
        assert result['ph_status'] == 'critical'
        assert result['ec_status'] == 'critical'


# ── Moving Averages Tests ──────────────────────────────────────────

class TestMovingAverages:
    def test_empty_buffer(self, analytics):
        result = analytics.get_moving_averages('empty_sensor')
        assert result == {}

    def test_moving_averages_calculated(self, loaded_analytics):
        result = loaded_analytics.get_moving_averages('test_sensor')
        assert 'temperature' in result
        assert 'ma_10' in result['temperature']
        assert 'ma_30' in result['temperature']
        assert 'ma_60' in result['temperature']
        assert result['temperature']['readings_count'] == 100

    def test_ma_values_reasonable(self, loaded_analytics):
        result = loaded_analytics.get_moving_averages('test_sensor')
        temp = result['temperature']
        # All temperatures were 22.0-22.4, so averages should be in that range
        assert 21.5 < temp['ma_10'] < 23.0
        assert 21.5 < temp['ma_30'] < 23.0
        assert 21.5 < temp['ma_60'] < 23.0


# ── Trend Detection Tests ─────────────────────────────────────────

class TestTrends:
    def test_rising_trend(self, analytics):
        """Increasing values should show 'rising' direction."""
        for i in range(60):
            analytics.ingest_reading({'temperature': 20.0 + i * 0.1}, 'rising')
        result = analytics.detect_trends('rising')
        assert result['temperature']['direction'] == 'rising'
        assert result['temperature']['slope'] > 0

    def test_falling_trend(self, analytics):
        """Decreasing values should show 'falling' direction."""
        for i in range(60):
            analytics.ingest_reading({'temperature': 30.0 - i * 0.1}, 'falling')
        result = analytics.detect_trends('falling')
        assert result['temperature']['direction'] == 'falling'
        assert result['temperature']['slope'] < 0

    def test_stable_trend(self, analytics):
        """Constant values should show 'stable' direction."""
        for i in range(60):
            analytics.ingest_reading({'temperature': 22.0}, 'stable')
        result = analytics.detect_trends('stable')
        assert result['temperature']['direction'] == 'stable'

    def test_insufficient_data(self, analytics):
        """Less than 5 readings should return empty."""
        for i in range(3):
            analytics.ingest_reading({'temperature': 22.0}, 'sparse')
        result = analytics.detect_trends('sparse')
        assert result == {}


# ── Anomaly Detection Tests ────────────────────────────────────────

class TestAnomalyDetection:
    def test_spike_detection(self, analytics):
        """A value far from the mean should trigger spike."""
        for i in range(50):
            analytics.ingest_reading({'temperature': 22.0 + (i % 3) * 0.1}, 'spike_test')

        # Now send a huge spike
        anomalies = analytics.detect_anomalies({'temperature': 35.0}, 'spike_test')
        spike_anomalies = [a for a in anomalies if a['type'] == 'spike']
        assert len(spike_anomalies) > 0
        assert spike_anomalies[0]['field'] == 'temperature'
        assert spike_anomalies[0]['z_score'] > 2.5

    def test_flatline_detection(self, analytics):
        """60+ identical readings should trigger flatline."""
        for i in range(65):
            analytics.ingest_reading({'temperature': 22.0}, 'flat_test')

        anomalies = analytics.detect_anomalies({'temperature': 22.0}, 'flat_test')
        flatline_anomalies = [a for a in anomalies if a['type'] == 'flatline']
        assert len(flatline_anomalies) > 0

    def test_sudden_jump_detection(self, analytics):
        """A >10% change from previous should trigger sudden_jump."""
        for i in range(20):
            analytics.ingest_reading({'ec': 1.5}, 'jump_test')

        anomalies = analytics.detect_anomalies({'ec': 2.0}, 'jump_test')
        jump_anomalies = [a for a in anomalies if a['type'] == 'sudden_jump']
        assert len(jump_anomalies) > 0
        assert jump_anomalies[0]['percent_change'] > 10

    def test_no_anomaly_normal_data(self, loaded_analytics):
        """Normal data should not trigger anomalies."""
        anomalies = loaded_analytics.detect_anomalies(
            {'temperature': 22.2, 'humidity': 60.5, 'ph': 6.1, 'ec': 1.6},
            'test_sensor'
        )
        # Should have no spike anomalies (jumps might trigger depending on last value)
        spike_anomalies = [a for a in anomalies if a['type'] == 'spike']
        assert len(spike_anomalies) == 0

    def test_insufficient_data_no_anomalies(self, analytics):
        """Less than 10 readings should not detect anomalies."""
        for i in range(5):
            analytics.ingest_reading({'temperature': 22.0}, 'few')
        anomalies = analytics.detect_anomalies({'temperature': 50.0}, 'few')
        assert anomalies == []


# ── Sensor Summary Tests ──────────────────────────────────────────

class TestSensorSummary:
    def test_no_data(self, analytics):
        result = analytics.get_sensor_summary('nonexistent')
        assert result['status'] == 'no_data'

    def test_full_summary(self, loaded_analytics):
        result = loaded_analytics.get_sensor_summary('test_sensor')
        assert 'vpd' in result
        assert 'nutrient_score' in result
        assert 'moving_averages' in result
        assert 'trends' in result
        assert 'anomalies' in result
        assert result['readings_in_buffer'] == 100


# ── Ingest Reading Tests ──────────────────────────────────────────

class TestIngestReading:
    def test_ingest_returns_vpd(self, analytics):
        result = analytics.ingest_reading(
            {'temperature': 22.0, 'humidity': 65.0}, 'ingest_test'
        )
        assert 'vpd' in result

    def test_ingest_returns_nutrient_score(self, analytics):
        result = analytics.ingest_reading(
            {'ph': 6.0, 'ec': 1.6}, 'ingest_test'
        )
        assert 'nutrient_score' in result

    def test_ingest_populates_buffer(self, analytics):
        analytics.ingest_reading({'temperature': 22.0}, 'buf_test')
        analytics.ingest_reading({'temperature': 23.0}, 'buf_test')
        buf = analytics._get_buffer('buf_test')
        assert len(buf) == 2


# ── Helper Function Tests ─────────────────────────────────────────

class TestHelpers:
    def test_mean(self):
        assert _mean([1, 2, 3, 4, 5]) == 3.0
        assert _mean([]) == 0.0

    def test_stddev(self):
        std = _stddev([2, 4, 4, 4, 5, 5, 7, 9])
        assert 1.9 < std < 2.1  # Known sample stddev ~2.0
        assert _stddev([]) == 0.0
        assert _stddev([5]) == 0.0

    def test_linear_regression_slope(self):
        # Perfect positive slope
        slope = _linear_regression_slope([0, 1, 2, 3], [0, 1, 2, 3])
        assert abs(slope - 1.0) < 0.001

        # Flat line
        slope = _linear_regression_slope([0, 1, 2, 3], [5, 5, 5, 5])
        assert abs(slope) < 0.001

    def test_range_score_optimal(self):
        score = _range_score(6.0, 5.8, 6.5, 5.5, 7.0, 50)
        assert score == 50

    def test_range_score_critical(self):
        score = _range_score(4.0, 5.8, 6.5, 5.5, 7.0, 50)
        assert score == 0

    def test_range_score_warning(self):
        score = _range_score(5.6, 5.8, 6.5, 5.5, 7.0, 50)
        assert 0 < score < 50
