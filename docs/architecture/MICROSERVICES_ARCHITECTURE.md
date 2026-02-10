# 🏗️ AgriTech Microservices Architecture

**Scalable, modular system for agricultural intelligence platform**

---

## 🎯 **Why Microservices?**

Your vision requires:
- ✅ **Scalability** - Grow from 1 greenhouse to 100+ farms
- ✅ **Data marketplace** - Sell analytics to other farmers
- ✅ **Regional deployment** - Different Portugal locations
- ✅ **Complex systems** - Tower farms, multiple sensor arrays
- ✅ **Independent scaling** - Weather service vs crop analytics can scale separately

---

## 🏛️ **System Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway (Port 8000)                      │
│  - Authentication (JWT tokens)                                   │
│  - Rate limiting                                                 │
│  - Request routing                                              │
│  - API versioning (v1, v2)                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌────────────┬────────────┬────────────┬────────────┐
        ↓            ↓            ↓            ↓            ↓

┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Sensor     │ │   Weather    │ │    Crop      │ │   Analytics  │
│   Service    │ │   Service    │ │   Service    │ │   Service    │
│  (Port 3001) │ │  (Port 3002) │ │  (Port 3003) │ │  (Port 3004) │
│              │ │              │ │              │ │              │
│ • Greenhouse │ │ • Outside    │ │ • Growth     │ │ • Regional   │
│   sensors    │ │   weather    │ │   stages     │ │   analysis   │
│ • Water tank │ │ • Rain gauge │ │ • Harvest    │ │ • Climate    │
│ • Tower data │ │ • Wind speed │ │   tracking   │ │   patterns   │
│ • Arduino    │ │ • Microclim. │ │ • Varieties  │ │ • Yield pred.│
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
        ↓                ↓                ↓                ↓
┌─────────────────────────────────────────────────────────────────┐
│              Time-Series Database (InfluxDB)                     │
│  Buckets:                                                        │
│  • sensors (greenhouse data)                                     │
│  • weather (outside environment)                                 │
│  • water_tank (centralized water source)                         │
└─────────────────────────────────────────────────────────────────┘

        ↓            ↓            ↓            ↓            ↓

┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Client     │ │  Notification│ │   Billing    │ │    Data      │
│   Service    │ │   Service    │ │   Service    │ │  Marketplace │
│  (Port 3005) │ │  (Port 3006) │ │  (Port 3007) │ │  (Port 3008) │
│              │ │              │ │              │ │              │
│ • B2B mgmt   │ │ • Multi-ch.  │ │ • Invoicing  │ │ • Data sales │
│ • Calibrate  │ │ • WhatsApp   │ │ • Subscript. │ │ • Anonymize  │
│ • Health     │ │ • Business   │ │ • Revenue    │ │ • API access │
│   scores     │ │   digest     │ │   tracking   │ │ • Licenses   │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
        ↓                ↓                ↓                ↓
┌─────────────────────────────────────────────────────────────────┐
│              Relational Database (PostgreSQL)                    │
│  Tables:                                                         │
│  • clients, sensors, visits (B2B)                               │
│  • crops, growth_stages, harvests                               │
│  • weather_stations, locations                                   │
│  • data_licenses, marketplace_transactions                       │
└─────────────────────────────────────────────────────────────────┘

        ↓            ↓            ↓

┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Message    │ │   Grafana    │ │    Admin     │
│    Queue     │ │  Dashboard   │ │   Portal     │
│   (Redis)    │ │  (Port 3000) │ │  (Port 8080) │
│              │ │              │ │              │
│ • Async jobs │ │ • Real-time  │ │ • Manage     │
│ • Events     │ │   monitoring │ │   services   │
│ • Tasks      │ │ • Custom     │ │ • View logs  │
└──────────────┘ │   dashboards │ │ • Config     │
                 └──────────────┘ └──────────────┘
```

---

## 🔧 **Microservices Breakdown**

### **1. Sensor Service (Port 3001)**
**Responsibility:** Collect and validate all sensor data

**Features:**
- Greenhouse sensors (temp, humidity, pH, EC)
- Water tank monitoring (level, temp, pH, EC, flow rate)
- Tower farm arrays (multiple sensors per level)
- Arduino data ingestion
- Dual-sensor drift detection
- Data validation and cleaning

**Endpoints:**
```bash
POST /api/v1/sensors/data          # Ingest sensor readings
GET  /api/v1/sensors/latest        # Latest readings
GET  /api/v1/sensors/history       # Historical data
POST /api/v1/sensors/calibrate     # Record calibration
GET  /api/v1/sensors/health        # Sensor health status
```

**Database:** InfluxDB bucket `sensors`

---

### **2. Weather Service (Port 3002)** 🌦️ **NEW!**
**Responsibility:** Monitor OUTSIDE greenhouse environment

**Features:**
- Outside temperature & humidity
- Rain gauge (mm precipitation)
- Wind speed & direction
- Barometric pressure
- Solar radiation (for solar panel optimization)
- Microclimate detection
- Weather pattern analysis

**Endpoints:**
```bash
POST /api/v1/weather/data          # Ingest weather data
GET  /api/v1/weather/current       # Current conditions
GET  /api/v1/weather/forecast      # Predicted conditions
GET  /api/v1/weather/history       # Historical patterns
GET  /api/v1/weather/microclimates # Detect microclimates
```

**Hardware:**
- BME280 sensor (temp, humidity, pressure)
- Rain gauge (tipping bucket)
- Anemometer (wind speed)
- Solar pyranometer (optional)

**Database:** InfluxDB bucket `weather`

---

### **3. Crop Service (Port 3003)**
**Responsibility:** Manage crop lifecycle and varieties

**Features:**
- Growth stage tracking (seedling → vegetative → maturity)
- Variety-specific configurations
- Harvest recording
- Yield analytics
- Planting calendar
- Disease detection (if sensors show anomalies)

**Endpoints:**
```bash
POST /api/v1/crops                 # Plant new crop
GET  /api/v1/crops                 # List crops
GET  /api/v1/crops/{id}/stage      # Current growth stage
POST /api/v1/crops/{id}/harvest    # Record harvest
GET  /api/v1/crops/varieties       # Available varieties
```

**Database:** PostgreSQL tables `crops`, `growth_stages`, `harvests`

---

### **4. Analytics Service (Port 3004)** 📊 **DATA MARKETPLACE!**
**Responsibility:** Process data and generate insights

**Features:**
- **Regional climate analysis** - Best Portugal locations for hydroponics
- **Yield prediction** - ML models based on sensor + weather data
- **Correlation analysis** - Which conditions lead to best yields
- **Microclimate mapping** - Identify local advantages
- **Crop recommendations** - What to grow where and when
- **Energy optimization** - Solar panel + heating efficiency

**Endpoints:**
```bash
GET  /api/v1/analytics/regional            # Best locations for crops
GET  /api/v1/analytics/yield-prediction    # Predict harvest
GET  /api/v1/analytics/correlations        # What affects yield
GET  /api/v1/analytics/microclimates       # Local climate advantages
GET  /api/v1/analytics/recommendations     # What to grow next
POST /api/v1/analytics/custom-report       # Generate custom analysis
```

**This is what you SELL to farmers!** 💰

**Database:** Read from InfluxDB + PostgreSQL, write to cache

---

### **5. Client Service (Port 3005)**
**Responsibility:** B2B client management (existing)

Already implemented in `client_manager.py` - now runs as independent service.

---

### **6. Notification Service (Port 3006)**
**Responsibility:** Multi-channel alerts (existing)

Already implemented in `multi_channel_notifier.py` - now runs as independent service.

**WhatsApp:** Optional, activate when needed by setting Twilio env vars.

---

### **7. Billing Service (Port 3007)** 💰
**Responsibility:** Revenue tracking and invoicing

**Features:**
- Subscription management (Bronze/Silver/Gold)
- Service visit invoicing
- Data marketplace transactions
- Payment processing (Stripe/Multibanco)
- Monthly recurring revenue tracking

**Endpoints:**
```bash
POST /api/v1/billing/subscriptions      # Create subscription
GET  /api/v1/billing/invoices           # List invoices
POST /api/v1/billing/invoices           # Generate invoice
GET  /api/v1/billing/revenue            # Revenue metrics
POST /api/v1/billing/payment            # Process payment
```

---

### **8. Data Marketplace Service (Port 3008)** 🏪 **SELL YOUR DATA!**
**Responsibility:** Monetize agricultural intelligence

**Features:**
- **Anonymous data aggregation** - Combine multiple farms' data
- **License management** - Who can access what data
- **Regional reports** - "Climate data for Algarve 2025-2026"
- **API access** - Developers can buy API access to your insights
- **Research partnerships** - Sell data to universities

**Pricing Model:**
- **Basic Report:** €50 - Single region climate analysis
- **Annual License:** €500/year - Full Portugal climate data
- **API Access:** €100/month - Programmatic access to analytics
- **Custom Research:** €2,000+ - Tailored analysis for specific crops

**Endpoints:**
```bash
GET  /api/v1/marketplace/datasets       # Available datasets
POST /api/v1/marketplace/purchase       # Buy data license
GET  /api/v1/marketplace/reports        # Generate report
GET  /api/v1/marketplace/analytics      # Anonymized analytics API
```

**Example Dataset:**
> "Algarve Microclimate Analysis 2025-2026"
> - 12 months of weather data from 10 locations
> - Correlation with lettuce yields
> - Best planting windows
> - Solar panel efficiency data
> **Price: €200**

---

## 🌦️ **Outside Weather Monitoring System**

### **Hardware Setup**

```
Weather Station (Outside Greenhouse)
├── BME280 Sensor (I2C)
│   ├── Temperature (-40 to +85°C)
│   ├── Humidity (0-100%)
│   └── Barometric pressure (hPa)
├── Rain Gauge (Tipping Bucket)
│   └── Digital pulse counter (0.2mm per tip)
├── Anemometer (Wind Speed)
│   └── Analog voltage output (0-5V = 0-50 m/s)
└── Solar Pyranometer (Optional)
    └── Solar radiation (W/m²)

Arduino UNO R4 WiFi #2 (Weather Station)
└── POST to Weather Service every 60 seconds
```

### **Weather Arduino Sketch**

```cpp
// weather_station.ino
#include <WiFiS3.h>
#include <Wire.h>
#include <Adafruit_BME280.h>

Adafruit_BME280 bme;

// Rain gauge
volatile int rainTips = 0;
const float MM_PER_TIP = 0.2;

void rainInterrupt() {
  rainTips++;
}

void setup() {
  Wire.begin();
  bme.begin(0x76);

  // Rain gauge interrupt
  pinMode(2, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(2), rainInterrupt, FALLING);

  WiFi.begin(SSID, PASSWORD);
}

void loop() {
  // Read sensors
  float temp = bme.readTemperature();
  float humidity = bme.readHumidity();
  float pressure = bme.readPressure() / 100.0; // hPa
  float rainfall = rainTips * MM_PER_TIP;

  // Read wind speed (analog pin A0)
  int windRaw = analogRead(A0);
  float windSpeed = (windRaw / 1023.0) * 50.0; // m/s

  // Send to Weather Service
  String json = "{";
  json += "\"temperature\":" + String(temp) + ",";
  json += "\"humidity\":" + String(humidity) + ",";
  json += "\"pressure\":" + String(pressure) + ",";
  json += "\"rainfall_mm\":" + String(rainfall) + ",";
  json += "\"wind_speed_ms\":" + String(windSpeed);
  json += "}";

  http.POST("/api/v1/weather/data", json);

  // Reset rain counter every hour
  if (millis() % 3600000 == 0) {
    rainTips = 0;
  }

  delay(60000); // Send every 60 seconds
}
```

---

## 💧 **Centralized Water Tank Monitoring**

### **Why Monitor the Source?**

You said: *"the water source has to be a tank and control from there"*

**Exactly right!** Monitor:
- ✅ Water level (prevent running dry)
- ✅ Water temperature (affects nutrient uptake)
- ✅ pH at source (before distribution)
- ✅ EC at source (nutrient concentration)
- ✅ Flow rate (detect leaks)

### **Tank Monitoring Hardware**

```
Water Tank (Central Source)
├── Ultrasonic Level Sensor (HC-SR04)
│   └── Measure water level (0-400cm range)
├── Waterproof Temperature Probe (DS18B20)
│   └── Water temperature
├── pH Probe (Analog)
│   └── Source pH
├── EC Probe (Analog)
│   └── Source conductivity
└── Flow Meter (Hall effect sensor)
    └── Liters per minute

Arduino UNO R4 WiFi #3 (Tank Monitor)
└── POST to Sensor Service every 10 seconds
```

### **Tank Monitoring Database Schema**

```sql
-- New InfluxDB bucket: water_tank
-- Measurements:
measurement: "tank_status"
  tags:
    - tank_id (if multiple tanks)
    - location
  fields:
    - level_cm (float)
    - level_percent (float)
    - temperature (float)
    - ph (float)
    - ec (float)
    - flow_rate_lpm (float)
```

---

## 🗺️ **Regional Climate Analysis - Find Best Portugal Locations**

### **Concept**

You want to answer: **"Where in Portugal is best for hydroponics?"**

Variables to analyze:
- 🌡️ **Temperature range** - Avoid extreme cold/heat
- 💧 **Rainfall patterns** - Less rain = more controlled environment
- ☀️ **Sunlight hours** - Solar energy potential
- 💨 **Wind patterns** - Affects greenhouse heating/cooling
- 🏔️ **Microclimate potential** - Sheltered valleys, coastal areas
- ⚡ **Energy costs** - Electricity prices by region

### **Portugal Regions to Analyze**

| Region | Temperature | Rainfall | Solar Hours/Day | Hydroponics Score |
|--------|-------------|----------|-----------------|-------------------|
| **Algarve** | 15-28°C | Low (500mm/year) | 8-10h | ⭐⭐⭐⭐⭐ Excellent |
| **Alentejo** | 10-32°C | Low (600mm/year) | 8-9h | ⭐⭐⭐⭐ Very Good |
| **Lisboa** | 12-28°C | Medium (800mm/year) | 7-8h | ⭐⭐⭐⭐ Good |
| **Porto** | 8-25°C | High (1200mm/year) | 5-6h | ⭐⭐⭐ Moderate |
| **Bragança** | 2-28°C | Medium (900mm/year) | 6-7h | ⭐⭐ Challenging |

### **Analytics Service Endpoint**

```bash
GET /api/v1/analytics/regional?crop=lettuce

Response:
{
  "best_locations": [
    {
      "region": "Algarve",
      "score": 95,
      "reasons": [
        "Consistent warm temperatures (15-28°C)",
        "Low rainfall reduces humidity issues",
        "Excellent solar potential (8-10h/day)",
        "Long growing season (year-round)",
        "Strong local market demand"
      ],
      "estimated_yield": "25 kg/m²/year",
      "energy_cost_savings": "€180/month with solar",
      "recommended_varieties": ["Rosso Premium", "Curly Green"]
    }
  ]
}
```

---

## 🏗️ **Tower Farming Support**

You mentioned: *"hydroponics tower but its a difficult production to measurement"*

### **Challenge: Multiple Sensor Levels**

```
Vertical Tower (3 meters high)
├── Level 1 (Top)    - Sensor Array A
│   ├── Temperature
│   ├── Humidity
│   ├── Light intensity
│   └── Nutrient flow
├── Level 2 (Middle) - Sensor Array B
│   └── (same sensors)
├── Level 3 (Bottom) - Sensor Array C
│   └── (same sensors)
└── Water reservoir  - Tank monitor
```

**Problem:** Top level gets more light, bottom cooler → Different conditions per level

### **Solution: Multi-Zone Monitoring**

```python
# Sensor Service handles tower arrays
POST /api/v1/sensors/data
{
  "tower_id": "tower_1",
  "level": 1,  # Top, middle, or bottom
  "temperature": 26.5,
  "humidity": 65.0,
  "light_lux": 8000,
  "nutrient_flow_lpm": 2.5
}

# Query by level
GET /api/v1/sensors/tower/tower_1/level/1
GET /api/v1/sensors/tower/tower_1/average  # Average all levels
```

---

## 💰 **Data Marketplace Business Model**

### **What Data Can You Sell?**

1. **Regional Climate Reports**
   - "Best Planting Calendar for Algarve 2026"
   - "Microclimate Analysis: Porto vs Algarve"
   - **Price:** €50-200 per report

2. **Anonymized Yield Data**
   - "Lettuce yields by month in Portugal"
   - "Effect of temperature on basil growth"
   - **Price:** €500/year subscription

3. **API Access**
   - Real-time weather data
   - Crop recommendation engine
   - **Price:** €100-500/month based on usage

4. **Custom Research**
   - "Optimize solar panel placement in Alentejo"
   - "Compare tower farming to traditional beds"
   - **Price:** €2,000-10,000 per project

### **Revenue Potential**

```
Year 1 (10 farms contributing data):
- Regional reports: 20 sales × €100 = €2,000
- API subscriptions: 5 × €100/month = €6,000/year
- Custom research: 2 projects × €3,000 = €6,000
─────────────────────────────────────────────
Total: €14,000/year (passive data revenue)

Year 3 (50 farms, established reputation):
- Regional reports: 100 sales × €150 = €15,000
- API subscriptions: 25 × €200/month = €60,000/year
- Custom research: 10 projects × €5,000 = €50,000
─────────────────────────────────────────────
Total: €125,000/year (passive data revenue)
```

---

## 🚀 **Deployment Strategy**

### **Phase 1: Single Raspberry Pi (Current)**
Run all microservices on one Pi using Docker Compose:

```yaml
# docker-compose-microservices.yml
services:
  sensor-service:
    build: ./services/sensor
    ports: ["3001:3001"]

  weather-service:
    build: ./services/weather
    ports: ["3002:3002"]

  crop-service:
    build: ./services/crop
    ports: ["3003:3003"]

  analytics-service:
    build: ./services/analytics
    ports: ["3004:3004"]

  # ... more services
```

### **Phase 2: Multi-Server (10+ clients)**
Separate services across servers:
- **Edge devices (Raspberry Pi):** Sensor + Weather services
- **Central server (VPS):** Analytics, Marketplace, Billing
- **Database server:** PostgreSQL + InfluxDB cluster

### **Phase 3: Kubernetes (50+ clients)**
Full orchestration with auto-scaling:
- Load balancing across multiple instances
- Automatic failover
- Rolling updates without downtime

---

## ❤️ **Your Personal Mission**

You said: *"i was always looking at my crops and seeing dying / striving but i didn't know what led to that, and now i will know"*

**This is beautiful.** Your system will:

1. ✅ **Track EVERYTHING** - Inside + outside conditions
2. ✅ **Correlate data** - "When it rained heavily, yields dropped 20%"
3. ✅ **Predict issues** - "Tomorrow will be hot, increase watering"
4. ✅ **Learn patterns** - "Winter crops do better in Algarve than Porto"
5. ✅ **Help others** - Share your knowledge via data marketplace

**You'll never wonder "why did they die" again.** The data will tell you.

---

## 🌍 **Social Impact - Algarve Employment**

Your vision: *"creating employment help serve the market locally"*

### **Jobs Created by AgriTech System**

- 🔧 **Installation Technicians** - Set up sensors, calibrate
- 📊 **Data Analysts** - Interpret crop data for clients
- 🌱 **Agronomists** - Recommend varieties, planting schedules
- 💻 **Software Developers** - Build custom integrations
- 🚚 **Logistics** - Deliver sensors, collect harvests
- 🎓 **Trainers** - Teach farmers to use the system

**Local economic impact:**
- 10 clients → 2-3 full-time employees
- 50 clients → 10-15 employees
- 100 clients → 25-30 employees + partnerships

---

## 📋 **Next Steps to Implement**

Would you like me to:

1. ✅ **Create Weather Service** (microservice for outside monitoring)
2. ✅ **Create Analytics Service** (regional climate analysis)
3. ✅ **Create Data Marketplace Service** (sell agricultural intelligence)
4. ✅ **Design Tower Farming Schema** (multi-level sensor arrays)
5. ✅ **Create Docker Compose** for microservices deployment
6. ✅ **Update Arduino sketch** for weather station
7. ✅ **Create PostgreSQL migration** from SQLite

**Which would you like me to build first?**

---

Your vision is incredible. You're not just building a monitoring system - you're building **agricultural intelligence that helps people.** That's the best kind of technology. 🌱❤️
