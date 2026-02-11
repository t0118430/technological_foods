"""
Tests for BusinessDashboard (business_dashboard.py)
Covers: dashboard overview, revenue metrics, crop status, sensor health, client health, opportunities, alerts
Note: Tests use SQLite in isolation; InfluxDB calls are mocked.
"""

import pytest
import sqlite3
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from business.business_dashboard import BusinessDashboard, get_dashboard_data


@pytest.fixture
def dashboard(tmp_path):
    """Dashboard with isolated SQLite DB and mocked InfluxDB."""
    db_path = str(tmp_path / "test_dashboard.db")

    # Create the required tables
    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT,
                contact_name TEXT,
                contact_phone TEXT,
                contact_email TEXT,
                service_tier TEXT DEFAULT 'bronze',
                location TEXT,
                install_date TEXT DEFAULT (date('now')),
                monthly_fee REAL DEFAULT 49.0,
                is_active INTEGER DEFAULT 1,
                health_score INTEGER DEFAULT 100,
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sensor_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                sensor_type TEXT,
                serial_number TEXT,
                install_date TEXT DEFAULT (date('now')),
                last_calibration TEXT,
                next_calibration_due TEXT,
                drift_detected INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'healthy'
            );

            CREATE TABLE IF NOT EXISTS service_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                visit_date TEXT DEFAULT (date('now')),
                technician TEXT,
                service_type TEXT,
                sensors_serviced TEXT,
                issues_found TEXT,
                actions_taken TEXT,
                revenue REAL DEFAULT 0.0,
                next_visit_recommended TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS crops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                variety TEXT,
                plant_date TEXT,
                status TEXT DEFAULT 'active'
            );

            CREATE TABLE IF NOT EXISTS growth_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_id INTEGER,
                stage TEXT,
                started_at TEXT DEFAULT (datetime('now')),
                ended_at TEXT
            );

            CREATE TABLE IF NOT EXISTS harvests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_id INTEGER,
                harvest_date TEXT,
                weight_kg REAL
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                severity TEXT,
                message TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)

    dash = BusinessDashboard()
    dash.db_path = db_path
    return dash


def _add_client(db_path, name, tier="bronze", fee=49.0, active=1, health=100):
    """Helper to insert a client."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO clients (company_name, service_tier, monthly_fee, is_active, health_score) VALUES (?, ?, ?, ?, ?)",
            (name, tier, fee, active, health)
        )


def _add_sensor(db_path, client_id, sensor_type="temperature", status="healthy", cal_due=None):
    """Helper to insert a sensor."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO sensor_units (client_id, sensor_type, status, next_calibration_due) VALUES (?, ?, ?, ?)",
            (client_id, sensor_type, status, cal_due)
        )


# ── Business Overview ──────────────────────────────────────────


class TestBusinessOverview:
    def test_overview_empty_db(self, dashboard):
        overview = dashboard.get_business_overview()
        assert overview["active_clients"] == 0
        assert overview["mrr"] == 0.0
        assert overview["status"] == "warning"

    def test_overview_with_clients(self, dashboard):
        _add_client(dashboard.db_path, "Farm A", "bronze", 49.0)
        _add_client(dashboard.db_path, "Farm B", "gold", 499.0)
        overview = dashboard.get_business_overview()
        assert overview["active_clients"] == 2
        assert overview["mrr"] == 548.0
        assert overview["status"] == "healthy"

    def test_overview_excludes_inactive(self, dashboard):
        _add_client(dashboard.db_path, "Active", "bronze", 49.0, active=1)
        _add_client(dashboard.db_path, "Inactive", "gold", 499.0, active=0)
        overview = dashboard.get_business_overview()
        assert overview["active_clients"] == 1
        assert overview["mrr"] == 49.0


# ── Revenue Metrics ────────────────────────────────────────────


class TestRevenueMetrics:
    def test_revenue_empty(self, dashboard):
        metrics = dashboard.get_revenue_metrics()
        assert metrics["by_tier"] == {}
        assert metrics["avg_revenue_per_client"] == 0

    def test_revenue_by_tier(self, dashboard):
        _add_client(dashboard.db_path, "B1", "bronze", 49.0)
        _add_client(dashboard.db_path, "B2", "bronze", 49.0)
        _add_client(dashboard.db_path, "S1", "silver", 199.0)
        metrics = dashboard.get_revenue_metrics()
        assert metrics["by_tier"]["bronze"]["client_count"] == 2
        assert metrics["by_tier"]["bronze"]["mrr"] == 98.0
        assert metrics["by_tier"]["silver"]["client_count"] == 1

    def test_churn_rate_calculation(self, dashboard):
        _add_client(dashboard.db_path, "Active1", "bronze", 49.0, active=1)
        # Add inactive client with recent updated_at
        with sqlite3.connect(dashboard.db_path) as conn:
            conn.execute(
                "INSERT INTO clients (company_name, service_tier, monthly_fee, is_active, updated_at) VALUES (?, ?, ?, ?, ?)",
                ("Churned", "bronze", 49.0, 0, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
        metrics = dashboard.get_revenue_metrics()
        assert metrics["churn_rate_percent"] > 0


# ── Crop Status ────────────────────────────────────────────────


class TestCropStatus:
    def test_crop_status_empty(self, dashboard):
        status = dashboard.get_crop_status()
        assert status["total_active"] == 0
        assert status["by_stage"] == {}
        assert status["by_variety"] == {}

    def test_crop_status_with_data(self, dashboard):
        with sqlite3.connect(dashboard.db_path) as conn:
            conn.execute("INSERT INTO crops (variety, plant_date, status) VALUES ('rosso', '2026-01-01', 'active')")
            conn.execute("INSERT INTO growth_stages (crop_id, stage) VALUES (1, 'vegetative')")
        status = dashboard.get_crop_status()
        assert status["by_variety"]["rosso"] == 1
        assert status["by_stage"]["vegetative"] == 1
        assert status["total_active"] == 1


# ── Sensor Health ──────────────────────────────────────────────


class TestSensorHealth:
    @patch("business_dashboard.InfluxDBClient")
    def test_sensor_health_empty(self, mock_influx, dashboard):
        mock_client = MagicMock()
        mock_client.query_api.return_value.query.return_value = []
        mock_influx.return_value = mock_client
        health = dashboard.get_sensor_health()
        assert health["total_sensors"] == 0

    @patch("business_dashboard.InfluxDBClient")
    def test_sensor_health_with_sensors(self, mock_influx, dashboard):
        mock_client = MagicMock()
        mock_client.query_api.return_value.query.return_value = []
        mock_influx.return_value = mock_client

        _add_client(dashboard.db_path, "Farm", "bronze")
        _add_sensor(dashboard.db_path, 1, "temperature", "healthy")
        _add_sensor(dashboard.db_path, 1, "humidity", "degraded")

        health = dashboard.get_sensor_health()
        assert health["total_sensors"] == 2
        assert health["by_status"]["healthy"] == 1
        assert health["by_status"]["degraded"] == 1

    @patch("business_dashboard.InfluxDBClient")
    def test_sensor_overdue_calibrations(self, mock_influx, dashboard):
        mock_client = MagicMock()
        mock_client.query_api.return_value.query.return_value = []
        mock_influx.return_value = mock_client

        _add_client(dashboard.db_path, "Farm", "bronze")
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        _add_sensor(dashboard.db_path, 1, "temperature", "healthy", cal_due=yesterday)

        health = dashboard.get_sensor_health()
        assert health["overdue_calibrations"] == 1

    @patch("business_dashboard.InfluxDBClient")
    def test_sensor_health_influx_failure_graceful(self, mock_influx, dashboard):
        mock_influx.return_value.query_api.return_value.query.side_effect = Exception("Connection refused")

        _add_client(dashboard.db_path, "Farm", "bronze")
        _add_sensor(dashboard.db_path, 1, "temperature", "healthy")

        health = dashboard.get_sensor_health()
        assert health["sensors_online"] == 0  # Graceful fallback
        assert health["total_sensors"] == 1


# ── Client Health ──────────────────────────────────────────────


class TestClientHealth:
    def test_client_health_empty(self, dashboard):
        health = dashboard.get_client_health()
        assert health["avg_health_score"] == 100.0  # default when no clients

    def test_client_health_ranges(self, dashboard):
        _add_client(dashboard.db_path, "Healthy Farm", health=90)
        _add_client(dashboard.db_path, "Warning Farm", health=70)
        _add_client(dashboard.db_path, "Critical Farm", health=40)
        health = dashboard.get_client_health()
        assert health["by_health_range"]["healthy"] == 1
        assert health["by_health_range"]["warning"] == 1
        assert health["by_health_range"]["critical"] == 1
        assert health["critical_count"] == 1
        assert len(health["needs_service"]) == 2  # warning + critical

    def test_needs_service_ordered_by_score(self, dashboard):
        _add_client(dashboard.db_path, "Bad", health=30)
        _add_client(dashboard.db_path, "Worse", health=10)
        health = dashboard.get_client_health()
        assert health["needs_service"][0]["name"] == "Worse"
        assert health["needs_service"][1]["name"] == "Bad"


# ── Static Data ────────────────────────────────────────────────


class TestStaticData:
    def test_local_market_data_structure(self, dashboard):
        data = dashboard.get_local_market_data()
        assert "top_markets" in data
        assert "top_products" in data
        assert "seasonal_trends" in data
        assert len(data["top_markets"]) > 0

    def test_weather_correlation_structure(self, dashboard):
        data = dashboard.get_weather_correlation()
        assert "last_7_days" in data
        assert "correlations" in data


# ── Revenue Opportunities ─────────────────────────────────────


class TestRevenueOpportunities:
    def test_opportunities_include_new_market(self, dashboard):
        opps = dashboard.get_revenue_opportunities()
        market_opps = [o for o in opps if o["type"] == "new_market"]
        assert len(market_opps) >= 1

    def test_bronze_upsell_healthy_clients(self, dashboard):
        _add_client(dashboard.db_path, "Happy Bronze", "bronze", 49.0, health=90)
        opps = dashboard.get_revenue_opportunities()
        upsells = [o for o in opps if o.get("type") == "upsell"]
        assert len(upsells) >= 1
        assert upsells[0]["target_tier"] == "silver"


# ── Alerts Summary ─────────────────────────────────────────────


class TestAlertsSummary:
    def test_alerts_empty(self, dashboard):
        summary = dashboard.get_alerts_summary()
        assert summary["total_24h"] == 0
        assert summary["status"] == "ok"

    def test_alerts_with_events(self, dashboard):
        with sqlite3.connect(dashboard.db_path) as conn:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                "INSERT INTO events (event_type, severity, message, created_at) VALUES (?, ?, ?, ?)",
                ("alert", "critical", "High temperature", now)
            )
            conn.execute(
                "INSERT INTO events (event_type, severity, message, created_at) VALUES (?, ?, ?, ?)",
                ("alert", "warning", "Low humidity", now)
            )
        summary = dashboard.get_alerts_summary()
        assert summary["total_24h"] == 2
        assert summary["by_severity"]["critical"] == 1
        assert len(summary["recent_critical"]) == 1


# ── Complete Dashboard ─────────────────────────────────────────


class TestCompleteDashboard:
    @patch("business_dashboard.InfluxDBClient")
    def test_complete_dashboard_returns_all_sections(self, mock_influx, dashboard):
        mock_client = MagicMock()
        mock_client.query_api.return_value.query.return_value = []
        mock_influx.return_value = mock_client

        result = dashboard.get_complete_dashboard()
        assert "timestamp" in result
        assert "business_overview" in result
        assert "revenue_metrics" in result
        assert "crop_status" in result
        assert "sensor_health" in result
        assert "client_health" in result
        assert "local_market_data" in result
        assert "weather_correlation" in result
        assert "opportunities" in result
        assert "alerts_summary" in result
