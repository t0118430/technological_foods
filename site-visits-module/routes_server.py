"""
Site Visits Routes - Extract from server.py

This file contains ONLY the site visits route handlers extracted from
the main server. Your C# equivalent would be an ASP.NET Controller
or Minimal API route group.

NOTE: This is a REFERENCE file, not runnable on its own.
      It shows the exact route logic you need to replicate.
"""

# ═══════════════════════════════════════════════════════════════════
# IMPORT (add to top of server.py)
# ═══════════════════════════════════════════════════════════════════

# from site_visits_manager import site_visits_manager


# ═══════════════════════════════════════════════════════════════════
# AUTH BYPASS (site visits are public - no API key needed)
# ═══════════════════════════════════════════════════════════════════

# In do_GET, add "/site-visits" and "/api/site-visits" to public routes:
#
#   if path in ("/", "/api/health", ..., "/site-visits") or path.startswith("/api/site-visits"):
#       pass  # Public — no auth required
#
# In do_POST / do_PUT / do_DELETE, skip auth for site-visits:
#
#   if not path.startswith("/api/site-visits"):
#       if not self._check_api_key():
#           return


# ═══════════════════════════════════════════════════════════════════
# GET ROUTES
# ═══════════════════════════════════════════════════════════════════

def handle_get_routes(self, path, query):
    """Add these elif blocks inside do_GET(), before the final else: 404"""

    # --- Serve HTML page ---
    # GET /site-visits
    if path == "/site-visits":
        sv_path = Path(__file__).resolve().parent.parent / "site_visits.html"
        if sv_path.exists():
            self._send_html(200, sv_path.read_text(encoding="utf-8"))
        else:
            self._send_html(404, "<h1>Not found</h1>")

    # --- Dashboard analytics (KPIs + charts + recent activity) ---
    # GET /api/site-visits/dashboard
    # Response: { kpis: {...}, charts: {...}, recent_activity: [...], top_clients: [...], inspectors: [...] }
    elif path == "/api/site-visits/dashboard":
        data = site_visits_manager.get_dashboard_stats()
        self._send_json(200, data)

    # --- Client list for form dropdown ---
    # GET /api/site-visits/clients
    # Response: { clients: [{ id, company_name, service_tier, location, health_score }] }
    elif path == "/api/site-visits/clients":
        clients = site_visits_manager.get_clients_list()
        self._send_json(200, {"clients": clients})

    # --- Export all visits (for CSV generation) ---
    # GET /api/site-visits/export
    # Response: { visits: [...all visits with client_name joined...] }
    elif path == "/api/site-visits/export":
        data = site_visits_manager.get_export_data()
        self._send_json(200, {"visits": data})

    # --- List visits (paginated + filtered) ---
    # GET /api/site-visits?page=1&per_page=15&visit_type=routine&sort=visit_date&sort_dir=desc
    # Response: { visits: [...], total: 35, page: 1, per_page: 15, total_pages: 3 }
    elif path == "/api/site-visits":
        page = int(query.get('page', ['1'])[0])
        per_page = int(query.get('per_page', ['20'])[0])
        filters = {
            'visit_type': query.get('visit_type', [None])[0],
            'inspector_name': query.get('inspector', [None])[0],
            'date_from': query.get('date_from', [None])[0],
            'date_to': query.get('date_to', [None])[0],
            'follow_up': query.get('follow_up', [None])[0],
            'search': query.get('search', [None])[0],
            'sort': query.get('sort', ['visit_date'])[0],
            'sort_dir': query.get('sort_dir', ['desc'])[0],
        }
        filters = {k: v for k, v in filters.items() if v is not None}
        result = site_visits_manager.list_visits(filters, page, per_page)
        self._send_json(200, result)

    # --- Single visit detail ---
    # GET /api/site-visits/{id}
    # Response: { id, visit_date, inspector_name, ..., issues_found: [...], sensor_readings_snapshot: {...} }
    elif path.startswith("/api/site-visits/"):
        visit_id = int(path.split("/api/site-visits/")[1])
        visit = site_visits_manager.get_visit(visit_id)
        if visit:
            self._send_json(200, visit)
        else:
            self._send_json(404, {"error": "Visit not found"})


# ═══════════════════════════════════════════════════════════════════
# POST ROUTES
# ═══════════════════════════════════════════════════════════════════

def handle_post_routes(self, path):
    """Add these elif blocks inside do_POST(), before the final else: 404"""

    # --- Create a new visit ---
    # POST /api/site-visits
    # Body: { inspector_name, visit_type, client_id?, facility_name?, zones_inspected?, ... }
    # Response: { status: "created", id: 36 }
    if path == "/api/site-visits":
        data = self._read_body()
        if not data.get('inspector_name'):
            self._send_json(400, {"error": "inspector_name required"})
            return
        if not data.get('visit_type'):
            self._send_json(400, {"error": "visit_type required"})
            return
        visit_id = site_visits_manager.create_visit(data)
        self._send_json(201, {"status": "created", "id": visit_id})

    # --- Mark follow-up as completed ---
    # POST /api/site-visits/{id}/complete-follow-up
    # Response: { status: "completed", id: 5 }
    elif path.endswith("/complete-follow-up") and "/api/site-visits/" in path:
        visit_id = int(path.split("/api/site-visits/")[1].split("/")[0])
        success = site_visits_manager.complete_follow_up(visit_id)
        if success:
            self._send_json(200, {"status": "completed", "id": visit_id})
        else:
            self._send_json(404, {"error": "Visit not found or no follow-up pending"})


# ═══════════════════════════════════════════════════════════════════
# PUT ROUTES
# ═══════════════════════════════════════════════════════════════════

def handle_put_routes(self, path):
    """Add this elif block inside do_PUT(), before the final else: 404"""

    # --- Update a visit (partial update) ---
    # PUT /api/site-visits/{id}
    # Body: { overall_rating: 5, observations: "Updated" }  (only fields to change)
    # Response: { status: "updated", id: 5 }
    if path.startswith("/api/site-visits/"):
        visit_id = int(path.split("/api/site-visits/")[1])
        data = self._read_body()
        success = site_visits_manager.update_visit(visit_id, data)
        if success:
            self._send_json(200, {"status": "updated", "id": visit_id})
        else:
            self._send_json(404, {"error": "Visit not found or no fields to update"})


# ═══════════════════════════════════════════════════════════════════
# DELETE ROUTES
# ═══════════════════════════════════════════════════════════════════

def handle_delete_routes(self, path):
    """Add this elif block inside do_DELETE(), before the final else: 404"""

    # --- Delete a visit ---
    # DELETE /api/site-visits/{id}
    # Response: { status: "deleted", id: 5 }
    if path.startswith("/api/site-visits/"):
        visit_id = int(path.split("/api/site-visits/")[1])
        if site_visits_manager.delete_visit(visit_id):
            self._send_json(200, {"status": "deleted", "id": visit_id})
        else:
            self._send_json(404, {"error": "Visit not found"})
