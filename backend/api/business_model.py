"""
Business Model & Multi-Tenant Management - SaaS Platform

Complete business-grade system with:
- Customer/Grower management
- Subscription tiers with different features
- Sensor inventory & upselling
- Business intelligence
- Revenue tracking

Author: AgriTech Hydroponics - SaaS Division
License: Proprietary
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger('business-model')

DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'agritech_business.db'
DB_PATH.parent.mkdir(exist_ok=True)


# Subscription Tier Configuration
SUBSCRIPTION_TIERS = {
    'bronze': {
        'name': 'Bronze',
        'price_monthly': 49,
        'features': {
            'alert_types': ['critical'],
            'data_retention_days': 7,
            'calibration_frequency_days': 90,
            'notification_channels': ['email', 'console'],
            'max_zones': 1,
            'max_crops': 3,
            'growth_stage_tracking': False,
            'harvest_analytics': False,
            'preventive_alerts': False,
            'escalation': False,
            'remote_support': False,
            'sensor_recommendations': False,
        },
        'support': 'Email (business hours)',
        'response_time_hours': 48
    },
    'silver': {
        'name': 'Silver',
        'price_monthly': 199,
        'features': {
            'alert_types': ['critical', 'warning', 'preventive'],
            'data_retention_days': 30,
            'calibration_frequency_days': 30,
            'notification_channels': ['email', 'sms', 'console'],
            'max_zones': 3,
            'max_crops': 10,
            'growth_stage_tracking': True,
            'harvest_analytics': True,
            'preventive_alerts': True,
            'escalation': False,
            'remote_support': False,
            'sensor_recommendations': True,
        },
        'support': 'Email + Phone (business hours)',
        'response_time_hours': 24
    },
    'gold': {
        'name': 'Gold',
        'price_monthly': 499,
        'features': {
            'alert_types': ['critical', 'warning', 'preventive', 'urgent'],
            'data_retention_days': 90,
            'calibration_frequency_days': 14,
            'notification_channels': ['email', 'sms', 'whatsapp', 'console', 'ntfy'],
            'max_zones': 10,
            'max_crops': 50,
            'growth_stage_tracking': True,
            'harvest_analytics': True,
            'preventive_alerts': True,
            'escalation': True,
            'remote_support': True,
            'sensor_recommendations': True,
        },
        'support': '24/7 Phone + Email',
        'response_time_hours': 4
    },
    'platinum': {
        'name': 'Platinum',
        'price_monthly': 799,
        'features': {
            'alert_types': ['critical', 'warning', 'preventive', 'urgent'],
            'data_retention_days': 180,  # Raw data, unlimited aggregated
            'calibration_frequency_days': 7,
            'notification_channels': ['email', 'sms', 'whatsapp', 'console', 'ntfy', 'phone_call'],
            'max_zones': 999,  # Unlimited
            'max_crops': 999,  # Unlimited
            'growth_stage_tracking': True,
            'harvest_analytics': True,
            'preventive_alerts': True,
            'escalation': True,
            'remote_support': True,
            'sensor_recommendations': True,
            'custom_dashboard': True,
            'priority_support': True,
            'dedicated_account_manager': True,
        },
        'support': '24/7 Priority + Dedicated Manager',
        'response_time_hours': 0.25  # 15 minutes
    }
}


class BusinessDatabase:
    """Multi-tenant business database for SaaS platform."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.init_business_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_business_database(self):
        """Initialize business/customer database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Customers/Growers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    company_name TEXT,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT,
                    address TEXT,
                    subscription_tier TEXT DEFAULT 'bronze',
                    subscription_start_date DATE NOT NULL,
                    subscription_end_date DATE,
                    auto_renew BOOLEAN DEFAULT 1,
                    status TEXT DEFAULT 'active',
                    total_revenue REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Customer sensor inventory
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_sensors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    sensor_type TEXT NOT NULL,
                    sensor_model TEXT,
                    serial_number TEXT,
                    installation_date DATE,
                    status TEXT DEFAULT 'active',
                    last_calibration DATE,
                    next_calibration_due DATE,
                    notes TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')

            # Sensor recommendations/upsells
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensor_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    sensor_type TEXT NOT NULL,
                    recommended_date DATE NOT NULL,
                    reason TEXT,
                    expected_improvement TEXT,
                    status TEXT DEFAULT 'pending',
                    responded_date DATE,
                    response TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')

            # Payment/billing history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'EUR',
                    payment_date DATE NOT NULL,
                    payment_method TEXT,
                    tier TEXT NOT NULL,
                    period_start DATE,
                    period_end DATE,
                    status TEXT DEFAULT 'completed',
                    notes TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')

            # Feature usage tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feature_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    feature_name TEXT NOT NULL,
                    usage_date DATE NOT NULL,
                    usage_count INTEGER DEFAULT 1,
                    metadata JSON,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')

            # Support tickets
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    severity TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'open',
                    assigned_to TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    response_time_hours REAL,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')

            # Business metrics cache
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS business_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_date DATE NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL,
                    metadata JSON,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(metric_date, metric_name)
                )
            ''')

            # Notification log (track what was sent to whom)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    notification_type TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    subject TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    delivered BOOLEAN,
                    tier_restricted BOOLEAN DEFAULT 0,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')

            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_customers_tier ON customers(subscription_tier)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensors_customer ON customer_sensors(customer_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_customer ON notification_log(customer_id)')

            conn.commit()
            logger.info("Business database initialized successfully")

    def create_customer(self, name: str, email: str, company_name: str = None,
                       phone: str = None, tier: str = 'bronze') -> int:
        """Create a new customer/grower."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            start_date = datetime.now().date()
            end_date = (datetime.now() + timedelta(days=365)).date()

            cursor.execute('''
                INSERT INTO customers (name, company_name, email, phone, subscription_tier,
                                     subscription_start_date, subscription_end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, company_name, email, phone, tier, start_date, end_date))

            customer_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Created customer {customer_id}: {name} ({tier} tier)")
            return customer_id

    def get_customer(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get customer details."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_customer_tier_config(self, customer_id: int) -> Dict[str, Any]:
        """Get tier configuration for customer."""
        customer = self.get_customer(customer_id)
        if not customer:
            return SUBSCRIPTION_TIERS['bronze']  # Default

        tier = customer['subscription_tier']
        return SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['bronze'])

    def can_use_feature(self, customer_id: int, feature: str) -> bool:
        """Check if customer's tier allows a feature."""
        config = self.get_customer_tier_config(customer_id)
        return config['features'].get(feature, False)

    def get_notification_channels(self, customer_id: int) -> List[str]:
        """Get allowed notification channels for customer's tier."""
        config = self.get_customer_tier_config(customer_id)
        return config['features'].get('notification_channels', ['console'])

    def add_sensor_to_customer(self, customer_id: int, sensor_type: str,
                              sensor_model: str = None, serial_number: str = None) -> int:
        """Add sensor to customer's inventory."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            installation_date = datetime.now().date()

            cursor.execute('''
                INSERT INTO customer_sensors (customer_id, sensor_type, sensor_model,
                                            serial_number, installation_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (customer_id, sensor_type, sensor_model, serial_number, installation_date))

            sensor_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Added {sensor_type} sensor to customer {customer_id}")
            return sensor_id

    def get_customer_sensors(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get all sensors for a customer."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM customer_sensors
                WHERE customer_id = ? AND status = 'active'
            ''', (customer_id,))
            return [dict(row) for row in cursor.fetchall()]

    def recommend_sensor(self, customer_id: int, sensor_type: str,
                        reason: str, expected_improvement: str) -> int:
        """Create sensor recommendation (upsell opportunity)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO sensor_recommendations (customer_id, sensor_type, recommended_date,
                                                   reason, expected_improvement)
                VALUES (?, ?, ?, ?, ?)
            ''', (customer_id, sensor_type, datetime.now().date(), reason, expected_improvement))

            rec_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Recommended {sensor_type} to customer {customer_id}")
            return rec_id

    def get_pending_recommendations(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get pending sensor recommendations for customer."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM sensor_recommendations
                WHERE customer_id = ? AND status = 'pending'
                ORDER BY recommended_date DESC
            ''', (customer_id,))
            return [dict(row) for row in cursor.fetchall()]

    def record_payment(self, customer_id: int, amount: float, tier: str,
                      period_months: int = 1) -> int:
        """Record payment and update customer."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            payment_date = datetime.now().date()
            period_start = payment_date
            period_end = (datetime.now() + timedelta(days=30 * period_months)).date()

            cursor.execute('''
                INSERT INTO payments (customer_id, amount, payment_date, tier,
                                    period_start, period_end)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (customer_id, amount, payment_date, tier, period_start, period_end))

            payment_id = cursor.lastrowid

            # Update customer total revenue and subscription
            cursor.execute('''
                UPDATE customers
                SET total_revenue = total_revenue + ?,
                    subscription_tier = ?,
                    subscription_end_date = ?,
                    updated_at = ?
                WHERE id = ?
            ''', (amount, tier, period_end, datetime.now(), customer_id))

            conn.commit()

            logger.info(f"Recorded payment of {amount} EUR for customer {customer_id}")
            return payment_id

    def log_notification(self, customer_id: int, notification_type: str,
                        channel: str, subject: str, delivered: bool = True,
                        tier_restricted: bool = False):
        """Log notification sent to customer."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notification_log (customer_id, notification_type, channel,
                                            subject, delivered, tier_restricted)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (customer_id, notification_type, channel, subject, delivered, tier_restricted))
            conn.commit()

    def calculate_business_metrics(self) -> Dict[str, Any]:
        """Calculate key business metrics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            metrics = {}

            # Total customers by tier
            cursor.execute('''
                SELECT subscription_tier, COUNT(*) as count
                FROM customers
                WHERE status = 'active'
                GROUP BY subscription_tier
            ''')
            metrics['customers_by_tier'] = {row['subscription_tier']: row['count']
                                           for row in cursor.fetchall()}

            # Monthly Recurring Revenue (MRR)
            mrr = 0
            for tier, count in metrics['customers_by_tier'].items():
                mrr += SUBSCRIPTION_TIERS[tier]['price_monthly'] * count
            metrics['mrr'] = mrr
            metrics['arr'] = mrr * 12  # Annual Recurring Revenue

            # Total customers
            cursor.execute('SELECT COUNT(*) as count FROM customers WHERE status = "active"')
            metrics['total_active_customers'] = cursor.fetchone()['count']

            # Average Revenue Per Customer (ARPC)
            if metrics['total_active_customers'] > 0:
                metrics['arpc'] = mrr / metrics['total_active_customers']
            else:
                metrics['arpc'] = 0

            # Total revenue (all time)
            cursor.execute('SELECT SUM(total_revenue) as total FROM customers')
            metrics['total_revenue_all_time'] = cursor.fetchone()['total'] or 0

            # Recent payments (last 30 days)
            cursor.execute('''
                SELECT SUM(amount) as recent_revenue
                FROM payments
                WHERE payment_date >= date('now', '-30 days')
            ''')
            metrics['revenue_last_30_days'] = cursor.fetchone()['recent_revenue'] or 0

            # Sensor recommendations (upsell pipeline)
            cursor.execute('''
                SELECT COUNT(*) as count FROM sensor_recommendations
                WHERE status = 'pending'
            ''')
            metrics['pending_upsells'] = cursor.fetchone()['count']

            return metrics

    def get_upsell_opportunities(self) -> List[Dict[str, Any]]:
        """Identify customers who should be upsold."""
        opportunities = []

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Customers on Bronze using lots of features → upgrade to Silver
            cursor.execute('''
                SELECT c.id, c.name, c.email, c.subscription_tier, COUNT(f.id) as feature_count
                FROM customers c
                JOIN feature_usage f ON c.id = f.customer_id
                WHERE c.subscription_tier = 'bronze'
                  AND f.usage_date >= date('now', '-7 days')
                GROUP BY c.id
                HAVING feature_count > 20
            ''')

            for row in cursor.fetchall():
                opportunities.append({
                    'customer_id': row['id'],
                    'customer_name': row['name'],
                    'current_tier': row['subscription_tier'],
                    'recommended_tier': 'silver',
                    'reason': 'High feature usage - would benefit from Silver tier',
                    'expected_revenue_increase': SUBSCRIPTION_TIERS['silver']['price_monthly'] -
                                                SUBSCRIPTION_TIERS['bronze']['price_monthly']
                })

            # Customers missing key sensors
            cursor.execute('''
                SELECT c.id, c.name, c.email, c.subscription_tier
                FROM customers c
                WHERE c.status = 'active'
                  AND c.id NOT IN (
                    SELECT DISTINCT customer_id FROM customer_sensors
                    WHERE sensor_type = 'ph'
                  )
            ''')

            for row in cursor.fetchall():
                opportunities.append({
                    'customer_id': row['id'],
                    'customer_name': row['name'],
                    'current_tier': row['subscription_tier'],
                    'recommendation_type': 'sensor',
                    'sensor_type': 'pH',
                    'reason': 'Missing pH sensor - critical for nutrient optimization',
                    'expected_improvement': '30% better yield with pH monitoring'
                })

        return opportunities


# Global instance
business_db = BusinessDatabase()
