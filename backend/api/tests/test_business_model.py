"""
Tests for BusinessDatabase (business_model.py)
Covers: customer CRUD, tier config, feature checks, sensors, recommendations, payments, metrics, upsells
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from business.business_model import BusinessDatabase, SUBSCRIPTION_TIERS


@pytest.fixture
def db(tmp_path):
    """Fresh business database for each test."""
    db_path = tmp_path / "test_business.db"
    return BusinessDatabase(db_path=db_path)


@pytest.fixture
def db_with_customer(db):
    """Database with one bronze customer pre-created."""
    cid = db.create_customer("Test Grower", "test@example.com", company_name="Test Farm", tier="bronze")
    return db, cid


# ── Customer CRUD ──────────────────────────────────────────────


class TestCustomerCRUD:
    def test_create_customer_returns_id(self, db):
        cid = db.create_customer("Alice", "alice@farm.com")
        assert isinstance(cid, int)
        assert cid > 0

    def test_create_customer_with_all_fields(self, db):
        cid = db.create_customer(
            "Bob", "bob@farm.com",
            company_name="Bob's Greens",
            phone="+351912345678",
            tier="gold"
        )
        customer = db.get_customer(cid)
        assert customer["name"] == "Bob"
        assert customer["company_name"] == "Bob's Greens"
        assert customer["phone"] == "+351912345678"
        assert customer["subscription_tier"] == "gold"
        assert customer["status"] == "active"

    def test_create_customer_default_tier_is_bronze(self, db):
        cid = db.create_customer("Default Tier", "default@farm.com")
        customer = db.get_customer(cid)
        assert customer["subscription_tier"] == "bronze"

    def test_get_customer_not_found_returns_none(self, db):
        assert db.get_customer(9999) is None

    def test_create_duplicate_email_raises(self, db):
        db.create_customer("Alice", "dup@farm.com")
        with pytest.raises(Exception):
            db.create_customer("Bob", "dup@farm.com")

    def test_customer_has_subscription_dates(self, db):
        cid = db.create_customer("Dates", "dates@farm.com")
        customer = db.get_customer(cid)
        assert customer["subscription_start_date"] is not None
        assert customer["subscription_end_date"] is not None


# ── Tier Configuration ─────────────────────────────────────────


class TestTierConfig:
    def test_get_tier_config_for_existing_customer(self, db_with_customer):
        db, cid = db_with_customer
        config = db.get_customer_tier_config(cid)
        assert config["name"] == "Bronze"
        assert config["price_monthly"] == 49

    def test_get_tier_config_nonexistent_customer_returns_bronze(self, db):
        config = db.get_customer_tier_config(9999)
        assert config["name"] == "Bronze"

    def test_all_tiers_exist_in_config(self):
        for tier in ["bronze", "silver", "gold", "platinum"]:
            assert tier in SUBSCRIPTION_TIERS
            assert "price_monthly" in SUBSCRIPTION_TIERS[tier]
            assert "features" in SUBSCRIPTION_TIERS[tier]

    def test_tier_prices_ascending(self):
        prices = [SUBSCRIPTION_TIERS[t]["price_monthly"] for t in ["bronze", "silver", "gold", "platinum"]]
        assert prices == sorted(prices)


# ── Feature Checks ─────────────────────────────────────────────


class TestFeatureChecks:
    def test_bronze_cannot_use_escalation(self, db_with_customer):
        db, cid = db_with_customer
        assert db.can_use_feature(cid, "escalation") is False

    def test_gold_can_use_escalation(self, db):
        cid = db.create_customer("Gold User", "gold@farm.com", tier="gold")
        assert db.can_use_feature(cid, "escalation") is True

    def test_bronze_notification_channels(self, db_with_customer):
        db, cid = db_with_customer
        channels = db.get_notification_channels(cid)
        assert "email" in channels
        assert "console" in channels
        assert "whatsapp" not in channels

    def test_gold_notification_channels_include_whatsapp(self, db):
        cid = db.create_customer("Gold", "gold2@farm.com", tier="gold")
        channels = db.get_notification_channels(cid)
        assert "whatsapp" in channels
        assert "ntfy" in channels

    def test_nonexistent_feature_returns_false(self, db_with_customer):
        db, cid = db_with_customer
        assert db.can_use_feature(cid, "nonexistent_feature") is False


# ── Sensor Inventory ───────────────────────────────────────────


class TestSensorInventory:
    def test_add_sensor(self, db_with_customer):
        db, cid = db_with_customer
        sid = db.add_sensor_to_customer(cid, "temperature", sensor_model="DHT20")
        assert isinstance(sid, int)
        assert sid > 0

    def test_get_customer_sensors(self, db_with_customer):
        db, cid = db_with_customer
        db.add_sensor_to_customer(cid, "temperature")
        db.add_sensor_to_customer(cid, "ph")
        sensors = db.get_customer_sensors(cid)
        assert len(sensors) == 2
        types = {s["sensor_type"] for s in sensors}
        assert types == {"temperature", "ph"}

    def test_get_sensors_empty_for_new_customer(self, db_with_customer):
        db, cid = db_with_customer
        assert db.get_customer_sensors(cid) == []


# ── Sensor Recommendations ─────────────────────────────────────


class TestSensorRecommendations:
    def test_recommend_sensor(self, db_with_customer):
        db, cid = db_with_customer
        rec_id = db.recommend_sensor(cid, "ph", "Missing pH monitoring", "30% better yield")
        assert isinstance(rec_id, int)
        assert rec_id > 0

    def test_get_pending_recommendations(self, db_with_customer):
        db, cid = db_with_customer
        db.recommend_sensor(cid, "ph", "Need pH", "Better yield")
        db.recommend_sensor(cid, "ec", "Need EC", "Better nutrient control")
        recs = db.get_pending_recommendations(cid)
        assert len(recs) == 2

    def test_no_pending_recommendations_for_new_customer(self, db_with_customer):
        db, cid = db_with_customer
        assert db.get_pending_recommendations(cid) == []


# ── Payments ───────────────────────────────────────────────────


class TestPayments:
    def test_record_payment_updates_revenue(self, db_with_customer):
        db, cid = db_with_customer
        db.record_payment(cid, 49.0, "bronze")
        customer = db.get_customer(cid)
        assert customer["total_revenue"] == 49.0

    def test_multiple_payments_accumulate(self, db_with_customer):
        db, cid = db_with_customer
        db.record_payment(cid, 49.0, "bronze")
        db.record_payment(cid, 199.0, "silver")
        customer = db.get_customer(cid)
        assert customer["total_revenue"] == 248.0

    def test_payment_upgrades_tier(self, db_with_customer):
        db, cid = db_with_customer
        db.record_payment(cid, 199.0, "silver")
        customer = db.get_customer(cid)
        assert customer["subscription_tier"] == "silver"

    def test_record_payment_returns_id(self, db_with_customer):
        db, cid = db_with_customer
        pid = db.record_payment(cid, 49.0, "bronze")
        assert isinstance(pid, int)
        assert pid > 0


# ── Business Metrics ───────────────────────────────────────────


class TestBusinessMetrics:
    def test_metrics_empty_database(self, db):
        metrics = db.calculate_business_metrics()
        assert metrics["total_active_customers"] == 0
        assert metrics["mrr"] == 0
        assert metrics["arpc"] == 0

    def test_metrics_with_customers(self, db):
        db.create_customer("Bronze1", "b1@farm.com", tier="bronze")
        db.create_customer("Silver1", "s1@farm.com", tier="silver")
        metrics = db.calculate_business_metrics()
        assert metrics["total_active_customers"] == 2
        assert metrics["mrr"] == 49 + 199  # bronze + silver
        assert metrics["arr"] == (49 + 199) * 12
        assert metrics["arpc"] == (49 + 199) / 2

    def test_metrics_customers_by_tier(self, db):
        db.create_customer("B1", "b1@farm.com", tier="bronze")
        db.create_customer("B2", "b2@farm.com", tier="bronze")
        db.create_customer("G1", "g1@farm.com", tier="gold")
        metrics = db.calculate_business_metrics()
        assert metrics["customers_by_tier"]["bronze"] == 2
        assert metrics["customers_by_tier"]["gold"] == 1


# ── Upsell Opportunities ──────────────────────────────────────


class TestUpsellOpportunities:
    def test_upsell_detects_missing_ph_sensor(self, db):
        cid = db.create_customer("No pH", "noph@farm.com", tier="bronze")
        # Customer has temperature but no pH
        db.add_sensor_to_customer(cid, "temperature")
        opportunities = db.get_upsell_opportunities()
        ph_recs = [o for o in opportunities if o.get("sensor_type") == "pH"]
        assert len(ph_recs) >= 1
        assert ph_recs[0]["customer_id"] == cid

    def test_upsell_empty_database(self, db):
        opportunities = db.get_upsell_opportunities()
        assert isinstance(opportunities, list)


# ── Notification Logging ──────────────────────────────────────


class TestNotificationLogging:
    def test_log_notification(self, db_with_customer):
        db, cid = db_with_customer
        # Should not raise
        db.log_notification(cid, "alert", "email", "High temp warning")

    def test_log_notification_with_tier_restriction(self, db_with_customer):
        db, cid = db_with_customer
        db.log_notification(cid, "alert", "whatsapp", "Restricted", tier_restricted=True)
