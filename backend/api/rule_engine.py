import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger('rule-engine')

RULES_FILE = Path(__file__).resolve().parent / 'rules_config.json'


class RuleEngine:
    def __init__(self, rules_file: Path = RULES_FILE):
        self.rules_file = rules_file
        self.rules: List[Dict[str, Any]] = []
        self.pending_commands: Dict[str, Dict[str, Any]] = {}
        self.load_rules()

    # ── Persistence ──────────────────────────────────────────

    def load_rules(self):
        """Load rules from JSON file. If missing, start with empty list."""
        if self.rules_file.exists():
            with open(self.rules_file, 'r') as f:
                data = json.load(f)
            self.rules = data.get('rules', [])
            logger.info(f"Loaded {len(self.rules)} rules from {self.rules_file.name}")
        else:
            self.rules = []
            logger.info("No rules file found — starting with empty rule set")

    def save_rules(self):
        """Persist current rules to JSON file."""
        with open(self.rules_file, 'w') as f:
            json.dump({'rules': self.rules}, f, indent=2)
        logger.info(f"Saved {len(self.rules)} rules to {self.rules_file.name}")

    # ── CRUD ─────────────────────────────────────────────────

    def get_rules(self) -> List[Dict[str, Any]]:
        return self.rules

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        for rule in self.rules:
            if rule['id'] == rule_id:
                return rule
        return None

    def create_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new rule. Requires at least: id, sensor, condition, threshold, action."""
        required = {'id', 'sensor', 'condition', 'threshold', 'action'}
        missing = required - set(rule.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        if self.get_rule(rule['id']):
            raise ValueError(f"Rule '{rule['id']}' already exists")
        if rule['condition'] not in ('above', 'below'):
            raise ValueError("Condition must be 'above' or 'below'")

        rule.setdefault('name', rule['id'])
        rule.setdefault('enabled', True)
        self.rules.append(rule)
        self.save_rules()
        return rule

    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update fields of an existing rule. Returns updated rule or None."""
        for rule in self.rules:
            if rule['id'] == rule_id:
                if 'condition' in updates and updates['condition'] not in ('above', 'below'):
                    raise ValueError("Condition must be 'above' or 'below'")
                rule.update(updates)
                rule['id'] = rule_id  # prevent id override
                self.save_rules()
                return rule
        return None

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule by id. Returns True if found and deleted."""
        before = len(self.rules)
        self.rules = [r for r in self.rules if r['id'] != rule_id]
        if len(self.rules) < before:
            self.save_rules()
            return True
        return False

    # ── Evaluation ───────────────────────────────────────────

    def evaluate(self, sensor_data: Dict[str, Any], sensor_id: str = "arduino_1") -> List[Dict[str, Any]]:
        """
        Evaluate all enabled rules against incoming sensor data.
        Returns list of triggered actions.
        Arduino-type actions are queued for polling.

        Supports preventive alerts with warning_margin:
        - If warning_margin is set, triggers preventive alert before reaching threshold
        - Preventive alerts use severity="preventive" by default
        """
        triggered = []

        for rule in self.rules:
            if not rule.get('enabled', True):
                continue

            sensor_key = rule['sensor']
            if sensor_key not in sensor_data:
                continue

            value = float(sensor_data[sensor_key])
            threshold = float(rule['threshold'])
            condition = rule['condition']
            warning_margin = rule.get('warning_margin', 0)

            # Check critical threshold
            critical_fired = (
                (condition == 'above' and value > threshold) or
                (condition == 'below' and value < threshold)
            )

            # Check preventive/warning threshold (if warning_margin is set)
            preventive_fired = False
            if warning_margin > 0:
                if condition == 'above':
                    warning_threshold = threshold - warning_margin
                    # Preventive fires when: warning < value < threshold (approaching from below)
                    preventive_fired = value > warning_threshold and value < threshold
                elif condition == 'below':
                    warning_threshold = threshold + warning_margin
                    # Preventive fires when: threshold < value < warning (approaching from above)
                    preventive_fired = value < warning_threshold and value > threshold

            # Fire critical alert
            if critical_fired:
                action = rule['action'].copy()
                triggered.append({
                    'rule_id': rule['id'],
                    'rule_name': rule.get('name', rule['id']),
                    'action': action,
                    'alert_type': 'critical'
                })

                if action.get('type') == 'arduino':
                    self._queue_arduino_command(sensor_id, action)

                logger.info(
                    f"Rule '{rule['id']}' fired (CRITICAL): {sensor_key}={value} "
                    f"{condition} {threshold} → {action}"
                )

            # Fire preventive alert
            elif preventive_fired:
                action = rule['action'].copy()
                # Override severity to preventive if it's a notification
                if action.get('type') == 'notify':
                    action['severity'] = 'preventive'
                    # Add preventive message if available
                    if 'preventive_message' in rule:
                        action['message'] = rule['preventive_message']
                    else:
                        action['message'] = f"Approaching limit: {rule.get('message', rule['name'])}"

                triggered.append({
                    'rule_id': rule['id'] + '_preventive',
                    'rule_name': f"{rule.get('name', rule['id'])} (Preventive)",
                    'action': action,
                    'alert_type': 'preventive',
                    'warning_threshold': warning_threshold,
                    'critical_threshold': threshold
                })

                logger.info(
                    f"Rule '{rule['id']}' fired (PREVENTIVE): {sensor_key}={value} "
                    f"approaching {condition} {threshold} (warning at {warning_threshold}) → {action}"
                )

        # If no arduino led rule fired, default LED off
        led_fired = any(
            t['action'].get('type') == 'arduino' and 'led' in t['action'].get('command', '')
            for t in triggered
        )
        if not led_fired:
            self._queue_arduino_command(sensor_id, {'type': 'arduino', 'command': 'led_off'})

        return triggered

    def _queue_arduino_command(self, sensor_id: str, action: Dict[str, Any]):
        """Add a command to the pending queue for an Arduino."""
        if sensor_id not in self.pending_commands:
            self.pending_commands[sensor_id] = {}

        command = action.get('command', '')
        if command.startswith('led'):
            # Normalize: led_on → on, led_off → off, led_blink → blink
            led_state = command.replace('led_', '')
            self.pending_commands[sensor_id]['led'] = led_state

    def get_pending_commands(self, sensor_id: str) -> Dict[str, Any]:
        """Get and clear pending commands for a sensor/arduino."""
        commands = self.pending_commands.pop(sensor_id, {})
        return commands
