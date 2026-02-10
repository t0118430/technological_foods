#!/bin/bash
# AgriTech SaaS Platform Health Check
# Tests all critical endpoints and services

set -e

API_URL="${API_URL:-http://localhost:3001}"
API_KEY="${API_KEY:-agritech-secret-key-2026}"
FAILED=0

echo "🏥 AgriTech SaaS Platform Health Check"
echo "========================================"
echo ""

# Check Docker services
echo "🐋 Checking Docker services..."
docker ps | grep -q agritech-influxdb && echo "✅ InfluxDB running" || { echo "❌ InfluxDB down"; FAILED=1; }
docker ps | grep -q agritech-grafana && echo "✅ Grafana running" || { echo "❌ Grafana down"; FAILED=1; }
docker ps | grep -q agritech-nodered && echo "✅ Node-RED running" || { echo "❌ Node-RED down"; FAILED=1; }
echo ""

# Check API server
echo "🌐 Checking API endpoints..."
curl -sf "$API_URL/api/data/latest" -H "X-API-Key: $API_KEY" > /dev/null && echo "✅ Latest data endpoint" || { echo "❌ Latest data endpoint down"; FAILED=1; }
curl -sf "$API_URL/api/dashboard" -H "X-API-Key: $API_KEY" > /dev/null && echo "✅ Dashboard endpoint" || { echo "❌ Dashboard endpoint down"; FAILED=1; }
curl -sf "$API_URL/api/crops" -H "X-API-Key: $API_KEY" > /dev/null && echo "✅ Crops endpoint" || { echo "❌ Crops endpoint down"; FAILED=1; }
echo ""

# Check business endpoints (if enabled)
echo "💼 Checking business endpoints..."
curl -sf "$API_URL/api/business/metrics" -H "X-API-Key: $API_KEY" > /dev/null && echo "✅ Business metrics endpoint" || echo "⚠️  Business metrics unavailable (optional)"
echo ""

# Check system resources
echo "💾 Checking system resources..."
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
  echo "❌ Disk usage critical: ${DISK_USAGE}%"
  FAILED=1
elif [ $DISK_USAGE -gt 80 ]; then
  echo "⚠️  Disk usage high: ${DISK_USAGE}%"
else
  echo "✅ Disk usage: ${DISK_USAGE}%"
fi

MEMORY_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
if [ $MEMORY_USAGE -gt 90 ]; then
  echo "❌ Memory usage critical: ${MEMORY_USAGE}%"
  FAILED=1
elif [ $MEMORY_USAGE -gt 80 ]; then
  echo "⚠️  Memory usage high: ${MEMORY_USAGE}%"
else
  echo "✅ Memory usage: ${MEMORY_USAGE}%"
fi
echo ""

# Check database
echo "🗄️  Checking database..."
if [ -f "backend/data/agritech.db" ]; then
  DB_SIZE=$(du -h backend/data/agritech.db | cut -f1)
  echo "✅ Database exists (size: $DB_SIZE)"
else
  echo "⚠️  Database not found (will be created on first run)"
fi
echo ""

# Final summary
echo "========================================"
if [ $FAILED -eq 0 ]; then
  echo "✅ All critical services healthy"
  exit 0
else
  echo "❌ Health check failed"
  exit 1
fi
