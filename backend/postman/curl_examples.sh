#!/usr/bin/env bash
# =============================================================================
# AgriTech Hydroponics API - cURL Examples
# =============================================================================
#
# Usage:
#   1. Set BASE_URL and API_KEY below (or export as env vars)
#   2. Run individual commands by copying them, or source the whole file
#
# Default server: http://localhost:3001
# Default API key: agritech-secret-key-2026  (must match backend/.env)
# =============================================================================

BASE_URL="${BASE_URL:-http://localhost:3001}"
API_KEY="${API_KEY:-agritech-secret-key-2026}"

# Shorthand for authenticated requests
AUTH="-H X-API-Key:${API_KEY}"

# =============================================================================
# PUBLIC ENDPOINTS (no API key needed)
# =============================================================================

# Health check
curl -s "$BASE_URL/api/health" | python -m json.tool

# API root
curl -s "$BASE_URL/" | python -m json.tool

# OpenAPI spec
curl -s "$BASE_URL/api/openapi.json" | python -m json.tool

# Swagger docs (HTML)
curl -s "$BASE_URL/api/docs" -o docs.html

# Business dashboard (HTML page)
curl -s "$BASE_URL/business" -o business.html

# Site visits backoffice (HTML page)
curl -s "$BASE_URL/site-visits" -o site_visits.html

# =============================================================================
# SITE VISITS (public - no API key)
# =============================================================================

# Dashboard stats & KPIs
curl -s "$BASE_URL/api/site-visits/dashboard" | python -m json.tool

# Client list (for form dropdowns)
curl -s "$BASE_URL/api/site-visits/clients" | python -m json.tool

# List visits (paginated)
curl -s "$BASE_URL/api/site-visits?page=1&per_page=10" | python -m json.tool

# List visits with filters
curl -s "$BASE_URL/api/site-visits?visit_type=routine&sort=visit_date&sort_dir=desc" | python -m json.tool

# Search visits
curl -s "$BASE_URL/api/site-visits?search=greenhouse&follow_up=pending" | python -m json.tool

# Get single visit
curl -s "$BASE_URL/api/site-visits/1" | python -m json.tool

# Create a new visit
curl -s -X POST "$BASE_URL/api/site-visits" \
  -H "Content-Type: application/json" \
  -d '{
    "inspector_name": "Maria Silva",
    "visit_type": "routine",
    "client_id": 1,
    "facility_name": "Greenhouse A",
    "zones_inspected": ["Zone 1", "Zone 2"],
    "crop_batches_checked": ["rosso_premium_001"],
    "sensor_readings_snapshot": {
      "temperature": 23.5,
      "humidity": 68.2,
      "ph": 6.1
    },
    "observations": "All crops healthy, good growth rate.",
    "issues_found": ["Minor leaf discoloration in Zone 2"],
    "actions_taken": "Adjusted nutrient solution EC.",
    "follow_up_required": true,
    "follow_up_date": "2026-02-18",
    "follow_up_notes": "Re-check Zone 2 leaf health.",
    "overall_rating": 4,
    "photo_notes": "Photos taken of Zone 2 plants."
  }' | python -m json.tool

# Update a visit
curl -s -X PUT "$BASE_URL/api/site-visits/1" \
  -H "Content-Type: application/json" \
  -d '{
    "observations": "Updated after re-inspection.",
    "overall_rating": 5
  }' | python -m json.tool

# Complete follow-up
curl -s -X POST "$BASE_URL/api/site-visits/1/complete-follow-up" | python -m json.tool

# Delete a visit
curl -s -X DELETE "$BASE_URL/api/site-visits/1" | python -m json.tool

# Export all visits (CSV-ready JSON)
curl -s "$BASE_URL/api/site-visits/export" | python -m json.tool

# =============================================================================
# SENSOR DATA (requires API key)
# =============================================================================

# Get latest sensor reading (Redis cache or InfluxDB fallback)
curl -s $AUTH "$BASE_URL/api/data/latest" | python -m json.tool

# Post sensor data from Arduino
curl -s -X POST $AUTH "$BASE_URL/api/data" \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_id": "arduino_1",
    "temperature": 24.5,
    "humidity": 65.3,
    "light": 850,
    "ph": 6.2,
    "ec": 1.8,
    "water_temp": 21.0
  }' | python -m json.tool

# Post dual sensor data (drift detection)
curl -s -X POST $AUTH "$BASE_URL/api/sensors/dual" \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_id": "ph_dual_1",
    "primary": {"ph": 6.1},
    "secondary": {"ph": 6.3},
    "drift": {"delta": 0.2, "threshold": 0.5}
  }' | python -m json.tool

# Get drift status for all sensors
curl -s $AUTH "$BASE_URL/api/sensors/drift/status" | python -m json.tool

# Get drift trend for specific sensor
curl -s $AUTH "$BASE_URL/api/sensors/drift/ph_dual_1" | python -m json.tool

# =============================================================================
# AC CONTROL (requires API key)
# =============================================================================

# Get AC state
curl -s $AUTH "$BASE_URL/api/ac" | python -m json.tool

# Control AC (turn on, set to cool at 22C)
curl -s -X POST $AUTH "$BASE_URL/api/ac" \
  -H "Content-Type: application/json" \
  -d '{
    "power": true,
    "temperature": 22,
    "mode": "cool"
  }' | python -m json.tool

# =============================================================================
# RULES ENGINE (requires API key)
# =============================================================================

# List all rules
curl -s $AUTH "$BASE_URL/api/rules" | python -m json.tool

# Get single rule
curl -s $AUTH "$BASE_URL/api/rules/temp_high" | python -m json.tool

# Create a rule
curl -s -X POST $AUTH "$BASE_URL/api/rules" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": "humidity_low",
    "name": "Low Humidity Alert",
    "sensor": "humidity",
    "threshold": 40.0,
    "condition": "below",
    "severity": "warning",
    "action": {
      "type": "alert",
      "message": "Humidity below safe minimum"
    }
  }' | python -m json.tool

# Update a rule
curl -s -X PUT $AUTH "$BASE_URL/api/rules/humidity_low" \
  -H "Content-Type: application/json" \
  -d '{
    "threshold": 35.0,
    "severity": "critical"
  }' | python -m json.tool

# Delete a rule
curl -s -X DELETE $AUTH "$BASE_URL/api/rules/humidity_low" | python -m json.tool

# Poll commands (Arduino config server)
curl -s $AUTH "$BASE_URL/api/commands?sensor_id=arduino_1" | python -m json.tool

# =============================================================================
# NOTIFICATIONS & ALERTS (requires API key)
# =============================================================================

# Notification status & history
curl -s $AUTH "$BASE_URL/api/notifications" | python -m json.tool

# Send test alert (fake data)
curl -s -X POST $AUTH "$BASE_URL/api/notifications/test" | python -m json.tool

# Send test alert with real sensor data
curl -s -X POST $AUTH "$BASE_URL/api/notifications/test-real" \
  -H "Content-Type: application/json" \
  -d '{"crop_id": 1}' | python -m json.tool

# Alert escalation status
curl -s $AUTH "$BASE_URL/api/escalation" | python -m json.tool

# =============================================================================
# CROPS & GROWTH STAGES (requires API key)
# =============================================================================

# List active crops
curl -s $AUTH "$BASE_URL/api/crops" | python -m json.tool

# Create crop batch
# Varieties: rosso_premium, curly_green, arugula_rocket, basil_genovese, mint_spearmint, tomato_cherry
curl -s -X POST $AUTH "$BASE_URL/api/crops" \
  -H "Content-Type: application/json" \
  -d '{
    "variety": "rosso_premium",
    "plant_date": "2026-02-11",
    "zone": "main",
    "notes": "Spring batch"
  }' | python -m json.tool

# Get crop details + stage history
curl -s $AUTH "$BASE_URL/api/crops/1" | python -m json.tool

# Get stage-specific optimal conditions
curl -s $AUTH "$BASE_URL/api/crops/1/conditions" | python -m json.tool

# Get stage-specific monitoring rules
curl -s $AUTH "$BASE_URL/api/crops/1/rules" | python -m json.tool

# Advance growth stage manually
# Stages: germination > seedling > transplant > vegetative > flowering* > fruiting* > maturity > harvest_ready
curl -s -X POST $AUTH "$BASE_URL/api/crops/1/advance" \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "vegetative",
    "reason": "Strong root system observed"
  }' | python -m json.tool

# Record harvest
curl -s -X POST $AUTH "$BASE_URL/api/crops/1/harvest" \
  -H "Content-Type: application/json" \
  -d '{
    "weight_kg": 2.5,
    "quality_grade": "premium",
    "market_value": 15.00,
    "notes": "Excellent color and texture"
  }' | python -m json.tool

# Crop dashboard (all crops overview)
curl -s $AUTH "$BASE_URL/api/dashboard" | python -m json.tool

# Harvest analytics
curl -s $AUTH "$BASE_URL/api/harvest/analytics" | python -m json.tool

# =============================================================================
# CALIBRATIONS (requires API key)
# =============================================================================

# Record a calibration
curl -s -X POST $AUTH "$BASE_URL/api/calibrations" \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_type": "ph",
    "next_due_days": 30,
    "performed_by": "Technician A",
    "notes": "Calibrated with pH 4.0 and 7.0 buffers"
  }' | python -m json.tool

# Get calibrations due
curl -s $AUTH "$BASE_URL/api/calibrations/due" | python -m json.tool

# =============================================================================
# BUSINESS INTELLIGENCE (requires API key)
# =============================================================================

# Full business dashboard (JSON)
curl -s $AUTH "$BASE_URL/api/business/dashboard" | python -m json.tool
