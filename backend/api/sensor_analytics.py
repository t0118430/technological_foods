"""
Sensor Analytics Engine - Derived intelligence from raw sensor data.

Provides: VPD, DLI, nutrient scoring, moving averages, trend detection,
anomaly detection, and historical analytics queries.

Uses in-memory rolling buffer (~30 min of readings) for fast computation.

Author: AgriTech Hydroponics
License: MIT
"""

import math
import logging
import os
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from influxdb_client import InfluxDBClient

logger = logging.getLogger('sensor-analytics')

INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', '')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', '')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', '')

# Lux to PPFD approximate conversion for sunlight/white LED
# 1 lux ~ 0.0185 umol/m2/s for sunlight (varies by spectrum)
LUX_TO_PPFD = 0.0185

# Rolling buffer: ~900 readings at 2s interval = 30 min
BUFFER_MAX_SIZE = 900

# Sensor fields we track
SENSOR_FIELDS = ['temperature', 'humidity', 'ph', 'ec', 'water_level', 'light_level']


class SensorAnalytics:
    """Core analytics engine with in-memory rolling buffer."""

    def __init__(self):
        self.buffers: Dict[str, deque] = {}  # sensor_id -> deque of readings
        self.daily_light: Dict[str, Dict] = {}  # sensor_id -> {date, accumulated_ppfd, hours}

    def _get_buffer(self, sensor_id: str) -> deque:
        if sensor_id not in self.buffers:
            self.buffers[sensor_id] = deque(maxlen=BUFFER_MAX_SIZE)
        return self.buffers[sensor_id]

    # ── Ingestion ──────────────────────────────────────────────────

    def ingest_reading(self, data: Dict[str, Any], sensor_id: str = 'arduino_1') -> Dict[str, Any]:
        """
        Called on every POST /api/data. Feeds rolling buffer, returns live derived metrics.

        Args:
            data: Raw sensor reading dict (temperature, humidity, ph, ec, etc.)
            sensor_id: Sensor identifier

        Returns:
            Dict with derived metrics (vpd, dli_progress, nutrient_score, anomalies)
        """
        reading = {
            'timestamp': datetime.now(),
            **{field: data.get(field) for field in SENSOR_FIELDS if data.get(field) is not None}
        }

        buf = self._get_buffer(sensor_id)
        buf.append(reading)

        # Calculate derived metrics
        result = {}

        temp = data.get('temperature')
        humidity = data.get('humidity')
        if temp is not None and humidity is not None:
            vpd = self.calculate_vpd(temp, humidity)
            result['vpd'] = vpd

        light = data.get('light_level')
        if light is not None:
            self._accumulate_light(sensor_id, light)
            dli_info = self.calculate_dli(sensor_id)
            result['dli'] = dli_info

        ph = data.get('ph')
        ec = data.get('ec')
        if ph is not None and ec is not None:
            score = self.calculate_nutrient_score(ph, ec)
            result['nutrient_score'] = score

        # Anomaly check
        anomalies = self.detect_anomalies(data, sensor_id)
        if anomalies:
            result['anomalies'] = anomalies

        return result

    # ── VPD (Vapor Pressure Deficit) ───────────────────────────────

    @staticmethod
    def calculate_vpd(temp: float, humidity: float) -> Dict[str, Any]:
        """
        Calculate Vapor Pressure Deficit in kPa.

        VPD = SVP * (1 - RH/100)
        SVP (Tetens formula) = 0.6108 * exp(17.27 * T / (T + 237.3))

        Optimal lettuce VPD: 0.8 - 1.2 kPa

        Args:
            temp: Temperature in Celsius
            humidity: Relative humidity in %

        Returns:
            Dict with vpd_kpa, classification, optimal range
        """
        svp = 0.6108 * math.exp((17.27 * temp) / (temp + 237.3))
        vpd = svp * (1 - humidity / 100.0)
        vpd = round(vpd, 3)

        if vpd < 0.4:
            classification = 'too_low'
            risk = 'High disease risk - increase ventilation'
        elif vpd < 0.8:
            classification = 'low'
            risk = 'Slightly low - monitor for mold'
        elif vpd <= 1.2:
            classification = 'optimal'
            risk = None
        elif vpd <= 1.6:
            classification = 'high'
            risk = 'Plants may stress - increase humidity or lower temp'
        else:
            classification = 'too_high'
            risk = 'Severe stress - plants closing stomata'

        return {
            'vpd_kpa': vpd,
            'classification': classification,
            'optimal_range': {'min': 0.8, 'max': 1.2},
            'risk': risk,
        }

    # ── DLI (Daily Light Integral) ─────────────────────────────────

    def _accumulate_light(self, sensor_id: str, light_lux: float):
        """Accumulate light readings for DLI calculation."""
        today = datetime.now().date().isoformat()

        if sensor_id not in self.daily_light:
            self.daily_light[sensor_id] = {'date': today, 'readings': [], 'total_ppfd_seconds': 0.0}

        dl = self.daily_light[sensor_id]

        # Reset on new day
        if dl['date'] != today:
            dl['date'] = today
            dl['readings'] = []
            dl['total_ppfd_seconds'] = 0.0

        ppfd = light_lux * LUX_TO_PPFD
        now = datetime.now()
        dl['readings'].append({'ppfd': ppfd, 'timestamp': now})

        # Accumulate: PPFD * interval_seconds / 1_000_000 = mol/m2 contribution
        if len(dl['readings']) >= 2:
            prev = dl['readings'][-2]
            interval = (now - prev['timestamp']).total_seconds()
            # Average PPFD over interval
            avg_ppfd = (ppfd + prev['ppfd']) / 2.0
            dl['total_ppfd_seconds'] += avg_ppfd * interval

    def calculate_dli(self, sensor_id: str) -> Dict[str, Any]:
        """
        Calculate Daily Light Integral from accumulated readings.

        DLI = sum(PPFD * time_interval) / 1,000,000 (converts umol to mol)
        Optimal lettuce DLI: 12-20 mol/m2/day

        Returns:
            Dict with current_dli, projected_dli, hours_of_light, classification
        """
        if sensor_id not in self.daily_light:
            return {'current_dli': 0, 'projected_dli': 0, 'classification': 'no_data'}

        dl = self.daily_light[sensor_id]
        current_dli = dl['total_ppfd_seconds'] / 1_000_000.0
        current_dli = round(current_dli, 2)

        # Project full-day DLI based on hours elapsed
        now = datetime.now()
        hours_elapsed = now.hour + now.minute / 60.0
        if hours_elapsed > 0:
            projected_dli = round(current_dli * (16.0 / hours_elapsed), 2)  # assume 16h photoperiod
        else:
            projected_dli = 0

        # Count hours with light > threshold
        light_readings = [r for r in dl['readings'] if r['ppfd'] > 5]  # >~270 lux threshold
        if len(light_readings) >= 2:
            first_light = light_readings[0]['timestamp']
            last_light = light_readings[-1]['timestamp']
            hours_of_light = round((last_light - first_light).total_seconds() / 3600, 1)
        else:
            hours_of_light = 0

        if current_dli < 6:
            classification = 'very_low'
        elif current_dli < 12:
            classification = 'low'
        elif current_dli <= 20:
            classification = 'optimal'
        elif current_dli <= 30:
            classification = 'high'
        else:
            classification = 'too_high'

        return {
            'current_dli': current_dli,
            'projected_dli': projected_dli,
            'hours_of_light': hours_of_light,
            'optimal_range': {'min': 12, 'max': 20},
            'classification': classification,
            'unit': 'mol/m2/day',
        }

    # ── Nutrient Score ─────────────────────────────────────────────

    @staticmethod
    def calculate_nutrient_score(ph: float, ec: float,
                                 variety: str = None, stage: str = None) -> Dict[str, Any]:
        """
        Combined pH+EC health score (0-100).

        Uses variety configs from config_loader if available, else defaults.

        Args:
            ph: Current pH value
            ec: Current EC value (mS/cm)
            variety: Optional variety name for specific ranges
            stage: Optional growth stage

        Returns:
            Dict with score, ph_status, ec_status, recommendations
        """
        # Default optimal ranges (lettuce general)
        ph_opt_min, ph_opt_max = 5.8, 6.5
        ec_opt_min, ec_opt_max = 1.2, 2.0
        ph_crit_min, ph_crit_max = 5.5, 7.0
        ec_crit_min, ec_crit_max = 0.8, 2.5

        # Try to load variety-specific ranges
        if variety:
            try:
                from config_loader import config_loader
                config = config_loader.load_variety(variety)
                optimal = config.get('optimal_ranges', {})

                ph_range = optimal.get('ph', {})
                if ph_range:
                    ph_opt_min = ph_range.get('optimal_min', ph_opt_min)
                    ph_opt_max = ph_range.get('optimal_max', ph_opt_max)
                    ph_crit_min = ph_range.get('critical_min', ph_crit_min)
                    ph_crit_max = ph_range.get('critical_max', ph_crit_max)

                ec_range = optimal.get('ec', {})
                if ec_range:
                    ec_opt_min = ec_range.get('optimal_min', ec_opt_min)
                    ec_opt_max = ec_range.get('optimal_max', ec_opt_max)
                    ec_crit_min = ec_range.get('critical_min', ec_crit_min)
                    ec_crit_max = ec_range.get('critical_max', ec_crit_max)

                # Stage-specific EC override
                if stage:
                    stages = config.get('growth_stages', {})
                    stage_info = stages.get(stage, {})
                    ec_range_str = stage_info.get('ec_range', '')
                    if ec_range_str and '-' in ec_range_str:
                        parts = ec_range_str.split('-')
                        ec_opt_min = float(parts[0])
                        ec_opt_max = float(parts[1])
            except Exception:
                pass  # Use defaults

        # pH score (0-50 points)
        ph_score = _range_score(ph, ph_opt_min, ph_opt_max, ph_crit_min, ph_crit_max, 50)

        # EC score (0-50 points)
        ec_score = _range_score(ec, ec_opt_min, ec_opt_max, ec_crit_min, ec_crit_max, 50)

        total = ph_score + ec_score
        recommendations = []

        if ph < ph_opt_min:
            recommendations.append(f'pH too low ({ph:.1f}) - add pH up solution')
        elif ph > ph_opt_max:
            recommendations.append(f'pH too high ({ph:.1f}) - add pH down solution')

        if ec < ec_opt_min:
            recommendations.append(f'EC too low ({ec:.2f}) - add nutrient concentrate')
        elif ec > ec_opt_max:
            recommendations.append(f'EC too high ({ec:.2f}) - dilute with fresh water')

        return {
            'score': round(total),
            'ph_score': round(ph_score),
            'ec_score': round(ec_score),
            'ph_status': 'optimal' if ph_opt_min <= ph <= ph_opt_max else 'warning' if ph_crit_min <= ph <= ph_crit_max else 'critical',
            'ec_status': 'optimal' if ec_opt_min <= ec <= ec_opt_max else 'warning' if ec_crit_min <= ec <= ec_crit_max else 'critical',
            'recommendations': recommendations,
        }

    # ── Moving Averages ────────────────────────────────────────────

    def get_moving_averages(self, sensor_id: str) -> Dict[str, Any]:
        """
        Calculate moving averages (10/30/60 readings) for all sensor fields.

        Returns:
            Dict keyed by field, each containing ma_10, ma_30, ma_60 values
        """
        buf = self._get_buffer(sensor_id)
        readings = list(buf)

        if not readings:
            return {}

        result = {}
        for field in SENSOR_FIELDS:
            values = [r[field] for r in readings if r.get(field) is not None]
            if not values:
                continue

            result[field] = {
                'current': values[-1],
                'ma_10': round(_mean(values[-10:]), 3) if len(values) >= 1 else None,
                'ma_30': round(_mean(values[-30:]), 3) if len(values) >= 1 else None,
                'ma_60': round(_mean(values[-60:]), 3) if len(values) >= 1 else None,
                'readings_count': len(values),
            }

        return result

    # ── Trend Detection ────────────────────────────────────────────

    def detect_trends(self, sensor_id: str, window: int = 60) -> Dict[str, Any]:
        """
        Linear regression slope per sensor field — rising/falling/stable.

        Args:
            sensor_id: Sensor identifier
            window: Number of recent readings to analyze

        Returns:
            Dict keyed by field with slope, direction, change_per_minute
        """
        buf = self._get_buffer(sensor_id)
        readings = list(buf)[-window:]

        if len(readings) < 5:
            return {}

        result = {}
        for field in SENSOR_FIELDS:
            values = [(i, r[field]) for i, r in enumerate(readings) if r.get(field) is not None]
            if len(values) < 5:
                continue

            xs = [v[0] for v in values]
            ys = [v[1] for v in values]
            slope = _linear_regression_slope(xs, ys)

            # Estimate time span
            first_ts = readings[0].get('timestamp')
            last_ts = readings[-1].get('timestamp')
            if first_ts and last_ts:
                minutes = max((last_ts - first_ts).total_seconds() / 60.0, 0.001)
                change_per_min = (ys[-1] - ys[0]) / minutes
            else:
                change_per_min = 0

            # Classify direction based on slope relative to value magnitude
            mean_val = _mean(ys)
            if mean_val != 0:
                relative_slope = abs(slope) / abs(mean_val)
            else:
                relative_slope = abs(slope)

            if relative_slope < 0.001:
                direction = 'stable'
            elif slope > 0:
                direction = 'rising'
            else:
                direction = 'falling'

            result[field] = {
                'slope': round(slope, 6),
                'direction': direction,
                'change_per_minute': round(change_per_min, 4),
                'window_readings': len(values),
            }

        return result

    # ── Anomaly Detection ──────────────────────────────────────────

    def detect_anomalies(self, data: Dict[str, Any], sensor_id: str) -> List[Dict[str, Any]]:
        """
        Z-score anomaly detection:
        - Spikes: value > 2.5 standard deviations from mean
        - Flatlines: 60+ identical consecutive readings
        - Sudden jumps: >10% change from previous reading

        Args:
            data: Current sensor reading
            sensor_id: Sensor identifier

        Returns:
            List of detected anomalies
        """
        buf = self._get_buffer(sensor_id)
        readings = list(buf)
        anomalies = []

        if len(readings) < 10:
            return anomalies

        for field in SENSOR_FIELDS:
            current = data.get(field)
            if current is None:
                continue

            values = [r[field] for r in readings if r.get(field) is not None]
            if len(values) < 10:
                continue

            mean = _mean(values)
            std = _stddev(values)

            # Spike detection (Z-score > 2.5)
            if std > 0:
                z_score = abs(current - mean) / std
                if z_score > 2.5:
                    anomalies.append({
                        'type': 'spike',
                        'field': field,
                        'value': current,
                        'z_score': round(z_score, 2),
                        'mean': round(mean, 3),
                        'std': round(std, 3),
                        'severity': 'high' if z_score > 3.5 else 'medium',
                    })

            # Flatline detection (60+ identical readings)
            if len(values) >= 60:
                recent_60 = values[-60:]
                if all(v == recent_60[0] for v in recent_60):
                    anomalies.append({
                        'type': 'flatline',
                        'field': field,
                        'value': current,
                        'consecutive_identical': 60,
                        'severity': 'high',
                    })

            # Sudden jump detection (>10% from previous)
            if len(values) >= 2:
                prev = values[-2]
                if prev != 0:
                    pct_change = abs(current - prev) / abs(prev) * 100
                    if pct_change > 10:
                        anomalies.append({
                            'type': 'sudden_jump',
                            'field': field,
                            'value': current,
                            'previous': prev,
                            'percent_change': round(pct_change, 1),
                            'severity': 'high' if pct_change > 25 else 'medium',
                        })

        return anomalies

    # ── Sensor Summary ─────────────────────────────────────────────

    def get_sensor_summary(self, sensor_id: str) -> Dict[str, Any]:
        """
        Complete analytics snapshot combining all analytics for a sensor.

        Returns:
            Dict with vpd, dli, nutrient_score, moving_averages, trends, anomalies
        """
        buf = self._get_buffer(sensor_id)
        readings = list(buf)

        if not readings:
            return {'status': 'no_data', 'sensor_id': sensor_id}

        latest = readings[-1]

        summary = {
            'sensor_id': sensor_id,
            'timestamp': datetime.now().isoformat(),
            'readings_in_buffer': len(readings),
        }

        # VPD
        temp = latest.get('temperature')
        humidity = latest.get('humidity')
        if temp is not None and humidity is not None:
            summary['vpd'] = self.calculate_vpd(temp, humidity)

        # DLI
        if sensor_id in self.daily_light:
            summary['dli'] = self.calculate_dli(sensor_id)

        # Nutrient Score
        ph = latest.get('ph')
        ec = latest.get('ec')
        if ph is not None and ec is not None:
            summary['nutrient_score'] = self.calculate_nutrient_score(ph, ec)

        # Moving Averages
        summary['moving_averages'] = self.get_moving_averages(sensor_id)

        # Trends
        summary['trends'] = self.detect_trends(sensor_id)

        # Current anomalies
        anomalies = self.detect_anomalies(latest, sensor_id)
        summary['anomalies'] = anomalies
        summary['anomaly_count'] = len(anomalies)

        return summary

    # ── Historical Analytics (InfluxDB) ────────────────────────────

    def query_historical_analytics(self, sensor_id: str, field: str,
                                   start: str, end: str,
                                   aggregation: str = '1h') -> Dict[str, Any]:
        """
        Query historical data with aggregation from InfluxDB.

        Args:
            sensor_id: Sensor identifier
            field: Sensor field to query (temperature, humidity, etc.)
            start: Start time (e.g., '-7d', '-24h', ISO timestamp)
            end: End time (e.g., 'now()', ISO timestamp)
            aggregation: Window size ('1h', '1d', '15m', etc.)

        Returns:
            Dict with data points and statistics
        """
        try:
            client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
            query_api = client.query_api()

            query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
              |> range(start: {start}, stop: {end})
              |> filter(fn: (r) => r._measurement == "sensor_reading")
              |> filter(fn: (r) => r.sensor_id == "{sensor_id}")
              |> filter(fn: (r) => r._field == "{field}")
              |> aggregateWindow(every: {aggregation}, fn: mean, createEmpty: false)
            '''

            tables = query_api.query(query)
            data_points = []
            for table in tables:
                for record in table.records:
                    data_points.append({
                        'time': str(record.get_time()),
                        'value': record.get_value(),
                    })

            client.close()

            # Compute stats
            values = [dp['value'] for dp in data_points if dp['value'] is not None]
            stats = {}
            if values:
                stats = {
                    'min': round(min(values), 3),
                    'max': round(max(values), 3),
                    'mean': round(_mean(values), 3),
                    'stddev': round(_stddev(values), 3),
                    'count': len(values),
                }

            return {
                'sensor_id': sensor_id,
                'field': field,
                'aggregation': aggregation,
                'data_points': data_points,
                'statistics': stats,
            }

        except Exception as e:
            logger.error(f"Historical analytics query error: {e}")
            return {
                'sensor_id': sensor_id,
                'field': field,
                'error': str(e),
                'data_points': [],
            }


# ── Helper functions ───────────────────────────────────────────────

def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def _linear_regression_slope(xs: List[float], ys: List[float]) -> float:
    """Simple linear regression slope (least squares)."""
    n = len(xs)
    if n < 2:
        return 0.0
    x_mean = _mean(xs)
    y_mean = _mean(ys)
    numerator = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
    denominator = sum((xs[i] - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _range_score(value: float, opt_min: float, opt_max: float,
                 crit_min: float, crit_max: float, max_points: float) -> float:
    """Score a value within optimal/critical ranges (0 to max_points)."""
    if opt_min <= value <= opt_max:
        return max_points
    elif crit_min <= value < opt_min:
        # Linear interpolation from critical to optimal
        return max_points * (value - crit_min) / (opt_min - crit_min) * 0.7
    elif opt_max < value <= crit_max:
        return max_points * (crit_max - value) / (crit_max - opt_max) * 0.7
    else:
        # Beyond critical
        return 0


# Global instance
sensor_analytics = SensorAnalytics()
