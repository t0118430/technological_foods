# AgriTech Technological Foods - Deep Analysis & Recommendations Prompt

Paste this into a new Claude Code session from the project root (`C:\git\technological_foods` or `~/dev/technological_foods`).

---

## PROMPT START

I'm working on an AgriTech NFT Hydroponics platform that automates greenhouse operations in the Algarve region (Portugal). I need you to deeply understand every piece of existing logic — how raw sensor data becomes processed intelligence and automated decisions — then identify what's missing and suggest improvements using publicly available data.

### Step 1: Read and understand the full codebase

Read ALL of these files thoroughly. Don't skim — I need you to understand the actual logic, formulas, thresholds, and business rules in each one:

**Core pipeline (data ingestion → processing → actions):**
1. `sessionschat/comprehensive_project_report.txt` — Project overview (start here for context)
2. `backend/api/server.py` — Read the full file. Understand every route handler, especially POST /api/data (the main ingestion hook) and how it fans out to every module
3. `backend/api/rules/rule_engine.py` — Read every rule. What conditions trigger what actions? What thresholds are used? How do rules compose with external data?
4. `backend/api/rules/rules_config.json` — The actual rule definitions

**Sensor intelligence (raw readings → derived metrics):**
5. `backend/api/sensor_analytics.py` — Read the VPD formula, DLI calculation, moving average windows, trend regression, anomaly detection (z-score thresholds, flatline detection, jump detection). Understand every calculation.
6. `backend/api/weather_service.py` — Read the correlation logic between indoor sensors and outdoor weather. How is HVAC load estimated? What advisory rules exist for heat waves, cold snaps, EC adjustments?
7. `backend/api/crop_intelligence.py` — Read the correlation analysis (how does it compare best vs worst batches?), the yield prediction formula, the health score weights. What data does it actually use vs what it could use?
8. `backend/api/sensors/drift_detection_service.py` — How does it detect sensor drift? What's the dual-sensor analysis logic?

**Crop lifecycle (growth tracking → harvest decisions):**
9. `backend/api/crops/growth_stage_manager.py` — Read the stage transition logic. What triggers a stage change? How are optimal conditions per stage defined? What variety-specific rules exist?
10. `backend/api/crops/config_loader.py` — Growth stage configurations and variety parameters
11. `backend/api/db/database.py` — Read the crop_condition_snapshots table and save/get methods. What data is persisted for intelligence?

**External data sources (already integrated):**
12. `backend/api/harvester/weather_source.py` — Open-Meteo integration details
13. `backend/api/harvester/solar_source.py` — Sunrise/sunset and day length
14. `backend/api/harvester/electricity_source.py` — OMIE day-ahead prices + ENTSO-E fallback
15. `backend/api/harvester/market_price_source.py` — Produce price tracking
16. `backend/api/harvester/tourism_source.py` — Seasonal demand multipliers
17. `backend/api/harvester/data_harvester.py` — How all sources are scheduled and orchestrated

**Market and business logic:**
18. `backend/api/market_data_service.py` — Read the hardcoded prices, seasonal multipliers, and demand curves. What assumptions are baked in?
19. `backend/api/data_export.py` — Read the weekly/monthly report generation logic. What metrics are summarized? What recommendations are auto-generated and based on what logic?
20. `backend/api/business/business_dashboard.py` — Revenue analytics and business metrics
21. `backend/api/business/client_manager.py` — Client health scoring and service scheduling

**Notifications and alerting:**
22. `backend/api/notifications/notification_service.py` — Alert formatting, sensor dashboard in notifications, cooldown logic
23. `backend/api/notifications/alert_escalation.py` — Escalation levels and timing
24. `backend/api/notifications/multi_channel_notifier.py` — Business intelligence reporting

**Data layer:**
25. `backend/sql/init.sql` — PostgreSQL schema (all 7 schemas — understand what data is modeled)
26. `backend/.env.example` — All configuration knobs

### Step 2: Document the existing logic in detail

After reading everything, produce a detailed analysis:

**A. Sensor-to-Intelligence Pipeline Map:**
For each sensor (temperature, humidity, pH, EC, water_level, light_level), trace its complete journey:
- Raw value arrives at POST /api/data
- What derived metrics does it feed into? (VPD needs temp+humidity, DLI needs light+time, etc.)
- What rules evaluate it? (list the actual thresholds from rules_config.json)
- What notifications does it trigger? (at what severity levels?)
- What business decisions does it inform? (harvest timing, AC control, client health)
- What reports include it? (weekly summaries, crop lifecycle reports)
- What gets persisted where? (InfluxDB raw, SQLite snapshots, PostgreSQL lifecycle)

**B. Formula and Threshold Audit:**
List every formula, threshold, and magic number in the codebase:
- VPD calculation and optimal ranges per variety
- DLI targets and accumulation method
- Anomaly detection parameters (z-score threshold, flatline count, jump percentage)
- Moving average window sizes and why those were chosen
- Health score weights (temp 25, pH 25, EC 25, humidity 15, VPD 10) — are these optimal?
- Yield prediction adjustment factors (0.7-1.1x) — what's the basis?
- Market seasonal multipliers — are they accurate for Algarve tourism patterns?
- Rule engine thresholds — are they validated against hydroponic research?

**C. Cross-module connections:**
Map which modules feed data to which other modules. Identify:
- Data that's calculated but never used downstream
- Modules that could benefit from each other's output but aren't connected
- Redundant calculations happening in multiple places
- Missing feedback loops (e.g., does harvest outcome feed back into growth optimization?)

### Step 3: Identify what's missing and what's wrong

Be critical. Look for:

**Logic gaps:**
- Sensor combinations we collect but don't correlate (e.g., EC + temperature interaction effects on nutrient uptake)
- Temporal patterns we ignore (day/night cycles, weekly trends, seasonal baselines)
- Growth stage transitions that should consider sensor trends but use only time
- Yield predictions that don't account for all available signals
- Rules that use static thresholds when they should be dynamic (per-variety, per-stage, per-season)

**Accuracy concerns:**
- Are the VPD optimal ranges correct for each variety? (Check against hydroponic literature)
- Are the DLI targets appropriate for Mediterranean greenhouse conditions?
- Are hardcoded market prices realistic for Algarve 2026?
- Do the seasonal demand multipliers match actual Algarve tourism data?
- Are anomaly detection thresholds too sensitive or too loose?

**Missing automations:**
- What decisions still require manual intervention but could be automated?
- What alerts should exist but don't?
- What reports would be valuable but aren't generated?

### Step 4: Suggest improvements using publicly available data

The system already integrates Open-Meteo, OMIE, and sunrise-sunset.org. Suggest NEW public data sources:

Consider these Portuguese and EU sources:
- **IPMA** (Instituto Portugues do Mar e da Atmosfera) — Portuguese meteorology, UV index, fire risk
- **SIMA** (Sistema de Informacao de Mercados Agricolas) — Real Portuguese wholesale produce prices
- **INE** (Instituto Nacional de Estatistica) — Tourism statistics, agricultural production data
- **DGADR** (Direcao-Geral de Agricultura e Desenvolvimento Rural) — Irrigation advisories, pest alerts
- **SNIRH** (Sistema Nacional de Informacao de Recursos Hidricos) — Water quality, reservoir levels
- **Copernicus** — Satellite vegetation indices, soil moisture, land surface temperature
- **ENTSO-E Transparency** — Electricity grid carbon intensity for sustainability reporting
- **APA** (Agencia Portuguesa do Ambiente) — Air quality, environmental alerts
- **FAO AQUASTAT** — Water efficiency benchmarks for hydroponics
- **OpenFoodFacts** — Consumer demand trends for organic/local produce
- **Turismo de Portugal** — Hotel occupancy, tourist arrivals (demand forecasting)

For each suggestion:
1. What specific data it provides (fields, granularity, update frequency)
2. Exactly how it connects to our existing sensor readings or business logic
3. What NEW automated decisions it enables that we can't do today
4. API access details (URL, auth, free tier limits, data format)
5. Which existing module it should integrate with (or new module needed)

### Step 5: Propose prioritized implementation plan

**Tier 1 — Quick wins (use existing data better, no new APIs):**
Things we can do TODAY with data we already have but aren't fully exploiting.
For each: what file to modify, what logic to add, expected outcome.

**Tier 2 — New free API integrations:**
External data that's freely available and would significantly improve decisions.
For each: new source file needed, integration with existing modules, new endpoint.

**Tier 3 — Advanced analytics (needs historical data accumulation):**
Models that need weeks/months of data before they become useful.
For each: what data to start collecting now, what analysis becomes possible, timeline.

### Context: Hardware & Varieties

- **Location**: Algarve, Portugal (37.0194, -7.9304), Mediterranean climate
- **Hardware**: Arduino UNO R4 WiFi + DHT20 sensor, Raspberry Pi 5 server
- **Sensors**: temperature, humidity, pH, EC, water_level, light_level (every 2 seconds)
- **Growing method**: NFT (Nutrient Film Technique) hydroponics, indoor greenhouse
- **Varieties**: rosso_premium (lettuce), curly_green (lettuce), arugula_rocket, basil_genovese, mint_spearmint, tomato_cherry
- **Lifecycle stages**: germination → seedling → transplant → vegetative → flowering* → fruiting* → maturity → harvest_ready
- **Storage**: InfluxDB (real-time) + PostgreSQL (lifecycle/BI, 7 schemas) + Redis (cache) + SQLite (default)
- **Business model**: SaaS for greenhouse operators (Bronze/Silver/Gold tiers)
- **Notifications**: ntfy push, email, SMS, WhatsApp (stubs), 3-tier escalation
- **External data already integrated**: Open-Meteo weather, OMIE electricity, sunrise-sunset.org, manual market prices, manual tourism index

### What I want as output:

1. **Complete pipeline map** — Every sensor value traced from ingestion to final use (decisions, reports, alerts)
2. **Formula audit** — Every calculation, threshold, and magic number listed with assessment of correctness
3. **Cross-module dependency map** — What talks to what, what's disconnected
4. **Gap analysis** — What we're missing, what's wrong, what could be better
5. **10-15 ranked improvement suggestions** with specific Portuguese/EU public data sources
6. **Detailed implementation plan** for the top 5 (exact files, functions, endpoints, logic)

Take your time. Read everything before writing anything. I want depth, not breadth.

## PROMPT END
