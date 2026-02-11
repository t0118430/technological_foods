import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from rules.rule_engine import RuleEngine


@pytest.fixture
def engine(tmp_path):
    """Create a RuleEngine with a temporary rules file and default rules."""
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps({"rules": [
        {
            "id": "ac_cooling",
            "name": "AC Auto Cooling",
            "enabled": True,
            "sensor": "temperature",
            "condition": "above",
            "threshold": 28.0,
            "action": {"type": "ac", "command": "cool", "target_temp": 24}
        },
        {
            "id": "ac_shutoff",
            "name": "AC Auto Shutoff",
            "enabled": True,
            "sensor": "temperature",
            "condition": "below",
            "threshold": 18.0,
            "action": {"type": "ac", "command": "off"}
        },
        {
            "id": "led_high_temp",
            "name": "LED Blink on High Temp",
            "enabled": True,
            "sensor": "temperature",
            "condition": "above",
            "threshold": 16.0,
            "action": {"type": "arduino", "command": "led_blink"}
        },
        {
            "id": "led_high_humidity",
            "name": "LED Blink on High Humidity",
            "enabled": True,
            "sensor": "humidity",
            "condition": "above",
            "threshold": 60.0,
            "action": {"type": "arduino", "command": "led_blink"}
        }
    ]}))
    return RuleEngine(rules_file)


@pytest.fixture
def empty_engine(tmp_path):
    """Create a RuleEngine with no existing rules file."""
    rules_file = tmp_path / "rules.json"
    return RuleEngine(rules_file)


# ── Rule Evaluation ──────────────────────────────────────────


class TestRuleEvaluation:

    def test_above_threshold_triggers(self, engine):
        """Temperature above 28 should trigger AC cooling rule."""
        triggered = engine.evaluate({"temperature": 30.0})
        rule_ids = [t["rule_id"] for t in triggered]
        assert "ac_cooling" in rule_ids

    def test_below_threshold_triggers(self, engine):
        """Temperature below 18 should trigger AC shutoff rule."""
        triggered = engine.evaluate({"temperature": 15.0})
        rule_ids = [t["rule_id"] for t in triggered]
        assert "ac_shutoff" in rule_ids

    def test_at_threshold_does_not_trigger(self, engine):
        """Temperature exactly at threshold should NOT trigger (strict inequality)."""
        triggered = engine.evaluate({"temperature": 28.0})
        rule_ids = [t["rule_id"] for t in triggered]
        assert "ac_cooling" not in rule_ids

    def test_multiple_rules_can_fire(self, engine):
        """Temperature 30 triggers both ac_cooling AND led_high_temp."""
        triggered = engine.evaluate({"temperature": 30.0})
        rule_ids = [t["rule_id"] for t in triggered]
        assert "ac_cooling" in rule_ids
        assert "led_high_temp" in rule_ids

    def test_humidity_rule_triggers(self, engine):
        """Humidity above 60 should trigger LED blink."""
        triggered = engine.evaluate({"humidity": 65.0})
        rule_ids = [t["rule_id"] for t in triggered]
        assert "led_high_humidity" in rule_ids

    def test_sensor_not_in_data_skipped(self, engine):
        """Rules for sensors not in the data are silently skipped."""
        triggered = engine.evaluate({"pH": 7.0})
        # Only LED-related rules matter; none should fire for pH
        ac_triggers = [t for t in triggered if t["action"].get("type") == "ac"]
        assert len(ac_triggers) == 0

    def test_disabled_rule_skipped(self, engine):
        """Disabled rules should not fire."""
        engine.update_rule("ac_cooling", {"enabled": False})
        triggered = engine.evaluate({"temperature": 30.0})
        rule_ids = [t["rule_id"] for t in triggered]
        assert "ac_cooling" not in rule_ids

    def test_normal_temp_no_ac_trigger(self, engine):
        """Temperature 22 is within range — no AC rules should fire."""
        triggered = engine.evaluate({"temperature": 22.0})
        ac_triggers = [t for t in triggered if t["action"].get("type") == "ac"]
        assert len(ac_triggers) == 0


# ── Arduino Command Queue ────────────────────────────────────


class TestCommandQueue:

    def test_commands_queued_for_arduino(self, engine):
        """LED blink command should be queued when temp > 16."""
        engine.evaluate({"temperature": 20.0}, sensor_id="arduino_1")
        commands = engine.get_pending_commands("arduino_1")
        assert commands.get("led") == "blink"

    def test_commands_cleared_after_poll(self, engine):
        """After polling, the command queue should be empty."""
        engine.evaluate({"temperature": 20.0}, sensor_id="arduino_1")
        engine.get_pending_commands("arduino_1")
        commands = engine.get_pending_commands("arduino_1")
        assert commands == {}

    def test_led_off_when_no_led_rule_fires(self, engine):
        """If no LED rule fires, the default command is led=off."""
        engine.evaluate({"temperature": 10.0}, sensor_id="arduino_1")
        commands = engine.get_pending_commands("arduino_1")
        assert commands.get("led") == "off"

    def test_different_sensor_ids_independent(self, engine):
        """Commands for different sensor IDs don't interfere."""
        engine.evaluate({"temperature": 20.0}, sensor_id="arduino_1")
        engine.evaluate({"temperature": 10.0}, sensor_id="arduino_2")

        cmd1 = engine.get_pending_commands("arduino_1")
        cmd2 = engine.get_pending_commands("arduino_2")

        assert cmd1.get("led") == "blink"
        assert cmd2.get("led") == "off"


# ── CRUD Operations ──────────────────────────────────────────


class TestCRUD:

    def test_create_rule(self, engine):
        new_rule = {
            "id": "pump_low_moisture",
            "name": "Pump On Low Moisture",
            "sensor": "soil_moisture",
            "condition": "below",
            "threshold": 30.0,
            "action": {"type": "arduino", "command": "pump_on"}
        }
        result = engine.create_rule(new_rule)
        assert result["id"] == "pump_low_moisture"
        assert engine.get_rule("pump_low_moisture") is not None

    def test_create_duplicate_fails(self, engine):
        with pytest.raises(ValueError, match="already exists"):
            engine.create_rule({
                "id": "ac_cooling",
                "sensor": "temperature",
                "condition": "above",
                "threshold": 30.0,
                "action": {"type": "ac", "command": "cool"}
            })

    def test_create_missing_fields_fails(self, engine):
        with pytest.raises(ValueError, match="Missing required"):
            engine.create_rule({"id": "incomplete"})

    def test_create_invalid_condition_fails(self, engine):
        with pytest.raises(ValueError, match="Condition must be"):
            engine.create_rule({
                "id": "bad_cond",
                "sensor": "temperature",
                "condition": "equals",
                "threshold": 20.0,
                "action": {"type": "arduino", "command": "led_on"}
            })

    def test_update_rule(self, engine):
        result = engine.update_rule("ac_cooling", {"threshold": 30.0})
        assert result["threshold"] == 30.0
        assert engine.get_rule("ac_cooling")["threshold"] == 30.0

    def test_update_nonexistent_returns_none(self, engine):
        result = engine.update_rule("nonexistent", {"threshold": 99.0})
        assert result is None

    def test_update_cannot_override_id(self, engine):
        engine.update_rule("ac_cooling", {"id": "hacked", "threshold": 30.0})
        assert engine.get_rule("ac_cooling") is not None
        assert engine.get_rule("hacked") is None

    def test_delete_rule(self, engine):
        assert engine.delete_rule("ac_cooling") is True
        assert engine.get_rule("ac_cooling") is None

    def test_delete_nonexistent_returns_false(self, engine):
        assert engine.delete_rule("nonexistent") is False

    def test_get_rules_returns_all(self, engine):
        rules = engine.get_rules()
        assert len(rules) == 4


# ── Persistence ──────────────────────────────────────────────


class TestPersistence:

    def test_rules_persist_to_file(self, tmp_path):
        """Rules survive save/load cycle."""
        rules_file = tmp_path / "rules.json"
        engine1 = RuleEngine(rules_file)
        engine1.create_rule({
            "id": "test_rule",
            "sensor": "temperature",
            "condition": "above",
            "threshold": 25.0,
            "action": {"type": "arduino", "command": "led_on"}
        })

        # Create new engine from same file
        engine2 = RuleEngine(rules_file)
        assert engine2.get_rule("test_rule") is not None
        assert engine2.get_rule("test_rule")["threshold"] == 25.0

    def test_empty_start(self, empty_engine):
        """Engine with no file starts with empty rules."""
        assert empty_engine.get_rules() == []

    def test_delete_persists(self, engine):
        """Deleted rules are removed from the file."""
        engine.delete_rule("ac_cooling")
        engine2 = RuleEngine(engine.rules_file)
        assert engine2.get_rule("ac_cooling") is None
        assert len(engine2.get_rules()) == 3
