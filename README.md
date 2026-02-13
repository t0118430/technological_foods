# AgriTech NFT Hydroponics Platform

> Smart greenhouse monitoring and automation for NFT hydroponics in the Algarve, Portugal.

## What This Platform Does

This platform monitors and automates an NFT (Nutrient Film Technique) hydroponic greenhouse using Arduino sensors, a Python API server, and a suite of data services. It collects real-time temperature, humidity, pH, EC, water level, and light data — then acts on it: firing alerts, controlling the AC unit, tracking crop lifecycles from seed to harvest, and generating business intelligence.

The system is designed for a single-site pilot but architected for multi-tenant SaaS. A product owner can register crop batches, monitor growth stages, receive escalating notifications when conditions drift out of range, and review weekly and monthly performance reports. Operators see live Grafana dashboards; the API serves everything a future mobile or web app would need.

External data sources (weather, electricity prices, solar data, market prices, tourism indices) are harvested automatically and correlated with indoor conditions. The rule engine is fully configurable at runtime — no Arduino redeployment needed to change thresholds or add new automation logic.

## Architecture

```
  Arduino UNO R4 WiFi          External APIs
  (DHT11, pH, EC, level)       (Open-Meteo, OMIE, PVGIS)
        │                              │
        │ POST /api/data               │ Data Harvester (scheduled)
        ▼                              ▼
  ┌─────────────────────────────────────────┐
  │          API Server (Python :3001)      │
  │                                         │
  │  Rule Engine ─► AC Control (Haier hOn)  │
  │  Crop Manager ─► Growth Stage Tracking  │
  │  Notifications ─► ntfy / WhatsApp / SMS │
  │  Sensor Analytics ─► VPD, DLI, Trends   │
  │  Crop Intelligence ─► Yield Prediction  │
  │  Business Module ─► SaaS Dashboard      │
  └───┬──────────┬─────────────────────────┘
      │          │
      ▼          ▼
  InfluxDB   PostgreSQL
  (hot data) (lifecycle,
   sensors)   BI, audit)
      │          │
      ▼          ▼
   Grafana (15 dashboards, 3 folders)
```

## Key Capabilities

| Capability | Description |
|---|---|
| **Sensor Monitoring** | Real-time temperature, humidity, pH, EC, water level, water temp, light |
| **Alert System** | 4-level escalation (preventive → warning → critical → urgent) with cooldowns |
| **Notification Channels** | Console, ntfy push, WhatsApp, SMS, Email — auto-detected from `.env` |
| **Crop Lifecycle** | Register batches, track 8 growth stages, auto-advance, record harvests |
| **Sensor Analytics** | VPD calculation, DLI tracking, trend detection, anomaly detection |
| **Weather Integration** | Outdoor weather, 3-day forecast, solar data, indoor vs outdoor correlation |
| **Business / SaaS** | Client management, 4 subscription tiers, revenue tracking, site visits |
| **Data Harvester** | Scheduled collection of weather, electricity, solar, market prices, tourism |
| **Rule Engine** | Runtime-configurable rules with Arduino, AC, and notification actions |
| **Dashboards** | 15 Grafana dashboards + 2 HTML backoffice UIs (business, site visits) |
| **Reports & Export** | CSV export, crop lifecycle reports, weekly and monthly summaries |
| **Crop Intelligence** | Condition-to-harvest correlations, yield prediction, health scoring |
| **Hardware Control** | AC via Haier hOn API, Arduino LED/pump commands via polling |
| **ETL Pipeline** | InfluxDB → PostgreSQL aggregation (hourly + daily) with background scheduler |
| **Calibration Tracking** | Record sensor calibrations, track due dates, drift detection |

## Quick Start

**1. Start infrastructure:**
```bash
cd backend
docker-compose up -d
# Starts: InfluxDB (:8086), PostgreSQL (:5432), Grafana (:3000), Node-RED (:1880)
```

**2. Install Python dependencies:**
```bash
cd backend/api
pip install -r requirements.txt
```

**3. Configure environment:**
```bash
cp .env.example .env
# Edit .env with your credentials (InfluxDB, Grafana, Twilio, Haier, SMTP, etc.)
```

**4. Start the API server:**
```bash
python server.py
# Server runs at http://localhost:3001
# Swagger UI at http://localhost:3001/api/docs
```

## API Overview

| Domain | Endpoints | Description |
|---|---|---|
| **Core** | `/api/health`, `/api/data`, `/api/data/latest` | Health check, sensor data ingestion |
| **AC Control** | `/api/ac` | Haier hOn AC status and commands |
| **Rules** | `/api/rules`, `/api/rules/{id}` | CRUD for runtime rule configuration |
| **Commands** | `/api/commands` | Arduino command polling queue |
| **Notifications** | `/api/notifications`, `/api/escalation` | Alert status, history, escalation |
| **Crops** | `/api/crops`, `/api/dashboard`, `/api/harvest` | Lifecycle management and analytics |
| **Calibration** | `/api/calibrations` | Sensor calibration tracking |
| **Analytics** | `/api/analytics/summary`, `vpd`, `dli`, `trends`, `anomalies` | Computed sensor metrics |
| **Weather** | `/api/weather/current`, `forecast`, `solar`, `correlation`, `advisory` | Outdoor conditions |
| **Market** | `/api/market/prices`, `demand` | Produce prices and seasonal demand |
| **Intelligence** | `/api/intelligence/correlations`, `recommendations`, `predict`, `health` | Crop optimization |
| **Export** | `/api/export/sensor-csv`, `crop-report/{id}` | CSV and report downloads |
| **Reports** | `/api/reports/weekly`, `monthly` | Summary reports |
| **Site Visits** | `/api/site-visits`, `dashboard`, `clients`, `export` | Field visit management |
| **Data Harvester** | `/api/harvester/status`, `weather`, `electricity`, `solar`, `market-prices`, `tourism` | External data sources |
| **ETL** | `/api/etl/status`, `run` | Pipeline status and manual trigger |
| **Help** | `/api/help` | Dashboard help content (JSON) |

Full interactive documentation: [Swagger UI](http://localhost:3001/api/docs)

## Documentation

| Category | Path | Audience | Files |
|---|---|---|---|
| **User Guide** | [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) | Product owner, operators | Comprehensive usage guide |
| **Backend README** | [`backend/README.md`](backend/README.md) | Developers | API reference, setup, Arduino integration |
| **Architecture** | [`docs/architecture/`](docs/architecture/) | Technical leads | Database design, microservices, multi-location |
| **DevOps** | [`docs/devops/`](docs/devops/) | DevOps, SRE | Deployment, CI/CD, Raspberry Pi setup |
| **Strategy** | [`docs/strategy/`](docs/strategy/) | Product owner, investors | Vision, grants, prototyping |
| **Planning** | [`docs/planning/`](docs/planning/) | Product owner, team | Backlog, user stories, scalability |
| **Guides** | [`docs/guides/`](docs/guides/) | Operators, developers | User manual, testing, site visits, local markets |
| **GitHub** | [`docs/github/`](docs/github/) | Developers | Issue templates, workflow guides |
| **Backend Docs** | [`backend/docs/`](backend/docs/) | Developers, operators | Alert escalation, growth stages, ETL, SaaS, varieties |
| **Security** | [`SECURITY.md`](SECURITY.md) | All | Security policy |

## Grafana Dashboards

### Production (7)
| Dashboard | Path | Data Source |
|---|---|---|
| Hydroponics Overview | `/d/hydroponics-overview` | InfluxDB |
| Greenhouse Realtime | `/d/greenhouse-realtime` | InfluxDB |
| Crop Lifecycle | `/d/crop-lifecycle` | PostgreSQL |
| Yield & Harvest | `/d/yield-harvest` | PostgreSQL |
| Alerts & Rule Engine | `/d/alerts-rule-engine` | PostgreSQL |
| Environment & Weather | `/d/environment-weather` | InfluxDB |
| Sensor Health | `/d/sensor-health` | Both |

### Business (4)
| Dashboard | Path | Data Source |
|---|---|---|
| SaaS Revenue | `/d/saas-revenue` | PostgreSQL |
| Client Health | `/d/client-health` | PostgreSQL |
| Site Visits | `/d/site-visits` | PostgreSQL |
| Market Intelligence | `/d/market-intelligence` | InfluxDB |

### DevOps (4)
| Dashboard | Path | Data Source |
|---|---|---|
| ETL & Data Pipeline | `/d/etl-pipeline` | PostgreSQL |
| API Performance | `/d/api-performance` | Stub |
| Docker Resources | `/d/docker-resources` | Stub |
| CI/CD Pipeline | `/d/cicd-pipeline` | Stub |

Dashboard JSON files: `grafana/dashboards/{production,business,devops}/`

## Technology Stack

| Layer | Technology |
|---|---|
| **Hardware** | Arduino UNO R4 WiFi, DHT11/DHT20, pH probe, EC meter, water level sensor |
| **API Server** | Python 3.x, built-in `http.server`, no framework |
| **Time-Series DB** | InfluxDB 2.x (sensor data, weather, energy) |
| **Relational DB** | PostgreSQL 15 (7 schemas: core, iot, crop, business, alert, bi, audit) |
| **Cache** | InfluxDB last() queries (sub-second on localhost) |
| **Dashboards** | Grafana (15 provisioned dashboards) |
| **Flow Automation** | Node-RED |
| **Notifications** | ntfy, Twilio (WhatsApp + SMS), SMTP Email |
| **AC Control** | Haier hOn API |
| **External Data** | Open-Meteo, OMIE, PVGIS, manual CSV imports |
| **CI/CD** | GitHub Actions, SonarQube |
| **Infrastructure** | Docker Compose (4 services) |
| **Documentation** | Swagger UI (OpenAPI 3.0) |
