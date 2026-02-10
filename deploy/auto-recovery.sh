#!/bin/bash
# Auto-recovery script
./health-check.sh || {
  echo "🔧 Attempting auto-recovery..."
  systemctl restart agritech-docker
  systemctl restart agritech-api
  sleep 10
  ./health-check.sh && echo "✅ Recovery successful" || echo "❌ Recovery failed"
}
