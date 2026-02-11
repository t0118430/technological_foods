"""
Site Visits Manager - Field Inspection Tracking System
Manages site visit records, follow-ups, and visit analytics.

Educational notes:
- Follows the same pattern as client_manager.py (SQLite + class-based manager)
- JSON columns store variable-length arrays in SQLite (no native array type)
- Parameterized queries (?) prevent SQL injection - never use f-strings in SQL
- Pagination uses LIMIT/OFFSET for scalability - without it, large tables kill performance
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

_DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / 'data' / 'agritech.db'

logger = logging.getLogger('site-visits')


class SiteVisitsManager:
    """Manages site visit records for field inspections"""

    def __init__(self, db_path: str = _DEFAULT_DB):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create site_visits table if it doesn't exist.

        Educational: JSON columns (zones_inspected, crop_batches_checked, etc.) store
        variable-length arrays. SQLite has no native array type, so we serialize to JSON.
        The CHECK constraint on visit_type enforces a known set of values at the DB level.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS site_visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    visit_date TEXT NOT NULL DEFAULT (date('now')),
                    inspector_name TEXT NOT NULL,
                    client_id INTEGER,
                    facility_name TEXT,
                    visit_type TEXT NOT NULL CHECK (visit_type IN ('routine','emergency','follow_up','audit')),
                    zones_inspected TEXT,
                    crop_batches_checked TEXT,
                    sensor_readings_snapshot TEXT,
                    observations TEXT,
                    issues_found TEXT,
                    actions_taken TEXT,
                    follow_up_required INTEGER DEFAULT 0,
                    follow_up_date TEXT,
                    follow_up_notes TEXT,
                    follow_up_completed INTEGER DEFAULT 0,
                    overall_rating INTEGER DEFAULT 3 CHECK (overall_rating BETWEEN 1 AND 5),
                    photo_notes TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_site_visits_date ON site_visits(visit_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_site_visits_client ON site_visits(client_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_site_visits_type ON site_visits(visit_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_site_visits_followup ON site_visits(follow_up_required, follow_up_completed)")

            conn.commit()
            logger.info("Site visits database initialized")

    # ── CRUD Operations ────────────────────────────────────────────

    def create_visit(self, data: Dict[str, Any]) -> int:
        """Create a new site visit record.

        Educational: We use parameterized queries (?) instead of f-strings to prevent
        SQL injection. The JSON fields are serialized with json.dumps() before storage.
        """
        # Serialize JSON fields
        zones = json.dumps(data.get('zones_inspected', []))
        batches = json.dumps(data.get('crop_batches_checked', []))
        snapshot = json.dumps(data.get('sensor_readings_snapshot', {}))
        issues = json.dumps(data.get('issues_found', []))

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO site_visits (
                    visit_date, inspector_name, client_id, facility_name,
                    visit_type, zones_inspected, crop_batches_checked,
                    sensor_readings_snapshot, observations, issues_found,
                    actions_taken, follow_up_required, follow_up_date,
                    follow_up_notes, overall_rating, photo_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('visit_date', datetime.now().strftime('%Y-%m-%d')),
                data['inspector_name'],
                data.get('client_id'),
                data.get('facility_name', ''),
                data['visit_type'],
                zones,
                batches,
                snapshot,
                data.get('observations', ''),
                issues,
                data.get('actions_taken', ''),
                1 if data.get('follow_up_required') else 0,
                data.get('follow_up_date'),
                data.get('follow_up_notes', ''),
                data.get('overall_rating', 3),
                data.get('photo_notes', ''),
            ))
            conn.commit()
            return cursor.lastrowid

    def get_visit(self, visit_id: int) -> Optional[Dict[str, Any]]:
        """Get a single visit by ID, with JSON fields parsed back to Python objects."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM site_visits WHERE id = ?", (visit_id,)).fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def update_visit(self, visit_id: int, data: Dict[str, Any]) -> bool:
        """Update an existing visit. Only updates fields present in data dict."""
        # Build SET clause dynamically from provided fields
        allowed = {
            'visit_date', 'inspector_name', 'client_id', 'facility_name',
            'visit_type', 'zones_inspected', 'crop_batches_checked',
            'sensor_readings_snapshot', 'observations', 'issues_found',
            'actions_taken', 'follow_up_required', 'follow_up_date',
            'follow_up_notes', 'follow_up_completed', 'overall_rating', 'photo_notes'
        }

        json_fields = {'zones_inspected', 'crop_batches_checked', 'sensor_readings_snapshot', 'issues_found'}

        sets = []
        values = []
        for key, value in data.items():
            if key not in allowed:
                continue
            if key in json_fields and isinstance(value, (list, dict)):
                value = json.dumps(value)
            if key == 'follow_up_required':
                value = 1 if value else 0
            sets.append(f"{key} = ?")
            values.append(value)

        if not sets:
            return False

        sets.append("updated_at = datetime('now')")
        values.append(visit_id)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE site_visits SET {', '.join(sets)} WHERE id = ?",
                values
            )
            conn.commit()
            return True

    def delete_visit(self, visit_id: int) -> bool:
        """Delete a visit record."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM site_visits WHERE id = ?", (visit_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ── List & Filter ──────────────────────────────────────────────

    def list_visits(self, filters: Dict[str, Any] = None, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """List visits with filtering and pagination.

        Educational: Pagination (LIMIT/OFFSET) is essential for scalability.
        Without it, querying 10k visits would send all rows to the client,
        causing slow responses and high memory usage. We also return total
        count so the UI can render page controls.
        """
        filters = filters or {}
        where_clauses = []
        params = []

        if filters.get('visit_type'):
            where_clauses.append("sv.visit_type = ?")
            params.append(filters['visit_type'])

        if filters.get('inspector_name'):
            where_clauses.append("sv.inspector_name LIKE ?")
            params.append(f"%{filters['inspector_name']}%")

        if filters.get('date_from'):
            where_clauses.append("sv.visit_date >= ?")
            params.append(filters['date_from'])

        if filters.get('date_to'):
            where_clauses.append("sv.visit_date <= ?")
            params.append(filters['date_to'])

        if filters.get('follow_up') == 'pending':
            where_clauses.append("sv.follow_up_required = 1 AND sv.follow_up_completed = 0")
        elif filters.get('follow_up') == 'completed':
            where_clauses.append("sv.follow_up_required = 1 AND sv.follow_up_completed = 1")

        if filters.get('search'):
            where_clauses.append("(sv.inspector_name LIKE ? OR sv.observations LIKE ? OR sv.facility_name LIKE ?)")
            search_term = f"%{filters['search']}%"
            params.extend([search_term, search_term, search_term])

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        sort_col = filters.get('sort', 'visit_date')
        sort_dir = 'ASC' if filters.get('sort_dir', 'desc').lower() == 'asc' else 'DESC'
        # Whitelist sort columns to prevent injection
        allowed_sorts = {'visit_date', 'inspector_name', 'visit_type', 'overall_rating', 'created_at'}
        if sort_col not in allowed_sorts:
            sort_col = 'visit_date'

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Count total matching records
            count_row = conn.execute(
                f"SELECT COUNT(*) as total FROM site_visits sv{where_sql}", params
            ).fetchone()
            total = count_row['total']

            # Fetch paginated results with client name join
            offset = (page - 1) * per_page
            rows = conn.execute(f"""
                SELECT sv.*, c.company_name as client_name
                FROM site_visits sv
                LEFT JOIN clients c ON sv.client_id = c.id
                {where_sql}
                ORDER BY sv.{sort_col} {sort_dir}
                LIMIT ? OFFSET ?
            """, params + [per_page, offset]).fetchall()

            visits = []
            for row in rows:
                visit = self._row_to_dict(row)
                visit['client_name'] = row['client_name'] or ''
                visits.append(visit)

            return {
                'visits': visits,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': max(1, -(-total // per_page)),  # Ceiling division
            }

    # ── Dashboard Analytics ────────────────────────────────────────

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Return KPIs, chart data, and recent activity for the dashboard.

        Educational: Aggregating data in SQL is far more efficient than loading
        all rows into Python and computing in-memory. The DB engine optimizes
        GROUP BY and aggregate functions (COUNT, AVG) with index scans.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # KPI: Total visits
            total = conn.execute("SELECT COUNT(*) as c FROM site_visits").fetchone()['c']

            # KPI: Visits this month
            this_month = conn.execute("""
                SELECT COUNT(*) as c FROM site_visits
                WHERE visit_date >= date('now', 'start of month')
            """).fetchone()['c']

            # KPI: Visits last month (for delta comparison)
            last_month = conn.execute("""
                SELECT COUNT(*) as c FROM site_visits
                WHERE visit_date >= date('now', 'start of month', '-1 month')
                  AND visit_date < date('now', 'start of month')
            """).fetchone()['c']

            # KPI: Pending follow-ups
            pending_followups = conn.execute("""
                SELECT COUNT(*) as c FROM site_visits
                WHERE follow_up_required = 1 AND follow_up_completed = 0
            """).fetchone()['c']

            # KPI: Average rating
            avg_rating = conn.execute(
                "SELECT AVG(overall_rating) as avg FROM site_visits"
            ).fetchone()['avg'] or 0

            # Chart: Visits by month (last 6 months)
            monthly_data = conn.execute("""
                SELECT strftime('%Y-%m', visit_date) as month, COUNT(*) as count
                FROM site_visits
                WHERE visit_date >= date('now', '-6 months')
                GROUP BY month
                ORDER BY month
            """).fetchall()

            # Chart: Visits by type
            type_data = conn.execute("""
                SELECT visit_type, COUNT(*) as count
                FROM site_visits
                GROUP BY visit_type
                ORDER BY count DESC
            """).fetchall()

            # Chart: Rating distribution
            rating_data = conn.execute("""
                SELECT overall_rating, COUNT(*) as count
                FROM site_visits
                GROUP BY overall_rating
                ORDER BY overall_rating
            """).fetchall()

            # Recent activity (last 10 visits)
            recent = conn.execute("""
                SELECT sv.*, c.company_name as client_name
                FROM site_visits sv
                LEFT JOIN clients c ON sv.client_id = c.id
                ORDER BY sv.created_at DESC
                LIMIT 10
            """).fetchall()

            # Top visited clients
            top_clients = conn.execute("""
                SELECT c.id, c.company_name, c.health_score,
                       COUNT(sv.id) as visit_count,
                       MAX(sv.visit_date) as last_visit
                FROM site_visits sv
                JOIN clients c ON sv.client_id = c.id
                GROUP BY c.id
                ORDER BY visit_count DESC
                LIMIT 10
            """).fetchall()

            # Inspector list (for datalist suggestions)
            inspectors = conn.execute("""
                SELECT DISTINCT inspector_name FROM site_visits
                ORDER BY inspector_name
            """).fetchall()

            return {
                'kpis': {
                    'total_visits': total,
                    'visits_this_month': this_month,
                    'visits_last_month': last_month,
                    'month_delta': this_month - last_month,
                    'pending_followups': pending_followups,
                    'avg_rating': round(avg_rating, 1),
                },
                'charts': {
                    'monthly': [{'month': r['month'], 'count': r['count']} for r in monthly_data],
                    'by_type': [{'type': r['visit_type'], 'count': r['count']} for r in type_data],
                    'ratings': [{'rating': r['overall_rating'], 'count': r['count']} for r in rating_data],
                },
                'recent_activity': [self._row_to_dict(r, include_client=True) for r in recent],
                'top_clients': [{
                    'id': r['id'],
                    'company_name': r['company_name'],
                    'health_score': r['health_score'],
                    'visit_count': r['visit_count'],
                    'last_visit': r['last_visit'],
                } for r in top_clients],
                'inspectors': [r['inspector_name'] for r in inspectors],
            }

    # ── Client List (for form dropdown) ────────────────────────────

    def get_clients_list(self) -> List[Dict[str, Any]]:
        """Query existing clients table for form dropdown.

        Educational: This is a deliberate coupling to the clients table from
        client_manager.py. In a microservices architecture, you'd call an API
        instead. Here we query directly because we're in the same SQLite DB.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT id, company_name, service_tier, location, health_score
                FROM clients
                WHERE is_active = 1
                ORDER BY company_name
            """).fetchall()
            return [{
                'id': r['id'],
                'company_name': r['company_name'],
                'service_tier': r['service_tier'],
                'location': r['location'],
                'health_score': r['health_score'],
            } for r in rows]

    # ── Export ─────────────────────────────────────────────────────

    def get_export_data(self) -> List[Dict[str, Any]]:
        """Return flat list of all visits for CSV export."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT sv.*, c.company_name as client_name
                FROM site_visits sv
                LEFT JOIN clients c ON sv.client_id = c.id
                ORDER BY sv.visit_date DESC
            """).fetchall()
            return [self._row_to_dict(r, include_client=True) for r in rows]

    # ── Follow-up Completion ───────────────────────────────────────

    def complete_follow_up(self, visit_id: int) -> bool:
        """Mark a visit's follow-up as completed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE site_visits
                SET follow_up_completed = 1, updated_at = datetime('now')
                WHERE id = ? AND follow_up_required = 1
            """, (visit_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ── Helpers ────────────────────────────────────────────────────

    def _row_to_dict(self, row, include_client: bool = False) -> Dict[str, Any]:
        """Convert a database row to a dict, parsing JSON fields back to Python objects."""
        d = {
            'id': row['id'],
            'visit_date': row['visit_date'],
            'inspector_name': row['inspector_name'],
            'client_id': row['client_id'],
            'facility_name': row['facility_name'] or '',
            'visit_type': row['visit_type'],
            'zones_inspected': self._parse_json(row['zones_inspected'], []),
            'crop_batches_checked': self._parse_json(row['crop_batches_checked'], []),
            'sensor_readings_snapshot': self._parse_json(row['sensor_readings_snapshot'], {}),
            'observations': row['observations'] or '',
            'issues_found': self._parse_json(row['issues_found'], []),
            'actions_taken': row['actions_taken'] or '',
            'follow_up_required': bool(row['follow_up_required']),
            'follow_up_date': row['follow_up_date'],
            'follow_up_notes': row['follow_up_notes'] or '',
            'follow_up_completed': bool(row['follow_up_completed']),
            'overall_rating': row['overall_rating'],
            'photo_notes': row['photo_notes'] or '',
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }
        if include_client:
            try:
                d['client_name'] = row['client_name'] or ''
            except (IndexError, KeyError):
                d['client_name'] = ''
        return d

    @staticmethod
    def _parse_json(value, default):
        """Safely parse a JSON string, returning default if invalid."""
        if not value:
            return default
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default


# Global instance (same pattern as client_manager.py)
site_visits_manager = SiteVisitsManager()
