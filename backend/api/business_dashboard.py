"""
Business Intelligence Dashboard API
Comprehensive metrics for AgriTech business operations
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from influxdb_client import InfluxDBClient

logger = logging.getLogger('business-dashboard')


class BusinessDashboard:
    """Aggregates all business metrics into a single dashboard"""

    def __init__(self):
        self.db_path = os.getenv('SQLITE_DB_PATH', 'backend/data/agritech.db')
        self.influx_url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
        self.influx_token = os.getenv('INFLUXDB_TOKEN', 'agritech2026')
        self.influx_org = os.getenv('INFLUXDB_ORG', 'agritech')
        self.influx_bucket = os.getenv('INFLUXDB_BUCKET', 'hydroponics')

    def get_complete_dashboard(self) -> Dict[str, Any]:
        """Get all dashboard metrics in one call"""
        return {
            "timestamp": datetime.now().isoformat(),
            "business_overview": self.get_business_overview(),
            "revenue_metrics": self.get_revenue_metrics(),
            "crop_status": self.get_crop_status(),
            "sensor_health": self.get_sensor_health(),
            "client_health": self.get_client_health(),
            "local_market_data": self.get_local_market_data(),
            "weather_correlation": self.get_weather_correlation(),
            "opportunities": self.get_revenue_opportunities(),
            "alerts_summary": self.get_alerts_summary(),
        }

    # ── Business Overview ─────────────────────────────────────────

    def get_business_overview(self) -> Dict[str, Any]:
        """High-level business KPIs"""
        with sqlite3.connect(self.db_path) as conn:
            # Active clients
            active_clients = conn.execute(
                "SELECT COUNT(*) FROM clients WHERE is_active = 1"
            ).fetchone()[0] or 0

            # MRR (Monthly Recurring Revenue)
            mrr = conn.execute(
                "SELECT SUM(monthly_fee) FROM clients WHERE is_active = 1"
            ).fetchone()[0] or 0.0

            # Active crops
            active_crops = conn.execute(
                "SELECT COUNT(*) FROM crops WHERE status = 'active'"
            ).fetchone()[0] or 0

            # Service visits this month
            start_of_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            visits_this_month = conn.execute(
                "SELECT COUNT(*) FROM service_visits WHERE visit_date >= ?",
                (start_of_month,)
            ).fetchone()[0] or 0

            # Service revenue this month
            service_revenue = conn.execute(
                "SELECT SUM(revenue) FROM service_visits WHERE visit_date >= ?",
                (start_of_month,)
            ).fetchone()[0] or 0.0

            # Total revenue this month
            total_revenue = mrr + service_revenue

            # Growth rate (compare to last month)
            last_month_start = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1).strftime('%Y-%m-%d')
            last_month_end = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            last_month_revenue = conn.execute(
                "SELECT SUM(revenue) FROM service_visits WHERE visit_date >= ? AND visit_date < ?",
                (last_month_start, last_month_end)
            ).fetchone()[0] or 0.0

            growth_rate = 0
            if last_month_revenue > 0:
                growth_rate = ((total_revenue - last_month_revenue) / last_month_revenue) * 100

        return {
            "active_clients": active_clients,
            "mrr": round(mrr, 2),
            "active_crops": active_crops,
            "visits_this_month": visits_this_month,
            "service_revenue_month": round(service_revenue, 2),
            "total_revenue_month": round(total_revenue, 2),
            "growth_rate_percent": round(growth_rate, 1),
            "status": "healthy" if active_clients > 0 else "warning",
        }

    # ── Revenue Metrics ───────────────────────────────────────────

    def get_revenue_metrics(self) -> Dict[str, Any]:
        """Detailed revenue breakdown"""
        with sqlite3.connect(self.db_path) as conn:
            # Revenue by service tier
            tier_revenue = conn.execute("""
                SELECT service_tier, COUNT(*) as count, SUM(monthly_fee) as revenue
                FROM clients WHERE is_active = 1
                GROUP BY service_tier
            """).fetchall()

            tiers = {}
            for tier, count, revenue in tier_revenue:
                tiers[tier] = {
                    "client_count": count,
                    "mrr": round(revenue, 2)
                }

            # Service visit revenue (last 30 days)
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            service_revenue_30d = conn.execute(
                "SELECT SUM(revenue) FROM service_visits WHERE visit_date >= ?",
                (thirty_days_ago,)
            ).fetchone()[0] or 0.0

            # Average revenue per client
            total_clients = conn.execute(
                "SELECT COUNT(*) FROM clients WHERE is_active = 1"
            ).fetchone()[0] or 1  # Avoid division by zero

            total_mrr = conn.execute(
                "SELECT SUM(monthly_fee) FROM clients WHERE is_active = 1"
            ).fetchone()[0] or 0.0

            avg_revenue_per_client = total_mrr / total_clients if total_clients > 0 else 0

            # Projected annual revenue
            monthly_total = total_mrr + (service_revenue_30d / 30 * 30)  # Normalize to 30 days
            projected_annual = monthly_total * 12

            # Churn rate (clients who became inactive in last 30 days)
            churned_clients = conn.execute("""
                SELECT COUNT(*) FROM clients
                WHERE is_active = 0
                  AND updated_at >= ?
            """, (thirty_days_ago,)).fetchone()[0] or 0

            churn_rate = (churned_clients / total_clients * 100) if total_clients > 0 else 0

        return {
            "by_tier": tiers,
            "service_revenue_30d": round(service_revenue_30d, 2),
            "avg_revenue_per_client": round(avg_revenue_per_client, 2),
            "projected_annual": round(projected_annual, 2),
            "churn_rate_percent": round(churn_rate, 1),
        }

    # ── Crop Status ───────────────────────────────────────────────

    def get_crop_status(self) -> Dict[str, Any]:
        """Current crop production status"""
        with sqlite3.connect(self.db_path) as conn:
            # Crops by growth stage
            stage_counts = conn.execute("""
                SELECT gs.stage, COUNT(DISTINCT gs.crop_id) as count
                FROM growth_stages gs
                JOIN crops c ON gs.crop_id = c.id
                WHERE c.status = 'active'
                  AND gs.ended_at IS NULL
                GROUP BY gs.stage
            """).fetchall()

            stages = {stage: count for stage, count in stage_counts}

            # Crops by variety
            variety_counts = conn.execute("""
                SELECT variety, COUNT(*) as count
                FROM crops
                WHERE status = 'active'
                GROUP BY variety
            """).fetchall()

            varieties = {variety: count for variety, count in variety_counts}

            # Upcoming harvests (next 7 days)
            today = datetime.now().date()
            upcoming_harvests = conn.execute("""
                SELECT c.id, c.variety, c.plant_date, gs.stage, gs.started_at
                FROM crops c
                JOIN growth_stages gs ON c.id = gs.crop_id
                WHERE c.status = 'active'
                  AND gs.ended_at IS NULL
                  AND gs.stage = 'maturity'
            """).fetchall()

            # Estimate harvest dates (simplified - assumes 50 days total cycle)
            harvests_due = []
            for crop_id, variety, plant_date, stage, stage_start in upcoming_harvests:
                if plant_date:
                    plant_dt = datetime.strptime(plant_date, '%Y-%m-%d').date()
                    harvest_date = plant_dt + timedelta(days=50)
                    days_until = (harvest_date - today).days
                    if 0 <= days_until <= 7:
                        harvests_due.append({
                            "crop_id": crop_id,
                            "variety": variety,
                            "harvest_date": harvest_date.isoformat(),
                            "days_until": days_until,
                        })

            # Total harvests this month
            start_of_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            harvests_this_month = conn.execute(
                "SELECT COUNT(*) FROM harvests WHERE harvest_date >= ?",
                (start_of_month,)
            ).fetchone()[0] or 0

            # Average yield per crop
            avg_yield = conn.execute(
                "SELECT AVG(weight_kg) FROM harvests WHERE harvest_date >= ?",
                (start_of_month,)
            ).fetchone()[0] or 0.0

        return {
            "by_stage": stages,
            "by_variety": varieties,
            "upcoming_harvests": harvests_due,
            "harvests_this_month": harvests_this_month,
            "avg_yield_kg": round(avg_yield, 2),
            "total_active": sum(stages.values()),
        }

    # ── Sensor Health ─────────────────────────────────────────────

    def get_sensor_health(self) -> Dict[str, Any]:
        """Sensor performance and reliability"""
        with sqlite3.connect(self.db_path) as conn:
            # Sensors by status
            status_counts = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM sensor_units
                GROUP BY status
            """).fetchall()

            by_status = {status: count for status, count in status_counts}

            # Sensors needing calibration (overdue)
            today = datetime.now().strftime('%Y-%m-%d')
            overdue_calibrations = conn.execute("""
                SELECT COUNT(*) FROM sensor_units
                WHERE next_calibration_due IS NOT NULL
                  AND next_calibration_due < ?
            """, (today,)).fetchone()[0] or 0

            # Sensors with drift detected
            drift_detected = conn.execute(
                "SELECT COUNT(*) FROM sensor_units WHERE drift_detected = 1"
            ).fetchone()[0] or 0

            # Average sensor age (days since install)
            avg_age = conn.execute("""
                SELECT AVG(julianday('now') - julianday(install_date))
                FROM sensor_units
            """).fetchone()[0] or 0

        # Get latest sensor readings from InfluxDB
        try:
            client = InfluxDBClient(url=self.influx_url, token=self.influx_token, org=self.influx_org)
            query_api = client.query_api()

            # Query for latest readings
            query = f'''
                from(bucket: "{self.influx_bucket}")
                  |> range(start: -5m)
                  |> filter(fn: (r) => r["_measurement"] == "sensor_reading")
                  |> last()
                  |> count()
            '''
            result = query_api.query(query=query)

            sensors_online = len(result) if result else 0
            client.close()
        except Exception as e:
            logger.error(f"Failed to query InfluxDB: {e}")
            sensors_online = 0

        total_sensors = sum(by_status.values())
        uptime_percent = (sensors_online / total_sensors * 100) if total_sensors > 0 else 0

        return {
            "by_status": by_status,
            "overdue_calibrations": overdue_calibrations,
            "drift_detected": drift_detected,
            "avg_age_days": round(avg_age, 0),
            "sensors_online": sensors_online,
            "total_sensors": total_sensors,
            "uptime_percent": round(uptime_percent, 1),
            "health": "good" if uptime_percent > 95 else "warning" if uptime_percent > 85 else "critical",
        }

    # ── Client Health ─────────────────────────────────────────────

    def get_client_health(self) -> Dict[str, Any]:
        """Client health scores and service needs"""
        with sqlite3.connect(self.db_path) as conn:
            # Clients by health score range
            health_ranges = conn.execute("""
                SELECT
                    CASE
                        WHEN health_score >= 80 THEN 'healthy'
                        WHEN health_score >= 60 THEN 'warning'
                        ELSE 'critical'
                    END as range,
                    COUNT(*) as count
                FROM clients
                WHERE is_active = 1
                GROUP BY range
            """).fetchall()

            by_health = {range_name: count for range_name, count in health_ranges}

            # Clients needing service (health < 80)
            clients_needing_service = conn.execute("""
                SELECT id, company_name, health_score
                FROM clients
                WHERE is_active = 1 AND health_score < 80
                ORDER BY health_score ASC
                LIMIT 5
            """).fetchall()

            needs_service = [
                {
                    "id": cid,
                    "name": name,
                    "health_score": score
                }
                for cid, name, score in clients_needing_service
            ]

            # Average health score
            avg_health = conn.execute(
                "SELECT AVG(health_score) FROM clients WHERE is_active = 1"
            ).fetchone()[0] or 100.0

        return {
            "by_health_range": by_health,
            "needs_service": needs_service,
            "avg_health_score": round(avg_health, 1),
            "critical_count": by_health.get('critical', 0),
        }

    # ── Local Market Data ─────────────────────────────────────────

    def get_local_market_data(self) -> Dict[str, Any]:
        """Algarve local market analysis"""
        # This would be populated from actual sales data
        # For now, return template structure
        return {
            "top_markets": [
                {
                    "name": "Loulé Market",
                    "location": "Loulé",
                    "weekly_revenue": 450,
                    "customers": 35,
                    "avg_basket": 12.85,
                    "premium_multiplier": 1.4
                },
                {
                    "name": "Olhão Fish Market",
                    "location": "Olhão",
                    "weekly_revenue": 320,
                    "customers": 12,
                    "avg_basket": 26.67,
                    "premium_multiplier": 1.6
                },
                {
                    "name": "Direct Restaurants",
                    "location": "Various",
                    "weekly_revenue": 850,
                    "customers": 8,
                    "avg_basket": 106.25,
                    "premium_multiplier": 1.8
                }
            ],
            "top_products": [
                {"name": "Rosso Premium Lettuce", "weekly_kg": 45, "revenue": 450},
                {"name": "Basil", "weekly_kg": 18, "revenue": 360},
                {"name": "Arugula", "weekly_kg": 52, "revenue": 416},
                {"name": "Mint", "weekly_kg": 12, "revenue": 180},
            ],
            "seasonal_trends": {
                "current_season": "winter",
                "tourist_multiplier": 1.0,
                "peak_season_months": ["may", "june", "july", "august", "september"],
                "notes": "Tourist season May-Sep provides 2-3x demand increase"
            }
        }

    # ── Weather Correlation ───────────────────────────────────────

    def get_weather_correlation(self) -> Dict[str, Any]:
        """Outside weather impact on crop performance"""
        # This would query weather data from InfluxDB bucket "weather"
        # For now, return template structure
        return {
            "last_7_days": {
                "avg_temp_outside": 16.5,
                "avg_temp_greenhouse": 21.2,
                "rainfall_mm": 12.5,
                "avg_humidity": 68,
                "solar_hours": 42,
            },
            "correlations": [
                {
                    "condition": "Outside temp >32°C for 3+ days",
                    "impact": "Rosso lettuce yields -15%",
                    "mitigation": "Shade cloth + increased ventilation"
                },
                {
                    "condition": "Night temp <18°C",
                    "impact": "Basil aroma +20% intensity",
                    "mitigation": "Optimal - no action needed"
                }
            ],
            "microclimate_insights": [
                "Greenhouse near Albufeira 2°C warmer than Loulé (coastal effect)",
                "Best production months: March-May and September-November"
            ]
        }

    # ── Revenue Opportunities ─────────────────────────────────────

    def get_revenue_opportunities(self) -> List[Dict[str, Any]]:
        """Actionable business opportunities"""
        opportunities = []

        with sqlite3.connect(self.db_path) as conn:
            # Clients on Bronze tier (upsell to Silver)
            bronze_clients = conn.execute("""
                SELECT id, company_name, monthly_fee, health_score
                FROM clients
                WHERE is_active = 1 AND service_tier = 'bronze' AND health_score >= 80
                LIMIT 3
            """).fetchall()

            for cid, name, fee, health in bronze_clients:
                opportunities.append({
                    "type": "upsell",
                    "client_id": cid,
                    "client_name": name,
                    "current_tier": "bronze",
                    "target_tier": "silver",
                    "revenue_increase": 150,  # €199 - €49
                    "description": f"Healthy client ({health}/100) - pitch expert reviews + WhatsApp alerts",
                    "priority": "medium",
                    "estimated_value": 150
                })

            # Clients needing calibration (service revenue)
            today = datetime.now().strftime('%Y-%m-%d')
            next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            upcoming_calibrations = conn.execute("""
                SELECT c.id, c.company_name, COUNT(su.id) as sensor_count
                FROM clients c
                JOIN sensor_units su ON c.id = su.client_id
                WHERE c.is_active = 1
                  AND su.next_calibration_due BETWEEN ? AND ?
                GROUP BY c.id
            """, (today, next_week)).fetchall()

            for cid, name, sensor_count in upcoming_calibrations:
                opportunities.append({
                    "type": "service_visit",
                    "client_id": cid,
                    "client_name": name,
                    "description": f"{sensor_count} sensor(s) need calibration this week",
                    "priority": "high",
                    "estimated_value": sensor_count * 25  # €25 per sensor
                })

        # New market opportunity (template)
        opportunities.append({
            "type": "new_market",
            "description": "Faro Sunday Market - untapped tourist market",
            "priority": "medium",
            "estimated_value": 400,
            "action": "Set up weekend stall, target tourists + expats"
        })

        return sorted(opportunities, key=lambda x: x.get('priority') == 'high', reverse=True)

    # ── Alerts Summary ────────────────────────────────────────────

    def get_alerts_summary(self) -> Dict[str, Any]:
        """Recent alerts and system events"""
        # This would query from events table
        with sqlite3.connect(self.db_path) as conn:
            # Alerts in last 24 hours
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')

            alerts_24h = conn.execute("""
                SELECT severity, COUNT(*) as count
                FROM events
                WHERE event_type = 'alert'
                  AND created_at >= ?
                GROUP BY severity
            """, (yesterday,)).fetchall()

            by_severity = {severity: count for severity, count in alerts_24h}

            # Total alerts
            total_alerts = sum(by_severity.values())

            # Recent critical alerts
            recent_critical = conn.execute("""
                SELECT message, created_at
                FROM events
                WHERE event_type = 'alert'
                  AND severity IN ('critical', 'urgent')
                  AND created_at >= ?
                ORDER BY created_at DESC
                LIMIT 5
            """, (yesterday,)).fetchall()

            critical_alerts = [
                {"message": msg, "timestamp": ts}
                for msg, ts in recent_critical
            ]

        return {
            "total_24h": total_alerts,
            "by_severity": by_severity,
            "recent_critical": critical_alerts,
            "status": "ok" if total_alerts < 5 else "warning" if total_alerts < 20 else "critical"
        }


# Global instance
dashboard = BusinessDashboard()


def get_dashboard_data() -> Dict[str, Any]:
    """Convenience function for API endpoint"""
    return dashboard.get_complete_dashboard()
