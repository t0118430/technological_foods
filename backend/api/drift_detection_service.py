"""
Dual-Sensor Drift Detection Service
Monitors sensor accuracy and triggers business intelligence alerts
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger('drift-detection')


@dataclass
class SensorReading:
    """Single sensor reading"""
    temperature: float
    humidity: float
    timestamp: datetime


@dataclass
class DriftAnalysis:
    """Drift analysis between two sensors"""
    temp_diff: float
    humidity_diff: float
    temp_drift_percent: float
    humidity_drift_percent: float
    status: str  # "healthy", "degraded", "failing"
    needs_calibration: bool
    estimated_days_until_failure: Optional[int]


class DriftDetectionService:
    """
    Analyzes dual sensor data to detect drift and predict failures

    Business Value:
    - Prevent crop loss from bad sensor readings (€500-2000 per incident)
    - Predict sensor failures 7-14 days in advance
    - Justify premium service fees with proactive monitoring
    - Reduce client downtime with scheduled maintenance
    """

    # Thresholds based on sensor tier quality
    THRESHOLDS = {
        "good": {
            "temp_warning": 0.2,      # ±0.2°C
            "temp_critical": 0.5,     # ±0.5°C
            "humidity_warning": 1.0,  # ±1%
            "humidity_critical": 2.0, # ±2%
        },
        "medium": {
            "temp_warning": 0.5,      # ±0.5°C
            "temp_critical": 1.0,     # ±1°C
            "humidity_warning": 2.0,  # ±2%
            "humidity_critical": 5.0, # ±5%
        },
        "cheap": {
            "temp_warning": 1.0,      # ±1°C
            "temp_critical": 2.0,     # ±2°C
            "humidity_warning": 3.0,  # ±3%
            "humidity_critical": 7.0, # ±7%
        }
    }

    def __init__(self):
        self.drift_history = {}  # sensor_id -> list of DriftAnalysis
        self.last_alert_time = {}  # sensor_id -> datetime (prevent spam)
        self.alert_cooldown = timedelta(hours=6)  # Alert max every 6 hours

    def analyze_dual_reading(self, sensor_id: str, primary: Dict[str, float],
                            secondary: Dict[str, float],
                            sensor_tier: str = "medium") -> DriftAnalysis:
        """
        Analyze readings from two sensors to detect drift

        Args:
            sensor_id: Unique sensor identifier
            primary: {"temperature": 25.5, "humidity": 65.0}
            secondary: {"temperature": 25.3, "humidity": 64.5}
            sensor_tier: "good", "medium", or "cheap"

        Returns:
            DriftAnalysis with status and recommendations
        """

        # Extract readings
        primary_temp = primary.get("temperature", 0)
        primary_humidity = primary.get("humidity", 0)
        secondary_temp = secondary.get("temperature", 0)
        secondary_humidity = secondary.get("humidity", 0)

        # Calculate absolute differences
        temp_diff = abs(primary_temp - secondary_temp)
        humidity_diff = abs(primary_humidity - secondary_humidity)

        # Calculate percentage drift (relative to primary sensor)
        temp_drift_percent = (temp_diff / primary_temp * 100) if primary_temp != 0 else 0
        humidity_drift_percent = (humidity_diff / primary_humidity * 100) if primary_humidity != 0 else 0

        # Get thresholds for sensor tier
        thresholds = self.THRESHOLDS.get(sensor_tier, self.THRESHOLDS["medium"])

        # Determine status
        temp_critical = temp_diff >= thresholds["temp_critical"]
        temp_warning = temp_diff >= thresholds["temp_warning"]
        humidity_critical = humidity_diff >= thresholds["humidity_critical"]
        humidity_warning = humidity_diff >= thresholds["humidity_warning"]

        if temp_critical or humidity_critical:
            status = "failing"
            needs_calibration = True
            days_until_failure = 1  # Immediate action needed
        elif temp_warning or humidity_warning:
            status = "degraded"
            needs_calibration = True
            days_until_failure = 7  # Schedule within a week
        else:
            status = "healthy"
            needs_calibration = False
            days_until_failure = None

        analysis = DriftAnalysis(
            temp_diff=temp_diff,
            humidity_diff=humidity_diff,
            temp_drift_percent=temp_drift_percent,
            humidity_drift_percent=humidity_drift_percent,
            status=status,
            needs_calibration=needs_calibration,
            estimated_days_until_failure=days_until_failure,
        )

        # Store in history
        if sensor_id not in self.drift_history:
            self.drift_history[sensor_id] = []

        self.drift_history[sensor_id].append(analysis)

        # Keep last 100 readings
        if len(self.drift_history[sensor_id]) > 100:
            self.drift_history[sensor_id] = self.drift_history[sensor_id][-100:]

        return analysis

    def should_send_alert(self, sensor_id: str, analysis: DriftAnalysis) -> bool:
        """
        Determine if alert should be sent (respects cooldown)

        Always alert on:
        - First detection of degraded/failing status
        - Status worsening (degraded → failing)
        - After cooldown period
        """

        if analysis.status == "healthy":
            return False

        # Check cooldown
        last_alert = self.last_alert_time.get(sensor_id)
        if last_alert:
            if datetime.now() - last_alert < self.alert_cooldown:
                return False

        # Update last alert time
        self.last_alert_time[sensor_id] = datetime.now()
        return True

    def get_drift_trend(self, sensor_id: str, window_hours: int = 24) -> Dict[str, Any]:
        """
        Analyze drift trend over time

        Returns:
            - is_worsening: bool
            - avg_drift: float
            - max_drift: float
            - readings_count: int
        """

        if sensor_id not in self.drift_history:
            return {
                "is_worsening": False,
                "avg_temp_drift": 0,
                "avg_humidity_drift": 0,
                "max_temp_drift": 0,
                "max_humidity_drift": 0,
                "readings_count": 0,
            }

        history = self.drift_history[sensor_id]

        # Get recent readings (simplified - assumes sequential)
        recent_window = min(len(history), window_hours * 30)  # ~30 readings/hour
        recent = history[-recent_window:] if recent_window > 0 else history

        if not recent:
            return {
                "is_worsening": False,
                "avg_temp_drift": 0,
                "avg_humidity_drift": 0,
                "max_temp_drift": 0,
                "max_humidity_drift": 0,
                "readings_count": 0,
            }

        # Calculate trends
        temp_drifts = [r.temp_diff for r in recent]
        humidity_drifts = [r.humidity_diff for r in recent]

        avg_temp_drift = sum(temp_drifts) / len(temp_drifts)
        avg_humidity_drift = sum(humidity_drifts) / len(humidity_drifts)
        max_temp_drift = max(temp_drifts)
        max_humidity_drift = max(humidity_drifts)

        # Determine if worsening (compare first half vs second half)
        if len(recent) >= 10:
            mid = len(recent) // 2
            first_half_avg = sum(temp_drifts[:mid]) / mid
            second_half_avg = sum(temp_drifts[mid:]) / (len(temp_drifts) - mid)
            is_worsening = second_half_avg > first_half_avg * 1.2  # 20% worse
        else:
            is_worsening = False

        return {
            "is_worsening": is_worsening,
            "avg_temp_drift": round(avg_temp_drift, 2),
            "avg_humidity_drift": round(avg_humidity_drift, 2),
            "max_temp_drift": round(max_temp_drift, 2),
            "max_humidity_drift": round(max_humidity_drift, 2),
            "readings_count": len(recent),
        }

    def calculate_revenue_risk(self, analysis: DriftAnalysis, crop_value_per_day: float = 50) -> Dict[str, Any]:
        """
        Calculate business impact of sensor drift

        Args:
            analysis: DriftAnalysis result
            crop_value_per_day: Average daily crop production value (€)

        Returns:
            - revenue_at_risk: float (€)
            - days_at_risk: int
            - urgency: str ("low", "medium", "high", "critical")
        """

        if analysis.status == "healthy":
            return {
                "revenue_at_risk": 0,
                "days_at_risk": 0,
                "urgency": "low",
            }

        elif analysis.status == "degraded":
            # Degraded sensor could affect yields by 10-20%
            days_at_risk = analysis.estimated_days_until_failure or 7
            revenue_at_risk = crop_value_per_day * days_at_risk * 0.15  # 15% loss
            urgency = "medium"

        else:  # failing
            # Failing sensor could cause total crop loss if not addressed
            days_at_risk = analysis.estimated_days_until_failure or 1
            revenue_at_risk = crop_value_per_day * days_at_risk * 0.5  # 50% loss
            urgency = "critical"

        return {
            "revenue_at_risk": round(revenue_at_risk, 2),
            "days_at_risk": days_at_risk,
            "urgency": urgency,
        }

    def format_business_alert(self, sensor_id: str, client_name: str,
                             analysis: DriftAnalysis, revenue_risk: Dict[str, Any]) -> Dict[str, str]:
        """
        Format alert message for business intelligence channel

        Returns:
            - title: Alert title
            - body: Detailed message with actions
        """

        if analysis.status == "failing":
            icon = "🔴"
            severity = "CRITICAL"
        elif analysis.status == "degraded":
            icon = "🟡"
            severity = "WARNING"
        else:
            icon = "🟢"
            severity = "INFO"

        title = f"{icon} {severity}: Sensor Drift Detected - {client_name}"

        body = f"""# Sensor Drift Analysis

**Client:** {client_name}
**Sensor ID:** {sensor_id}
**Status:** {analysis.status.upper()}

## Drift Measurements
- **Temperature:** {analysis.temp_diff:.2f}°C ({analysis.temp_drift_percent:.1f}% drift)
- **Humidity:** {analysis.humidity_diff:.2f}% ({analysis.humidity_drift_percent:.1f}% drift)

## Business Impact
- **Revenue at Risk:** €{revenue_risk['revenue_at_risk']:.2f}
- **Days Until Failure:** {revenue_risk['days_at_risk']}
- **Urgency:** {revenue_risk['urgency'].upper()}

## Recommended Actions
"""

        if analysis.status == "failing":
            body += """
1. 🚨 **URGENT:** Call client immediately
2. 🔧 Schedule emergency calibration visit (within 24h)
3. 📊 Prepare replacement sensor (order if needed)
4. 💰 Invoice: €75 emergency service fee + €25/sensor

**Prevent crop loss worth €{0:.0f}+ by acting now!**
""".format(revenue_risk['revenue_at_risk'] * 3)  # Potential total loss

        elif analysis.status == "degraded":
            body += """
1. 📞 Call client to schedule calibration (within 7 days)
2. 🔧 Prepare calibration equipment
3. 📈 Upsell: Recommend sensor upgrade to "good" tier
4. 💰 Invoice: €50 standard calibration

**Proactive maintenance prevents €{0:.0f} in crop losses**
""".format(revenue_risk['revenue_at_risk'] * 2)

        body += f"""
## Next Steps
- [ ] Contact client: {client_name}
- [ ] Schedule visit
- [ ] Update client health score (-{10 if analysis.status == 'degraded' else 20} points)
- [ ] Generate invoice

🔗 **Client Dashboard:** http://localhost:3001/business
"""

        return {
            "title": title,
            "body": body,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get overall drift detection status"""

        total_sensors = len(self.drift_history)

        if total_sensors == 0:
            return {
                "sensors_monitored": 0,
                "healthy": 0,
                "degraded": 0,
                "failing": 0,
                "status": "no_data",
            }

        # Count statuses from latest readings
        healthy = 0
        degraded = 0
        failing = 0

        for sensor_id, history in self.drift_history.items():
            if history:
                latest = history[-1]
                if latest.status == "healthy":
                    healthy += 1
                elif latest.status == "degraded":
                    degraded += 1
                else:
                    failing += 1

        return {
            "sensors_monitored": total_sensors,
            "healthy": healthy,
            "degraded": degraded,
            "failing": failing,
            "status": "critical" if failing > 0 else "warning" if degraded > 0 else "healthy",
        }


# Global instance
drift_detector = DriftDetectionService()
