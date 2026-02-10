#!/bin/bash
# AgriTech Health Check
FAILED=0

# Check Docker services
docker ps | grep -q agritech-influxdb || { echo "❌ InfluxDB down"; FAILED=1; }
docker ps | grep -q agritech-grafana || { echo "❌ Grafana down"; FAILED=1; }
docker ps | grep -q agritech-nodered || { echo "❌ Node-RED down"; FAILED=1; }

# Check API server
curl -s http://localhost:3001/api/data/latest > /dev/null || { echo "❌ API down"; FAILED=1; }

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
  echo "⚠️  Disk usage critical: ${DISK_USAGE}%"
  FAILED=1
fi

[ $FAILED -eq 0 ] && echo "✅ All services healthy" || exit 1
