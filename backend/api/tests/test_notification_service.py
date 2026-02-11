import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from notifications.notification_service import (
    NotificationChannel,
    NotificationService,
    ConsoleChannel,
    WhatsAppChannel,
    SMSChannel,
    EmailChannel,
    NtfyChannel,
    _gauge,
    _sensor_status,
    SENSOR_META,
)
from rules.rule_engine import RuleEngine


# ── Helpers ───────────────────────────────────────────────────


class FakeChannel(NotificationChannel):
    """Test double that records every send call."""

    def __init__(self, channel_name="fake", available=True, should_fail=False):
        self._name = channel_name
        self._available = available
        self._should_fail = should_fail
        self.sent: list = []

    @property
    def name(self) -> str:
        return self._name

    def send(self, subject: str, body: str) -> bool:
        if self._should_fail:
            raise RuntimeError("channel error")
        self.sent.append({"subject": subject, "body": body})
        return True

    def is_available(self) -> bool:
        return self._available


# ── Channel Interface ─────────────────────────────────────────


class TestChannels:

    def test_console_channel_is_available(self):
        ch = ConsoleChannel()
        assert ch.is_available() is True
        assert ch.name == "console"

    def test_console_channel_sends(self):
        ch = ConsoleChannel()
        result = ch.send("Test Subject", "Test body")
        assert result is True

    def test_whatsapp_unavailable_without_credentials(self):
        ch = WhatsAppChannel()
        assert ch.is_available() is False
        assert ch.name == "whatsapp"

    def test_sms_unavailable_without_credentials(self):
        ch = SMSChannel()
        assert ch.is_available() is False
        assert ch.name == "sms"

    def test_email_unavailable_without_credentials(self):
        ch = EmailChannel()
        assert ch.is_available() is False
        assert ch.name == "email"

    def test_whatsapp_send_returns_false_when_unavailable(self):
        ch = WhatsAppChannel()
        assert ch.send("Subject", "Body") is False

    def test_sms_send_returns_false_when_unavailable(self):
        ch = SMSChannel()
        assert ch.send("Subject", "Body") is False

    def test_email_send_returns_false_when_unavailable(self):
        ch = EmailChannel()
        assert ch.send("Subject", "Body") is False

    def test_ntfy_unavailable_without_topic(self):
        ch = NtfyChannel()
        assert ch.is_available() is False
        assert ch.name == "ntfy"

    @patch.dict('os.environ', {'NTFY_TOPIC': 'test-agritech'})
    def test_ntfy_available_with_topic(self):
        ch = NtfyChannel()
        assert ch.is_available() is True

    def test_ntfy_send_returns_false_when_unavailable(self):
        ch = NtfyChannel()
        assert ch.send("Subject", "Body") is False

    @patch.dict('os.environ', {'NTFY_TOPIC': 'test-agritech'})
    @patch('notifications.notification_service.urllib.request.urlopen')
    def test_ntfy_send_posts_to_endpoint(self, mock_urlopen):
        ch = NtfyChannel()
        result = ch.send("[CRITICAL] Test Subject", "Test body")
        assert result is True
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://ntfy.sh/test-agritech"
        assert req.get_header("Title") == "[CRITICAL] Test Subject"
        assert req.get_header("Markdown") == "yes"
        assert req.data == b"Test body"

    @patch.dict('os.environ', {'NTFY_TOPIC': 'test-agritech'})
    @patch('notifications.notification_service.urllib.request.urlopen')
    def test_ntfy_send_sets_priority_from_severity(self, mock_urlopen):
        ch = NtfyChannel()
        ch.send("[CRITICAL] High temp", "body")
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Priority") == "5"
        assert req.get_header("Tags") == "rotating_light"

    @patch.dict('os.environ', {'NTFY_TOPIC': 'test-agritech'})
    @patch('notifications.notification_service.urllib.request.urlopen')
    def test_ntfy_send_warning_priority(self, mock_urlopen):
        ch = NtfyChannel()
        ch.send("[WARNING] Low humidity", "body")
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Priority") == "4"
        assert req.get_header("Tags") == "warning"

    @patch.dict('os.environ', {'NTFY_TOPIC': 'my-topic', 'NTFY_TOKEN': 'tk_secret'})
    @patch('notifications.notification_service.urllib.request.urlopen')
    def test_ntfy_send_includes_auth_token(self, mock_urlopen):
        ch = NtfyChannel()
        ch.send("Subject", "Body")
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Authorization") == "Bearer tk_secret"

    @patch.dict('os.environ', {'NTFY_URL': 'https://my-ntfy.example.com', 'NTFY_TOPIC': 'farm'})
    @patch('notifications.notification_service.urllib.request.urlopen')
    def test_ntfy_send_uses_custom_url(self, mock_urlopen):
        ch = NtfyChannel()
        ch.send("Subject", "Body")
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://my-ntfy.example.com/farm"


# ── Notification Service ──────────────────────────────────────


class TestNotificationService:

    def test_notify_sends_to_available_channels(self):
        ch1 = FakeChannel("ch1", available=True)
        ch2 = FakeChannel("ch2", available=False)
        svc = NotificationService(channels=[ch1, ch2], cooldown_seconds=0)

        results = svc.notify("rule_1", "warning", "Test alert")

        assert len(results) == 2
        assert results[0]["channel"] == "ch1"
        assert results[0]["sent"] is True
        assert results[1]["channel"] == "ch2"
        assert results[1]["sent"] is False
        assert len(ch1.sent) == 1
        assert len(ch2.sent) == 0

    def test_notify_records_history(self):
        ch = FakeChannel()
        svc = NotificationService(channels=[ch], cooldown_seconds=0)

        svc.notify("rule_1", "critical", "High temp", {"temperature": 35.0})

        status = svc.get_status()
        assert len(status["recent_alerts"]) == 1
        alert = status["recent_alerts"][0]
        assert alert["rule_id"] == "rule_1"
        assert alert["severity"] == "critical"
        assert alert["sensor_data"]["temperature"] == 35.0

    def test_channel_failure_does_not_crash(self):
        ch_ok = FakeChannel("ok")
        ch_fail = FakeChannel("broken", should_fail=True)
        svc = NotificationService(channels=[ch_ok, ch_fail], cooldown_seconds=0)

        results = svc.notify("rule_1", "warning", "Test")

        assert results[0]["sent"] is True
        assert results[1]["sent"] is False


# ── Cooldown ──────────────────────────────────────────────────


class TestCooldown:

    def test_duplicate_within_cooldown_is_skipped(self):
        ch = FakeChannel()
        svc = NotificationService(channels=[ch], cooldown_seconds=60)

        first = svc.notify("rule_1", "warning", "Alert")
        second = svc.notify("rule_1", "warning", "Alert")

        assert len(first) == 1
        assert len(second) == 0  # Skipped due to cooldown
        assert len(ch.sent) == 1

    def test_different_rules_not_affected_by_cooldown(self):
        ch = FakeChannel()
        svc = NotificationService(channels=[ch], cooldown_seconds=60)

        svc.notify("rule_1", "warning", "Alert 1")
        svc.notify("rule_2", "warning", "Alert 2")

        assert len(ch.sent) == 2

    def test_cooldown_expires(self):
        ch = FakeChannel()
        svc = NotificationService(channels=[ch], cooldown_seconds=1)

        svc.notify("rule_1", "warning", "First")
        time.sleep(1.1)
        svc.notify("rule_1", "warning", "Second")

        assert len(ch.sent) == 2

    def test_test_alert_bypasses_cooldown(self):
        ch = FakeChannel()
        svc = NotificationService(channels=[ch], cooldown_seconds=9999)

        svc.test_alert()
        svc.test_alert()

        assert len(ch.sent) == 2  # Both sent, cooldown bypassed

    def test_test_alert_with_real_data(self):
        """Test that test_alert can accept real sensor data."""
        ch = FakeChannel()
        svc = NotificationService(channels=[ch], cooldown_seconds=0)

        real_data = {"temperature": 24.5, "humidity": 58.3}
        svc.test_alert(sensor_data=real_data)

        assert len(ch.sent) == 1
        body = ch.sent[0]["body"]
        assert "24.5" in body
        assert "58.3" in body
        assert "Using real sensor data" in body

    def test_test_alert_without_data_uses_defaults(self):
        """Test that test_alert uses default data when no sensor_data provided."""
        ch = FakeChannel()
        svc = NotificationService(channels=[ch], cooldown_seconds=0)

        svc.test_alert()  # No sensor_data parameter

        assert len(ch.sent) == 1
        body = ch.sent[0]["body"]
        assert "31.5" in body  # Default temperature
        assert "82.0" in body  # Default humidity


# ── Status API ────────────────────────────────────────────────


class TestStatus:

    def test_get_status_returns_channels(self):
        ch1 = FakeChannel("console", available=True)
        ch2 = FakeChannel("whatsapp", available=False)
        svc = NotificationService(channels=[ch1, ch2])

        status = svc.get_status()

        assert len(status["channels"]) == 2
        assert status["channels"][0] == {"name": "console", "available": True}
        assert status["channels"][1] == {"name": "whatsapp", "available": False}

    def test_history_capped_at_max(self):
        ch = FakeChannel()
        svc = NotificationService(channels=[ch], cooldown_seconds=0)

        for i in range(60):
            svc.notify(f"rule_{i}", "info", f"Alert {i}")

        assert len(svc.history) == 50  # MAX_HISTORY


# ── Integration with Rule Engine ──────────────────────────────


class TestRuleEngineIntegration:

    @pytest.fixture
    def engine_with_notify(self, tmp_path):
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(json.dumps({"rules": [
            {
                "id": "notify_high_temp",
                "name": "Alert: Temperature Too High",
                "enabled": True,
                "sensor": "temperature",
                "condition": "above",
                "threshold": 30.0,
                "action": {
                    "type": "notify",
                    "severity": "critical",
                    "message": "Temperature too high"
                }
            },
            {
                "id": "notify_low_ph",
                "name": "Alert: pH Too Acidic",
                "enabled": True,
                "sensor": "ph",
                "condition": "below",
                "threshold": 5.5,
                "action": {
                    "type": "notify",
                    "severity": "critical",
                    "message": "pH too acidic"
                }
            }
        ]}))
        return RuleEngine(rules_file)

    def test_notify_rule_triggers_on_high_temp(self, engine_with_notify):
        triggered = engine_with_notify.evaluate({"temperature": 32.0})
        rule_ids = [t["rule_id"] for t in triggered]
        assert "notify_high_temp" in rule_ids
        action = next(t["action"] for t in triggered if t["rule_id"] == "notify_high_temp")
        assert action["type"] == "notify"
        assert action["severity"] == "critical"

    def test_notify_rule_does_not_trigger_normal_temp(self, engine_with_notify):
        triggered = engine_with_notify.evaluate({"temperature": 25.0})
        rule_ids = [t["rule_id"] for t in triggered]
        assert "notify_high_temp" not in rule_ids

    def test_ph_rule_triggers_on_acidic(self, engine_with_notify):
        triggered = engine_with_notify.evaluate({"ph": 4.5})
        rule_ids = [t["rule_id"] for t in triggered]
        assert "notify_low_ph" in rule_ids

    def test_multiple_sensors_trigger_independently(self, engine_with_notify):
        triggered = engine_with_notify.evaluate({
            "temperature": 32.0,
            "ph": 4.5,
        })
        rule_ids = [t["rule_id"] for t in triggered]
        assert "notify_high_temp" in rule_ids
        assert "notify_low_ph" in rule_ids


# ── Dashboard Formatting ─────────────────────────────────────


class TestDashboardFormat:

    def test_gauge_empty(self):
        assert _gauge(0, 0, 100, width=10) == "\u25b1" * 10

    def test_gauge_full(self):
        assert _gauge(100, 0, 100, width=10) == "\u25b0" * 10

    def test_gauge_half(self):
        bar = _gauge(50, 0, 100, width=10)
        assert bar == "\u25b0" * 5 + "\u25b1" * 5

    def test_gauge_clamps_above_max(self):
        bar = _gauge(200, 0, 100, width=10)
        assert bar == "\u25b0" * 10

    def test_sensor_status_normal(self):
        label, icon = _sensor_status(25.0, 15, 30)
        assert label == "Normal"
        assert "\u2705" in icon

    def test_sensor_status_high(self):
        label, icon = _sensor_status(35.0, 15, 30)
        assert label == "Alto"
        assert "\u26a0" in icon

    def test_sensor_status_low(self):
        label, icon = _sensor_status(10.0, 15, 30)
        assert label == "Baixo"
        assert "\u26a0" in icon

    def test_format_body_contains_dashboard(self):
        ch = FakeChannel()
        svc = NotificationService(channels=[ch], cooldown_seconds=0)
        sensor_data = {"temperature": 31.5, "humidity": 45.0}

        svc.notify("test_rule", "warning", "Test", sensor_data)

        body = ch.sent[0]["body"]
        assert "Painel de Sensores" in body
        assert "Temperatura" in body
        assert "31.5" in body
        assert "Humidade" in body
        assert "45.0" in body
        assert "Faixa ideal" in body

    def test_format_body_shows_status_icons(self):
        ch = FakeChannel()
        svc = NotificationService(channels=[ch], cooldown_seconds=0)
        # temperature 31.5 is above max 30 → Alto
        svc.notify("r1", "warning", "Test", {"temperature": 31.5})
        body = ch.sent[0]["body"]
        assert "Alto" in body

    def test_format_body_unknown_sensor_falls_back(self):
        ch = FakeChannel()
        svc = NotificationService(channels=[ch], cooldown_seconds=0)
        svc.notify("r1", "info", "Test", {"unknown_sensor": 42})
        body = ch.sent[0]["body"]
        assert "unknown_sensor: 42" in body


# ── Full Pipeline: Arduino Input → Rules → Alerts + Commands ──


class TestArduinoAlertPipeline:
    """
    End-to-end tests simulating real Arduino DHT20 sensor data flowing
    through the rule engine and triggering notifications + LED commands.
    Mirrors the POST /api/data handler in server.py.
    """

    FULL_RULES = [
        {
            "id": "ac_cooling", "name": "AC Auto Cooling", "enabled": True,
            "sensor": "temperature", "condition": "above", "threshold": 28.0,
            "action": {"type": "ac", "command": "cool", "target_temp": 24}
        },
        {
            "id": "ac_shutoff", "name": "AC Auto Shutoff", "enabled": True,
            "sensor": "temperature", "condition": "below", "threshold": 18.0,
            "action": {"type": "ac", "command": "off"}
        },
        {
            "id": "led_high_temp", "name": "LED Blink on High Temp", "enabled": True,
            "sensor": "temperature", "condition": "above", "threshold": 16.0,
            "action": {"type": "arduino", "command": "led_blink"}
        },
        {
            "id": "led_high_humidity", "name": "LED Blink on High Humidity", "enabled": True,
            "sensor": "humidity", "condition": "above", "threshold": 60.0,
            "action": {"type": "arduino", "command": "led_blink"}
        },
        {
            "id": "notify_high_temp", "name": "Alert: Temperature Too High", "enabled": True,
            "sensor": "temperature", "condition": "above", "threshold": 30.0,
            "action": {"type": "notify", "severity": "critical", "message": "Temperature too high for hydroponics"}
        },
        {
            "id": "notify_low_temp", "name": "Alert: Temperature Too Low", "enabled": True,
            "sensor": "temperature", "condition": "below", "threshold": 15.0,
            "action": {"type": "notify", "severity": "warning", "message": "Temperature too low for hydroponics"}
        },
        {
            "id": "notify_high_humidity", "name": "Alert: Humidity Too High", "enabled": True,
            "sensor": "humidity", "condition": "above", "threshold": 80.0,
            "action": {"type": "notify", "severity": "warning", "message": "Humidity too high — risk of mold"}
        },
        {
            "id": "notify_low_humidity", "name": "Alert: Humidity Too Low", "enabled": True,
            "sensor": "humidity", "condition": "below", "threshold": 40.0,
            "action": {"type": "notify", "severity": "warning", "message": "Humidity too low — plants may dehydrate"}
        },
    ]

    @pytest.fixture
    def pipeline(self, tmp_path):
        """Set up rule engine + notification service with full rules."""
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(json.dumps({"rules": self.FULL_RULES}))
        engine = RuleEngine(rules_file)
        channel = FakeChannel("test_channel")
        notifier = NotificationService(channels=[channel], cooldown_seconds=0)
        return engine, notifier, channel

    def _run_pipeline(self, engine, notifier, sensor_data, sensor_id="arduino_1"):
        """Simulate the POST /api/data flow from server.py."""
        triggered = engine.evaluate(sensor_data, sensor_id)

        notify_actions = [t for t in triggered if t['action'].get('type') == 'notify']
        for t in notify_actions:
            notifier.notify(
                rule_id=t['rule_id'],
                severity=t['action'].get('severity', 'warning'),
                message=t['action'].get('message', t['rule_name']),
                sensor_data=sensor_data,
            )

        commands = engine.get_pending_commands(sensor_id)
        return triggered, commands

    # ── Normal readings: no alerts ────────────────────────────

    def test_normal_readings_no_alerts(self, pipeline):
        """Normal temp+humidity should not trigger any notifications."""
        engine, notifier, channel = pipeline
        triggered, commands = self._run_pipeline(
            engine, notifier, {"temperature": 22.0, "humidity": 55.0}
        )

        notify_triggers = [t for t in triggered if t['action']['type'] == 'notify']
        assert len(notify_triggers) == 0
        assert len(channel.sent) == 0

    def test_normal_readings_led_blinks(self, pipeline):
        """Temp 22 is above LED threshold (16), so LED should blink."""
        engine, notifier, channel = pipeline
        triggered, commands = self._run_pipeline(
            engine, notifier, {"temperature": 22.0, "humidity": 55.0}
        )

        assert commands.get("led") == "blink"

    def test_cold_readings_led_off(self, pipeline):
        """Temp 10 is below LED threshold (16) and humidity 50 is below 60 — LED off."""
        engine, notifier, channel = pipeline
        triggered, commands = self._run_pipeline(
            engine, notifier, {"temperature": 10.0, "humidity": 50.0}
        )

        assert commands.get("led") == "off"

    # ── High temperature: critical alert + AC + LED ───────────

    def test_high_temp_triggers_critical_alert(self, pipeline):
        """Temp 32 should fire notify_high_temp with critical severity."""
        engine, notifier, channel = pipeline
        triggered, commands = self._run_pipeline(
            engine, notifier, {"temperature": 32.0, "humidity": 55.0}
        )

        assert len(channel.sent) == 1
        assert "[CRITICAL]" in channel.sent[0]["subject"]
        assert "Temperature too high" in channel.sent[0]["subject"]

    def test_high_temp_triggers_ac_cooling(self, pipeline):
        """Temp 32 should also trigger AC cooling rule."""
        engine, notifier, channel = pipeline
        triggered, _ = self._run_pipeline(
            engine, notifier, {"temperature": 32.0, "humidity": 55.0}
        )

        ac_triggers = [t for t in triggered if t['action']['type'] == 'ac']
        assert len(ac_triggers) == 1
        assert ac_triggers[0]['rule_id'] == 'ac_cooling'
        assert ac_triggers[0]['action']['command'] == 'cool'
        assert ac_triggers[0]['action']['target_temp'] == 24

    def test_high_temp_led_blinks(self, pipeline):
        """Temp 32 is above LED threshold — LED should blink."""
        engine, notifier, channel = pipeline
        _, commands = self._run_pipeline(
            engine, notifier, {"temperature": 32.0, "humidity": 55.0}
        )

        assert commands.get("led") == "blink"

    # ── Low temperature: warning alert + AC off ───────────────

    def test_low_temp_triggers_warning_alert(self, pipeline):
        """Temp 12 should fire notify_low_temp with warning severity."""
        engine, notifier, channel = pipeline
        triggered, _ = self._run_pipeline(
            engine, notifier, {"temperature": 12.0, "humidity": 55.0}
        )

        assert len(channel.sent) == 1
        assert "[WARNING]" in channel.sent[0]["subject"]
        assert "Temperature too low" in channel.sent[0]["subject"]

    def test_low_temp_triggers_ac_shutoff(self, pipeline):
        """Temp 12 should trigger AC shutoff rule."""
        engine, notifier, channel = pipeline
        triggered, _ = self._run_pipeline(
            engine, notifier, {"temperature": 12.0, "humidity": 55.0}
        )

        ac_triggers = [t for t in triggered if t['action']['type'] == 'ac']
        assert len(ac_triggers) == 1
        assert ac_triggers[0]['action']['command'] == 'off'

    # ── High humidity: warning alert + LED ────────────────────

    def test_high_humidity_triggers_warning(self, pipeline):
        """Humidity 85 should fire notify_high_humidity."""
        engine, notifier, channel = pipeline
        triggered, _ = self._run_pipeline(
            engine, notifier, {"temperature": 22.0, "humidity": 85.0}
        )

        assert len(channel.sent) == 1
        assert "Humidity too high" in channel.sent[0]["subject"]
        assert "mold" in channel.sent[0]["body"]

    def test_high_humidity_led_blinks(self, pipeline):
        """Humidity 85 is above LED humidity threshold — LED should blink."""
        engine, notifier, channel = pipeline
        _, commands = self._run_pipeline(
            engine, notifier, {"temperature": 22.0, "humidity": 85.0}
        )

        assert commands.get("led") == "blink"

    # ── Low humidity: warning alert ───────────────────────────

    def test_low_humidity_triggers_warning(self, pipeline):
        """Humidity 30 should fire notify_low_humidity."""
        engine, notifier, channel = pipeline
        triggered, _ = self._run_pipeline(
            engine, notifier, {"temperature": 22.0, "humidity": 30.0}
        )

        assert len(channel.sent) == 1
        assert "Humidity too low" in channel.sent[0]["subject"]
        assert "dehydrate" in channel.sent[0]["body"]

    # ── Multiple alerts at once ───────────────────────────────

    def test_high_temp_and_high_humidity_both_alert(self, pipeline):
        """Temp 32 + humidity 85 should fire BOTH notification rules."""
        engine, notifier, channel = pipeline
        triggered, _ = self._run_pipeline(
            engine, notifier, {"temperature": 32.0, "humidity": 85.0}
        )

        assert len(channel.sent) == 2
        subjects = [m["subject"] for m in channel.sent]
        assert any("Temperature too high" in s for s in subjects)
        assert any("Humidity too high" in s for s in subjects)

    def test_low_temp_and_low_humidity_both_alert(self, pipeline):
        """Temp 12 + humidity 30 should fire both low-end notifications."""
        engine, notifier, channel = pipeline
        triggered, _ = self._run_pipeline(
            engine, notifier, {"temperature": 12.0, "humidity": 30.0}
        )

        assert len(channel.sent) == 2
        subjects = [m["subject"] for m in channel.sent]
        assert any("Temperature too low" in s for s in subjects)
        assert any("Humidity too low" in s for s in subjects)

    # ── Alert body contains sensor dashboard ──────────────────

    def test_alert_body_includes_sensor_dashboard(self, pipeline):
        """Alert body should include the sensor data dashboard."""
        engine, notifier, channel = pipeline
        self._run_pipeline(
            engine, notifier, {"temperature": 32.0, "humidity": 55.0}
        )

        body = channel.sent[0]["body"]
        assert "Painel de Sensores" in body
        assert "Temperatura" in body
        assert "32.0" in body
        assert "Humidade" in body
        assert "55.0" in body

    # ── Cooldown prevents duplicate alerts ────────────────────

    def test_repeated_readings_respect_cooldown(self, tmp_path):
        """Same rule should not fire twice within cooldown window."""
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(json.dumps({"rules": self.FULL_RULES}))
        engine = RuleEngine(rules_file)
        channel = FakeChannel("test_channel")
        notifier = NotificationService(channels=[channel], cooldown_seconds=60)

        self._run_pipeline(engine, notifier, {"temperature": 32.0, "humidity": 55.0})
        self._run_pipeline(engine, notifier, {"temperature": 33.0, "humidity": 55.0})

        # Only 1 alert despite 2 high-temp readings (cooldown blocks the second)
        assert len(channel.sent) == 1

    # ── Boundary values ───────────────────────────────────────

    def test_exactly_at_threshold_no_alert(self, pipeline):
        """Values exactly at threshold should NOT trigger (strict inequality)."""
        engine, notifier, channel = pipeline
        self._run_pipeline(
            engine, notifier, {"temperature": 30.0, "humidity": 80.0}
        )

        assert len(channel.sent) == 0

    def test_just_above_threshold_triggers(self, pipeline):
        """Values just above threshold should trigger."""
        engine, notifier, channel = pipeline
        self._run_pipeline(
            engine, notifier, {"temperature": 30.1, "humidity": 80.1}
        )

        assert len(channel.sent) == 2
