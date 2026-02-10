# 📘 AgriTech Hydroponics - User Manual

**Version**: 2.0.0 (SaaS Platform)
**Last Updated**: 2026-02-09
**Target Users**: Farmers, Greenhouse Operators, System Administrators

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Getting Started](#getting-started)
3. [Dashboard Usage](#dashboard-usage)
4. [API Endpoints](#api-endpoints)
5. [Mobile App (ntfy)](#mobile-app)
6. [Configuration Management](#configuration-management)
7. [Alert Management](#alert-management)
8. [Client Tiers](#client-tiers)
9. [Troubleshooting](#troubleshooting)

---

## 🌟 System Overview

### What is AgriTech Hydroponics?

A **smart greenhouse monitoring system** that:
- ✅ Monitors temperature, humidity, pH, EC, water level, light
- ✅ Sends real-time alerts to your phone
- ✅ Automatically controls AC/climate systems
- ✅ Predicts sensor failures before they happen
- ✅ Provides business analytics for crop optimization

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    Your Greenhouse                       │
│                                                          │
│  ┌──────────────┐         ┌─────────────────┐          │
│  │  Arduino R4  │ ──WiFi─→│  Raspberry Pi   │          │
│  │   + Sensors  │         │   (Server)      │          │
│  └──────────────┘         └─────────────────┘          │
│                                    │                     │
└────────────────────────────────────┼─────────────────────┘
                                     │
                                     ↓
                        ┌────────────────────────┐
                        │   Cloud Dashboard      │
                        │   + Mobile Alerts      │
                        └────────────────────────┘
```

---

## 🚀 Getting Started

### Step 1: Access the System

**Web Dashboard:**
```
http://your-raspberry-pi-ip:3001
```

**Default Ports:**
- API Server: `3001`
- Grafana: `3000`
- InfluxDB: `8086`
- Node-RED: `1880`

### Step 2: First-Time Setup

#### A. Configure WiFi (Raspberry Pi)
```bash
sudo raspi-config
# → System Options → Wireless LAN
# → Enter WiFi name and password
```

#### B. Configure Arduino
```bash
# Edit config.h with your WiFi and API settings
cd arduino/temp_hum_light_sending_api/
cp config.h.example config.h
nano config.h
```

Required settings:
```cpp
#define WIFI_SSID "YourWiFiName"
#define WIFI_PASSWORD "YourWiFiPassword"
#define API_HOST "192.168.1.100"  // Raspberry Pi IP
#define API_PORT 3001
#define API_KEY "your-secret-api-key"
```

#### C. Install ntfy Mobile App
1. Download **ntfy** from:
   - Android: [Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
   - iOS: [App Store](https://apps.apple.com/app/ntfy/id1625396347)

2. Subscribe to your topic:
   - Tap `+` button
   - Enter topic: `agritech-client-alerts` (or your custom topic)
   - Save

3. You'll now receive push notifications for all alerts!

---

## 📊 Dashboard Usage

### Main Dashboard

Access: `http://raspberry-pi-ip:3001/dashboard`

**Features:**
- 📈 Real-time sensor readings
- 🌡️ Temperature trends
- 💧 Humidity levels
- 🔔 Active alerts
- 📉 Historical data graphs

### Dashboard Sections

#### 1. **Live Sensor Data**
```
┌──────────────────────────────────────────┐
│ 🌡️  Temperature:  24.5°C  ✅ Normal     │
│ 💧  Humidity:     65.0%   ✅ Normal     │
│ 🧪  pH:           6.2     ✅ Normal     │
│ ⚡  EC:           1.8 mS  ✅ Normal     │
│ 🚰  Water Level:  85%     ✅ Normal     │
│ ☀️  Light:        2500 lux ✅ Normal    │
└──────────────────────────────────────────┘
```

#### 2. **Alert History**
View recent alerts:
- Critical alerts (red)
- Warnings (yellow)
- Preventive alerts (blue)
- Resolved issues (green)

#### 3. **System Status**
- Arduino connection status
- Last data received
- Sensor health scores
- VPN connection (if multi-location)

---

## 🔌 API Endpoints

### Authentication

All API requests require an API key:

```bash
curl -H "X-API-Key: your-secret-api-key" \
  http://raspberry-pi-ip:3001/api/health
```

### Available Endpoints

#### **GET /api/health**
Check system health

```bash
curl http://raspberry-pi-ip:3001/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "influxdb": "http://localhost:8086",
  "version": "2.0.0"
}
```

---

#### **GET /api/data/latest**
Get latest sensor readings

```bash
curl -H "X-API-Key: your-key" \
  http://raspberry-pi-ip:3001/api/data/latest
```

**Response:**
```json
{
  "latest": {
    "temperature": 24.5,
    "humidity": 65.0,
    "ph": 6.2,
    "ec": 1.8,
    "water_level": 85,
    "light": 2500,
    "timestamp": "2026-02-09T14:30:00Z"
  }
}
```

---

#### **POST /api/data**
Send sensor data (Arduino → Server)

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "temperature": 24.5,
    "humidity": 65.0,
    "light": 2500
  }' \
  http://raspberry-pi-ip:3001/api/data
```

---

#### **GET /api/rules**
List all configured rules

```bash
curl -H "X-API-Key: your-key" \
  http://raspberry-pi-ip:3001/api/rules
```

**Response:**
```json
{
  "rules": [
    {
      "id": "temp_high",
      "name": "Temperature Too High",
      "sensor": "temperature",
      "condition": "above",
      "threshold": 30,
      "action": {
        "type": "notify",
        "severity": "critical",
        "message": "Temperature critical!"
      },
      "enabled": true
    }
  ]
}
```

---

#### **POST /api/rules**
Create a new rule

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "id": "humidity_low",
    "name": "Humidity Too Low",
    "sensor": "humidity",
    "condition": "below",
    "threshold": 40,
    "action": {
      "type": "notify",
      "severity": "warning",
      "message": "Humidity is too low!"
    }
  }' \
  http://raspberry-pi-ip:3001/api/rules
```

---

#### **PUT /api/rules/{rule_id}**
Update an existing rule

```bash
curl -X PUT \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "threshold": 35,
    "enabled": false
  }' \
  http://raspberry-pi-ip:3001/api/rules/humidity_low
```

---

#### **DELETE /api/rules/{rule_id}**
Delete a rule

```bash
curl -X DELETE \
  -H "X-API-Key: your-key" \
  http://raspberry-pi-ip:3001/api/rules/humidity_low
```

---

#### **GET /api/ac**
Get AC controller status

```bash
curl -H "X-API-Key: your-key" \
  http://raspberry-pi-ip:3001/api/ac
```

**Response:**
```json
{
  "power": true,
  "mode": "cool",
  "temperature": 24,
  "fan_speed": "auto"
}
```

---

#### **POST /api/ac/power**
Turn AC on/off

```bash
# Turn ON
curl -X POST \
  -H "X-API-Key: your-key" \
  -d '{"power": true}' \
  http://raspberry-pi-ip:3001/api/ac/power

# Turn OFF
curl -X POST \
  -H "X-API-Key: your-key" \
  -d '{"power": false}' \
  http://raspberry-pi-ip:3001/api/ac/power
```

---

#### **GET /api/business/dashboard**
Business analytics (requires Pro/Enterprise tier)

```bash
curl -H "X-API-Key: your-key" \
  http://raspberry-pi-ip:3001/api/business/dashboard
```

**Response:**
```json
{
  "revenue": {
    "mrr": 1500,
    "arr": 18000,
    "ltv": 54000
  },
  "clients": {
    "total": 10,
    "active": 9,
    "churn_rate": 5.0
  },
  "sensors": {
    "healthy": 18,
    "degraded": 2,
    "failing": 0
  }
}
```

---

#### **GET /api/drift/report**
Sensor drift analysis

```bash
curl -H "X-API-Key: your-key" \
  http://raspberry-pi-ip:3001/api/drift/report
```

---

### Swagger UI Documentation

Interactive API documentation:

```
http://raspberry-pi-ip:3001/api/docs
```

Features:
- ✅ Try endpoints directly in browser
- ✅ See request/response examples
- ✅ Copy curl commands
- ✅ Test authentication

---

## 📱 Mobile App (ntfy)

### Setting Up Alerts

#### 1. **Subscribe to Topics**

**Client Alerts** (crop conditions):
- Topic: `agritech-client-alerts`
- Receives: Temperature, humidity, pH, EC alerts

**Business Alerts** (revenue, analytics):
- Topic: `agritech-business-private`
- Requires: Password (set in .env)

**Emergency Alerts** (system failures):
- Topic: `agritech-emergency`
- Critical only

#### 2. **Alert Examples**

**Critical Alert:**
```
🚨 CRITICAL: Temperature Too High
Temperature: 35.2°C (limit: 30°C)
Location: Porto Greenhouse #1
Time: 14:30
Action: AC cooling activated
```

**Preventive Alert:**
```
👁️ PREVENTIVE: Approaching Temperature Limit
Temperature: 28.5°C (warning at 28°C, critical at 30°C)
Trend: Rising 0.5°C/hour
Recommendation: Monitor closely
```

**Sensor Drift Alert:**
```
⚠️ DEGRADED: Sensor Drift Detected
Sensor: Temperature #1
Drift: 1.2°C from sensor #2
Health Score: 75/100
Action: Schedule calibration within 2 weeks
```

#### 3. **Alert Priority Levels**

| Level | Icon | Sound | Use Case |
|-------|------|-------|----------|
| Critical | 🚨 | Loud | Immediate action needed |
| Urgent | 🔥 | High | Address within 1 hour |
| Warning | ⚠️ | Medium | Monitor situation |
| Preventive | 👁️ | Low | Approaching limit |
| Info | ℹ️ | Silent | FYI only |

---

## ⚙️ Configuration Management

### Variety-Specific Configs

Load different settings for different crops:

#### **Available Configs:**
- `basil_genovese` - Basil (sweet)
- `arugula_rocket` - Arugula
- `curly_green` - Lettuce (curly)
- `rosso_premium` - Lettuce (red)
- `mint_spearmint` - Mint
- `tomato_cherry` - Cherry tomatoes

#### **Load a Config:**

```bash
curl -X POST \
  -H "X-API-Key: your-key" \
  -d '{"variety": "basil_genovese"}' \
  http://raspberry-pi-ip:3001/api/config/load
```

#### **View Current Config:**

```bash
curl -H "X-API-Key: your-key" \
  http://raspberry-pi-ip:3001/api/config/current
```

**Response:**
```json
{
  "variety": "basil_genovese",
  "thresholds": {
    "temperature": {"min": 18, "max": 28},
    "humidity": {"min": 50, "max": 70},
    "ph": {"min": 5.5, "max": 6.5}
  },
  "growth_stage": "vegetative",
  "loaded_at": "2026-02-09T14:30:00Z"
}
```

---

### Growth Stage Management

Adjust settings as crop matures:

#### **Stages:**
1. **Germination** (0-7 days)
2. **Seedling** (7-14 days)
3. **Vegetative** (14-30 days)
4. **Flowering** (30-45 days)
5. **Fruiting** (45-60 days)
6. **Harvest** (60+ days)

#### **Set Growth Stage:**

```bash
curl -X POST \
  -H "X-API-Key: your-key" \
  -d '{"stage": "flowering"}' \
  http://raspberry-pi-ip:3001/api/growth/stage
```

System automatically adjusts:
- Temperature ranges
- Humidity targets
- Light duration
- EC levels

---

## 🔔 Alert Management

### Alert Types

#### 1. **Critical Alerts**
- Immediate action required
- SMS + WhatsApp + ntfy push
- Escalates if not acknowledged within 15 minutes

**Examples:**
- Temperature > 35°C
- Water level < 10%
- pH outside safe range (< 4.0 or > 8.0)

#### 2. **Warning Alerts**
- Monitor situation closely
- ntfy push notification
- No automatic escalation

**Examples:**
- Temperature 30-35°C
- Humidity outside ideal range
- EC slightly high/low

#### 3. **Preventive Alerts**
- Approaching limits
- Early warning system
- ntfy notification only

**Examples:**
- Temperature approaching 30°C (warning at 28°C)
- Sensor drift detected
- Battery low

### Alert Escalation

If critical alert not acknowledged:

```
15 min → L1: Greenhouse operator (ntfy)
1 hour → L2: On-call technician (WhatsApp)
4 hours → L3: Manager (SMS + Phone call)
8 hours → L4: Emergency contact (All channels)
```

### Acknowledge Alerts

```bash
curl -X POST \
  -H "X-API-Key: your-key" \
  -d '{"alert_id": "temp_high_20260209_1430"}' \
  http://raspberry-pi-ip:3001/api/alerts/acknowledge
```

---

## 💼 Client Tiers

### Free Tier
- ✅ 1 location
- ✅ 2 sensors
- ✅ Basic alerts (ntfy only)
- ✅ 7-day data retention
- ❌ No business dashboard
- ❌ No API access

### Pro Tier (€150/month)
- ✅ 3 locations
- ✅ 10 sensors
- ✅ All alert channels (WhatsApp, SMS, Email)
- ✅ 90-day data retention
- ✅ Business dashboard
- ✅ API access (1000 req/day)
- ✅ Custom crop configs
- ✅ Growth stage tracking

### Enterprise Tier (€500/month)
- ✅ Unlimited locations
- ✅ Unlimited sensors
- ✅ Unlimited alerts
- ✅ Unlimited data retention
- ✅ Priority support
- ✅ Unlimited API access
- ✅ Custom integrations
- ✅ SLA guarantees
- ✅ Dedicated account manager

### Check Your Tier

```bash
curl -H "X-API-Key: your-key" \
  http://raspberry-pi-ip:3001/api/client/info
```

---

## 🛠️ Troubleshooting

### Common Issues

#### **1. Arduino Not Sending Data**

**Symptoms:**
- Dashboard shows "No data received"
- Last update timestamp is old

**Fix:**
```bash
# Check Arduino serial monitor
# Should show:
# WiFi Connected! IP: 192.168.1.50
# Data sent: 200 OK

# If WiFi fails, check config.h:
# - WIFI_SSID correct?
# - WIFI_PASSWORD correct?
# - API_HOST = Raspberry Pi IP?
```

---

#### **2. Alerts Not Arriving**

**Symptoms:**
- Sensor values exceed threshold
- No ntfy notification

**Fix:**
```bash
# Test notification system
curl -X POST \
  -H "X-API-Key: your-key" \
  -d '{"severity": "test", "message": "Test alert"}' \
  http://raspberry-pi-ip:3001/api/notify/test

# Check ntfy topic in .env
cat backend/.env | grep NTFY_TOPIC

# Verify mobile app subscription matches topic
```

---

#### **3. Raspberry Pi Not Accessible**

**Symptoms:**
- Can't access dashboard
- Ping timeout

**Fix:**
```bash
# Method 1: Find Pi IP address
# Check router admin page for "raspberrypi" device

# Method 2: Direct connection
# Connect Pi to monitor/keyboard
# Run: hostname -I

# Method 3: Network scan
# Windows:
arp -a
# Mac/Linux:
sudo nmap -sn 192.168.1.0/24 | grep -i raspberry
```

---

#### **4. High CPU Usage**

**Symptoms:**
- Raspberry Pi running hot
- Dashboard slow

**Fix:**
```bash
# Check processes
top

# Restart services
sudo systemctl restart agritech-api
sudo systemctl restart influxdb

# Check logs
sudo journalctl -u agritech-api -n 50
```

---

#### **5. Database Full**

**Symptoms:**
- "Disk full" errors
- InfluxDB write failures

**Fix:**
```bash
# Check disk usage
df -h

# Run data retention cleanup
cd /opt/technological_foods/backend
python3 api/data_retention.py --clean

# Or adjust retention in .env:
# DATA_RETENTION_DAYS=30  # Keep 30 days only
```

---

## 📞 Support

### Documentation
- User Manual: This document
- Testing Guide: `TESTING_GUIDE.md`
- API Reference: `http://raspberry-pi-ip:3001/api/docs`
- Architecture Docs: `docs/MULTI_LOCATION_ARCHITECTURE.md`

### Contact
- Email: support@agritech.example
- Phone: +351 XXX XXX XXX
- Business Hours: Mon-Fri 9:00-18:00 (Lisbon time)

### Emergency (24/7)
- Critical system failures only
- SMS: +351 XXX XXX XXX
- WhatsApp: +351 XXX XXX XXX

---

## 🎓 Training Resources

### Video Tutorials
1. Initial Setup (15 min)
2. Dashboard Overview (10 min)
3. Creating Custom Rules (20 min)
4. Mobile App Configuration (5 min)
5. Troubleshooting Common Issues (25 min)

### Quick Start Checklist

**Day 1:**
- [ ] Connect Raspberry Pi to WiFi
- [ ] Flash Arduino with firmware
- [ ] Configure WiFi on Arduino
- [ ] Verify data appears on dashboard
- [ ] Install ntfy app
- [ ] Test alert notification

**Day 2:**
- [ ] Create custom rules for your crop
- [ ] Set up AC automation (if available)
- [ ] Configure growth stage
- [ ] Review historical data

**Day 3:**
- [ ] Optimize alert thresholds
- [ ] Set up backup system
- [ ] Document your baseline values
- [ ] Schedule maintenance tasks

---

**Next Document**: See `TESTING_GUIDE.md` for comprehensive testing procedures.
