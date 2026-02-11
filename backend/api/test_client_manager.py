"""
Tests for ClientManager (client_manager.py)
Covers: client CRUD, health scores, sensor management, service visits, revenue metrics
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from client_manager import ClientManager, ServiceTier, Client, SensorUnit


@pytest.fixture
def manager(tmp_path):
    """Fresh ClientManager with isolated DB."""
    db_path = tmp_path / "test_client.db"
    return ClientManager(db_path=str(db_path))


@pytest.fixture
def manager_with_client(manager):
    """ClientManager with one pre-created Bronze client."""
    cid = manager.add_client(
        company_name="Test Farm Ltd",
        contact_name="Maria Silva",
        contact_phone="+351912345678",
        contact_email="maria@testfarm.pt",
        service_tier=ServiceTier.BRONZE,
        location="Loulé, Algarve"
    )
    return manager, cid


# ── Client Management ──────────────────────────────────────────


class TestClientManagement:
    def test_add_client_returns_id(self, manager):
        cid = manager.add_client(
            company_name="Farm A",
            contact_name="Alice",
            contact_phone="+351900000001",
            contact_email="alice@farma.pt",
            service_tier=ServiceTier.BRONZE,
            location="Faro"
        )
        assert isinstance(cid, int)
        assert cid > 0

    def test_add_client_default_fee_by_tier(self, manager):
        cid = manager.add_client(
            company_name="Silver Farm",
            contact_name="Bob",
            contact_phone="+351900000002",
            contact_email="bob@silverfarm.pt",
            service_tier=ServiceTier.SILVER,
            location="Olhão"
        )
        client = manager.get_client(cid)
        assert client.monthly_fee == 199.0

    def test_add_client_custom_fee(self, manager):
        cid = manager.add_client(
            company_name="Custom Farm",
            contact_name="Carlos",
            contact_phone="+351900000003",
            contact_email="carlos@custom.pt",
            service_tier=ServiceTier.GOLD,
            location="Tavira",
            monthly_fee=450.0
        )
        client = manager.get_client(cid)
        assert client.monthly_fee == 450.0

    def test_get_client_returns_client_object(self, manager_with_client):
        manager, cid = manager_with_client
        client = manager.get_client(cid)
        assert isinstance(client, Client)
        assert client.company_name == "Test Farm Ltd"
        assert client.contact_name == "Maria Silva"
        assert client.service_tier == ServiceTier.BRONZE
        assert client.is_active is True
        assert client.health_score == 100

    def test_get_client_not_found_returns_none(self, manager):
        assert manager.get_client(9999) is None

    def test_list_clients_active_only(self, manager):
        manager.add_client("Farm1", "A", "1", "a@farm.com", ServiceTier.BRONZE, "Faro")
        manager.add_client("Farm2", "B", "2", "b@farm.com", ServiceTier.SILVER, "Loulé")
        clients = manager.list_clients(active_only=True)
        assert len(clients) == 2
        assert all(c.is_active for c in clients)

    def test_list_clients_sorted_by_name(self, manager):
        manager.add_client("Zebra Farm", "Z", "1", "z@farm.com", ServiceTier.BRONZE, "Faro")
        manager.add_client("Alpha Farm", "A", "2", "a@farm.com", ServiceTier.BRONZE, "Faro")
        clients = manager.list_clients()
        assert clients[0].company_name == "Alpha Farm"
        assert clients[1].company_name == "Zebra Farm"


# ── Health Score ───────────────────────────────────────────────


class TestHealthScore:
    @patch("client_manager.ClientManager.get_client_issues", return_value=[])
    def test_health_score_decrease(self, mock_issues, manager_with_client):
        manager, cid = manager_with_client
        with patch("client_manager.business_reporter", create=True):
            manager.update_health_score(cid, -20, "Sensor failure")
        client = manager.get_client(cid)
        assert client.health_score == 80

    @patch("client_manager.ClientManager.get_client_issues", return_value=[])
    def test_health_score_clamped_to_zero(self, mock_issues, manager_with_client):
        manager, cid = manager_with_client
        with patch("client_manager.business_reporter", create=True):
            manager.update_health_score(cid, -200, "Total failure")
        client = manager.get_client(cid)
        assert client.health_score == 0

    def test_health_score_clamped_to_100(self, manager_with_client):
        manager, cid = manager_with_client
        manager.update_health_score(cid, +50, "Great performance")
        client = manager.get_client(cid)
        assert client.health_score == 100  # already at 100, stays at 100

    def test_get_client_issues_no_sensors(self, manager_with_client):
        manager, cid = manager_with_client
        issues = manager.get_client_issues(cid)
        assert issues == []


# ── Sensor Management ──────────────────────────────────────────


class TestSensorManagement:
    def test_add_sensor(self, manager_with_client):
        manager, cid = manager_with_client
        sid = manager.add_sensor(cid, "temperature", "SN-TEMP-001")
        assert isinstance(sid, int)
        assert sid > 0

    def test_report_sensor_drift_failing(self, manager_with_client):
        manager, cid = manager_with_client
        sid = manager.add_sensor(cid, "temperature", "SN-TEMP-002")
        with patch.object(manager, "update_health_score") as mock_health:
            manager.report_sensor_drift(sid, 6.0)  # > 5.0 = failing
            mock_health.assert_called_once()
            call_args = mock_health.call_args
            assert call_args[0][1] == -20  # -20 points for failing

    def test_report_sensor_drift_degraded(self, manager_with_client):
        manager, cid = manager_with_client
        sid = manager.add_sensor(cid, "humidity", "SN-HUM-001")
        with patch.object(manager, "update_health_score") as mock_health:
            manager.report_sensor_drift(sid, 3.0)  # > 2.0 = degraded
            mock_health.assert_called_once()
            assert mock_health.call_args[0][1] == -10

    def test_report_sensor_drift_healthy_no_action(self, manager_with_client):
        manager, cid = manager_with_client
        sid = manager.add_sensor(cid, "ph", "SN-PH-001")
        with patch.object(manager, "update_health_score") as mock_health:
            manager.report_sensor_drift(sid, 1.0)  # < 2.0 = healthy
            mock_health.assert_not_called()

    def test_report_sensor_drift_nonexistent_sensor(self, manager):
        # Should not raise
        manager.report_sensor_drift(9999, 10.0)


# ── Service Visits ─────────────────────────────────────────────


class TestServiceVisits:
    def test_record_service_visit(self, manager_with_client):
        manager, cid = manager_with_client
        sid = manager.add_sensor(cid, "temperature", "SN-001")
        with patch.object(manager, "update_health_score"):
            visit_id = manager.record_service_visit(
                client_id=cid,
                technician="João Tech",
                service_type="calibration",
                sensors_serviced=[sid],
                issues_found="Minor drift",
                actions_taken="Recalibrated",
                revenue=50.0
            )
        assert isinstance(visit_id, int)
        assert visit_id > 0

    def test_service_visit_resets_sensor_status(self, manager_with_client):
        manager, cid = manager_with_client
        sid = manager.add_sensor(cid, "temperature", "SN-002")
        # First degrade the sensor
        with patch.object(manager, "update_health_score"):
            manager.report_sensor_drift(sid, 3.0)
        # Then service it
        with patch.object(manager, "update_health_score"):
            manager.record_service_visit(
                client_id=cid,
                technician="Tech",
                service_type="calibration",
                sensors_serviced=[sid],
                issues_found="Drift",
                actions_taken="Recalibrated",
                revenue=50.0
            )
        # Verify sensor is healthy again - check DB directly
        import sqlite3
        with sqlite3.connect(manager.db_path) as conn:
            row = conn.execute(
                "SELECT status, drift_detected FROM sensor_units WHERE id = ?", (sid,)
            ).fetchone()
            assert row[0] == "healthy"
            assert row[1] == 0  # drift_detected reset


# ── Revenue Metrics ────────────────────────────────────────────


class TestRevenueMetrics:
    def test_revenue_metrics_empty(self, manager):
        metrics = manager.get_revenue_metrics()
        assert metrics["mrr"] == 0.0
        assert metrics["service_revenue_30d"] == 0.0

    def test_revenue_metrics_with_clients(self, manager):
        manager.add_client("Farm1", "A", "1", "a@f.com", ServiceTier.BRONZE, "Faro")
        manager.add_client("Farm2", "B", "2", "b@f.com", ServiceTier.GOLD, "Loulé")
        metrics = manager.get_revenue_metrics()
        assert metrics["mrr"] == 49.0 + 499.0

    def test_get_clients_needing_service_empty(self, manager):
        results = manager.get_clients_needing_service()
        assert isinstance(results, list)
