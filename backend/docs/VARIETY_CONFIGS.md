# 🌱 DRY Variety Configuration System

## Overview

Professional, research-based hydroponics configuration for **two lettuce varieties** following **DRY principles** (Don't Repeat Yourself).

---

## 🎯 What We Built

### **Three-Layer Configuration System**

```
┌─────────────────────────────────────────────┐
│   Base Config (base_hydroponics.json)      │
│   • Common settings for all lettuces       │
│   • Sensor calibration schedules           │
│   • Maintenance routines                   │
│   • Time-based notifications               │
└────────────────┬────────────────────────────┘
                 │
         ┌───────┴───────┐
         ↓               ↓
┌─────────────────┐ ┌─────────────────┐
│ Rosso Premium   │ │ Curly Green     │
│ (Red Lettuce)   │ │ (Green Lettuce) │
│                 │ │                 │
│ • Overrides     │ │ • Overrides     │
│ • Specifics     │ │ • Specifics     │
└─────────────────┘ └─────────────────┘
```

---

## 📋 Varieties Configured

### 🔴 **Rosso Premium (Red/Purple Leaf Lettuce)**

**Scientific:** *Lactuca sativa* 'Rosso'
**Maturity:** 45-55 days
**Market Value:** Premium
**Difficulty:** Medium

**Optimal Conditions:**
| Parameter | Range | Notes |
|-----------|-------|-------|
| Temperature | 20-24°C | Tolerates warmer temps |
| Humidity | 50-65% | Lower than green varieties |
| pH | 5.8-6.3 | Slightly acidic for color |
| EC | 1.4-2.0 mS/cm | Higher for intense flavor |
| Light | 400-700 lux | More light = deeper red |

**Key Features:**
- 🎨 High anthocyanin content (deep red color)
- 🌡️ Heat tolerant
- 💡 Requires more light for color development
- 🥗 Slightly bitter, gourmet taste

**Common Issues & Solutions:**
- **Green instead of red** → Increase light to 500+ lux, maintain 22-24°C
- **Tip burn** → Reduce EC to 1.6, add calcium, increase fans
- **Bolting** → Cool system below 28°C, reduce photoperiod

---

### 🟢 **Curly Green (Lollo Bionda)**

**Scientific:** *Lactuca sativa* 'Lollo Bionda'
**Maturity:** 40-50 days
**Market Value:** Standard
**Difficulty:** Easy

**Optimal Conditions:**
| Parameter | Range | Notes |
|-----------|-------|-------|
| Temperature | 18-22°C | Prefers cooler temps |
| Humidity | 55-70% | Moderate-high |
| pH | 6.0-6.5 | Slightly higher than red |
| EC | 1.2-1.8 mS/cm | Lower to prevent bitterness |
| Light | 300-500 lux | Moderate, avoid excess |

**Key Features:**
- ✨ Bright green, very crispy
- 🍃 Mild, sweet flavor
- ⚡ Fast growing (40-50 days)
- 😊 Easy to grow

**Common Issues & Solutions:**
- **Bitter taste** → Cool to <22°C, reduce EC to 1.4, less light
- **Yellowing** → Increase EC to 1.6, check roots, warm to 20°C
- **Bolting** → URGENT! Cool immediately, reduce light to 12h
- **Brown edges** → Reduce EC, add calcium, increase humidity

---

## 🔬 Research-Based Ranges

All values based on:
- Cornell University Controlled Environment Agriculture
- University of Arizona Hydroponics Research
- NASA Space Crop Production

### **Sensor Specifications**

| Sensor | Type | Accuracy | Calibration Interval |
|--------|------|----------|---------------------|
| Temperature | DHT20 | ±0.5°C | Every 90 days |
| Humidity | DHT20 | ±2% | Every 90 days |
| pH | Probe | ±0.1 | Every 30 days ⚠️ |
| EC | Probe | ±0.05 | Every 30 days ⚠️ |
| Water Level | Ultrasonic | ±5% | Every 180 days |
| Light | Lux Meter | ±10% | Every 365 days |

---

## 📅 Automated Schedules

### **Calibration Reminders**

The system automatically reminds you when sensors need calibration:

```json
{
  "ph": {
    "interval_days": 30,
    "requires_solution": true,
    "solutions": ["pH 4.0", "pH 7.0", "pH 10.0"]
  },
  "ec": {
    "interval_days": 30,
    "requires_solution": true,
    "standard": "1.413 mS/cm at 25°C"
  },
  "temperature": {
    "interval_days": 90
  }
}
```

### **Time-Based Notifications**

| Time | Frequency | Message |
|------|-----------|---------|
| 08:00 | Daily | ☀️ Morning Check: Review overnight conditions |
| 20:00 | Daily | 🌙 Evening Check: Verify systems before night |
| Sat 09:00 | Weekly | 🔧 Weekly Maintenance: Filters, pH, EC |
| 1st @ 10:00 | Monthly | 📐 Monthly Calibration: pH and EC sensors |

---

## 🏗️ DRY Architecture

### **Inheritance Hierarchy**

```python
Base Config
    ├── Common settings (system_name, cultivation_method)
    ├── Sensor specs (calibration intervals)
    ├── Base ranges (general lettuce)
    ├── Maintenance schedule
    └── Time-based notifications

Variety Config (extends base)
    ├── Variety metadata (name, type, maturity)
    ├── Optimal ranges (overrides base)
    ├── Growth stages (seedling, vegetative, mature)
    ├── Nutrient formula
    ├── Preventive actions
    ├── Common issues & solutions
    └── Harvest guidelines
```

### **Configuration Merging**

```python
# Example: Temperature for Rosso Premium

Base says:    15-28°C (critical range)
Rosso says:   20-28°C (prefers warmer)
              ↓
Result:       20-28°C (variety-specific optimal)
              Base inherited for undefined values
```

---

## 🚀 Usage

### **Load a Variety Configuration**

```python
from config_loader import config_loader

# Load Rosso Premium
rosso_config = config_loader.load_variety('rosso_premium')

# Access optimal ranges
temp_range = rosso_config['optimal_ranges']['temperature']
print(f"Optimal temp: {temp_range['optimal_min']}-{temp_range['optimal_max']}°C")

# Get auto-generated rules
rules = rosso_config['rules']
for rule in rules:
    print(f"Rule: {rule['name']}")
```

### **Get Calibration Schedule**

```python
schedule = config_loader.get_calibration_schedule(rosso_config)

for sensor, info in schedule.items():
    print(f"{sensor}: Calibrate every {info['interval_days']} days")
    if info['requires_solution']:
        print(f"  Needs: {', '.join(info['solutions'])}")
```

### **Get Maintenance Tasks**

```python
maintenance = config_loader.get_maintenance_schedule(rosso_config)

print("Weekly tasks:")
for task in maintenance['weekly']:
    print(f"  • {task}")
```

---

## 📊 Comparison: Rosso vs Curly

| Parameter | Rosso Premium | Curly Green | Winner |
|-----------|---------------|-------------|--------|
| **Temperature** | 20-24°C (warmer) | 18-22°C (cooler) | Curly (less heating) |
| **Humidity** | 50-65% (lower) | 55-70% (higher) | Rosso (less mold risk) |
| **pH** | 5.8-6.3 (acidic) | 6.0-6.5 (neutral) | Similar |
| **EC** | 1.4-2.0 (higher) | 1.2-1.8 (lower) | Curly (cheaper nutrients) |
| **Light** | 400-700 (high) | 300-500 (moderate) | Curly (lower electricity) |
| **Maturity** | 45-55 days | 40-50 days | Curly (faster harvest) |
| **Market Price** | Premium ($$$) | Standard ($$) | Rosso (higher revenue) |
| **Difficulty** | Medium | Easy | Curly (beginner-friendly) |

### **Cost-Benefit Analysis**

**Curly Green:**
- ✅ Cheaper to produce (less light, lower EC)
- ✅ Faster to market (40-50 days)
- ✅ Easier for beginners
- ❌ Lower market price

**Rosso Premium:**
- ✅ Premium market price (2-3x higher)
- ✅ Differentiated product
- ✅ Heat tolerant (summer production)
- ❌ Higher production costs
- ❌ Requires expertise

**Recommendation:** Start with Curly Green, add Rosso Premium once profitable.

---

## 🔔 Notification Examples

### **Preventive Alert (Rosso)**
```
[PREVENTIVE] Alface Rosso Premium: Temperatura aproximando máximo

⚡ Ação Recomendada:
  Increase air circulation. Verify AC is working.
  Consider reducing light intensity.

📊 Painel de Sensores:
🌡️ Temperatura: 26.5°C  ⚠️ Alto (approaching 28°C limit)
```

### **Critical Alert (Curly - Heat Sensitive!)**
```
[CRITICAL] Alface Crespa Verde: Temperatura muito alta

⚡ Ação Recomendada:
  URGENT: Curly lettuce sensitive to heat!
  Increase ventilation, add shade cloth,
  run AC if available, mist canopy.

📊 Painel de Sensores:
🌡️ Temperatura: 27.0°C  🚨 Muito Alto (limit 26°C)
```

### **Calibration Reminder**
```
[INFO] 📐 Monthly Calibration Due

Sensors needing calibration:
  • pH Sensor (last: 32 days ago)
    Solutions needed: pH 4.0, pH 7.0, pH 10.0

  • EC Sensor (last: 31 days ago)
    Standard: 1.413 mS/cm at 25°C

⚡ Ação Recomendada:
  Set aside 30 minutes for calibration.
  Gather solutions and follow sensor manual.
```

---

## 📁 File Structure

```
backend/
├── config/
│   ├── base_hydroponics.json        # Base configuration
│   ├── variety_rosso_premium.json   # Rosso Premium overrides
│   └── variety_curly_green.json     # Curly Green overrides
│
├── api/
│   ├── config_loader.py             # DRY config loader
│   └── test_config_loader.py        # 19 tests (all passing)
│
└── VARIETY_CONFIGS.md               # This file
```

---

## ✅ Testing

**19 tests passing:**
```bash
pytest api/test_config_loader.py -v
```

Tests cover:
- ✅ Config loading and merging
- ✅ Variety overrides
- ✅ Rule generation
- ✅ Calibration schedules
- ✅ Variety-specific differences
- ✅ DRY principles

---

## 🎓 Best Practices

### **When to Use Each Variety**

**Rosso Premium:**
- Gourmet restaurants
- Farmers markets
- High-end grocery stores
- Summer growing (heat tolerant)
- When you have experience

**Curly Green:**
- Supermarkets
- Salad bars
- Bulk production
- Year-round growing
- When learning hydroponics

### **Production Strategy**

**Beginner:** Start with 100% Curly Green
**Intermediate:** 70% Curly, 30% Rosso
**Advanced:** 50% Curly, 50% Rosso (or all Rosso for premium market)

---

## 🔮 Future Enhancements

- [ ] More varieties (butterhead, romaine, arugula)
- [ ] Growth stage automation (adjust EC by age)
- [ ] Seasonal profiles (summer vs winter)
- [ ] Multi-zone support (different varieties same system)
- [ ] AI-optimized ranges (learn from your data)
- [ ] Mobile app for variety management

---

**Built with ❤️ for profitable hydroponic farming**
*Based on scientific research and best practices*
