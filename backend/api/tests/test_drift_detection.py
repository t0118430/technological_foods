"""
Tests for DriftDetectionService (drift_detection_service.py)
Covers: dual-sensor analysis, thresholds, alert cooldown, trends, revenue risk, formatting, status
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from sensors.drift_detection_service import DriftDetectionService, DriftAnalysis, SensorReading


@pytest.fixture
def detector():
    """Fresh DriftDetectionService instance."""
    return DriftDetectionService()


# ── Dual Reading Analysis ──────────────────────────────────────


class TestDualReadingAnalysis:
    def test_healthy_readings_identical(self, detector):
        result = detector.analyze_dual_reading(
            "sensor-1",
            {"temperature": 25.0, "humidity": 65.0},
            {"temperature": 25.0, "humidity": 65.0},
            sensor_tier="medium"
        )
        assert result.status == "healthy"
        assert result.needs_calibration is False
        assert result.temp_diff == 0.0
        assert result.humidity_diff == 0.0

    def test_healthy_within_threshold(self, detector):
        result = detector.analyze_dual_reading(
            "sensor-2",
            {"temperature": 25.0, "humidity": 65.0},
            {"temperature": 25.3, "humidity": 65.5},
            sensor_tier="medium"
        )
        assert result.status == "healthy"
        assert result.needs_calibration is False

    def test_degraded_temp_warning(self, detector):
        result = detector.analyze_dual_reading(
            "sensor-3",
            {"temperature": 25.0, "humidity": 65.0},
            {"temperature": 25.6, "humidity": 65.0},  # 0.6 diff > 0.5 warning
            sensor_tier="medium"
        )
        assert result.status == "degraded"
        assert result.needs_calibration is True
        assert result.estimated_days_until_failure == 7

    def test_degraded_humidity_warning(self, detector):
        result = detector.analyze_dual_reading(
            "sensor-4",
            {"temperature": 25.0, "humidity": 65.0},
            {"temperature": 25.0, "humidity": 67.5},  # 2.5 diff > 2.0 warning
            sensor_tier="medium"
        )
        assert result.status == "degraded"
        assert result.needs_calibration is True

    def test_failing_temp_critical(self, detector):
        result = detector.analyze_dual_reading(
            "sensor-5",
            {"temperature": 25.0, "humidity": 65.0},
            {"temperature": 26.5, "humidity": 65.0},  # 1.5 diff > 1.0 critical
            sensor_tier="medium"
        )
        assert result.status == "failing"
        assert result.needs_calibration is True
        assert result.estimated_days_until_failure == 1

    def test_failing_humidity_critical(self, detector):
        result = detector.analyze_dual_reading(
            "sensor-6",
            {"temperature": 25.0, "humidity": 65.0},
            {"temperature": 25.0, "humidity": 71.0},  # 6.0 diff > 5.0 critical
            sensor_tier="medium"
        )
        assert result.status == "failing"

    def test_drift_percent_calculated(self, detector):
        result = detector.analyze_dual_reading(
            "sensor-7",
            {"temperature": 20.0, "humidity": 50.0},
            {"temperature": 22.0, "humidity": 55.0},
        )
        assert result.temp_drift_percent == pytest.approx(10.0)
        assert result.humidity_drift_percent == pytest.approx(10.0)

    def test_zero_primary_no_division_error(self, detector):
        result = detector.analyze_dual_reading(
            "sensor-8",
            {"temperature": 0.0, "humidity": 0.0},
            {"temperature": 1.0, "humidity": 1.0},
        )
        assert result.temp_drift_percent == 0
        assert result.humidity_drift_percent == 0


# ── Sensor Tiers ───────────────────────────────────────────────


class TestSensorTiers:
    def test_good_tier_stricter_thresholds(self, detector):
        # Same readings degraded in "good" tier but healthy in "cheap" tier
        primary = {"temperature": 25.0, "humidity": 65.0}
        secondary = {"temperature": 25.3, "humidity": 65.5}

        good_result = detector.analyze_dual_reading("g1", primary, secondary, "good")
        cheap_result = detector.analyze_dual_reading("c1", primary, secondary, "cheap")

        assert good_result.status == "degraded"
        assert cheap_result.status == "healthy"

    def test_unknown_tier_defaults_to_medium(self, detector):
        result = detector.analyze_dual_reading(
            "sensor-unk",
            {"temperature": 25.0, "humidity": 65.0},
            {"temperature": 25.6, "humidity": 65.0},
            sensor_tier="nonexistent"
        )
        # Should use medium thresholds (0.5 warning) -> 0.6 is degraded
        assert result.status == "degraded"


# ── Alert Cooldown ─────────────────────────────────────────────


class TestAlertCooldown:
    def test_healthy_never_alerts(self, detector):
        analysis = DriftAnalysis(0, 0, 0, 0, "healthy", False, None)
        assert detector.should_send_alert("s1", analysis) is False

    def test_first_degraded_alerts(self, detector):
        analysis = DriftAnalysis(0.6, 0, 2.4, 0, "degraded", True, 7)
        assert detector.should_send_alert("s1", analysis) is True

    def test_second_alert_within_cooldown_blocked(self, detector):
        analysis = DriftAnalysis(0.6, 0, 2.4, 0, "degraded", True, 7)
        detector.should_send_alert("s1", analysis)  # first alert
        assert detector.should_send_alert("s1", analysis) is False  # cooldown

    def test_alert_after_cooldown_passes(self, detector):
        analysis = DriftAnalysis(0.6, 0, 2.4, 0, "degraded", True, 7)
        detector.should_send_alert("s1", analysis)
        # Manually expire the cooldown
        detector.last_alert_time["s1"] = datetime.now() - timedelta(hours=7)
        assert detector.should_send_alert("s1", analysis) is True


# ── Drift Trends ───────────────────────────────────────────────


class TestDriftTrends:
    def test_no_data_returns_defaults(self, detector):
        trend = detector.get_drift_trend("nonexistent")
        assert trend["is_worsening"] is False
        assert trend["readings_count"] == 0

    def test_trend_with_data(self, detector):
        # Feed some readings
        for i in range(20):
            detector.analyze_dual_reading(
                "trend-sensor",
                {"temperature": 25.0, "humidity": 65.0},
                {"temperature": 25.0 + i * 0.01, "humidity": 65.0},
            )
        trend = detector.get_drift_trend("trend-sensor")
        assert trend["readings_count"] == 20
        assert trend["avg_temp_drift"] >= 0
        assert trend["max_temp_drift"] >= trend["avg_temp_drift"]

    def test_worsening_trend_detected(self, detector):
        # First half: small drift. Second half: large drift
        for i in range(10):
            detector.analyze_dual_reading(
                "worsening",
                {"temperature": 25.0, "humidity": 65.0},
                {"temperature": 25.1, "humidity": 65.0},
            )
        for i in range(10):
            detector.analyze_dual_reading(
                "worsening",
                {"temperature": 25.0, "humidity": 65.0},
                {"temperature": 26.0, "humidity": 65.0},  # Much larger drift
            )
        trend = detector.get_drift_trend("worsening")
        assert trend["is_worsening"] is True

    def test_history_capped_at_100(self, detector):
        for i in range(120):
            detector.analyze_dual_reading(
                "capped",
                {"temperature": 25.0, "humidity": 65.0},
                {"temperature": 25.1, "humidity": 65.0},
            )
        assert len(detector.drift_history["capped"]) == 100


# ── Revenue Risk ───────────────────────────────────────────────


class TestRevenueRisk:
    def test_healthy_zero_risk(self, detector):
        analysis = DriftAnalysis(0, 0, 0, 0, "healthy", False, None)
        risk = detector.calculate_revenue_risk(analysis)
        assert risk["revenue_at_risk"] == 0
        assert risk["urgency"] == "low"

    def test_degraded_medium_risk(self, detector):
        analysis = DriftAnalysis(0.6, 0, 2.4, 0, "degraded", True, 7)
        risk = detector.calculate_revenue_risk(analysis, crop_value_per_day=100)
        assert risk["revenue_at_risk"] == 100 * 7 * 0.15  # 105.0
        assert risk["urgency"] == "medium"

    def test_failing_critical_risk(self, detector):
        analysis = DriftAnalysis(1.5, 0, 6.0, 0, "failing", True, 1)
        risk = detector.calculate_revenue_risk(analysis, crop_value_per_day=100)
        assert risk["revenue_at_risk"] == 100 * 1 * 0.5  # 50.0
        assert risk["urgency"] == "critical"

    def test_custom_crop_value(self, detector):
        analysis = DriftAnalysis(0.6, 0, 2.4, 0, "degraded", True, 7)
        risk = detector.calculate_revenue_risk(analysis, crop_value_per_day=200)
        assert risk["revenue_at_risk"] == 200 * 7 * 0.15


# ── Business Alert Formatting ──────────────────────────────────


class TestAlertFormatting:
    def test_failing_alert_format(self, detector):
        analysis = DriftAnalysis(1.5, 3.0, 6.0, 4.6, "failing", True, 1)
        risk = {"revenue_at_risk": 50.0, "days_at_risk": 1, "urgency": "critical"}
        alert = detector.format_business_alert("sensor-1", "Test Farm", analysis, risk)
        assert "CRITICAL" in alert["title"]
        assert "Test Farm" in alert["title"]
        assert "sensor-1" in alert["body"]
        assert "URGENT" in alert["body"]

    def test_degraded_alert_format(self, detector):
        analysis = DriftAnalysis(0.6, 1.0, 2.4, 1.5, "degraded", True, 7)
        risk = {"revenue_at_risk": 105.0, "days_at_risk": 7, "urgency": "medium"}
        alert = detector.format_business_alert("sensor-2", "Green Farm", analysis, risk)
        assert "WARNING" in alert["title"]
        assert "Green Farm" in alert["title"]


# ── Service Status ─────────────────────────────────────────────


class TestServiceStatus:
    def test_status_no_data(self, detector):
        status = detector.get_status()
        assert status["sensors_monitored"] == 0
        assert status["status"] == "no_data"

    def test_status_all_healthy(self, detector):
        detector.analyze_dual_reading(
            "s1",
            {"temperature": 25.0, "humidity": 65.0},
            {"temperature": 25.0, "humidity": 65.0},
        )
        status = detector.get_status()
        assert status["sensors_monitored"] == 1
        assert status["healthy"] == 1
        assert status["status"] == "healthy"

    def test_status_with_failing_sensor(self, detector):
        detector.analyze_dual_reading(
            "s1",
            {"temperature": 25.0, "humidity": 65.0},
            {"temperature": 25.0, "humidity": 65.0},
        )
        detector.analyze_dual_reading(
            "s2",
            {"temperature": 25.0, "humidity": 65.0},
            {"temperature": 27.0, "humidity": 65.0},  # failing
        )
        status = detector.get_status()
        assert status["failing"] == 1
        assert status["healthy"] == 1
        assert status["status"] == "critical"
