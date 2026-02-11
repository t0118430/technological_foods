"""
Data Export & Reporting Service.

CSV export of sensor data, crop lifecycle reports, and weekly/monthly summaries.

Author: AgriTech Hydroponics
License: MIT
"""

import csv
import io
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from influxdb_client import InfluxDBClient

logger = logging.getLogger('data-export')

INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', '')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', '')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', '')

SENSOR_FIELDS = ['temperature', 'humidity', 'ph', 'ec', 'water_level', 'light_level']


class DataExportService:
    """Export sensor data and generate reports."""

    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            from database import db
            self._db = db
        return self._db

    # ── CSV Export ─────────────────────────────────────────────────

    def export_sensor_csv(self, sensor_id: str, start: str = '-7d', end: str = 'now()',
                          fields: List[str] = None,
                          aggregation: str = None) -> str:
        """
        Export sensor data as CSV string.

        Args:
            sensor_id: Sensor identifier
            start: Start time (InfluxDB format: '-7d', '-24h', ISO timestamp)
            end: End time
            fields: List of fields to include (default: all)
            aggregation: Optional aggregation window ('1h', '1d', '15m')

        Returns:
            CSV string ready for download
        """
        if fields is None:
            fields = SENSOR_FIELDS

        try:
            client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
            query_api = client.query_api()

            field_filter = ' or '.join(f'r._field == "{f}"' for f in fields)

            if aggregation:
                query = f'''
                from(bucket: "{INFLUXDB_BUCKET}")
                  |> range(start: {start}, stop: {end})
                  |> filter(fn: (r) => r._measurement == "sensor_reading")
                  |> filter(fn: (r) => r.sensor_id == "{sensor_id}")
                  |> filter(fn: (r) => {field_filter})
                  |> aggregateWindow(every: {aggregation}, fn: mean, createEmpty: false)
                  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
                  |> sort(columns: ["_time"])
                '''
            else:
                query = f'''
                from(bucket: "{INFLUXDB_BUCKET}")
                  |> range(start: {start}, stop: {end})
                  |> filter(fn: (r) => r._measurement == "sensor_reading")
                  |> filter(fn: (r) => r.sensor_id == "{sensor_id}")
                  |> filter(fn: (r) => {field_filter})
                  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
                  |> sort(columns: ["_time"])
                '''

            tables = query_api.query(query)
            client.close()

            # Build CSV
            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            header = ['timestamp'] + fields
            writer.writerow(header)

            for table in tables:
                for record in table.records:
                    row = [str(record.get_time())]
                    for field in fields:
                        val = record.values.get(field, '')
                        row.append(val if val is not None else '')
                    writer.writerow(row)

            return output.getvalue()

        except Exception as e:
            logger.error(f"CSV export error: {e}")
            # Return error as CSV with header
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['error'])
            writer.writerow([str(e)])
            return output.getvalue()

    # ── Crop Report ────────────────────────────────────────────────

    def export_crop_report(self, crop_id: int) -> Dict[str, Any]:
        """
        Full crop lifecycle report with conditions per stage.

        Args:
            crop_id: Crop ID

        Returns:
            Dict with complete crop lifecycle data
        """
        try:
            crop = self.db.get_crop(crop_id)
            if not crop:
                return {'error': f'Crop {crop_id} not found'}

            variety = crop['variety']
            stages = crop.get('stages', [])

            # Load variety config
            from config_loader import config_loader
            config = config_loader.load_variety(variety)
            optimal_ranges = config.get('optimal_ranges', {})

            # Get all condition snapshots
            snapshots = self.db.get_condition_snapshots(crop_id)

            # Get harvest data
            harvest = None
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM harvests WHERE crop_id = ? LIMIT 1', (crop_id,))
                row = cursor.fetchone()
                if row:
                    harvest = dict(row)

            # Build stage reports
            stage_reports = []
            for stage in stages:
                stage_name = stage['stage']
                started = stage['started_at']
                ended = stage.get('ended_at')

                start_dt = datetime.fromisoformat(started)
                end_dt = datetime.fromisoformat(ended) if ended else datetime.now()
                duration = (end_dt - start_dt).days

                # Filter snapshots for this stage
                stage_snapshots = [
                    s for s in snapshots
                    if s['snapshot_date'] >= started[:10] and
                       (ended is None or s['snapshot_date'] <= ended[:10])
                ]

                # Average conditions
                avgs = {}
                for field in ['avg_temperature', 'avg_humidity', 'avg_ph', 'avg_ec', 'avg_vpd', 'avg_dli']:
                    vals = [s[field] for s in stage_snapshots if s.get(field) is not None]
                    if vals:
                        avgs[field.replace('avg_', '')] = round(sum(vals) / len(vals), 2)

                optimal_pcts = [s['time_in_optimal_pct'] for s in stage_snapshots
                               if s.get('time_in_optimal_pct') is not None]

                stage_reports.append({
                    'stage': stage_name,
                    'started': started,
                    'ended': ended,
                    'duration_days': duration,
                    'average_conditions': avgs,
                    'time_in_optimal_pct': round(sum(optimal_pcts) / len(optimal_pcts), 1) if optimal_pcts else None,
                    'data_points': len(stage_snapshots),
                })

            # Total lifecycle
            plant_date = crop.get('plant_date')
            total_days = None
            if plant_date and harvest:
                plant_dt = datetime.strptime(plant_date, '%Y-%m-%d')
                harvest_dt = datetime.strptime(harvest['harvest_date'], '%Y-%m-%d')
                total_days = (harvest_dt - plant_dt).days

            return {
                'report_type': 'crop_lifecycle',
                'generated_at': datetime.now().isoformat(),
                'crop': {
                    'id': crop_id,
                    'variety': variety,
                    'display_name': config.get('variety', {}).get('display_name', variety),
                    'plant_date': plant_date,
                    'status': crop.get('status'),
                    'zone': crop.get('zone'),
                    'total_days': total_days,
                },
                'optimal_ranges': {k: {'min': v.get('optimal_min'), 'max': v.get('optimal_max')}
                                   for k, v in optimal_ranges.items()
                                   if 'optimal_min' in v},
                'stages': stage_reports,
                'harvest': harvest,
                'condition_snapshots_total': len(snapshots),
            }

        except Exception as e:
            logger.error(f"Crop report error: {e}")
            return {'error': str(e)}

    # ── Weekly Summary ─────────────────────────────────────────────

    def generate_weekly_summary(self, sensor_id: str) -> Dict[str, Any]:
        """
        Weekly report with daily averages, VPD/DLI, anomalies, recommendations.

        Args:
            sensor_id: Sensor identifier

        Returns:
            Dict with weekly summary data
        """
        try:
            from sensor_analytics import sensor_analytics

            # Query daily averages from InfluxDB for last 7 days
            daily_data = self._query_daily_data(sensor_id, days=7)

            # Get current analytics snapshot
            summary = sensor_analytics.get_sensor_summary(sensor_id)

            # Get anomaly history (from buffer)
            trends = sensor_analytics.detect_trends(sensor_id)

            # Weather context
            weather_context = None
            try:
                from weather_service import weather_service
                forecast = weather_service.get_forecast(days=3)
                if not forecast.get('error'):
                    weather_context = forecast.get('daily_summaries', [])
            except Exception:
                pass

            # Generate recommendations
            recommendations = _generate_weekly_recommendations(daily_data, trends)

            return {
                'report_type': 'weekly_summary',
                'sensor_id': sensor_id,
                'generated_at': datetime.now().isoformat(),
                'period': {
                    'start': (datetime.now() - timedelta(days=7)).date().isoformat(),
                    'end': datetime.now().date().isoformat(),
                },
                'daily_averages': daily_data,
                'current_snapshot': {
                    'vpd': summary.get('vpd'),
                    'dli': summary.get('dli'),
                    'nutrient_score': summary.get('nutrient_score'),
                },
                'trends': trends,
                'weather_context': weather_context,
                'recommendations': recommendations,
            }

        except Exception as e:
            logger.error(f"Weekly summary error: {e}")
            return {'error': str(e)}

    # ── Monthly Summary ────────────────────────────────────────────

    def generate_monthly_summary(self, sensor_id: str) -> Dict[str, Any]:
        """
        Monthly report with daily averages, harvest outcomes, yield trends, market context.

        Args:
            sensor_id: Sensor identifier

        Returns:
            Dict with monthly summary data
        """
        try:
            # Query daily averages for last 30 days
            daily_data = self._query_daily_data(sensor_id, days=30)

            # Get harvest data for the month
            start_date = (datetime.now() - timedelta(days=30)).date().isoformat()
            harvest_data = []
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT h.*, c.variety
                    FROM harvests h
                    JOIN crops c ON h.crop_id = c.id
                    WHERE h.harvest_date >= ?
                    ORDER BY h.harvest_date DESC
                ''', (start_date,))
                harvest_data = [dict(row) for row in cursor.fetchall()]

            # Harvest statistics
            harvest_stats = {}
            if harvest_data:
                weights = [h['weight_kg'] for h in harvest_data if h.get('weight_kg')]
                harvest_stats = {
                    'total_harvests': len(harvest_data),
                    'total_yield_kg': round(sum(weights), 2) if weights else 0,
                    'avg_yield_kg': round(sum(weights) / len(weights), 2) if weights else 0,
                    'best_yield_kg': round(max(weights), 2) if weights else 0,
                    'varieties_harvested': list(set(h['variety'] for h in harvest_data)),
                }

            # Market context
            market_context = None
            try:
                from market_data_service import market_data_service
                market_context = {
                    'prices': market_data_service.get_market_prices(),
                    'seasonal': market_data_service.get_seasonal_demand(),
                }
            except Exception:
                pass

            # Weekly breakdown
            weekly_breakdown = _compute_weekly_breakdown(daily_data)

            return {
                'report_type': 'monthly_summary',
                'sensor_id': sensor_id,
                'generated_at': datetime.now().isoformat(),
                'period': {
                    'start': start_date,
                    'end': datetime.now().date().isoformat(),
                },
                'daily_averages': daily_data,
                'weekly_breakdown': weekly_breakdown,
                'harvest_summary': harvest_stats,
                'harvests': harvest_data,
                'market_context': market_context,
            }

        except Exception as e:
            logger.error(f"Monthly summary error: {e}")
            return {'error': str(e)}

    # ── Internal Helpers ───────────────────────────────────────────

    def _query_daily_data(self, sensor_id: str, days: int = 7) -> List[Dict]:
        """Query daily averages from InfluxDB."""
        try:
            client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
            query_api = client.query_api()

            query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
              |> range(start: -{days}d)
              |> filter(fn: (r) => r._measurement == "sensor_reading")
              |> filter(fn: (r) => r.sensor_id == "{sensor_id}")
              |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
              |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
              |> sort(columns: ["_time"])
            '''

            tables = query_api.query(query)
            client.close()

            results = []
            for table in tables:
                for record in table.records:
                    day_data = {'date': str(record.get_time())[:10]}
                    for field in SENSOR_FIELDS:
                        val = record.values.get(field)
                        if val is not None:
                            day_data[field] = round(val, 2)
                    results.append(day_data)

            return results

        except Exception as e:
            logger.error(f"Daily data query error: {e}")
            return []


# ── Module-level helpers ───────────────────────────────────────────

def _generate_weekly_recommendations(daily_data: List[Dict], trends: Dict) -> List[str]:
    """Generate recommendations based on weekly data and trends."""
    recommendations = []

    if not daily_data:
        recommendations.append('No sensor data available for analysis — check sensor connectivity')
        return recommendations

    # Temperature trends
    temps = [d.get('temperature') for d in daily_data if d.get('temperature') is not None]
    if temps:
        avg_temp = sum(temps) / len(temps)
        if avg_temp > 26:
            recommendations.append('Average temperature trending high — consider increased ventilation')
        elif avg_temp < 18:
            recommendations.append('Average temperature trending low — check heating system')

    # pH stability
    phs = [d.get('ph') for d in daily_data if d.get('ph') is not None]
    if len(phs) >= 3:
        ph_range = max(phs) - min(phs)
        if ph_range > 1.0:
            recommendations.append(f'pH fluctuating widely ({min(phs):.1f}-{max(phs):.1f}) — check buffer capacity')

    # EC trends
    if trends.get('ec', {}).get('direction') == 'rising':
        recommendations.append('EC trending upward — consider diluting nutrient solution')
    elif trends.get('ec', {}).get('direction') == 'falling':
        recommendations.append('EC trending downward — plants consuming nutrients, top up solution')

    if not recommendations:
        recommendations.append('All parameters within normal ranges — maintain current conditions')

    return recommendations


def _compute_weekly_breakdown(daily_data: List[Dict]) -> List[Dict]:
    """Group daily data into weekly buckets."""
    if not daily_data:
        return []

    weeks = {}
    for day in daily_data:
        date_str = day.get('date', '')
        if not date_str:
            continue
        try:
            dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
            week_num = dt.isocalendar()[1]
            week_key = f'W{week_num}'
        except (ValueError, IndexError):
            continue

        if week_key not in weeks:
            weeks[week_key] = []
        weeks[week_key].append(day)

    result = []
    for week_key, days in sorted(weeks.items()):
        week_summary = {'week': week_key, 'days': len(days)}
        for field in SENSOR_FIELDS:
            vals = [d[field] for d in days if d.get(field) is not None]
            if vals:
                week_summary[f'avg_{field}'] = round(sum(vals) / len(vals), 2)
        result.append(week_summary)

    return result


# Global instance
data_export_service = DataExportService()
