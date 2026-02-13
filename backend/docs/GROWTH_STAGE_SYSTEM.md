# 🌱 Growth Stage Management System

## Complete Database-Driven Crop Lifecycle Tracking

**Problem Solved:** Different growth stages (seedling, vegetative, mature) need different optimal conditions. Your system now automatically tracks crop age and applies stage-specific monitoring!

---

## 🎯 Hybrid Database Architecture

```
┌─────────────────────────────────────────────────┐
│           InfluxDB (Time-Series)                │
│   • Sensor readings (temp, humidity, pH, EC)    │
│   • High-frequency data (every 2 seconds)       │
│   • Optimized for metrics & graphs              │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│          SQLite/PostgreSQL (Relational)         │
│   • Crop tracking (variety, plant date, stage)  │
│   • Growth stage history                        │
│   • Harvest records                             │
│   • Sensor calibration log                      │
│   • System events                               │
└─────────────────────────────────────────────────┘
```

**Why Hybrid?**
- ✅ InfluxDB = Fast time-series sensor data
- ✅ SQLite = Relational crop lifecycle data
- ✅ Best tool for each job

---

## 📊 Database Schema

### **crops** - Crop Batches
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| variety | TEXT | rosso_premium, curly_green |
| plant_date | DATE | When planted |
| expected_harvest_date | DATE | Estimated harvest |
| actual_harvest_date | DATE | Actual harvest |
| status | TEXT | active, harvested |
| zone | TEXT | Growing zone (main, zone_a) |
| notes | TEXT | Additional info |

### **growth_stages** - Stage Transitions
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| crop_id | INTEGER | Foreign key to crops |
| stage | TEXT | seedling, vegetative, maturity |
| started_at | TIMESTAMP | When stage started |
| ended_at | TIMESTAMP | When stage ended (NULL if current) |
| expected_duration_days | INTEGER | Expected days in stage |

### **harvests** - Harvest Records
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| crop_id | INTEGER | Foreign key to crops |
| harvest_date | DATE | When harvested |
| weight_kg | REAL | Total weight |
| quality_grade | TEXT | premium, standard |
| market_value | REAL | Revenue |
| notes | TEXT | Additional info |

### **calibrations** - Sensor Maintenance
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| sensor_type | TEXT | temperature, pH, EC |
| calibration_date | TIMESTAMP | When calibrated |
| next_due_date | DATE | Next calibration due |
| performed_by | TEXT | Who did it |
| notes | TEXT | Calibration details |

---

## 🌿 Growth Stages

### **Seedling Stage** (Days 0-14)

**Rosso Premium:**
- Days: 0-14
- EC: 0.8-1.2 mS/cm (gentle)
- Light: 16 hours
- Focus: Root establishment

**Curly Green:**
- Days: 0-12 (faster!)
- EC: 0.6-1.0 mS/cm (lower)
- Light: 16 hours
- Focus: Fast germination

### **Vegetative Stage** (Days 14-35)

**Rosso Premium:**
- Days: 14-35
- EC: 1.4-1.8 mS/cm (increased)
- Light: 14 hours
- Focus: Leaf development, color intensification

**Curly Green:**
- Days: 12-30
- EC: 1.2-1.6 mS/cm
- Light: 14 hours
- Focus: Rapid leaf expansion

### **Maturity Stage** (Days 35-55)

**Rosso Premium:**
- Days: 35-55
- EC: 1.6-2.0 mS/cm (peak)
- Light: 12 hours
- Focus: Peak anthocyanin, ready to harvest

**Curly Green:**
- Days: 30-50
- EC: 1.4-1.8 mS/cm
- Light: 12 hours
- Focus: Maximum crispness, harvest window

---

## 🚀 How It Works

### **1. Plant New Crop**

```bash
curl -X POST http://localhost:3001/api/crops \
  -H "X-API-Key: agritech-secret-key-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "variety": "rosso_premium",
    "plant_date": "2026-02-08",
    "zone": "main",
    "notes": "Batch #12 - Premium seeds"
  }'
```

**Response:**
```json
{
  "crop_id": 1,
  "variety": "rosso_premium",
  "plant_date": "2026-02-08",
  "current_stage": "seedling",
  "expected_harvest_days": 55,
  "zone": "main"
}
```

### **2. System Tracks Automatically**

The system:
- ✅ Starts crop in "seedling" stage
- ✅ Applies seedling-specific conditions (EC 0.8-1.2)
- ✅ Monitors with stage-aware rules
- ✅ Auto-advances after 14 days

### **3. Get Current Conditions**

```bash
curl http://localhost:3001/api/crops/1/conditions \
  -H "X-API-Key: agritech-secret-key-2026"
```

**Response:**
```json
{
  "crop_id": 1,
  "variety": "rosso_premium",
  "current_stage": "seedling",
  "stage_started": "2026-02-08T10:00:00",
  "days_in_stage": 5,
  "conditions": {
    "temperature": {"optimal_min": 20, "optimal_max": 24},
    "humidity": {"optimal_min": 50, "optimal_max": 65},
    "ph": {"optimal_min": 5.8, "optimal_max": 6.3},
    "ec": {
      "optimal_min": 0.8,
      "optimal_max": 1.2,
      "stage_specific": true
    },
    "light_hours": 16,
    "notes": "Gentle conditions for establishment"
  }
}
```

### **4. Stage-Specific Rules**

```bash
curl http://localhost:3001/api/crops/1/rules \
  -H "X-API-Key: agritech-secret-key-2026"
```

Rules automatically adjust EC thresholds based on stage:
- Seedling: EC 0.8-1.2 mS/cm
- Vegetative: EC 1.4-1.8 mS/cm
- Maturity: EC 1.6-2.0 mS/cm

### **5. Auto-Advancement**

After 14 days (Rosso Premium seedling duration):
```
System checks: Days in stage (14) >= Expected (14)
   ↓
Auto-advance to "vegetative"
   ↓
New rules applied: EC 1.4-1.8 (higher nutrients)
   ↓
Notification sent: "Crop advanced to vegetative stage"
```

### **6. Manual Advancement** (if needed)

```bash
curl -X POST http://localhost:3001/api/crops/1/advance \
  -H "X-API-Key: agritech-secret-key-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "maturity",
    "reason": "Visual inspection shows ready for maturity stage"
  }'
```

### **7. Harvest Recording**

```bash
curl -X POST http://localhost:3001/api/crops/1/harvest \
  -H "X-API-Key: agritech-secret-key-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "weight_kg": 2.5,
    "quality_grade": "premium",
    "market_value": 15.50,
    "notes": "Excellent color, crisp texture"
  }'
```

**System automatically:**
- Records harvest data
- Marks crop as "harvested"
- Closes all growth stages
- Available for analytics

---

## 📈 Dashboard & Analytics

### **Crop Dashboard**

```bash
curl http://localhost:3001/api/dashboard \
  -H "X-API-Key: agritech-secret-key-2026"
```

**Response:**
```json
{
  "total_active_crops": 3,
  "crops": [
    {
      "crop_id": 1,
      "variety": "rosso_premium",
      "plant_date": "2026-02-08",
      "current_stage": "vegetative",
      "days_in_stage": 18,
      "zone": "main"
    },
    {
      "crop_id": 2,
      "variety": "curly_green",
      "plant_date": "2026-02-15",
      "current_stage": "seedling",
      "days_in_stage": 8,
      "zone": "main"
    }
  ],
  "stage_summary": {
    "seedling": 1,
    "vegetative": 1,
    "maturity": 1
  },
  "variety_summary": {
    "rosso_premium": 2,
    "curly_green": 1
  },
  "alerts": [
    {
      "type": "stage_advancement_due",
      "count": 1,
      "crops": [...]
    },
    {
      "type": "calibration_due",
      "sensors": ["pH", "EC"]
    }
  ]
}
```

### **Harvest Analytics**

```bash
curl http://localhost:3001/api/harvest/analytics \
  -H "X-API-Key: agritech-secret-key-2026"
```

**Response:**
```json
{
  "by_variety": [
    {
      "variety": "rosso_premium",
      "count": 5,
      "avg_weight": 2.3,
      "avg_value": 14.20
    },
    {
      "variety": "curly_green",
      "count": 8,
      "avg_weight": 2.1,
      "avg_value": 6.50
    }
  ],
  "recent_harvests": [...]
}
```

---

## 🔔 Stage-Specific Notifications

### **Example: Seedling Stage**

```
[PREVENTIVE] Rosso Premium (seedling): EC aproximando máximo

Current: EC 1.15 mS/cm (approaching 1.2 mS/cm limit for seedlings)

⚡ Ação Recomendada:
  Seedlings are sensitive! Dilute solution gradually.
  Target: 0.8-1.2 mS/cm for establishment phase.

📊 Stage: Seedling (Day 12 of 14)
Next stage: Vegetative (in ~2 days, EC will increase to 1.4-1.8)
```

### **Example: Auto-Advancement**

```
[INFO] ✅ Stage Advancement: Rosso Premium

Crop #1 automatically advanced:
  From: Seedling → To: Vegetative
  Days in seedling: 14 (expected: 14)

📊 New Conditions:
  EC: 1.4-1.8 mS/cm (increased from 0.8-1.2)
  Light: 14 hours (reduced from 16)
  Focus: Rapid leaf development & color intensification

⚡ Action Required:
  Increase nutrient concentration to 1.6 mS/cm
  Reduce photoperiod to 14 hours
  Monitor for color development
```

---

## 📅 Sensor Calibration Tracking

### **Record Calibration**

```bash
curl -X POST http://localhost:3001/api/calibrations \
  -H "X-API-Key: agritech-secret-key-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_type": "pH",
    "next_due_days": 30,
    "performed_by": "António",
    "notes": "Calibrated with pH 4.0, 7.0, 10.0 buffers. Readings accurate."
  }'
```

### **Check Due Calibrations**

```bash
curl http://localhost:3001/api/calibrations/due \
  -H "X-API-Key: agritech-secret-key-2026"
```

**Response:**
```json
{
  "calibrations_due": [
    {
      "sensor_type": "pH",
      "last_calibration": "2026-01-08",
      "next_due_date": "2026-02-07"
    },
    {
      "sensor_type": "EC",
      "last_calibration": "2026-01-10",
      "next_due_date": "2026-02-09"
    }
  ]
}
```

---

## 💡 Example Workflow

### **Complete Crop Lifecycle**

```bash
# Day 0: Plant Rosso Premium
POST /api/crops {"variety": "rosso_premium"}
→ Crop #1 created, stage: seedling, EC: 0.8-1.2

# Days 1-14: Seedling stage
→ System monitors with seedling rules (gentle EC)
→ Notifications if EC exceeds 1.2 or drops below 0.8

# Day 14: Auto-advancement
→ System advances to vegetative
→ EC rules update to 1.4-1.8
→ Notification sent to increase nutrients

# Days 15-35: Vegetative stage
→ Monitor with vegetative rules
→ Color development focus for Rosso

# Day 35: Auto-advancement
→ System advances to maturity
→ EC rules update to 1.6-2.0
→ Peak anthocyanin production

# Days 36-55: Maturity stage
→ Monitor for harvest readiness
→ Daily inspections recommended

# Day 50: Harvest!
POST /api/crops/1/harvest {"weight_kg": 2.5, "quality_grade": "premium"}
→ Harvest recorded
→ Crop marked as harvested
→ Data available for analytics

# Analysis
GET /api/harvest/analytics
→ Rosso avg: 2.3kg, $14.20
→ Optimize next batch based on data!
```

---

## 🎓 Business Intelligence

### **Performance Tracking**

```sql
-- Average yield by variety
SELECT variety, AVG(weight_kg), AVG(market_value)
FROM harvests h
JOIN crops c ON h.crop_id = c.id
GROUP BY variety

-- Best performing batches
SELECT crop_id, weight_kg, market_value, quality_grade
FROM harvests
ORDER BY market_value DESC
LIMIT 10

-- Growth stage duration analysis
SELECT stage, AVG(JULIANDAY(ended_at) - JULIANDAY(started_at)) as avg_days
FROM growth_stages
WHERE ended_at IS NOT NULL
GROUP BY stage
```

### **Optimization Insights**

- 📊 Track which conditions produce best yields
- 🌡️ Correlate temperature profiles with quality grades
- 💰 Calculate ROI per variety
- ⏱️ Optimize stage durations for faster cycles

---

## 🏗️ Database Location

```
backend/
└── data/
    └── agritech.db  # SQLite database (auto-created)
```

**Backup Strategy:**
```bash
# Daily backup
cp data/agritech.db backups/agritech_$(date +%Y%m%d).db

# Weekly full backup
sqlite3 data/agritech.db ".backup backups/weekly_backup.db"
```

---

## 🔄 Migration Path

**Start: SQLite** (simple, embedded, perfect for single-site)

**Scale: PostgreSQL** (when you need multi-site or advanced features)

```python
# Change one line:
DATABASE_URL = "postgresql://user:pass@localhost/agritech"

# Schema is the same!
```

---

## ✅ Complete Feature List

- ✅ **Crop Tracking** - Plant date, variety, zone
- ✅ **Growth Stages** - Auto-track seedling → vegetative → mature
- ✅ **Stage-Specific Rules** - Different EC thresholds per stage
- ✅ **Auto-Advancement** - Progress stages based on days
- ✅ **Manual Override** - Operator can advance manually
- ✅ **Harvest Recording** - Weight, quality, value
- ✅ **Performance Analytics** - Yield, revenue by variety
- ✅ **Calibration Tracking** - Sensor maintenance log
- ✅ **Event Logging** - Complete system history
- ✅ **Dashboard** - Real-time crop status
- ✅ **Alerts** - Stage advancement due, calibration due

---

## 📚 API Reference Summary

### Crop Management
- `POST /api/crops` - Create new crop
- `GET /api/crops` - List active crops
- `GET /api/crops/{id}` - Get crop details
- `GET /api/crops/{id}/conditions` - Stage-specific conditions
- `GET /api/crops/{id}/rules` - Stage-specific rules
- `POST /api/crops/{id}/advance` - Advance stage
- `POST /api/crops/{id}/harvest` - Record harvest

### Dashboard & Analytics
- `GET /api/dashboard` - Comprehensive dashboard
- `GET /api/harvest/analytics` - Performance metrics

### Calibration
- `POST /api/calibrations` - Record calibration
- `GET /api/calibrations/due` - Sensors needing calibration

---

**Your system now has professional-grade crop lifecycle management!** 🌱

From seed to harvest, every stage tracked with optimal conditions automatically applied. Database-backed, analytics-ready, business-intelligent! 🚀
