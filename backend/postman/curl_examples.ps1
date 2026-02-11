# =============================================================================
# AgriTech Hydroponics API - PowerShell / cURL Examples (Windows)
# =============================================================================
#
# Set these variables or use defaults:
$BASE_URL = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost:3001" }
$API_KEY  = if ($env:API_KEY)  { $env:API_KEY }  else { "agritech-secret-key-2026" }

# --- PUBLIC (no API key) ---

# Health check
curl -s "$BASE_URL/api/health"

# Site visits dashboard
curl -s "$BASE_URL/api/site-visits/dashboard"

# List site visits
curl -s "$BASE_URL/api/site-visits?page=1&per_page=10"

# Get single visit
curl -s "$BASE_URL/api/site-visits/1"

# Create a visit
curl -s -X POST "$BASE_URL/api/site-visits" `
  -H "Content-Type: application/json" `
  -d '{"inspector_name":"Maria Silva","visit_type":"routine","facility_name":"Greenhouse A","zones_inspected":["Zone 1"],"observations":"All healthy.","overall_rating":4}'

# --- PROTECTED (needs API key) ---

# Latest sensor reading
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/data/latest"

# Post sensor data
curl -s -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" `
  "$BASE_URL/api/data" `
  -d '{"sensor_id":"arduino_1","temperature":24.5,"humidity":65.3,"light":850,"ph":6.2,"ec":1.8}'

# List rules
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/rules"

# List crops
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/crops"

# Crop dashboard
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/dashboard"

# Notification status
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/notifications"

# Business dashboard
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/business/dashboard"

# AC state
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/ac"
