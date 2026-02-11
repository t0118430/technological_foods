"""
Client & Calibration Management System
Tracks B2B clients, sensor health, and service revenue opportunities
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

_DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / 'data' / 'agritech.db'

logger = logging.getLogger('client-manager')


class ServiceTier(Enum):
    """B2B service tiers (from ALERT_ESCALATION.md)"""
    BRONZE = "bronze"      # €49/month - Basic monitoring
    SILVER = "silver"      # €199/month - Expert reviews
    GOLD = "gold"          # €499/month - 24/7 + remote fixes


@dataclass
class Client:
    """B2B Client information"""
    id: int
    company_name: str
    contact_name: str
    contact_phone: str
    contact_email: str
    service_tier: ServiceTier
    location: str
    install_date: str
    monthly_fee: float
    is_active: bool
    health_score: int  # 0-100, negative points system
    notes: str


@dataclass
class SensorUnit:
    """Sensor equipment installed at client location"""
    id: int
    client_id: int
    sensor_type: str  # "temperature", "humidity", "ph", "ec", etc.
    serial_number: str
    install_date: str
    last_calibration: Optional[str]
    next_calibration_due: Optional[str]
    drift_detected: bool
    failure_count: int
    status: str  # "healthy", "degraded", "failing", "offline"


@dataclass
class ServiceVisit:
    """Record of calibration/maintenance visits"""
    id: int
    client_id: int
    visit_date: str
    technician: str
    service_type: str  # "calibration", "repair", "installation", "training"
    sensors_serviced: str  # JSON list of sensor IDs
    issues_found: str
    actions_taken: str
    revenue: float
    next_visit_recommended: Optional[str]


class ClientManager:
    """Manages B2B clients and calibration tracking"""

    def __init__(self, db_path: str = _DEFAULT_DB):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Create client management tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
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
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS sensor_units (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    sensor_type TEXT NOT NULL,
                    serial_number TEXT UNIQUE,
                    install_date TEXT DEFAULT (date('now')),
                    last_calibration TEXT,
                    next_calibration_due TEXT,
                    drift_detected INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'healthy',
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (client_id) REFERENCES clients(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS service_visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    visit_date TEXT DEFAULT (date('now')),
                    technician TEXT,
                    service_type TEXT,
                    sensors_serviced TEXT,
                    issues_found TEXT,
                    actions_taken TEXT,
                    revenue REAL DEFAULT 0.0,
                    next_visit_recommended TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (client_id) REFERENCES clients(id)
                )
            """)

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_clients_active ON clients(is_active)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sensors_client ON sensor_units(client_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sensors_status ON sensor_units(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_client ON service_visits(client_id)")

            conn.commit()
            logger.info("Client management database initialized")

    # ── Client Management ─────────────────────────────────────────

    def add_client(self, company_name: str, contact_name: str, contact_phone: str,
                   contact_email: str, service_tier: ServiceTier,
                   location: str, monthly_fee: float = None) -> int:
        """Register new B2B client"""

        if monthly_fee is None:
            tier_fees = {
                ServiceTier.BRONZE: 49.0,
                ServiceTier.SILVER: 199.0,
                ServiceTier.GOLD: 499.0,
            }
            monthly_fee = tier_fees[service_tier]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO clients (company_name, contact_name, contact_phone, contact_email,
                                     service_tier, location, monthly_fee)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (company_name, contact_name, contact_phone, contact_email,
                  service_tier.value, location, monthly_fee))
            conn.commit()
            return cursor.lastrowid

    def get_client(self, client_id: int) -> Optional[Client]:
        """Get client by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
            if not row:
                return None
            return Client(
                id=row['id'],
                company_name=row['company_name'],
                contact_name=row['contact_name'],
                contact_phone=row['contact_phone'],
                contact_email=row['contact_email'],
                service_tier=ServiceTier(row['service_tier']),
                location=row['location'],
                install_date=row['install_date'],
                monthly_fee=row['monthly_fee'],
                is_active=bool(row['is_active']),
                health_score=row['health_score'],
                notes=row['notes'] or "",
            )

    def list_clients(self, active_only: bool = True) -> List[Client]:
        """List all clients"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM clients"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY company_name"

            rows = conn.execute(query).fetchall()
            return [
                Client(
                    id=row['id'],
                    company_name=row['company_name'],
                    contact_name=row['contact_name'],
                    contact_phone=row['contact_phone'],
                    contact_email=row['contact_email'],
                    service_tier=ServiceTier(row['service_tier']),
                    location=row['location'],
                    install_date=row['install_date'],
                    monthly_fee=row['monthly_fee'],
                    is_active=bool(row['is_active']),
                    health_score=row['health_score'],
                    notes=row['notes'] or "",
                )
                for row in rows
            ]

    def update_health_score(self, client_id: int, delta: int, reason: str):
        """Update client health score (negative points system)

        Args:
            client_id: Client ID
            delta: Points to add/subtract (negative = worse health)
            reason: Reason for health change
        """
        with sqlite3.connect(self.db_path) as conn:
            current = conn.execute(
                "SELECT health_score FROM clients WHERE id = ?", (client_id,)
            ).fetchone()[0]

            new_score = max(0, min(100, current + delta))

            conn.execute("""
                UPDATE clients
                SET health_score = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (new_score, client_id))
            conn.commit()

            logger.info(f"Client {client_id} health: {current} → {new_score} ({reason})")

            # Send alert if health is critically low
            if new_score < 60:
                from notifications.multi_channel_notifier import business_reporter
                issues = self.get_client_issues(client_id)
                business_reporter.send_client_health_alert(
                    client_name=self.get_client(client_id).company_name,
                    health_score=new_score,
                    issues=issues
                )

    def get_client_issues(self, client_id: int) -> List[str]:
        """Get list of issues affecting client health"""
        issues = []

        # Check overdue calibrations
        with sqlite3.connect(self.db_path) as conn:
            overdue = conn.execute("""
                SELECT COUNT(*) FROM sensor_units
                WHERE client_id = ?
                  AND next_calibration_due IS NOT NULL
                  AND date(next_calibration_due) < date('now')
            """, (client_id,)).fetchone()[0]

            if overdue > 0:
                issues.append(f"{overdue} sensor(es) com calibração atrasada")

            # Check degraded sensors
            degraded = conn.execute("""
                SELECT COUNT(*) FROM sensor_units
                WHERE client_id = ? AND status IN ('degraded', 'failing')
            """, (client_id,)).fetchone()[0]

            if degraded > 0:
                issues.append(f"{degraded} sensor(es) degradado(s)")

            # Check offline sensors
            offline = conn.execute("""
                SELECT COUNT(*) FROM sensor_units
                WHERE client_id = ? AND status = 'offline'
            """, (client_id,)).fetchone()[0]

            if offline > 0:
                issues.append(f"{offline} sensor(es) offline")

        return issues

    # ── Sensor Management ─────────────────────────────────────────

    def add_sensor(self, client_id: int, sensor_type: str, serial_number: str) -> int:
        """Register new sensor at client location"""
        # Auto-schedule first calibration in 90 days
        next_calibration = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO sensor_units (client_id, sensor_type, serial_number,
                                          next_calibration_due)
                VALUES (?, ?, ?, ?)
            """, (client_id, sensor_type, serial_number, next_calibration))
            conn.commit()
            return cursor.lastrowid

    def report_sensor_drift(self, sensor_id: int, drift_value: float):
        """Report sensor drift detected by dual-sensor system"""
        with sqlite3.connect(self.db_path) as conn:
            sensor = conn.execute(
                "SELECT client_id, status FROM sensor_units WHERE id = ?",
                (sensor_id,)
            ).fetchone()

            if not sensor:
                return

            client_id, current_status = sensor

            # Update sensor status based on drift severity
            if drift_value > 5.0:
                new_status = "failing"
                self.update_health_score(client_id, -20, f"Sensor {sensor_id} failing")
            elif drift_value > 2.0:
                new_status = "degraded"
                self.update_health_score(client_id, -10, f"Sensor {sensor_id} degraded")
            else:
                new_status = "healthy"
                return  # No action needed

            conn.execute("""
                UPDATE sensor_units
                SET drift_detected = 1, status = ?, failure_count = failure_count + 1
                WHERE id = ?
            """, (new_status, sensor_id))
            conn.commit()

            logger.warning(f"Sensor {sensor_id} drift detected: {drift_value}% ({new_status})")

    # ── Service Visit Management ──────────────────────────────────

    def record_service_visit(self, client_id: int, technician: str, service_type: str,
                             sensors_serviced: List[int], issues_found: str,
                             actions_taken: str, revenue: float) -> int:
        """Record calibration/service visit"""

        with sqlite3.connect(self.db_path) as conn:
            # Record visit
            import json
            cursor = conn.execute("""
                INSERT INTO service_visits (client_id, technician, service_type,
                                            sensors_serviced, issues_found,
                                            actions_taken, revenue)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (client_id, technician, service_type,
                  json.dumps(sensors_serviced), issues_found, actions_taken, revenue))

            # Update sensor calibration dates
            today = datetime.now().strftime('%Y-%m-%d')
            next_cal = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

            for sensor_id in sensors_serviced:
                conn.execute("""
                    UPDATE sensor_units
                    SET last_calibration = ?,
                        next_calibration_due = ?,
                        drift_detected = 0,
                        status = 'healthy'
                    WHERE id = ?
                """, (today, next_cal, sensor_id))

            # Improve client health score after service
            self.update_health_score(client_id, +15, "Service visit completed")

            conn.commit()
            return cursor.lastrowid

    def get_clients_needing_service(self) -> List[Dict[str, Any]]:
        """Get clients that need calibration visits (for daily digest)"""

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT c.id, c.company_name, c.health_score,
                       MAX(sv.visit_date) as last_visit,
                       COUNT(su.id) as sensor_count,
                       SUM(CASE WHEN su.status != 'healthy' THEN 1 ELSE 0 END) as unhealthy_sensors
                FROM clients c
                LEFT JOIN service_visits sv ON c.id = sv.client_id
                LEFT JOIN sensor_units su ON c.id = su.client_id
                WHERE c.is_active = 1
                  AND (c.health_score < 80
                       OR su.next_calibration_due < date('now', '+7 days'))
                GROUP BY c.id
                ORDER BY c.health_score ASC
            """).fetchall()

            results = []
            for row in rows:
                last_visit = datetime.strptime(row['last_visit'], '%Y-%m-%d') if row['last_visit'] else None
                days_since = (datetime.now() - last_visit).days if last_visit else 9999

                results.append({
                    'id': row['id'],
                    'name': row['company_name'],
                    'health_score': row['health_score'],
                    'days_since_service': days_since,
                    'unhealthy_sensors': row['unhealthy_sensors'],
                })

            return results

    # ── Business Intelligence ─────────────────────────────────────

    def get_revenue_metrics(self) -> Dict[str, Any]:
        """Calculate revenue metrics for business reporting"""

        with sqlite3.connect(self.db_path) as conn:
            # Monthly recurring revenue
            mrr = conn.execute("""
                SELECT SUM(monthly_fee) FROM clients WHERE is_active = 1
            """).fetchone()[0] or 0.0

            # Service revenue (last 30 days)
            service_revenue = conn.execute("""
                SELECT SUM(revenue) FROM service_visits
                WHERE visit_date >= date('now', '-30 days')
            """).fetchone()[0] or 0.0

            # Scheduled calibrations this month
            scheduled = conn.execute("""
                SELECT COUNT(*) FROM sensor_units
                WHERE next_calibration_due BETWEEN date('now') AND date('now', '+30 days')
            """).fetchone()[0] or 0

            return {
                'mrr': mrr,
                'service_revenue_30d': service_revenue,
                'total_revenue_30d': mrr + service_revenue,
                'scheduled_calibrations': scheduled,
                'revenue_estimate': scheduled * 50.0,  # €50 per calibration
            }


# Global instance
client_manager = ClientManager()
