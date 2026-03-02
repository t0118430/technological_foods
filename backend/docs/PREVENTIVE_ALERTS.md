# 🚨 Preventive Alert System

## Overview

The Preventive Alert System warns you **before** sensor values reach critical thresholds, giving you time to take corrective action. This is especially important for hydroponics where rapid changes can damage crops.

## How It Works

### Three-Tier Alert System

```
┌─────────────────────────────────────────────────┐
│          SAFE ZONE (No Alerts)                  │
├─────────────────────────────────────────────────┤
│  ⚠️  PREVENTIVE ZONE (Warning - Take Action)    │
├─────────────────────────────────────────────────┤
│  🚨  CRITICAL ZONE (Threshold Exceeded)         │
└─────────────────────────────────────────────────┘
```

### Alert Levels

| Severity | Priority | When It Triggers | Purpose |
|----------|----------|------------------|---------|
| **PREVENTIVE** | 3 | Approaching threshold (within margin) | Early warning - prepare action |
| **WARNING** | 4 | Moderate issue | Take action soon |
| **CRITICAL** | 5 | Threshold exceeded | Immediate action required |

## Configuration

### Rule Structure

Each rule can have:
- `threshold`: Critical limit
- `warning_margin`: Distance from threshold to start warning
- `action.recommended_action`: What to do when critical
- `preventive_action`: What to do when approaching

### Example: Low Temperature Rule

```json
{
  "id": "notify_low_temp",
  "sensor": "temperature",
  "condition": "below",
  "threshold": 15.0,
  "warning_margin": 2.0,
  "action": {
    "type": "notify",
    "severity": "critical",
    "message": "Temperature too low for hydroponics",
    "recommended_action": "1) Check heating system. 2) Insulate grow area. 3) Move plants to warmer location if possible."
  },
  "preventive_message": "Temperature approaching minimum threshold",
  "preventive_action": "Monitor heating system. Prepare backup heat source. Check for drafts or cold spots."
}
```

### How It Triggers

**For "below" conditions:**
- **Preventive**: `threshold < value < (threshold + margin)`
- **Critical**: `value < threshold`

Example with temp threshold 15°C, margin 2°C:
- ✅ 20°C → No alert (safe)
- 👀 16.5°C → **PREVENTIVE** alert (between 15-17°C)
- 🚨 14°C → **CRITICAL** alert (below 15°C)

**For "above" conditions:**
- **Preventive**: `(threshold - margin) < value < threshold`
- **Critical**: `value > threshold`

Example with temp threshold 30°C, margin 2°C:
- ✅ 25°C → No alert (safe)
- 👀 28.5°C → **PREVENTIVE** alert (between 28-30°C)
- 🚨 31°C → **CRITICAL** alert (above 30°C)

## Current Rules with Preventive Alerts

### Temperature

| Parameter | Value |
|-----------|-------|
| **Low Threshold** | 15°C |
| **High Threshold** | 30°C |
| **Warning Margin** | 2°C |

**Low Temp Preventive (15-17°C):**
- 👀 Monitor heating system
- 👀 Prepare backup heat source
- 👀 Check for drafts or cold spots

**Low Temp Critical (<15°C):**
- 🚨 Check heating system immediately
- 🚨 Insulate grow area
- 🚨 Move plants to warmer location

**High Temp Preventive (28-30°C):**
- 👀 Increase air circulation
- 👀 Verify AC is working
- 👀 Consider reducing light intensity

**High Temp Critical (>30°C):**
- 🚨 Increase ventilation/air circulation
- 🚨 Check AC/cooling system
- 🚨 Add shade or reduce light intensity
- 🚨 Check water temperature

### Humidity

| Parameter | Value |
|-----------|-------|
| **Low Threshold** | 40% |
| **High Threshold** | 80% |
| **Warning Margin** | 5% |

**Low Humidity Preventive (40-45%):**
- 👀 Prepare humidifier
- 👀 Reduce air exchange rate
- 👀 Monitor plant transpiration

**Low Humidity Critical (<40%):**
- 🚨 Add humidifier or misting system
- 🚨 Reduce ventilation temporarily
- 🚨 Place water trays near plants
- 🚨 Check for air leaks

**High Humidity Preventive (75-80%):**
- 👀 Turn on exhaust fans
- 👀 Check dehumidifier
- 👀 Ensure good air circulation

**High Humidity Critical (>80%):**
- 🚨 Increase ventilation/exhaust
- 🚨 Run dehumidifier
- 🚨 Check for water leaks
- 🚨 Space plants further apart

## Notification Format

### Console/Logs
```
[PREVENTIVE] Temperature approaching minimum threshold
Regra: notify_low_temp_preventive
Severidade: PREVENTIVE
Mensagem: Temperature approaching minimum threshold
Hora: 2026-02-08 21:30:00

⚡ Ação Recomendada:
  Monitor heating system. Prepare backup heat source. Check for drafts.

📊 Painel de Sensores:

🌡️ Temperatura: 16.5°C  ⚠️ Baixo
  Faixa ideal: 15–30°C
  ▰▰▰▰▱▱▱▱▱▱▱▱
```

### ntfy Push Notification
- **Priority**: 3 (default)
- **Tag**: 👀 eyes emoji
- **Title**: [PREVENTIVE] Temperature approaching minimum threshold
- **Body**: Full sensor dashboard + recommended action

## Architecture & Best Practices

### Modular Design

```
┌─────────────────────────────────────────────────┐
│         Arduino Sensor (DHT20)                  │
└──────────────────┬──────────────────────────────┘
                   │ POST /api/data
                   ↓
┌─────────────────────────────────────────────────┐
│         API Server (server.py)                  │
│  - Stores data in InfluxDB                      │
│  - Passes to Rule Engine                        │
└──────────────────┬──────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────┐
│         Rule Engine (rule_engine.py)            │
│  - Evaluates rules against sensor data          │
│  - Checks critical AND preventive thresholds    │
│  - Returns triggered actions                    │
└──────────────────┬──────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────┐
│    Notification Service (notification_service.py)│
│  - Sends via multiple channels                  │
│  - Includes recommended actions                 │
│  - Respects cooldown periods                    │
└─────────────────────────────────────────────────┘
```

### Separation of Concerns

| Component | Responsibility |
|-----------|----------------|
| **Rule Engine** | Business logic - when to alert |
| **Notification Service** | Delivery mechanism - how to alert |
| **Server** | Orchestration - coordinates components |
| **Rules Config** | Configuration - what to alert |

### Microservices Principles

1. **Single Responsibility**: Each class has one job
2. **Open/Closed**: Add new channels without modifying core
3. **Dependency Injection**: Services passed as parameters
4. **Configuration-Driven**: Rules in JSON, not code
5. **Testable**: 109 unit tests covering all scenarios

## Testing

### Run All Tests
```bash
cd backend
python -m pytest api/ -v
```

### Test Preventive Alerts Only
```bash
python -m pytest api/test_preventive_alerts.py -v
```

### Test with Real Arduino Data
```bash
./snapshot.sh
```

## Usage Examples

### 1. Manual Snapshot
```bash
cd backend
./snapshot.sh
```
Get current readings + notification with any active alerts

### 2. Automatic Monitoring
Start the server and Arduino - alerts sent automatically:
```bash
cd backend
python api/server.py
```

### 3. Via API
```bash
# Test with real data from InfluxDB
curl -X POST http://localhost:3001/api/notifications/test-real \
  -H "X-API-Key: agritech-secret-key-2026"

# Check notification status
curl http://localhost:3001/api/notifications \
  -H "X-API-Key: agritech-secret-key-2026"
```

### 4. Add/Modify Rules
```bash
# Create new rule
curl -X POST http://localhost:3001/api/rules \
  -H "X-API-Key: agritech-secret-key-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "ph_high",
    "sensor": "ph",
    "condition": "above",
    "threshold": 7.0,
    "warning_margin": 0.3,
    "action": {
      "type": "notify",
      "severity": "critical",
      "message": "pH too high"
    }
  }'

# Update existing rule
curl -X PUT http://localhost:3001/api/rules/ph_high \
  -H "X-API-Key: agritech-secret-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"threshold": 7.2}'
```

## Benefits for Hydroponics

### 1. **Proactive Management**
- Get warnings before damage occurs
- Time to adjust environment gradually
- Reduce plant stress

### 2. **Actionable Intelligence**
- Every alert includes specific steps to take
- No guessing what to do
- Context-aware recommendations

### 3. **Cost Savings**
- Prevent crop loss from environmental issues
- Avoid emergency interventions
- Optimize resource usage

### 4. **Peace of Mind**
- 24/7 monitoring
- Push notifications on your phone
- Know immediately when action needed

## Future Enhancements

- [ ] Trend analysis (rising/falling rates)
- [ ] Predictive alerts (ML-based)
- [ ] Integration with automation (auto-adjust AC, humidifier)
- [ ] Multi-zone monitoring
- [ ] Alert escalation (if no action taken)
- [ ] SMS/WhatsApp/Email channels
- [ ] Custom alert schedules (quiet hours)

---

**Built with ❤️ for AgriTech Hydroponics**
*Following microservices best practices and modular design*
