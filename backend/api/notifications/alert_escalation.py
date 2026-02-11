"""
Alert Escalation System - Enterprise-grade monitoring with smart escalation.

Prevents alert spam while ensuring critical issues get attention through
progressive priority escalation when user doesn't take action.

Author: AgriTech Hydroponics
License: MIT
"""

import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger('alert-escalation')


@dataclass
class EscalationLevel:
    """Defines an escalation level with timing and messaging."""
    name: str
    severity: str
    priority: int  # 1-5 for ntfy
    wait_minutes: int  # How long to wait before escalating to next level
    message_template: str
    suggested_action: str
    tags: str = ""  # ntfy tags


# Escalation sequence configuration
ESCALATION_LEVELS = [
    EscalationLevel(
        name="PREVENTIVE",
        severity="preventive",
        priority=3,
        wait_minutes=5,
        message_template="{original_message}",
        suggested_action="Monitor the situation. {preventive_action}",
        tags="eyes"
    ),
    EscalationLevel(
        name="WARNING",
        severity="warning",
        priority=4,
        wait_minutes=10,
        message_template="⚠️ ESCALATED: {sensor_name} still out of range - {original_message}",
        suggested_action="Please take action soon. {recommended_action}",
        tags="warning"
    ),
    EscalationLevel(
        name="CRITICAL",
        severity="critical",
        priority=5,
        wait_minutes=15,
        message_template="🚨 CRITICAL: {sensor_name} not improving - {original_message}",
        suggested_action="URGENT: {recommended_action}",
        tags="rotating_light"
    ),
    EscalationLevel(
        name="URGENT",
        severity="urgent",
        priority=5,
        wait_minutes=15,
        message_template="🔴 ACTION REQUIRED: {sensor_name} needs immediate intervention - {original_message}",
        suggested_action="IMMEDIATE ACTION NEEDED: {recommended_action}. Consider contacting support for assistance.",
        tags="rotating_light,sos"
    ),
]


@dataclass
class AlertState:
    """Tracks the state of an active alert."""
    rule_id: str
    sensor: str
    original_value: float
    threshold: float
    condition: str  # 'above' or 'below'
    first_triggered: float  # timestamp
    last_sent: float  # timestamp
    escalation_level: int = 0  # Index into ESCALATION_LEVELS
    sent_count: int = 0
    worst_value: float = None  # Track if getting worse
    original_message: str = ""
    preventive_action: str = ""
    recommended_action: str = ""

    def __post_init__(self):
        if self.worst_value is None:
            self.worst_value = self.original_value


class AlertEscalationManager:
    """
    Manages alert escalation lifecycle.

    Responsibilities:
    - Track active alerts
    - Determine when to escalate
    - Detect user action (problem improving)
    - Clear resolved alerts
    - Prevent spam
    """

    def __init__(self):
        self.active_alerts: Dict[str, AlertState] = {}
        self.resolved_alerts: List[Dict[str, Any]] = []
        self.max_history = 100

    def should_send_alert(self, rule_id: str, sensor: str, current_value: float,
                         threshold: float, condition: str,
                         original_message: str = "",
                         preventive_action: str = "",
                         recommended_action: str = "") -> Optional[Dict[str, Any]]:
        """
        Determine if an alert should be sent and at what escalation level.

        Returns:
            None if alert should be suppressed (too soon to escalate)
            Dict with escalation info if alert should be sent
        """
        now = time.time()

        # Check if this is a new alert
        if rule_id not in self.active_alerts:
            # New alert - send at preventive level
            self.active_alerts[rule_id] = AlertState(
                rule_id=rule_id,
                sensor=sensor,
                original_value=current_value,
                threshold=threshold,
                condition=condition,
                first_triggered=now,
                last_sent=now,
                escalation_level=0,
                original_message=original_message,
                preventive_action=preventive_action,
                recommended_action=recommended_action
            )
            return self._build_alert_info(rule_id, current_value)

        # Existing alert - check if we should escalate
        alert = self.active_alerts[rule_id]

        # Check if situation is improving (user took action)
        if self._is_improving(alert, current_value):
            logger.info(f"Alert {rule_id}: Situation improving, not escalating")
            # Don't escalate, but update tracking
            alert.worst_value = current_value
            return None  # Suppress alert - user is fixing it

        # Check if situation is getting worse
        if self._is_getting_worse(alert, current_value):
            alert.worst_value = current_value
            logger.warning(f"Alert {rule_id}: Situation worsening! {alert.original_value} → {current_value}")

        # Check if enough time has passed to escalate
        current_level_config = ESCALATION_LEVELS[alert.escalation_level]
        time_since_last = (now - alert.last_sent) / 60  # minutes

        if time_since_last < current_level_config.wait_minutes:
            # Too soon to send again
            return None

        # Time to escalate!
        if alert.escalation_level < len(ESCALATION_LEVELS) - 1:
            alert.escalation_level += 1
            logger.info(f"Alert {rule_id}: Escalating to level {alert.escalation_level}")
        else:
            # Already at max level, keep repeating
            logger.warning(f"Alert {rule_id}: At max escalation, repeating URGENT alert")

        alert.last_sent = now
        alert.sent_count += 1

        return self._build_alert_info(rule_id, current_value)

    def _is_improving(self, alert: AlertState, current_value: float) -> bool:
        """Check if the situation is improving (moving away from danger)."""
        if alert.condition == 'above':
            # For 'above' threshold, improving means decreasing value
            return current_value < alert.worst_value
        else:  # 'below'
            # For 'below' threshold, improving means increasing value
            return current_value > alert.worst_value

    def _is_getting_worse(self, alert: AlertState, current_value: float) -> bool:
        """Check if the situation is getting worse (moving toward danger)."""
        if alert.condition == 'above':
            # For 'above' threshold, worse means increasing value
            return current_value > alert.worst_value
        else:  # 'below'
            # For 'below' threshold, worse means decreasing value
            return current_value < alert.worst_value

    def _build_alert_info(self, rule_id: str, current_value: float) -> Dict[str, Any]:
        """Build alert information for current escalation level."""
        alert = self.active_alerts[rule_id]
        level = ESCALATION_LEVELS[alert.escalation_level]

        # Calculate time since first alert
        elapsed_minutes = (time.time() - alert.first_triggered) / 60

        return {
            'should_send': True,
            'escalation_level': alert.escalation_level,
            'level_name': level.name,
            'severity': level.severity,
            'priority': level.priority,
            'tags': level.tags,
            'message': level.message_template.format(
                sensor_name=alert.sensor.replace('_', ' ').title(),
                original_message=alert.original_message,
            ),
            'suggested_action': level.suggested_action.format(
                preventive_action=alert.preventive_action,
                recommended_action=alert.recommended_action,
            ),
            'current_value': current_value,
            'threshold': alert.threshold,
            'elapsed_minutes': int(elapsed_minutes),
            'sent_count': alert.sent_count,
            'is_worsening': current_value == alert.worst_value and alert.worst_value != alert.original_value,
        }

    def clear_alert(self, rule_id: str, current_value: float, reason: str = "resolved"):
        """Clear an active alert when situation is resolved."""
        if rule_id not in self.active_alerts:
            return None

        alert = self.active_alerts.pop(rule_id)

        # Record in history
        resolution = {
            'rule_id': rule_id,
            'sensor': alert.sensor,
            'resolved_at': datetime.now().isoformat(),
            'duration_minutes': int((time.time() - alert.first_triggered) / 60),
            'max_escalation': ESCALATION_LEVELS[alert.escalation_level].name,
            'alerts_sent': alert.sent_count,
            'original_value': alert.original_value,
            'final_value': current_value,
            'reason': reason,
        }

        self.resolved_alerts.append(resolution)
        if len(self.resolved_alerts) > self.max_history:
            self.resolved_alerts = self.resolved_alerts[-self.max_history:]

        logger.info(
            f"Alert {rule_id} resolved: {alert.sensor} {alert.original_value}→{current_value} "
            f"after {resolution['duration_minutes']} min, {alert.sent_count} alerts sent"
        )

        return resolution

    def check_for_resolved_alerts(self, sensor_data: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Check if any active alerts have been resolved (values back in safe zone).

        Returns list of resolution info for alerts that were cleared.
        """
        resolved = []
        rules_to_clear = []

        for rule_id, alert in self.active_alerts.items():
            sensor_value = sensor_data.get(alert.sensor)
            if sensor_value is None:
                continue

            # Check if value is now in safe zone
            is_safe = False
            if alert.condition == 'above':
                is_safe = sensor_value <= alert.threshold
            else:  # 'below'
                is_safe = sensor_value >= alert.threshold

            if is_safe:
                rules_to_clear.append((rule_id, sensor_value))

        # Clear resolved alerts
        for rule_id, final_value in rules_to_clear:
            resolution = self.clear_alert(rule_id, final_value, "back_to_safe_zone")
            if resolution:
                resolved.append(resolution)

        return resolved

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get summary of all active alerts."""
        now = time.time()
        result = []

        for rule_id, alert in self.active_alerts.items():
            level = ESCALATION_LEVELS[alert.escalation_level]
            elapsed_minutes = int((now - alert.first_triggered) / 60)

            result.append({
                'rule_id': rule_id,
                'sensor': alert.sensor,
                'escalation_level': level.name,
                'elapsed_minutes': elapsed_minutes,
                'alerts_sent': alert.sent_count,
                'current_value': alert.worst_value,
                'threshold': alert.threshold,
            })

        return result

    def get_status(self) -> Dict[str, Any]:
        """Get overall escalation system status."""
        return {
            'active_alerts': len(self.active_alerts),
            'active_alert_details': self.get_active_alerts(),
            'recent_resolutions': self.resolved_alerts[-10:],
            'escalation_levels': [
                {
                    'name': level.name,
                    'severity': level.severity,
                    'wait_minutes': level.wait_minutes,
                }
                for level in ESCALATION_LEVELS
            ],
        }


# Global instance
escalation_manager = AlertEscalationManager()
