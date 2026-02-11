import os
import time
import logging
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger('notification-service')

COOLDOWN_SECONDS = int(os.getenv('NOTIFICATION_COOLDOWN', '900'))
MAX_HISTORY = 50

# ── Sensor Metadata (for dashboard formatting) ───────────────

SENSOR_META = {
    "temperature": {"label": "Temperatura",  "unit": "°C",    "min": 15,  "max": 30,  "abs_min": 0,   "abs_max": 50,  "emoji": "\U0001f321\ufe0f"},
    "humidity":    {"label": "Humidade",     "unit": "%",     "min": 40,  "max": 80,  "abs_min": 0,   "abs_max": 100, "emoji": "\U0001f4a7"},
    "ph":          {"label": "pH",           "unit": "",      "min": 5.5, "max": 7.0, "abs_min": 0,   "abs_max": 14,  "emoji": "\U0001f9ea"},
    "ec":          {"label": "EC",           "unit": " mS/cm","min": 0.8, "max": 2.5, "abs_min": 0,   "abs_max": 5,   "emoji": "\u26a1"},
    "water_level": {"label": "Nivel Agua",   "unit": "%",     "min": 20,  "max": 100, "abs_min": 0,   "abs_max": 100, "emoji": "\U0001f6b0"},
    "light":       {"label": "Luz",          "unit": " lux",  "min": 200, "max": 8000,"abs_min": 0,   "abs_max": 10000,"emoji": "\u2600\ufe0f"},
}


def _gauge(value: float, abs_min: float, abs_max: float, width: int = 12) -> str:
    """Build a simple visual gauge bar."""
    span = abs_max - abs_min
    ratio = (value - abs_min) / span if span > 0 else 0
    ratio = max(0.0, min(1.0, ratio))
    filled = round(ratio * width)
    return '\u25b0' * filled + '\u25b1' * (width - filled)


def _sensor_status(value: float, ideal_min: float, ideal_max: float):
    """Return (label, icon) for a sensor reading."""
    if ideal_min <= value <= ideal_max:
        return "Normal", "\u2705"
    elif value > ideal_max:
        return "Alto", "\u26a0\ufe0f"
    else:
        return "Baixo", "\u26a0\ufe0f"


# ── Channel Interface ─────────────────────────────────────────

class NotificationChannel(ABC):
    """Abstract base for notification channels (WhatsApp, SMS, Email, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def send(self, subject: str, body: str) -> bool:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


# ── Concrete Channels ─────────────────────────────────────────

class ConsoleChannel(NotificationChannel):
    """Prints alerts to console/logger. Always available."""

    @property
    def name(self) -> str:
        return "console"

    def send(self, subject: str, body: str) -> bool:
        logger.warning(f"[ALERT] {subject}\n{body}")
        return True

    def is_available(self) -> bool:
        return True


class WhatsAppChannel(NotificationChannel):
    """WhatsApp via Twilio. Stub — ready for integration."""

    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID', '')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN', '')
        self.from_number = os.getenv('TWILIO_WHATSAPP_FROM', '')
        self.to_number = os.getenv('TWILIO_WHATSAPP_TO', '')

    @property
    def name(self) -> str:
        return "whatsapp"

    def send(self, subject: str, body: str) -> bool:
        if not self.is_available():
            return False
        # TODO: Implement with twilio
        # from twilio.rest import Client
        # client = Client(self.account_sid, self.auth_token)
        # client.messages.create(
        #     body=f"{subject}\n{body}",
        #     from_=f"whatsapp:{self.from_number}",
        #     to=f"whatsapp:{self.to_number}"
        # )
        logger.info(f"[WhatsApp stub] Would send: {subject}")
        return True

    def is_available(self) -> bool:
        return bool(self.account_sid and self.auth_token)


class SMSChannel(NotificationChannel):
    """SMS via Twilio. Stub — ready for integration."""

    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID', '')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN', '')
        self.from_number = os.getenv('TWILIO_SMS_FROM', '')
        self.to_number = os.getenv('TWILIO_SMS_TO', '')

    @property
    def name(self) -> str:
        return "sms"

    def send(self, subject: str, body: str) -> bool:
        if not self.is_available():
            return False
        logger.info(f"[SMS stub] Would send: {subject}")
        return True

    def is_available(self) -> bool:
        return bool(self.account_sid and self.auth_token)


class EmailChannel(NotificationChannel):
    """Email via SMTP. Stub — ready for integration."""

    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', '')
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_pass = os.getenv('SMTP_PASS', '')
        self.to_email = os.getenv('ALERT_EMAIL_TO', '')

    @property
    def name(self) -> str:
        return "email"

    def send(self, subject: str, body: str) -> bool:
        if not self.is_available():
            return False
        logger.info(f"[Email stub] Would send: {subject}")
        return True

    def is_available(self) -> bool:
        return bool(self.smtp_host and self.smtp_user)


class NtfyChannel(NotificationChannel):
    """Push notifications via ntfy.sh (or self-hosted ntfy)."""

    def __init__(self):
        self.url = os.getenv('NTFY_URL', 'https://ntfy.sh')
        self.topic = os.getenv('NTFY_TOPIC', '')
        self.token = os.getenv('NTFY_TOKEN', '')

    @property
    def name(self) -> str:
        return "ntfy"

    _PRIORITY_MAP = {
        "urgent": "5",
        "critical": "5",
        "warning": "4",
        "preventive": "3",
        "info": "3",
        "test": "3"
    }
    _TAG_MAP = {
        "urgent": "rotating_light,sos",
        "critical": "rotating_light",
        "warning": "warning",
        "preventive": "eyes",
        "info": "information_source",
        "test": "test_tube",
    }

    def send(self, subject: str, body: str) -> bool:
        if not self.is_available():
            return False
        endpoint = f"{self.url.rstrip('/')}/{self.topic}"
        headers = {"Title": subject, "Markdown": "yes"}
        # Extract severity from subject "[SEVERITY] ..." format
        severity = ""
        if subject.startswith("[") and "]" in subject:
            severity = subject[1:subject.index("]")].lower()
        if severity in self._PRIORITY_MAP:
            headers["Priority"] = self._PRIORITY_MAP[severity]
        if severity in self._TAG_MAP:
            headers["Tags"] = self._TAG_MAP[severity]
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(endpoint, data=body.encode(), headers=headers)
        urllib.request.urlopen(req, timeout=10)
        return True

    def send_with_priority(self, subject: str, body: str, priority: int, tags: str) -> bool:
        """Send with explicit priority override (for escalation)."""
        if not self.is_available():
            return False
        endpoint = f"{self.url.rstrip('/')}/{self.topic}"
        headers = {
            "Title": subject,
            "Markdown": "yes",
            "Priority": str(priority),
            "Tags": tags,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(endpoint, data=body.encode(), headers=headers)
        urllib.request.urlopen(req, timeout=10)
        return True

    def is_available(self) -> bool:
        return bool(self.topic)


# ── Notification Service (Orchestrator) ───────────────────────

class NotificationService:
    def __init__(self, channels: List[NotificationChannel] = None,
                 cooldown_seconds: int = COOLDOWN_SECONDS):
        self.channels: List[NotificationChannel] = channels or [
            ConsoleChannel(),
            WhatsAppChannel(),
            SMSChannel(),
            EmailChannel(),
            NtfyChannel(),
        ]
        self.cooldown_seconds = cooldown_seconds
        self.cooldowns: Dict[str, float] = {}
        self.history: List[Dict[str, Any]] = []

    def _is_on_cooldown(self, rule_id: str) -> bool:
        last = self.cooldowns.get(rule_id)
        if last is None:
            return False
        return (time.time() - last) < self.cooldown_seconds

    def _record(self, rule_id: str, severity: str, message: str,
                sensor_data: Dict[str, Any], results: List[Dict[str, Any]]):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "rule_id": rule_id,
            "severity": severity,
            "message": message,
            "sensor_data": sensor_data,
            "channels": results,
        }
        self.history.append(entry)
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

    def notify(self, rule_id: str, severity: str, message: str,
               sensor_data: Dict[str, Any] = None, recommended_action: str = None,
               escalation_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Send alert through all available channels. Respects cooldown (unless escalating).

        Args:
            rule_id: Unique identifier for the rule
            severity: Alert severity (critical, warning, preventive, info)
            message: Alert message
            sensor_data: Current sensor readings
            recommended_action: Suggested action to take (for preventive alerts)
            escalation_info: Escalation details (bypasses cooldown, adds context)
        """
        # Escalation system bypasses cooldown
        if not escalation_info and self._is_on_cooldown(rule_id):
            logger.debug(f"Notification '{rule_id}' on cooldown — skipped")
            return []

        # Build message body
        body = self._format_body(rule_id, severity, message, sensor_data or {}, recommended_action)

        # Add escalation context if present
        if escalation_info:
            escalation_context = self._format_escalation_context(escalation_info)
            body = escalation_context + "\n\n" + body

        results = self._send_all(
            subject=f"[{severity.upper()}] {message}",
            body=body,
            escalation_info=escalation_info,
        )

        if results:
            self.cooldowns[rule_id] = time.time()
            self._record(rule_id, severity, message, sensor_data or {}, results)

        return results

    def test_alert(self, sensor_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Send a test alert through all channels. Bypasses cooldown.

        Args:
            sensor_data: Optional sensor data to include. If None, uses default test data.
        """
        if sensor_data is None:
            sensor_data = {
                "temperature": 31.5, "humidity": 82.0,
                "ph": 7.3, "ec": 2.8, "water_level": 15.0,
            }

        message = "This is a test alert from the AgriTech notification system."
        if sensor_data:
            message += " Using real sensor data."

        results = self._send_all(
            subject="[TEST] AgriTech Alert System Test",
            body=self._format_body(
                "test", "test",
                message,
                sensor_data,
            ),
        )
        self._record("test", "test", "Test alert", sensor_data, results)
        return results

    def _format_escalation_context(self, escalation_info: Dict[str, Any]) -> str:
        """Format escalation information for notification."""
        lines = []
        level = escalation_info['level_name']
        elapsed = escalation_info['elapsed_minutes']
        sent_count = escalation_info['sent_count']

        if sent_count == 1:
            lines.append(f"\u26a0\ufe0f FIRST ALERT: {level}")
        else:
            lines.append(f"\ud83d\udd14 ESCALATION {sent_count}: {level}")
            lines.append(f"\u23f1\ufe0f Time since first alert: {elapsed} minutes")

        if escalation_info.get('is_worsening'):
            lines.append("\ud83d\udcc9 \u26a0\ufe0f SITUATION WORSENING")

        return "\n".join(lines)

    def _send_all(self, subject: str, body: str, escalation_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        results = []
        for ch in self.channels:
            available = ch.is_available()
            sent = False
            if available:
                try:
                    # Pass escalation info to channels that support it (like ntfy)
                    if escalation_info and hasattr(ch, 'send_with_priority'):
                        sent = ch.send_with_priority(
                            subject, body,
                            priority=escalation_info['priority'],
                            tags=escalation_info['tags']
                        )
                    else:
                        sent = ch.send(subject, body)
                except Exception as e:
                    logger.error(f"Channel '{ch.name}' failed: {e}")
            results.append({
                "channel": ch.name,
                "available": available,
                "sent": sent,
            })
        return results

    def _format_body(self, rule_id: str, severity: str, message: str,
                     sensor_data: Dict[str, Any], recommended_action: str = None) -> str:
        lines = [
            f"Regra: {rule_id}",
            f"Severidade: {severity.upper()}",
            f"Mensagem: {message}",
            f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        # Add recommended action for preventive alerts
        if recommended_action:
            lines.append("")
            lines.append("\u26a1 A\u00e7\u00e3o Recomendada:")
            lines.append(f"  {recommended_action}")

        if sensor_data:
            lines.append("")
            lines.append("\U0001f4ca Painel de Sensores:")
            lines.append("")
            for key, value in sensor_data.items():
                meta = SENSOR_META.get(key)
                if meta:
                    try:
                        val = float(value)
                    except (TypeError, ValueError):
                        lines.append(f"  {key}: {value}")
                        continue
                    status, icon = _sensor_status(val, meta["min"], meta["max"])
                    gauge = _gauge(val, meta["abs_min"], meta["abs_max"])
                    lines.append(f"{meta['emoji']} {meta['label']}: {val}{meta['unit']}  {icon} {status}")
                    lines.append(f"  Faixa ideal: {meta['min']}\u2013{meta['max']}{meta['unit']}")
                    lines.append(f"  {gauge}")
                    lines.append("")
                else:
                    lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def get_status(self) -> Dict[str, Any]:
        return {
            "channels": [
                {"name": ch.name, "available": ch.is_available()}
                for ch in self.channels
            ],
            "cooldown_seconds": self.cooldown_seconds,
            "recent_alerts": self.history[-10:],
        }


# Global instance
notifier = NotificationService()
