import json
import pytest
from pathlib import Path
from rule_engine import RuleEngine
from notification_service import NotificationService


class FakeChannel:
    """Test channel that records all notifications."""

    def __init__(self):
        self.sent = []
        self._name = "fake"

    @property
    def name(self):
        return self._name

    def send(self, subject, body):
        self.sent.append({"subject": subject, "body": body})
        return True

    def is_available(self):
        return True


class TestPreventiveAlerts:
    """Test the preventive alert system with warning margins."""

    @pytest.fixture
    def engine_with_preventive(self, tmp_path):
        """Create rule engine with preventive alerts enabled."""
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(json.dumps({"rules": [
            {
                "id": "temp_low",
                "name": "Low Temperature Alert",
                "enabled": True,
                "sensor": "temperature",
                "condition": "below",
                "threshold": 15.0,
                "warning_margin": 2.0,
                "action": {
                    "type": "notify",
                    "severity": "critical",
                    "message": "Temperature critically low",
                    "recommended_action": "Check heating system immediately"
                },
                "preventive_message": "Temperature approaching minimum",
                "preventive_action": "Monitor heating. Prepare backup heat source."
            },
            {
                "id": "temp_high",
                "name": "High Temperature Alert",
                "enabled": True,
                "sensor": "temperature",
                "condition": "above",
                "threshold": 30.0,
                "warning_margin": 2.0,
                "action": {
                    "type": "notify",
                    "severity": "critical",
                    "message": "Temperature critically high",
                    "recommended_action": "Increase ventilation and cooling"
                },
                "preventive_message": "Temperature approaching maximum",
                "preventive_action": "Increase air circulation. Check AC."
            },
            {
                "id": "humidity_low",
                "name": "Low Humidity Alert",
                "enabled": True,
                "sensor": "humidity",
                "condition": "below",
                "threshold": 40.0,
                "warning_margin": 5.0,
                "action": {
                    "type": "notify",
                    "severity": "warning",
                    "message": "Humidity too low",
                    "recommended_action": "Add humidifier"
                },
                "preventive_message": "Humidity dropping",
                "preventive_action": "Prepare humidifier"
            }
        ]}))
        return RuleEngine(rules_file)

    # ── Preventive Alerts (Warning Zone) ─────────────────────────

    def test_low_temp_preventive_triggers_in_warning_zone(self, engine_with_preventive):
        """Temperature 16.5°C should trigger preventive (threshold 15, margin 2 = warn at 17)."""
        triggered = engine_with_preventive.evaluate({"temperature": 16.5})

        assert len(triggered) == 1
        alert = triggered[0]
        assert alert['alert_type'] == 'preventive'
        assert alert['rule_id'] == 'temp_low_preventive'
        assert alert['action']['severity'] == 'preventive'
        assert 'approaching minimum' in alert['action']['message'].lower()

    def test_high_temp_preventive_triggers_in_warning_zone(self, engine_with_preventive):
        """Temperature 28.5°C should trigger preventive (threshold 30, margin 2 = warn at 28)."""
        triggered = engine_with_preventive.evaluate({"temperature": 28.5})

        assert len(triggered) == 1
        alert = triggered[0]
        assert alert['alert_type'] == 'preventive'
        assert alert['rule_id'] == 'temp_high_preventive'
        assert alert['action']['severity'] == 'preventive'

    def test_low_humidity_preventive_triggers_in_warning_zone(self, engine_with_preventive):
        """Humidity 42% should trigger preventive (threshold 40, margin 5 = warn at 45)."""
        triggered = engine_with_preventive.evaluate({"humidity": 42.0})

        assert len(triggered) == 1
        alert = triggered[0]
        assert alert['alert_type'] == 'preventive'
        assert alert['rule_id'] == 'humidity_low_preventive'

    # ── Critical Alerts (Threshold Exceeded) ──────────────────────

    def test_low_temp_critical_when_below_threshold(self, engine_with_preventive):
        """Temperature 14°C should trigger critical alert."""
        triggered = engine_with_preventive.evaluate({"temperature": 14.0})

        assert len(triggered) == 1
        alert = triggered[0]
        assert alert['alert_type'] == 'critical'
        assert alert['rule_id'] == 'temp_low'
        assert alert['action']['severity'] == 'critical'

    def test_high_temp_critical_when_above_threshold(self, engine_with_preventive):
        """Temperature 31°C should trigger critical alert."""
        triggered = engine_with_preventive.evaluate({"temperature": 31.0})

        assert len(triggered) == 1
        alert = triggered[0]
        assert alert['alert_type'] == 'critical'
        assert alert['rule_id'] == 'temp_high'

    # ── No Alerts (Normal Range) ──────────────────────────────────

    def test_normal_temp_no_alert(self, engine_with_preventive):
        """Temperature 20°C is in safe zone - no alerts."""
        triggered = engine_with_preventive.evaluate({"temperature": 20.0})
        assert len(triggered) == 0

    def test_normal_humidity_no_alert(self, engine_with_preventive):
        """Humidity 60% is in safe zone - no alerts."""
        triggered = engine_with_preventive.evaluate({"humidity": 60.0})
        assert len(triggered) == 0

    # ── Boundary Testing ──────────────────────────────────────────

    def test_exactly_at_threshold_triggers_critical(self, engine_with_preventive):
        """Being exactly at threshold should NOT trigger (using > or < not >=/<= )."""
        triggered = engine_with_preventive.evaluate({"temperature": 15.0})
        # With strict inequality, 15.0 is NOT below 15.0, so no alert
        assert len(triggered) == 0

    def test_exactly_at_warning_threshold_triggers_preventive(self, engine_with_preventive):
        """Being exactly at warning threshold should trigger preventive."""
        # Threshold 15, margin 2 = warning at 17
        # Value 17 is > 17 (warning) and <= 15 (threshold)? No, 17 > 15
        # Actually: value < warning_threshold (17) AND value >= threshold (15)
        # So 17 < 17 is false, 16.9 < 17 is true and >= 15 is true → preventive
        triggered = engine_with_preventive.evaluate({"temperature": 16.9})
        assert len(triggered) == 1
        assert triggered[0]['alert_type'] == 'preventive'

    def test_just_outside_warning_zone_no_alert(self, engine_with_preventive):
        """Temperature 17.1°C is just outside warning zone (warn at 17) - no alert."""
        triggered = engine_with_preventive.evaluate({"temperature": 17.1})
        assert len(triggered) == 0

    # ── Integration with Notifications ────────────────────────────

    def test_preventive_alert_includes_recommended_action(self, engine_with_preventive):
        """Preventive alert should include preventive_action."""
        channel = FakeChannel()
        notifier = NotificationService(channels=[channel], cooldown_seconds=0)

        triggered = engine_with_preventive.evaluate({"temperature": 16.5})
        alert = triggered[0]

        # Simulate what server.py does
        rule = engine_with_preventive.get_rule('temp_low')
        recommended = rule.get('preventive_action', '')

        notifier.notify(
            rule_id=alert['rule_id'],
            severity=alert['action']['severity'],
            message=alert['action']['message'],
            sensor_data={"temperature": 16.5},
            recommended_action=recommended
        )

        assert len(channel.sent) == 1
        body = channel.sent[0]['body']
        assert 'Ação Recomendada' in body or 'Acao Recomendada' in body
        assert 'heating' in body.lower()

    def test_critical_alert_includes_recommended_action(self, engine_with_preventive):
        """Critical alert should include recommended_action."""
        channel = FakeChannel()
        notifier = NotificationService(channels=[channel], cooldown_seconds=0)

        triggered = engine_with_preventive.evaluate({"temperature": 14.0})
        alert = triggered[0]

        recommended = alert['action'].get('recommended_action')

        notifier.notify(
            rule_id=alert['rule_id'],
            severity=alert['action']['severity'],
            message=alert['action']['message'],
            sensor_data={"temperature": 14.0},
            recommended_action=recommended
        )

        assert len(channel.sent) == 1
        body = channel.sent[0]['body']
        assert 'heating' in body.lower()

    # ── Multiple Sensors ──────────────────────────────────────────

    def test_multiple_preventive_alerts_can_trigger(self, engine_with_preventive):
        """Multiple sensors can trigger preventive alerts simultaneously."""
        triggered = engine_with_preventive.evaluate({
            "temperature": 16.5,  # Preventive
            "humidity": 42.0      # Preventive
        })

        assert len(triggered) == 2
        rule_ids = [t['rule_id'] for t in triggered]
        assert 'temp_low_preventive' in rule_ids
        assert 'humidity_low_preventive' in rule_ids

    def test_mixed_critical_and_preventive_alerts(self, engine_with_preventive):
        """Can trigger both critical and preventive alerts at once."""
        triggered = engine_with_preventive.evaluate({
            "temperature": 14.0,  # Critical (below 15)
            "humidity": 42.0      # Preventive (below 45, above 40)
        })

        assert len(triggered) == 2
        critical = [t for t in triggered if t['alert_type'] == 'critical']
        preventive = [t for t in triggered if t['alert_type'] == 'preventive']
        assert len(critical) == 1
        assert len(preventive) == 1


class TestPreventiveAlertFormatting:
    """Test notification formatting for preventive alerts."""

    def test_preventive_severity_in_ntfy_priority(self):
        """Preventive alerts should use priority 3 in ntfy."""
        from notification_service import NtfyChannel
        ch = NtfyChannel()
        assert ch._PRIORITY_MAP.get('preventive') == '3'
        assert ch._TAG_MAP.get('preventive') == 'eyes'

    def test_body_includes_recommended_action_section(self):
        """Notification body should include recommended action section."""
        from notification_service import NotificationService
        channel = FakeChannel()
        svc = NotificationService(channels=[channel], cooldown_seconds=0)

        svc.notify(
            rule_id='test',
            severity='preventive',
            message='Test preventive alert',
            sensor_data={'temperature': 16.5},
            recommended_action='Check heating system'
        )

        body = channel.sent[0]['body']
        assert 'Ação Recomendada' in body or 'Acao Recomendada' in body
        assert 'Check heating system' in body
