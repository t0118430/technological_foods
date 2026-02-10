# 🧪 AgriTech Hydroponics - Testing Guide

**Version**: 2.0.0
**Last Updated**: 2026-02-09
**Purpose**: Comprehensive testing procedures for all system components

---

## 📋 Table of Contents

1. [Pre-Deployment Testing](#pre-deployment-testing)
2. [Hardware Testing](#hardware-testing)
3. [Backend API Testing](#backend-api-testing)
4. [Notification System Testing](#notification-system-testing)
5. [Rule Engine Testing](#rule-engine-testing)
6. [AC Controller Testing](#ac-controller-testing)
7. [Integration Testing](#integration-testing)
8. [Load Testing](#load-testing)
9. [Security Testing](#security-testing)
10. [Multi-Location Testing](#multi-location-testing)

---

## ✅ Pre-Deployment Testing

### Environment Check

```bash
# 1. Check Python version (requires 3.8+)
python3 --version

# 2. Check required services
systemctl status influxdb
systemctl status agritech-api

# 3. Verify environment variables
cd backend
cat .env | grep -v '^#' | grep '='

# 4. Test database connection
python3 << EOF
from influxdb_client import InfluxDBClient
import os
from dotenv import load_dotenv

load_dotenv()
client = InfluxDBClient(
    url=os.getenv('INFLUXDB_URL'),
    token=os.getenv('INFLUXDB_TOKEN'),
    org=os.getenv('INFLUXDB_ORG')
)
print("✅ InfluxDB connection successful!" if client.ping() else "❌ Connection failed")
EOF
```

---

## 🔌 Hardware Testing

### Arduino Sensor Testing

#### Test 1: WiFi Connection

```cpp
// In Arduino Serial Monitor (115200 baud)
// Expected output:

=== AgriTech Dual Sensor System ===
Initializing...
Connecting to WiFi: YourWiFiName
...........
WiFi Connected!
IP: 192.168.1.50
```

**Pass Criteria:**
- ✅ WiFi connects within 10 seconds
- ✅ IP address assigned
- ✅ No disconnections for 5 minutes

---

#### Test 2: Sensor Readings

```cpp
// Expected output:
┌─────────────────────────────────────────┐
│     DUAL SENSOR COMPARISON              │
├─────────────────────────────────────────┤
│ PRIMARY:   24.5°C  65.0%     │
│ SECONDARY: 24.3°C  64.8%     │
├─────────────────────────────────────────┤
│ TEMP DRIFT:  0.2°C (0.8%)  ✅ OK
│ HUM. DRIFT:  0.2% (0.3%)   ✅ OK
├─────────────────────────────────────────┤
│ STATUS: ✅ HEALTHY - Both sensors accurate │
└─────────────────────────────────────────┘
```

**Pass Criteria:**
- ✅ Temperature: -40°C to 80°C
- ✅ Humidity: 0% to 100%
- ✅ Readings update every 2 seconds
- ✅ Drift < 0.5°C and < 2%

**Fail Conditions:**
- ❌ Temperature = 0.0°C (sensor disconnected)
- ❌ Humidity = 0.0% (sensor error)
- ❌ No updates for > 10 seconds

---

#### Test 3: API Communication

```bash
# Monitor Arduino serial output
# Should show:

POST /api/data HTTP/1.1
Host: 192.168.1.100:3001
Content-Type: application/json
X-API-Key: your-secret-key

{"temperature":24.5,"humidity":65.0,"light":2500}

Response: 200 OK
{"status":"success","timestamp":"2026-02-09T14:30:00Z"}
```

**Pass Criteria:**
- ✅ HTTP 200 response
- ✅ Data sent every 2 seconds
- ✅ No timeout errors

**Fail Conditions:**
- ❌ HTTP 401 (wrong API key)
- ❌ HTTP 500 (server error)
- ❌ Connection timeout

---

### Raspberry Pi Testing

#### Test 1: System Resources

```bash
# Check CPU, RAM, disk usage
htop  # Press q to exit

# Expected:
# CPU: < 50% average
# RAM: < 70% used
# Swap: 0% (should not swap)

# Check disk space
df -h
# Expected: /dev/root < 80% full

# Check temperature
vcgencmd measure_temp
# Expected: < 70°C (idle), < 80°C (load)
```

**Pass Criteria:**
- ✅ CPU < 50% idle
- ✅ RAM < 70% used
- ✅ Disk < 80% full
- ✅ Temperature < 70°C

---

#### Test 2: Network Connectivity

```bash
# Test internet connection
ping -c 4 google.com

# Test local network
ping -c 4 192.168.1.1  # Router

# Test InfluxDB
curl http://localhost:8086/health

# Test API server
curl http://localhost:3001/api/health
```

**Pass Criteria:**
- ✅ All pings respond < 50ms
- ✅ 0% packet loss
- ✅ InfluxDB returns {"status":"pass"}
- ✅ API returns {"status":"healthy"}

---

## 🌐 Backend API Testing

### Manual Testing (curl)

#### Test 1: Health Check

```bash
curl -v http://localhost:3001/api/health
```

**Expected Response:**
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "healthy",
  "influxdb": "http://localhost:8086",
  "version": "2.0.0"
}
```

---

#### Test 2: Authentication

```bash
# Without API key (should fail)
curl -v http://localhost:3001/api/data/latest

# Expected: 401 Unauthorized

# With valid API key
curl -H "X-API-Key: your-secret-key" \
  http://localhost:3001/api/data/latest

# Expected: 200 OK with data
```

---

#### Test 3: Post Sensor Data

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{
    "temperature": 25.0,
    "humidity": 60.0,
    "ph": 6.0,
    "ec": 1.5,
    "water_level": 80,
    "light": 3000
  }' \
  http://localhost:3001/api/data
```

**Expected Response:**
```json
HTTP/1.1 200 OK
{
  "status": "success",
  "timestamp": "2026-02-09T14:30:00Z",
  "triggered_rules": []
}
```

---

#### Test 4: Query Latest Data

```bash
curl -H "X-API-Key: your-secret-key" \
  http://localhost:3001/api/data/latest
```

**Expected Response:**
```json
{
  "latest": {
    "temperature": 25.0,
    "humidity": 60.0,
    "ph": 6.0,
    "ec": 1.5,
    "water_level": 80,
    "light": 3000,
    "timestamp": "2026-02-09T14:30:00Z"
  }
}
```

---

### Automated Testing (pytest)

#### Run All Tests

```bash
cd backend
python3 -m pytest api/test_*.py -v

# Expected output:
api/test_rule_engine.py::test_create_rule PASSED
api/test_rule_engine.py::test_evaluate_rule PASSED
api/test_notification_service.py::test_ntfy_send PASSED
api/test_config_loader.py::test_load_variety PASSED
api/test_alert_escalation.py::test_escalation PASSED
api/test_preventive_alerts.py::test_warning_margin PASSED

======================== 25 passed in 2.34s ========================
```

---

#### Test Individual Modules

**Rule Engine:**
```bash
python3 -m pytest api/test_rule_engine.py -v
```

**Notification Service:**
```bash
python3 -m pytest api/test_notification_service.py -v
```

**Config Loader:**
```bash
python3 -m pytest api/test_config_loader.py -v
```

---

#### Test Coverage Report

```bash
cd backend
python3 -m pytest --cov=api --cov-report=html api/test_*.py

# View report
xdg-open htmlcov/index.html  # Linux
open htmlcov/index.html       # Mac
start htmlcov/index.html      # Windows
```

**Pass Criteria:**
- ✅ Total coverage > 80%
- ✅ Critical modules (rule_engine, notification_service) > 90%

---

## 🔔 Notification System Testing

### Test 1: ntfy Push Notifications

```bash
cd backend
python3 test_real_notification.py
```

**Expected Output:**
```
🧪 Testing AgriTech Notification System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1: Simple notification
✅ Sent successfully

Test 2: Critical alert with emoji
✅ Sent successfully

Test 3: Markdown formatting
✅ Sent successfully

Test 4: Preventive alert
✅ Sent successfully

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ All tests passed!
Check your ntfy app for 4 notifications
```

**Verify on Phone:**
- [ ] Received 4 notifications
- [ ] Correct titles and icons
- [ ] Markdown formatting rendered
- [ ] Priority levels correct (critical = high priority)

---

### Test 2: Multi-Channel Routing

```bash
# Test channel selection by alert level
python3 << EOF
from multi_channel_notifier import multi_notifier, AlertLevel

# Info → ntfy only
multi_notifier.notify(
    subject="Test Info Alert",
    body="This should go to ntfy only",
    level=AlertLevel.INFO
)

# Critical → all channels
multi_notifier.notify(
    subject="Test Critical Alert",
    body="This should go to ALL channels",
    level=AlertLevel.CRITICAL
)
EOF
```

**Expected Behavior:**
- ✅ Info alert: ntfy only
- ✅ Warning: ntfy + email
- ✅ Critical: ntfy + email + SMS + WhatsApp

---

### Test 3: Cooldown Mechanism

```bash
# Send same alert twice rapidly
python3 << EOF
from notification_service import notifier

# First alert (should send)
notifier.send_alert("test_sensor", 35.0, "temperature", 30.0, "above")

# Immediate second alert (should be suppressed)
notifier.send_alert("test_sensor", 35.5, "temperature", 30.0, "above")
EOF
```

**Expected Output:**
```
✅ Alert sent: temperature above threshold
⏸️  Alert suppressed (cooldown active: 14m 59s remaining)
```

**Pass Criteria:**
- ✅ First alert sends immediately
- ✅ Duplicate alerts suppressed for 15 minutes
- ✅ After 15 minutes, can send again

---

## ⚙️ Rule Engine Testing

### Test 1: Basic Rule Evaluation

```bash
cd backend
python3 << EOF
from rule_engine import RuleEngine

engine = RuleEngine()

# Create test rule
engine.create_rule({
    "id": "test_temp_high",
    "name": "Test Temperature High",
    "sensor": "temperature",
    "condition": "above",
    "threshold": 30,
    "action": {
        "type": "notify",
        "severity": "critical",
        "message": "Temperature too high!"
    }
})

# Test with data ABOVE threshold (should trigger)
triggered = engine.evaluate({"temperature": 35.0})
print(f"✅ Rule triggered: {len(triggered) > 0}")

# Test with data BELOW threshold (should not trigger)
triggered = engine.evaluate({"temperature": 25.0})
print(f"✅ No trigger: {len(triggered) == 0}")

# Cleanup
engine.delete_rule("test_temp_high")
EOF
```

**Expected Output:**
```
✅ Rule triggered: True
✅ No trigger: True
```

---

### Test 2: Preventive Alerts (Warning Margins)

```bash
python3 << EOF
from rule_engine import RuleEngine

engine = RuleEngine()

# Create rule with warning margin
engine.create_rule({
    "id": "test_preventive",
    "sensor": "temperature",
    "condition": "above",
    "threshold": 30,
    "warning_margin": 2,  # Warning at 28°C
    "action": {
        "type": "notify",
        "severity": "critical",
        "message": "Temperature critical!"
    },
    "preventive_message": "Approaching temperature limit"
})

# Test preventive zone (28-30°C)
triggered = engine.evaluate({"temperature": 29.0})
print(f"Preventive alerts: {len([t for t in triggered if t['alert_type'] == 'preventive'])}")

# Test critical zone (>30°C)
triggered = engine.evaluate({"temperature": 32.0})
print(f"Critical alerts: {len([t for t in triggered if t['alert_type'] == 'critical'])}")

engine.delete_rule("test_preventive")
EOF
```

**Expected Output:**
```
Preventive alerts: 1
Critical alerts: 1
```

---

### Test 3: Arduino Command Queuing

```bash
python3 << EOF
from rule_engine import RuleEngine

engine = RuleEngine()

# Create rule with Arduino action
engine.create_rule({
    "id": "test_led",
    "sensor": "temperature",
    "condition": "above",
    "threshold": 25,
    "action": {
        "type": "arduino",
        "command": "led_on"
    }
})

# Trigger rule
engine.evaluate({"temperature": 30.0})

# Check pending commands
commands = engine.get_pending_commands("arduino_1")
print(f"Pending LED command: {commands.get('led')}")

# Consume commands (Arduino polls this)
engine.consume_pending_commands("arduino_1")
commands = engine.get_pending_commands("arduino_1")
print(f"After consume: {commands}")

engine.delete_rule("test_led")
EOF
```

**Expected Output:**
```
Pending LED command: on
After consume: {'led': 'off'}  # Default state
```

---

## 🌡️ AC Controller Testing

### Test 1: AC Status Query

```bash
curl -H "X-API-Key: your-key" \
  http://localhost:3001/api/ac
```

**Expected Response:**
```json
{
  "initialized": true,
  "power": false,
  "mode": "cool",
  "temperature": 24,
  "fan_speed": "auto"
}
```

---

### Test 2: AC Power Control

```bash
# Turn ON
curl -X POST \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"power": true}' \
  http://localhost:3001/api/ac/power

# Wait 5 seconds

# Turn OFF
curl -X POST \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"power": false}' \
  http://localhost:3001/api/ac/power
```

**Verify:**
- [ ] AC physically turned on/off
- [ ] LED indicator changed
- [ ] Status endpoint reflects change

---

### Test 3: Temperature Control

```bash
# Set to 22°C (cool mode)
curl -X POST \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"temperature": 22}' \
  http://localhost:3001/api/ac/temperature
```

**Verify:**
- [ ] AC display shows 22°C
- [ ] Mode switches to cool
- [ ] Fan starts

---

## 🔗 Integration Testing

### End-to-End Test: Sensor → Alert → Action

**Scenario**: Temperature rises above threshold, triggers alert and AC

```bash
# Step 1: Create rule
curl -X POST \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "e2e_test",
    "sensor": "temperature",
    "condition": "above",
    "threshold": 28,
    "action": {
      "type": "notify",
      "severity": "warning",
      "message": "Temperature rising!"
    }
  }' \
  http://localhost:3001/api/rules

# Step 2: Simulate high temperature from Arduino
curl -X POST \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "temperature": 30.5,
    "humidity": 65.0,
    "sensor_id": "arduino_1"
  }' \
  http://localhost:3001/api/data

# Step 3: Verify alert was sent (check phone)
# Step 4: Check alert history
curl -H "X-API-Key: your-key" \
  http://localhost:3001/api/alerts/history

# Step 5: Cleanup
curl -X DELETE \
  -H "X-API-Key: your-key" \
  http://localhost:3001/api/rules/e2e_test
```

**Expected Flow:**
1. ✅ Rule created successfully
2. ✅ Data received by server
3. ✅ Rule triggered (temperature 30.5 > 28)
4. ✅ ntfy notification received on phone
5. ✅ Alert logged in database
6. ✅ Alert visible in history

---

### Drift Detection Test

```bash
cd backend
python3 << EOF
from drift_detection_service import DriftDetector

detector = DriftDetector()

# Simulate dual sensor readings
for i in range(10):
    # Primary sensor
    detector.record_reading("primary", temperature=25.0 + i*0.1, humidity=60.0)
    # Secondary sensor (with drift)
    detector.record_reading("secondary", temperature=25.5 + i*0.1, humidity=61.0)

# Analyze drift
report = detector.analyze_drift()
print(f"Temperature drift: {report['temperature_drift']:.2f}°C")
print(f"Humidity drift: {report['humidity_drift']:.2f}%")
print(f"Health score: {report['health_score']}/100")
print(f"Status: {report['status']}")
EOF
```

**Expected Output:**
```
Temperature drift: 0.50°C
Humidity drift: 1.00%
Health score: 85/100
Status: degraded
```

**Pass Criteria:**
- ✅ Drift detection within ±0.1°C accuracy
- ✅ Health score calculated correctly
- ✅ Status matches drift level

---

## 📊 Load Testing

### Test 1: API Throughput

```bash
# Install Apache Bench (if not installed)
sudo apt install apache2-utils

# Test API endpoint with 1000 requests, 10 concurrent
ab -n 1000 -c 10 \
  -H "X-API-Key: your-key" \
  http://localhost:3001/api/health
```

**Expected Results:**
```
Requests per second:    500+ [#/sec]
Time per request:       2-20 ms
Failed requests:        0
```

**Pass Criteria:**
- ✅ > 100 req/sec
- ✅ 0% failed requests
- ✅ p95 latency < 50ms

---

### Test 2: Concurrent Sensor Data Ingestion

```bash
# Simulate 10 Arduinos sending data simultaneously
for i in {1..10}; do
  curl -X POST \
    -H "X-API-Key: your-key" \
    -H "Content-Type: application/json" \
    -d "{\"temperature\": $((20 + i)), \"humidity\": 60, \"sensor_id\": \"arduino_$i\"}" \
    http://localhost:3001/api/data &
done
wait

echo "All requests completed"
```

**Pass Criteria:**
- ✅ All requests return 200 OK
- ✅ All data points saved to InfluxDB
- ✅ No database errors

---

### Test 3: Long-Running Stability

```bash
# Run continuous load for 1 hour
timeout 3600 bash << 'EOF'
while true; do
  curl -s -H "X-API-Key: your-key" \
    http://localhost:3001/api/health > /dev/null
  sleep 1
done
EOF

# Check for errors
sudo journalctl -u agritech-api --since "1 hour ago" | grep -i error
```

**Pass Criteria:**
- ✅ No crashes
- ✅ No memory leaks
- ✅ Response times stable

---

## 🔒 Security Testing

### Test 1: Authentication Bypass Attempt

```bash
# Try without API key
curl -v http://localhost:3001/api/data/latest
# Expected: 401 Unauthorized

# Try with wrong API key
curl -v -H "X-API-Key: wrong-key" \
  http://localhost:3001/api/data/latest
# Expected: 401 Unauthorized

# Try with SQL injection
curl -v -H "X-API-Key: ' OR '1'='1" \
  http://localhost:3001/api/data/latest
# Expected: 401 Unauthorized
```

**Pass Criteria:**
- ✅ All attempts return 401
- ✅ No data leaked
- ✅ No SQL injection vulnerability

---

### Test 2: Input Validation

```bash
# Test invalid sensor data
curl -X POST \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "temperature": "not_a_number",
    "humidity": -50
  }' \
  http://localhost:3001/api/data

# Expected: 400 Bad Request
```

---

### Test 3: Rate Limiting

```bash
# Send 100 requests rapidly
for i in {1..100}; do
  curl -s -H "X-API-Key: your-key" \
    http://localhost:3001/api/data/latest
done
```

**Expected:**
- First 50-60 requests: 200 OK
- After limit: 429 Too Many Requests

---

## 🌍 Multi-Location Testing

### VPN Connectivity Test

```bash
# On Porto central server
sudo wg show

# Expected output:
interface: wg0
  public key: <central-public-key>
  private key: (hidden)
  listening port: 51820

peer: <lisbon-public-key>
  endpoint: 89.XXX.XXX.XXX:51820
  allowed ips: 10.200.0.2/32
  latest handshake: 10 seconds ago
  transfer: 1.5 MiB received, 800 KiB sent

peer: <algarve-public-key>
  endpoint: 91.XXX.XXX.XXX:51820
  allowed ips: 10.200.0.3/32
  latest handshake: 5 seconds ago
  transfer: 900 KiB received, 500 KiB sent
```

**Pass Criteria:**
- ✅ Latest handshake < 2 minutes
- ✅ Data transfer > 0
- ✅ Can ping remote sites: `ping 10.200.0.2`

---

### Remote Data Collection Test

```bash
# From Porto, query Lisbon sensor
curl -H "X-API-Key: your-key" \
  http://10.200.0.2:3001/api/data/latest

# Should return Lisbon greenhouse data
```

---

## ✅ Pre-Deployment Checklist

Before pushing to production:

**Backend:**
- [ ] All pytest tests pass
- [ ] No hardcoded credentials in code
- [ ] .env file configured correctly
- [ ] API key is strong (32+ characters)
- [ ] Database backup tested
- [ ] Log rotation configured

**Arduino:**
- [ ] Sensors reading correctly
- [ ] WiFi connection stable (> 5 min uptime)
- [ ] API communication working
- [ ] LED indicators functioning
- [ ] Power supply adequate (5V 2A+)

**Notifications:**
- [ ] ntfy app installed and subscribed
- [ ] Test notifications received
- [ ] Alert priorities configured
- [ ] Cooldown working (no spam)

**Security:**
- [ ] Firewall rules active
- [ ] SSH key-only (no password auth)
- [ ] VPN encryption enabled
- [ ] Fail2ban installed
- [ ] Backups encrypted

**Monitoring:**
- [ ] Grafana dashboards configured
- [ ] Alert thresholds set
- [ ] Health checks passing
- [ ] Logs centralized

---

## 📝 Test Report Template

```markdown
# Test Report - [Date]

## Summary
- **Tester**: [Name]
- **Environment**: [dev/staging/prod]
- **Branch**: [feature/dashboard]
- **Duration**: [X hours]

## Results

### Hardware Tests
- Arduino WiFi: ✅ PASS
- Sensor readings: ✅ PASS
- API communication: ✅ PASS

### Backend Tests
- Unit tests: ✅ PASS (25/25)
- Integration tests: ✅ PASS
- Load tests: ✅ PASS (500 req/sec)

### Notification Tests
- ntfy push: ✅ PASS
- Alert routing: ✅ PASS
- Cooldown: ✅ PASS

### Issues Found
1. [Issue description]
   - Severity: [Low/Medium/High/Critical]
   - Status: [Open/Fixed/Wont Fix]

## Recommendation
- [ ] Ready for deployment
- [ ] Needs fixes before deployment
- [ ] Requires further testing

## Notes
[Any additional observations]
```

---

**Next Steps**: See `DEV_BRANCH_STATUS.md` for current dev branch state and deployment readiness.
