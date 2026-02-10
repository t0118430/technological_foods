# 🏢 AgriTech Business Intelligence System

Complete guide to the B2B client management, calibration tracking, and revenue optimization features.

---

## 📊 **Overview**

The AgriTech Business Intelligence system transforms your agricultural monitoring platform into a **service business** with:

- 🔧 **Calibration Service Tracking** - Monitor client sensor health
- 💰 **Revenue Management** - Track MRR, service fees, opportunities
- 📱 **Multi-Channel Alerts** - Redundant notification system
- 📈 **Health Score System** - Proactive client maintenance
- 🎯 **3-Tier Alert Levels** - Aggressive, Medium, Optimist

---

## 🎯 **Service Business Model**

### **Three Service Tiers** (from ALERT_ESCALATION.md)

| Tier | Monthly Fee | Features | Target Clients |
|------|-------------|----------|----------------|
| **🥉 Bronze** | €49/month | Basic monitoring, console alerts | Small farms, hobbyists |
| **🥈 Silver** | €199/month | Expert weekly reviews, WhatsApp alerts | Commercial farms |
| **🥇 Gold** | €499/month | 24/7 monitoring, remote fixes, phone support | Large operations |

### **Additional Revenue Streams**

- 🔧 **On-site calibration:** €50-100 per visit
- 📦 **Sensor hardware sales:** €200-500 per unit
- 🎓 **Training sessions:** €300-500 per session
- 📊 **Custom dashboards:** €1000-2000 one-time

### **Revenue Potential** (30 clients mix)

```
10 Bronze × €49  = €490/month
15 Silver × €199 = €2,985/month
5 Gold × €499    = €2,495/month
────────────────────────────────
MRR Total        = €5,970/month
Annual (MRR)     = €71,640/year

Service visits (avg 2/month per client × €75 avg) = €4,500/month
Hardware sales (1 new client/month × €300 avg) = €300/month
────────────────────────────────────────────────────────────────
Total Monthly    = €10,770
Annual Total     = €129,240/year
```

---

## 📱 **Multi-Channel Notification System**

### **Three Redundant ntfy Channels**

```
┌─────────────────────────────────────────┐
│  🟢 CLIENT_PUBLIC (agritech-client)     │
│  - Crop alerts (temp, pH, water)       │
│  - Growth stage notifications           │
│  - Harvest reminders                    │
│  - Customer-facing, clean messaging     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  🔒 BUSINESS_PRIVATE (agritech-business)│
│  - Daily revenue digest                 │
│  - Client health scores                 │
│  - Sensor failure predictions           │
│  - Service visit reminders              │
│  - Revenue opportunities                │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  🚨 EMERGENCY (agritech-emergency)      │
│  - System crashes                       │
│  - Data loss events                     │
│  - Security breaches                    │
│  - Critical failures only               │
└─────────────────────────────────────────┘
```

### **3-Tier Alert Levels**

| Level | Icon | Priority | Use Case |
|-------|------|----------|----------|
| **🟢 Optimist** | Green circle | Low (3) | Everything improving, FYI only |
| **🟡 Medium** | Yellow circle | Medium (4) | Attention needed soon, not urgent |
| **🔴 Aggressive** | Red circle + siren | High (5) | Urgent action required immediately |

### **Setup Instructions**

1. **Install ntfy app** on your phone:
   - Android: [Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
   - iOS: [App Store](https://apps.apple.com/app/ntfy/id1625396347)

2. **Subscribe to your topics:**
   - Open app → + button
   - Enter topic names (e.g., `agritech-client-alerts`)
   - Enable notifications

3. **Configure in `.env`:**
   ```bash
   NTFY_URL=https://ntfy.sh
   NTFY_TOPIC_CLIENT=agritech-client-alerts
   NTFY_TOPIC_BUSINESS=agritech-business-private
   NTFY_TOPIC_EMERGENCY=agritech-emergency-911
   ```

4. **Test the system:**
   ```bash
   cd backend/api
   python3 test_multi_channel.py
   ```

---

## 🔧 **Client & Calibration Management**

### **Database Schema**

#### **clients** table
```sql
- id: Client unique ID
- company_name: Business name
- contact_name, contact_phone, contact_email: Primary contact
- service_tier: bronze / silver / gold
- location: City, address
- install_date: When system was installed
- monthly_fee: Subscription amount
- is_active: Active subscription?
- health_score: 0-100 (negative points system)
- notes: Free-text notes
```

#### **sensor_units** table
```sql
- id: Sensor unique ID
- client_id: Which client owns this sensor
- sensor_type: temperature / humidity / ph / ec
- serial_number: Hardware serial
- install_date: When installed
- last_calibration: Last calibration date
- next_calibration_due: When next calibration needed (auto 90 days)
- drift_detected: Boolean flag for drift
- failure_count: How many times sensor failed
- status: healthy / degraded / failing / offline
```

#### **service_visits** table
```sql
- id: Visit unique ID
- client_id: Which client
- visit_date: When visit occurred
- technician: Who performed service
- service_type: calibration / repair / installation
- sensors_serviced: JSON list of sensor IDs
- issues_found: Text description
- actions_taken: What was done
- revenue: How much charged
- next_visit_recommended: Optional future visit date
```

### **Health Score System (Negative Points)**

Clients start at **100/100 health**. Points are **deducted** when issues occur:

| Event | Points Deducted | Trigger |
|-------|-----------------|---------|
| **Overdue calibration** | -5 per week | Calibration date passed |
| **Sensor drift detected** | -10 | Dual-sensor comparison shows >2% diff |
| **Sensor failing** | -20 | Drift >5% or complete failure |
| **Sensor offline** | -15 | No data received for 24h |
| **Alert frequency** | -2 per alert | >5 alerts in 24h |
| **Service visit completed** | +15 | After calibration/repair |
| **Month without issues** | +5 | Gradual recovery |

### **Alert Thresholds**

- **Health Score < 60:** 🔴 **URGENT** - Send aggressive alert to business channel
- **Health Score 60-79:** 🟡 **ATTENTION** - Schedule service visit
- **Health Score 80-100:** 🟢 **HEALTHY** - All good, routine monitoring

---

## 📈 **Daily Business Digest**

Every day at 2:00 AM, the system sends a comprehensive report to the **BUSINESS_PRIVATE** channel:

### **Report Contents**

```markdown
# 📊 Relatório Diário AgriTech
**Data:** 2026-02-08 02:00

## ✅ Sistema operando perfeitamente

### 🌱 Cultivos Ativos
- Total: 12
- Fase Seedling: 3
- Fase Vegetativa: 6
- Fase Maturidade: 3

### 📈 Alertas (24h)
- **Total:** 2
- Críticos: 0
- Avisos: 1
- Preventivos: 1

### 🔧 Clientes Necessitando Serviço
- ⚠️ **Quinta do João** (Score: 72/100) - Último serviço: 85 dias atrás
- ⚠️ **AgriCoop Lisboa** (Score: 65/100) - Último serviço: 110 dias atrás

### 💰 Receita Potencial
- Calibrações agendadas: 5
- Valor estimado: €250.00

### ⚡ Sistema
- Uptime: 99.8%
- Sensores online: 45/48
- Uso de disco: 62%
```

---

## 🎯 **API Endpoints**

### **Client Management**

```bash
# Add new client
POST /api/clients
{
  "company_name": "Quinta do João",
  "contact_name": "João Silva",
  "contact_phone": "+351912345678",
  "contact_email": "joao@quinta.pt",
  "service_tier": "silver",
  "location": "Évora, Portugal"
}

# List all clients
GET /api/clients
GET /api/clients?active_only=true

# Get client details + health score
GET /api/clients/1

# Update client
PATCH /api/clients/1
{
  "service_tier": "gold",
  "monthly_fee": 499.0
}
```

### **Sensor Management**

```bash
# Register new sensor for client
POST /api/clients/1/sensors
{
  "sensor_type": "temperature",
  "serial_number": "DHT20-00123"
}

# Report sensor drift (auto-called by dual-sensor system)
POST /api/sensors/5/drift
{
  "drift_percent": 3.5,
  "reference_value": 25.0,
  "measured_value": 25.87
}

# Get sensors needing calibration
GET /api/sensors/calibration-due
GET /api/sensors/calibration-due?days=7  # Due within 7 days
```

### **Service Visits**

```bash
# Record service visit
POST /api/clients/1/visits
{
  "technician": "António Técnico",
  "service_type": "calibration",
  "sensors_serviced": [5, 6, 7],
  "issues_found": "Sensor 5 had drift, sensor 7 wiring loose",
  "actions_taken": "Recalibrated all sensors, tightened connections",
  "revenue": 75.0,
  "next_visit_recommended": "2026-05-10"
}

# Get visit history
GET /api/clients/1/visits
GET /api/visits?from=2026-01-01&to=2026-02-01
```

### **Business Intelligence**

```bash
# Get revenue metrics
GET /api/business/metrics
{
  "mrr": 5970.0,
  "service_revenue_30d": 4500.0,
  "total_revenue_30d": 10470.0,
  "scheduled_calibrations": 5,
  "revenue_estimate": 250.0
}

# Get clients needing service
GET /api/business/service-needed
[
  {
    "id": 1,
    "name": "Quinta do João",
    "health_score": 72,
    "days_since_service": 85,
    "unhealthy_sensors": 2
  }
]

# Send test business digest
POST /api/business/test-digest
```

### **Notifications**

```bash
# Send manual alert to client
POST /api/notify/client
{
  "level": "medium",  # optimist, medium, aggressive
  "title": "Temperatura elevada",
  "body": "A temperatura está a subir. Verificar ventilação."
}

# Send business alert (internal)
POST /api/notify/business
{
  "level": "aggressive",
  "title": "Cliente urgente",
  "body": "Quinta do João tem 3 sensores offline há 48h"
}

# Send emergency alert
POST /api/notify/emergency
{
  "title": "Sistema crítico",
  "body": "InfluxDB falhou, backup em execução"
}
```

---

## 🔄 **Dual-Sensor Redundancy System**

### **Concept**

Install **two sensors** (one good, one intentionally degraded) to:
- **Detect drift automatically** by comparing readings
- **Predict failures** before they impact crops
- **Validate calibration** without external references

### **How It Works**

```
Sensor A (Primary)    → 25.5°C
Sensor B (Reference)  → 25.0°C
────────────────────────────────
Difference            = 0.5°C (2% drift)

If drift > 2%: Mark sensor as "degraded", -10 health points
If drift > 5%: Mark sensor as "failing", -20 health points
```

### **Arduino Implementation** (Future)

```cpp
// Read both sensors
float tempA = dhtA.readTemperature();
float tempB = dhtB.readTemperature();

// Calculate drift
float drift = abs((tempA - tempB) / tempB * 100.0);

// Send to API with drift info
POST /api/sensors/drift
{
  "sensor_id": 5,
  "primary_value": 25.5,
  "reference_value": 25.0,
  "drift_percent": 2.0
}
```

---

## 🌱 **Hot-Culture Crop Recommendations**

### **Why Hot Crops?**

If you're using **solar panels** and generating **excess heat**, grow crops that:
- ✅ Thrive in warmer conditions (22-28°C)
- ✅ Have higher market value
- ✅ Offset electrical costs

### **Recommended Crops**

| Crop | Optimal Temp | Market Value | Heat Tolerance | ROI |
|------|--------------|--------------|----------------|-----|
| 🍅 **Tomato** | 22-28°C | High (€3-5/kg) | Excellent | ⭐⭐⭐⭐⭐ |
| 🌶️ **Bell Pepper** | 24-27°C | Very High (€5-8/kg) | Excellent | ⭐⭐⭐⭐⭐ |
| 🥒 **Cucumber** | 22-26°C | Medium (€2-3/kg) | Good | ⭐⭐⭐⭐ |
| 🌿 **Basil** | 20-25°C | High (€8-12/kg) | Good | ⭐⭐⭐⭐ |
| 🥬 **Lettuce (Heat)** | 18-24°C | Medium (€2-4/kg) | Moderate | ⭐⭐⭐ |

### **Energy Economics**

```
Scenario: 50m² greenhouse with solar panels

Electrical heating (no solar): €300/month
With solar (80% offset): €60/month
Heat from crops: -€50/month (passive heat generation)
────────────────────────────────────────────────
Net savings: €240/month (€2,880/year)

Tomato crop value: 50m² × 15kg/m²/cycle × €4/kg × 4 cycles/year = €12,000/year

Total benefit: €14,880/year
```

---

## 📊 **Scalability Roadmap**

### **Phase 1: Single Raspberry Pi** (Current)
- 1-3 clients
- Local SD card storage
- Single location monitoring
- Manual calibration visits

### **Phase 2: Multi-Client** (3-10 clients)
- USB SSD for backups
- Automated daily reports
- Remote sensor monitoring
- Scheduled calibration reminders

### **Phase 3: Server Upgrade** (10-30 clients)
- Dedicated server (mini PC or cloud VPS)
- PostgreSQL database (replace SQLite)
- Load balancer for multiple Raspberry Pi nodes
- Real-time client dashboard
- Mobile app for technicians

### **Phase 4: Enterprise** (30+ clients)
- Quarter-room server rack
- Multi-zone support (different grow rooms per client)
- Kubernetes deployment
- Redundant InfluxDB cluster
- Machine learning for predictive maintenance
- White-label solutions for partners

### **Hardware Requirements (Phase 3)**

```
Mini Server (recommended):
- Intel NUC 11 Pro or equivalent
- 16GB RAM, 500GB SSD
- Cost: €500-800
- Supports 30-50 clients

OR

Cloud VPS:
- Hetzner CPX31 (4 vCPU, 8GB RAM)
- €14/month
- Unlimited clients (within performance limits)
```

---

## 🔐 **Security & Privacy**

### **Client Data Protection**

- ✅ **Database encryption** - SQLite with SQLCipher
- ✅ **API authentication** - Bearer token for all endpoints
- ✅ **Private ntfy channels** - Business data never on public topics
- ✅ **GDPR compliance** - Client data deletion on request
- ✅ **Audit logs** - All service visits recorded

### **Recommended Security Hardening**

```bash
# Enable UFW firewall
sudo ufw enable
sudo ufw allow 3001/tcp  # API only

# Disable unused services
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon

# Auto-update security patches
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

---

## 📞 **Support & Maintenance**

### **Daily Tasks** (Automated)
- ✅ Backup database to USB SSD
- ✅ Send business digest to private channel
- ✅ Check sensor health scores
- ✅ Update calibration due dates

### **Weekly Tasks** (Manual)
- 📋 Review client health scores
- 📞 Call clients with score < 70
- 📅 Schedule calibration visits
- 💰 Generate invoices for service visits

### **Monthly Tasks**
- 📊 Analyze revenue metrics
- 🎯 Identify upsell opportunities (Bronze → Silver)
- 🔧 Review sensor failure patterns
- 📈 Update pricing/tiers based on costs

---

## 🚀 **Next Steps**

1. ✅ **Set up multi-channel ntfy** (this guide)
2. ✅ **Add your first test client** (`POST /api/clients`)
3. ✅ **Configure daily digest** (runs automatically at 2 AM)
4. ✅ **Install dual sensors** (for drift detection)
5. ✅ **Record first service visit** (test revenue tracking)
6. 📱 **Create mobile-friendly dashboard** (future enhancement)
7. 🤝 **Onboard first paying client!**

---

## 📚 **Related Documentation**

- `ALERT_ESCALATION.md` - Smart escalation system details
- `GROWTH_STAGE_SYSTEM.md` - Crop lifecycle management
- `PREVENTIVE_ALERTS.md` - 3-tier warning system
- `VARIETY_CONFIGS.md` - Crop-specific configurations
- `DEPLOYMENT.md` - Raspberry Pi setup guide

---

**Questions? Issues?**

Open an issue on GitHub or contact support.

**Built with ❤️ by AgriTech Team**
