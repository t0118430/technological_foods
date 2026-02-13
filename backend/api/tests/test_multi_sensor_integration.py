"""
Multi-Sensor Integration Tests

Tests the full multi-device flow with two simulated Arduino sensors
sending data to separate zones. Verifies buffer isolation, per-sensor
rule evaluation, notification routing, and documents query_latest bugs
where sensor_id is not propagated.

Devices:
  arduino_1 → Zone main       → Tomato (28°C, high light)
  arduino_2 → Zone greenhouse_b → Lettuce (20°C, moderate light)
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from sensor_analytics import SensorAnalytics
from rules.rule_engine import RuleEngine
from notifications.notification_service import NotificationService, NotificationChannel


# ── Helpers ────────────────────────────────────────────────────


class FakeChannel(NotificationChannel):
    """Test double that records every send call."""

    def __init__(self, channel_name="fake"):
        self._name = channel_name
        self.sent: list = []

    @property
    def name(self) -> str:
        return self._name

    def send(self, subject: str, body: str) -> bool:
        self.sent.append({"subject": subject, "body": body})
        return True

    def is_available(self) -> bool:
        return True


# ── Sensor Data Profiles ──────────────────────────────────────

ARDUINO_1_NORMAL = {
    "temperature": 28.0,
    "humidity": 55.0,
    "ph": 6.0,
    "ec": 2.2,
    "light_level": 800,
    "water_level": 70.0,
}

ARDUINO_2_NORMAL = {
    "temperature": 20.0,
    "humidity": 70.0,
    "ph": 6.2,
    "ec": 1.4,
    "light_level": 400,
    "water_level": 75.0,
}

ARDUINO_1_HOT = {
    "temperature": 32.0,
    "humidity": 50.0,
    "ph": 6.0,
    "ec": 2.2,
    "light_level": 900,
    "water_level": 68.0,
}

ARDUINO_2_COOL = {
    "temperature": 20.0,
    "humidity": 72.0,
    "ph": 6.3,
    "ec": 1.3,
    "light_level": 350,
    "water_level": 76.0,
}

# Both above threshold
ARDUINO_1_ABOVE = {"temperature": 31.0, "humidity": 55.0}
ARDUINO_2_ABOVE = {"temperature": 31.5, "humidity": 55.0}


# ── Rules sets ────────────────────────────────────────────────

MULTI_SENSOR_RULES = [
    {
        "id": "temp_high",
        "name": "Temperature Too High",
        "enabled": True,
        "sensor": "temperature",
        "condition": "above",
        "threshold": 30.0,
        "action": {
            "type": "notify",
            "severity": "critical",
            "message": "Temperature exceeded 30°C",
        },
    },
    {
        "id": "temp_low",
        "name": "Temperature Too Low",
        "enabled": True,
        "sensor": "temperature",
        "condition": "below",
        "threshold": 15.0,
        "action": {
            "type": "notify",
            "severity": "warning",
            "message": "Temperature below 15°C",
        },
    },
    {
        "id": "humidity_high",
        "name": "Humidity Too High",
        "enabled": True,
        "sensor": "humidity",
        "condition": "above",
        "threshold": 80.0,
        "action": {
            "type": "notify",
            "severity": "warning",
            "message": "Humidity too high",
        },
    },
    {
        "id": "led_high_temp",
        "name": "LED Blink on High Temp",
        "enabled": True,
        "sensor": "temperature",
        "condition": "above",
        "threshold": 16.0,
        "action": {"type": "arduino", "command": "led_blink"},
    },
    {
        "id": "temp_high_preventive",
        "name": "Temperature Approaching High",
        "enabled": True,
        "sensor": "temperature",
        "condition": "above",
        "threshold": 30.0,
        "warning_margin": 2.0,
        "action": {
            "type": "notify",
            "severity": "critical",
            "message": "Temperature critically high",
        },
        "preventive_message": "Temperature approaching 30°C",
        "preventive_action": "Increase ventilation",
    },
]


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def analytics():
    """Fresh SensorAnalytics instance with no readings."""
    return SensorAnalytics()


@pytest.fixture
def engine(tmp_path):
    """RuleEngine loaded with multi-sensor rules in a temp file."""
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps({"rules": MULTI_SENSOR_RULES}))
    return RuleEngine(rules_file)


@pytest.fixture
def channel():
    """FakeChannel to capture notification sends."""
    return FakeChannel()


@pytest.fixture
def notifier(channel):
    """NotificationService with zero cooldown and a FakeChannel."""
    return NotificationService(channels=[channel], cooldown_seconds=0)


@pytest.fixture
def pipeline(engine, notifier, channel):
    """Complete pipeline: engine + notifier + channel."""
    return engine, notifier, channel


@pytest.fixture
def mock_db():
    """Mock database for crop CRUD."""
    db = MagicMock()
    db.get_active_crops.return_value = [
        {
            "id": 1,
            "variety": "tomato_cherry",
            "plant_date": "2026-01-15",
            "zone": "main",
            "status": "active",
            "current_stage": "vegetative",
        },
        {
            "id": 2,
            "variety": "curly_green",
            "plant_date": "2026-01-20",
            "zone": "greenhouse_b",
            "status": "active",
            "current_stage": "seedling",
        },
    ]
    return db


def _run_pipeline(engine, notifier, sensor_data, sensor_id="arduino_1"):
    """Simulate the POST /api/data flow from server.py."""
    triggered = engine.evaluate(sensor_data, sensor_id)
    notify_actions = [t for t in triggered if t["action"].get("type") == "notify"]
    for t in notify_actions:
        notifier.notify(
            rule_id=t["rule_id"],
            severity=t["action"].get("severity", "warning"),
            message=t["action"].get("message", t["rule_name"]),
            sensor_data=sensor_data,
        )
    commands = engine.get_pending_commands(sensor_id)
    return triggered, commands


# ══════════════════════════════════════════════════════════════
# 1. Data Ingestion Isolation
# ══════════════════════════════════════════════════════════════


class TestDataIngestionIsolation:
    """Verify that two sensors maintain separate analytics buffers."""

    def test_two_sensors_create_separate_buffers(self, analytics):
        """Ingesting from two sensors creates two distinct buffer keys."""
        analytics.ingest_reading(ARDUINO_1_NORMAL, "arduino_1")
        analytics.ingest_reading(ARDUINO_2_NORMAL, "arduino_2")

        assert "arduino_1" in analytics.buffers
        assert "arduino_2" in analytics.buffers
        assert len(analytics.buffers) == 2

    def test_arduino_1_buffer_has_own_readings_only(self, analytics):
        """Buffer for arduino_1 contains only arduino_1 data."""
        analytics.ingest_reading(ARDUINO_1_NORMAL, "arduino_1")
        analytics.ingest_reading(ARDUINO_2_NORMAL, "arduino_2")

        buf1 = list(analytics.buffers["arduino_1"])
        assert len(buf1) == 1
        assert buf1[0]["temperature"] == 28.0

    def test_arduino_2_buffer_has_own_readings_only(self, analytics):
        """Buffer for arduino_2 contains only arduino_2 data."""
        analytics.ingest_reading(ARDUINO_1_NORMAL, "arduino_1")
        analytics.ingest_reading(ARDUINO_2_NORMAL, "arduino_2")

        buf2 = list(analytics.buffers["arduino_2"])
        assert len(buf2) == 1
        assert buf2[0]["temperature"] == 20.0

    def test_anomaly_spike_on_one_sensor_does_not_affect_other(self, analytics):
        """A temperature spike on arduino_1 should not create anomaly on arduino_2."""
        # Build baseline for both sensors
        for _ in range(30):
            analytics.ingest_reading({"temperature": 22.0, "humidity": 60.0}, "arduino_1")
            analytics.ingest_reading({"temperature": 20.0, "humidity": 65.0}, "arduino_2")

        # Spike on arduino_1 only
        spike_data = {"temperature": 45.0, "humidity": 60.0}
        result1 = analytics.ingest_reading(spike_data, "arduino_1")

        # Normal reading on arduino_2
        normal_data = {"temperature": 20.0, "humidity": 65.0}
        result2 = analytics.ingest_reading(normal_data, "arduino_2")

        # arduino_1 should have anomalies, arduino_2 should not
        assert "anomalies" in result1, "Spike on arduino_1 should produce anomalies"
        assert "anomalies" not in result2, "Normal reading on arduino_2 should have no anomalies"

    def test_vpd_uses_correct_sensor_temperature(self, analytics):
        """VPD calculation uses the temperature from the correct sensor's reading."""
        result1 = analytics.ingest_reading(ARDUINO_1_NORMAL, "arduino_1")
        result2 = analytics.ingest_reading(ARDUINO_2_NORMAL, "arduino_2")

        # VPD is a static calc from the reading data, so both should compute correctly
        assert "vpd" in result1
        assert "vpd" in result2
        # Higher temp (28) should produce higher VPD than lower temp (20) at similar humidity
        assert result1["vpd"]["vpd_kpa"] > result2["vpd"]["vpd_kpa"]


# ══════════════════════════════════════════════════════════════
# 2. Rule Evaluation Per-Sensor
# ══════════════════════════════════════════════════════════════


class TestRuleEvaluationPerSensor:
    """Verify rules fire independently per sensor_id."""

    def test_hot_sensor_triggers_cold_sensor_does_not(self, engine):
        """temp_high rule triggers for arduino_1 (32°C) but not arduino_2 (20°C)."""
        triggered_1 = engine.evaluate(ARDUINO_1_HOT, "arduino_1")
        triggered_2 = engine.evaluate(ARDUINO_2_COOL, "arduino_2")

        notify_1 = [t for t in triggered_1 if t["rule_id"] == "temp_high"]
        notify_2 = [t for t in triggered_2 if t["rule_id"] == "temp_high"]

        assert len(notify_1) == 1, "arduino_1 at 32°C should trigger temp_high"
        assert len(notify_2) == 0, "arduino_2 at 20°C should not trigger temp_high"

    def test_each_sensor_gets_own_pending_commands(self, engine):
        """Arduino commands are queued separately per sensor_id."""
        engine.evaluate(ARDUINO_1_HOT, "arduino_1")
        engine.evaluate(ARDUINO_2_COOL, "arduino_2")

        cmd_1 = engine.get_pending_commands("arduino_1")
        cmd_2 = engine.get_pending_commands("arduino_2")

        # Both are above 16°C so led_blink triggers for both
        assert cmd_1.get("led") == "blink"
        assert cmd_2.get("led") == "blink"

    def test_preventive_margin_triggers_per_sensor(self, engine):
        """Preventive alert at 29°C (within 2° margin of 30°C threshold)."""
        preventive_data = {"temperature": 29.0, "humidity": 55.0}

        triggered = engine.evaluate(preventive_data, "arduino_1")
        preventive = [t for t in triggered if t["alert_type"] == "preventive"]

        assert len(preventive) == 1, "29°C should trigger preventive for temp_high_preventive rule"
        assert "approaching" in preventive[0]["action"]["message"].lower()

    def test_preventive_does_not_fire_for_cool_sensor(self, engine):
        """arduino_2 at 20°C should not trigger any preventive alert."""
        triggered = engine.evaluate(ARDUINO_2_COOL, "arduino_2")
        preventive = [t for t in triggered if t["alert_type"] == "preventive"]

        assert len(preventive) == 0

    def test_both_sensors_above_threshold_trigger_independently(self, engine):
        """When both sensors exceed threshold, both get their own trigger."""
        triggered_1 = engine.evaluate(ARDUINO_1_ABOVE, "arduino_1")
        triggered_2 = engine.evaluate(ARDUINO_2_ABOVE, "arduino_2")

        notify_1 = [t for t in triggered_1 if t["rule_id"] == "temp_high"]
        notify_2 = [t for t in triggered_2 if t["rule_id"] == "temp_high"]

        assert len(notify_1) == 1
        assert len(notify_2) == 1


# ══════════════════════════════════════════════════════════════
# 3. query_latest Bugs — Documented with xfail
# ══════════════════════════════════════════════════════════════


class TestQueryLatestBugs:
    """Document bugs where sensor_id is not passed to query_latest."""

    @pytest.mark.xfail(
        reason="Bug: query_latest() defaults to arduino_1 when called without sensor_id"
    )
    def test_query_latest_without_arg_defaults_to_arduino_1(self):
        """query_latest() called with no args silently defaults to arduino_1."""
        # This documents the default behaviour — endpoints that forget to pass
        # sensor_id will always query arduino_1 data even for arduino_2 requests.
        from server import query_latest

        # If the system supported sensor_id=None returning ALL sensors, this
        # would pass.  Instead it defaults to "arduino_1".
        import inspect
        sig = inspect.signature(query_latest)
        default = sig.parameters["sensor_id"].default
        # The bug: default should be None (requiring explicit sensor_id),
        # not a hardcoded "arduino_1"
        assert default is None, f"Default is '{default}', should be None"

    @pytest.mark.xfail(
        reason="Bug: analytics VPD endpoint reads sensor_id from query but server.py pattern relies on default"
    )
    def test_analytics_vpd_endpoint_sensor_id_propagation(self):
        """The /api/analytics/vpd endpoint reads sensor_id from query params
        but calls sensor_analytics methods that may not propagate it."""
        # This documents that while the endpoint parses sensor_id from the
        # query string, the internal call chain may still use defaults.
        # A proper fix would pass sensor_id all the way through.
        assert False, "Endpoint accepts sensor_id param but internal calls may default to arduino_1"

    @pytest.mark.xfail(
        reason="Bug: analytics anomalies endpoint same pattern as VPD"
    )
    def test_analytics_anomalies_endpoint_sensor_id_propagation(self):
        """The /api/analytics/anomalies endpoint has the same pattern."""
        assert False, "Endpoint accepts sensor_id param but internal calls may default to arduino_1"

    @pytest.mark.xfail(
        reason="Bug: /api/data/latest does not accept sensor_id parameter"
    )
    def test_data_latest_no_sensor_id_param(self):
        """GET /api/data/latest should accept sensor_id but doesn't expose it."""
        assert False, "/api/data/latest always returns arduino_1 data"

    @pytest.mark.xfail(
        reason="Bug: crops table has no sensor_id column, uses zone as proxy"
    )
    def test_crops_table_missing_sensor_id_column(self):
        """The crops table has zone but no sensor_id, making device-to-crop
        mapping indirect and fragile."""
        assert False, "crops table should have sensor_id column for direct device mapping"


# ══════════════════════════════════════════════════════════════
# 4. Crop-Zone Filtering
# ══════════════════════════════════════════════════════════════


class TestCropZoneFiltering:
    """Test crop retrieval and zone-based filtering with mock database."""

    def test_get_active_crops_returns_both(self, mock_db):
        """get_active_crops() returns crops from both zones."""
        crops = mock_db.get_active_crops()
        assert len(crops) == 2
        varieties = {c["variety"] for c in crops}
        assert varieties == {"tomato_cherry", "curly_green"}

    def test_filter_by_zone_main(self, mock_db):
        """Filtering by zone='main' returns only the tomato crop."""
        crops = mock_db.get_active_crops()
        main_crops = [c for c in crops if c.get("zone") == "main"]

        assert len(main_crops) == 1
        assert main_crops[0]["variety"] == "tomato_cherry"

    def test_filter_by_zone_greenhouse_b(self, mock_db):
        """Filtering by zone='greenhouse_b' returns only the lettuce crop."""
        crops = mock_db.get_active_crops()
        gh_crops = [c for c in crops if c.get("zone") == "greenhouse_b"]

        assert len(gh_crops) == 1
        assert gh_crops[0]["variety"] == "curly_green"

    def test_no_zone_filter_returns_all(self, mock_db):
        """No zone filter returns all active crops."""
        crops = mock_db.get_active_crops()
        # Simulate the server.py pattern: no zone param → no filtering
        zone = None
        if zone:
            crops = [c for c in crops if c.get("zone") == zone]
        assert len(crops) == 2

    def test_unknown_zone_returns_empty(self, mock_db):
        """Filtering by a non-existent zone returns nothing."""
        crops = mock_db.get_active_crops()
        filtered = [c for c in crops if c.get("zone") == "rooftop"]

        assert len(filtered) == 0


# ══════════════════════════════════════════════════════════════
# 5. Notification Routing
# ══════════════════════════════════════════════════════════════


class TestNotificationRouting:
    """Verify notifications carry correct sensor data per device."""

    def test_arduino_1_trigger_contains_its_data(self, pipeline):
        """Notification from arduino_1 trigger should reference its sensor values."""
        engine, notifier, channel = pipeline
        _run_pipeline(engine, notifier, ARDUINO_1_HOT, "arduino_1")

        assert len(channel.sent) >= 1
        body = channel.sent[0]["body"]
        # Body should contain arduino_1's temperature (32.0)
        assert "32" in body

    def test_arduino_2_normal_does_not_notify(self, pipeline):
        """arduino_2 at normal readings should not produce notifications."""
        engine, notifier, channel = pipeline
        _run_pipeline(engine, notifier, ARDUINO_2_COOL, "arduino_2")

        # No notify rules should fire for 20°C
        notify_msgs = [s for s in channel.sent]
        # Only temp_high fires above 30; arduino_2 is at 20
        assert len(notify_msgs) == 0

    def test_separate_rules_trigger_separate_notifications(self, pipeline):
        """Different threshold breaches on different sensors → independent notifications."""
        engine, notifier, channel = pipeline

        # arduino_1 triggers temp_high (32°C)
        _run_pipeline(engine, notifier, ARDUINO_1_HOT, "arduino_1")
        count_after_1 = len(channel.sent)
        assert count_after_1 >= 1

        # arduino_2 with high humidity (85%) triggers humidity_high
        humid_data = {"temperature": 20.0, "humidity": 85.0}
        _run_pipeline(engine, notifier, humid_data, "arduino_2")
        count_after_2 = len(channel.sent)

        assert count_after_2 > count_after_1, "arduino_2 humidity breach should add notification"

    def test_cooldown_is_per_rule_not_per_sensor(self, engine, channel):
        """Two sensors triggering the same rule_id: cooldown blocks the second."""
        # Use non-zero cooldown to test cooldown behavior
        notifier = NotificationService(channels=[channel], cooldown_seconds=300)

        # arduino_1 triggers temp_high AND temp_high_preventive (both critical at 32°C)
        _run_pipeline(engine, notifier, ARDUINO_1_HOT, "arduino_1")
        count_after_1 = len(channel.sent)
        assert count_after_1 >= 1

        # arduino_2 also triggers same rules — cooldown blocks them
        _run_pipeline(engine, notifier, ARDUINO_2_ABOVE, "arduino_2")
        assert len(channel.sent) == count_after_1, "Cooldown is per rule_id, second sensor blocked"

    def test_different_rules_not_blocked_by_cooldown(self, engine, channel):
        """Different rule_ids should not share cooldown."""
        notifier = NotificationService(channels=[channel], cooldown_seconds=300)

        # arduino_1 triggers temp_high
        _run_pipeline(engine, notifier, ARDUINO_1_HOT, "arduino_1")
        count_after_temp = len(channel.sent)
        assert count_after_temp >= 1

        # arduino_2 triggers humidity_high (different rule_id)
        _run_pipeline(engine, notifier, {"temperature": 20.0, "humidity": 85.0}, "arduino_2")
        count_after_humid = len(channel.sent)
        assert count_after_humid > count_after_temp, "Different rule_id should not be blocked"


# ══════════════════════════════════════════════════════════════
# 6. End-to-End Two-Device Flow
# ══════════════════════════════════════════════════════════════


class TestEndToEndTwoDeviceFlow:
    """Full pipeline integration: ingest → analytics → rules → notifications."""

    def test_full_pipeline_arduino_1(self, analytics, pipeline):
        """Complete flow for arduino_1: ingest + rules + notifications."""
        engine, notifier, channel = pipeline

        # Ingest
        result = analytics.ingest_reading(ARDUINO_1_HOT, "arduino_1")
        assert "vpd" in result

        # Rules + notifications
        triggered, commands = _run_pipeline(engine, notifier, ARDUINO_1_HOT, "arduino_1")

        temp_alerts = [t for t in triggered if t["rule_id"] == "temp_high"]
        assert len(temp_alerts) == 1
        assert len(channel.sent) >= 1
        assert commands.get("led") == "blink"

    def test_full_pipeline_arduino_2(self, analytics, pipeline):
        """Complete flow for arduino_2: ingest + rules — no alerts expected."""
        engine, notifier, channel = pipeline

        # Ingest
        result = analytics.ingest_reading(ARDUINO_2_COOL, "arduino_2")
        assert "vpd" in result

        # Rules (20°C should not trigger temp_high)
        triggered, commands = _run_pipeline(engine, notifier, ARDUINO_2_COOL, "arduino_2")

        temp_alerts = [t for t in triggered if t["rule_id"] == "temp_high"]
        assert len(temp_alerts) == 0
        assert len(channel.sent) == 0

    def test_sequential_no_cross_contamination(self, analytics, pipeline):
        """Ingest arduino_1 then arduino_2 — verify no cross-contamination."""
        engine, notifier, channel = pipeline

        # arduino_1 first (hot)
        analytics.ingest_reading(ARDUINO_1_HOT, "arduino_1")
        _run_pipeline(engine, notifier, ARDUINO_1_HOT, "arduino_1")
        alerts_after_1 = len(channel.sent)

        # arduino_2 second (cool)
        analytics.ingest_reading(ARDUINO_2_COOL, "arduino_2")
        _run_pipeline(engine, notifier, ARDUINO_2_COOL, "arduino_2")
        alerts_after_2 = len(channel.sent)

        # arduino_2 should not have added any alerts
        assert alerts_after_2 == alerts_after_1

        # Buffers should be isolated
        buf1 = list(analytics.buffers["arduino_1"])
        buf2 = list(analytics.buffers["arduino_2"])
        assert buf1[0]["temperature"] == 32.0
        assert buf2[0]["temperature"] == 20.0

    def test_concurrent_pattern_buffers_isolated(self, analytics):
        """Alternating ingestion from both sensors keeps buffers separate."""
        for i in range(20):
            analytics.ingest_reading(
                {"temperature": 28.0 + (i * 0.1), "humidity": 55.0}, "arduino_1"
            )
            analytics.ingest_reading(
                {"temperature": 20.0 + (i * 0.05), "humidity": 70.0}, "arduino_2"
            )

        buf1 = list(analytics.buffers["arduino_1"])
        buf2 = list(analytics.buffers["arduino_2"])

        assert len(buf1) == 20
        assert len(buf2) == 20

        # All arduino_1 temps should be >= 28.0
        assert all(r["temperature"] >= 28.0 for r in buf1)
        # All arduino_2 temps should be <= 21.0
        assert all(r["temperature"] <= 21.0 for r in buf2)

    def test_both_zones_represented_in_crop_status(self, analytics, mock_db):
        """After ingesting from both sensors, crop status reflects both zones."""
        analytics.ingest_reading(ARDUINO_1_NORMAL, "arduino_1")
        analytics.ingest_reading(ARDUINO_2_NORMAL, "arduino_2")

        crops = mock_db.get_active_crops()
        zones = {c["zone"] for c in crops}

        assert "main" in zones
        assert "greenhouse_b" in zones
        # Both sensors have data
        assert "arduino_1" in analytics.buffers
        assert "arduino_2" in analytics.buffers
