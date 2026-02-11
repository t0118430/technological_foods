# AgriTech Technological Foods — Deep Codebase Analysis & Prioritized Improvement Plan

> Generated: 2026-02-11 | Based on full reading of 26+ source files
> Location: Algarve, Portugal (37.0194°N, 7.9304°W) | NFT Hydroponics | 6 Varieties

---

## Table of Contents

1. [Sensor-to-Intelligence Pipeline Map](#1-sensor-to-intelligence-pipeline-map)
2. [Formula & Threshold Audit](#2-formula--threshold-audit)
3. [Cross-Module Dependency Map](#3-cross-module-dependency-map)
4. [Gap Analysis](#4-gap-analysis)
5. [Improvement Suggestions (Ranked)](#5-improvement-suggestions-ranked)
6. [Implementation Plans (Top 10)](#6-implementation-plans-top-10)
7. [New Public Data Source Integrations](#7-new-public-data-source-integrations)

---

## 1. Sensor-to-Intelligence Pipeline Map

Every sensor reading arrives via `POST /api/data` in `server.py` and fans out to multiple systems.

### 1.1 Temperature (°C)

| Stage | Where | Details |
|-------|-------|---------|
| **Ingestion** | `server.py` POST /api/data | Written to InfluxDB `sensor_reading`, cached in Redis |
| **Derived Metrics** | `sensor_analytics.py:104-145` | VPD = SVP × (1 − RH/100) where SVP = 0.6108 × e^(17.27T/(T+237.3)) |
| **Moving Averages** | `sensor_analytics.py:318-345` | MA-10, MA-30, MA-60 readings |
| **Trend Detection** | `sensor_analytics.py:349-406` | Linear regression slope → rising/falling/stable |
| **Anomaly Detection** | `sensor_analytics.py:410-484` | Z-score >2.5σ spike, flatline 60+, jump >10% |
| **Rule Evaluation** | `rules_config.json` | `notify_high_temp` >30°C (warning margin 2°C), `notify_low_temp` <15°C (margin 2°C), `ac_cooling` >28°C, `ac_shutoff` <18°C |
| **Escalation** | `alert_escalation.py` | 4-level: Preventive (5min) → Warning (10min) → Critical (15min) → Urgent (15min repeat) |
| **Notifications** | `notification_service.py` | 5 channels (console, ntfy, email, SMS, WhatsApp), 15min cooldown |
| **Weather Correlation** | `weather_service.py:257-327` | Indoor vs outdoor temp differential, HVAC load estimation |
| **Crop Health** | `crop_intelligence.py:356-472` | Temperature = 25/100 points in health score |
| **Reports** | `data_export.py:230-286` | Weekly summary: daily temp averages, recommendations if avg >26°C or <18°C |
| **Storage** | InfluxDB (raw), SQLite/PG (condition snapshots), Redis (latest) |

### 1.2 Humidity (%)

| Stage | Where | Details |
|-------|-------|---------|
| **Ingestion** | `server.py` POST /api/data | InfluxDB + Redis |
| **Derived Metrics** | `sensor_analytics.py:104-145` | VPD calculation (humidity is the RH component) |
| **Anomaly Detection** | `sensor_analytics.py:410-484` | Same z-score/flatline/jump thresholds as temp |
| **Rule Evaluation** | `rules_config.json` | `notify_high_humidity` >80% (margin 5%), `notify_low_humidity` <40% (margin 5%), `led_high_humidity` >60% |
| **Crop Health** | `crop_intelligence.py:403` | Humidity = 15/100 points in health score |
| **Weather Correlation** | `weather_service.py:310-312` | Efficiency = 100 − abs(humidity − 60) × 2 |
| **Drift Detection** | `drift_detection_service.py` | Dual-sensor humidity diff: good ±1%, medium ±2%, cheap ±3% warning |
| **Storage** | InfluxDB, SQLite/PG snapshots, Redis |

### 1.3 pH

| Stage | Where | Details |
|-------|-------|---------|
| **Ingestion** | `server.py` POST /api/data | InfluxDB + Redis |
| **Derived Metrics** | `sensor_analytics.py:233-314` | Nutrient score: pH (0-50 pts) + EC (0-50 pts), optimal 5.8-6.5 |
| **Rule Evaluation** | `rules_config.json` | `notify_high_ph` >7.0 (critical), `notify_low_ph` <5.5 (critical) |
| **Crop Health** | `crop_intelligence.py:403` | pH = 25/100 points in health score |
| **Reports** | `data_export.py:420-426` | Weekly: flags pH range >1.0 as unstable |
| **Gap** | No `warning_margin` on pH rules — no preventive alerts for pH |
| **Storage** | InfluxDB, SQLite/PG snapshots, Redis |

### 1.4 EC (Electrical Conductivity, mS/cm)

| Stage | Where | Details |
|-------|-------|---------|
| **Ingestion** | `server.py` POST /api/data | InfluxDB + Redis |
| **Derived Metrics** | `sensor_analytics.py:233-314` | Nutrient score: EC (0-50 pts), optimal 1.2-2.0, critical 0.8-2.5 |
| **Stage-Specific** | `growth_stage_manager.py:197-278` | EC ranges vary by growth stage (from variety config) |
| **Rule Evaluation** | `rules_config.json` | `notify_high_ec` >2.5 (warning), `notify_low_ec` <0.8 (warning) |
| **Crop Health** | `crop_intelligence.py:403` | EC = 25/100 points in health score |
| **Reports** | `data_export.py:428-431` | Weekly: flags EC trend direction |
| **Gap** | No `warning_margin` on EC rules; EC thresholds are static, not stage-aware in rule engine |
| **Storage** | InfluxDB, SQLite/PG snapshots, Redis |

### 1.5 Water Level (%)

| Stage | Where | Details |
|-------|-------|---------|
| **Ingestion** | `server.py` POST /api/data | InfluxDB + Redis |
| **Rule Evaluation** | `rules_config.json` | `notify_low_water` <20% (critical) |
| **Gap** | No derived metrics, no trend analysis specific to water consumption patterns |
| **Gap** | No correlation with evapotranspiration from weather data |
| **Storage** | InfluxDB, Redis |

### 1.6 Light Level (lux)

| Stage | Where | Details |
|-------|-------|---------|
| **Ingestion** | `server.py` POST /api/data | InfluxDB + Redis |
| **Derived Metrics** | `sensor_analytics.py:149-228` | DLI = Σ(PPFD × interval) / 1,000,000 mol/m²/day. PPFD = lux × 0.0185 |
| **Solar Correlation** | `weather_service.py:188-253` | Supplemental lighting: target 14h photoperiod |
| **DLI Classification** | `sensor_analytics.py:210-219` | very_low <6, low <12, optimal 12-20, high <30, too_high >30 |
| **Gap** | No light-level rules in `rules_config.json` — DLI calculated but no alerts |
| **Gap** | DLI projection assumes 16h photoperiod but solar data uses 14h target |
| **Storage** | InfluxDB, Redis, daily_light in-memory only |

---

## 2. Formula & Threshold Audit

### 2.1 Core Formulas

| # | Formula | Location | Assessment |
|---|---------|----------|------------|
| 1 | **VPD** = 0.6108 × e^(17.27T/(T+237.3)) × (1 − RH/100) | `sensor_analytics.py:120-121` | **Correct** — Standard Tetens formula. Widely used in horticulture. |
| 2 | **DLI** = Σ(avg_PPFD × interval_seconds) / 1,000,000 | `sensor_analytics.py:168-174` | **Correct** — Trapezoidal integration method. |
| 3 | **PPFD** = lux × 0.0185 | `sensor_analytics.py:31` | **Approximate** — 0.0185 valid for sunlight spectrum. LEDs vary: 0.012-0.020 depending on color temp. Should be configurable. |
| 4 | **Nutrient Score** = pH_score(0-50) + EC_score(0-50) | `sensor_analytics.py:288-293` | **Reasonable** but weights arbitrary. No research basis for equal 50/50 split. |
| 5 | **Health Score** = temp(25) + pH(25) + EC(25) + humidity(15) + VPD(10) | `crop_intelligence.py:403` | **Questionable weights** — VPD should arguably be higher (it's the primary transpiration driver). See Section 4.2. |
| 6 | **Yield Prediction** = historical_avg × (0.7 + optimal_pct/100 × 0.4) | `crop_intelligence.py:317` | **Simplistic** — Factor range 0.7-1.1x. Doesn't account for variety, season, stage duration, or batch size. |
| 7 | **Greenhouse Efficiency** = (temp_eff + humidity_eff) / 2 | `weather_service.py:310-312` | **Crude** — Fixed target 22°C/60% not variety-aware. Should use dynamic targets. |
| 8 | **Revenue Risk** = crop_value/day × days_at_risk × loss_factor | `drift_detection_service.py:233-270` | **Hardcoded** — Uses fixed €50/day, 15% degraded, 50% failing. Should use real crop economics. |
| 9 | **Trend Detection** = linear_regression_slope / mean_value | `sensor_analytics.py:386-393` | **Correct method** but relative_slope threshold of 0.001 is untested — may be too sensitive for pH, too loose for temperature. |
| 10 | **Standard Deviation** = sample stddev (n-1 denominator) | `sensor_analytics.py:618-623` | **Correct** — Bessel's correction applied. |
| 11 | **DLI Projection** = current_dli × (16h / hours_elapsed) | `sensor_analytics.py:197` | **Inconsistent** — Uses 16h photoperiod but solar advisory uses 14h target. Should match. |

### 2.2 Magic Numbers & Thresholds

| # | Value | Location | Purpose | Assessment |
|---|-------|----------|---------|------------|
| 1 | `BUFFER_MAX_SIZE = 900` | `sensor_analytics.py:34` | ~30min at 2s interval | **Reasonable** for real-time analytics. |
| 2 | `LUX_TO_PPFD = 0.0185` | `sensor_analytics.py:31` | Lux to µmol/m²/s | **Approximate** — Should be configurable per light source. |
| 3 | Z-score threshold `2.5` | `sensor_analytics.py:446` | Anomaly spike detection | **Standard** — Good default. High severity at 3.5 is also reasonable. |
| 4 | Flatline threshold `60` readings | `sensor_analytics.py:458` | 60 identical = 2 min | **Possibly too sensitive** for water_level (changes slowly). Suggest per-sensor flatline thresholds. |
| 5 | Jump threshold `10%` | `sensor_analytics.py:474` | Sudden change detection | **Possibly too loose** for pH (10% of 6.0 = 0.6 is huge); **too sensitive** for light (10% of 5000 = 500 is normal cloud). |
| 6 | VPD optimal `0.8-1.2 kPa` | `sensor_analytics.py:130-131` | Lettuce VPD range | **Correct for lettuce** but not for all varieties. Basil prefers 0.8-1.4, tomato 0.8-1.6. |
| 7 | DLI optimal `12-20 mol/m²/day` | `sensor_analytics.py:212-213` | Lettuce DLI range | **Correct for lettuce**. Basil needs 14-22, tomato needs 20-30. Variety-specific targets missing. |
| 8 | Target photoperiod `14h` | `weather_service.py:229` | Supplemental lighting calc | **Correct for lettuce**, but tomato needs 12-16h (14 is fine). Not variety-specific. |
| 9 | `COOLDOWN_SECONDS = 900` (15min) | `notification_service.py:12` | Alert spam prevention | **Reasonable** but should be severity-dependent. Critical alerts need shorter cooldown. |
| 10 | Escalation timing `5/10/15/15 min` | `alert_escalation.py:34-69` | Escalation levels | **Well-designed** progressive escalation. |
| 11 | Drift cooldown `6 hours` | `drift_detection_service.py:70` | Drift alert frequency | **Reasonable** for sensor maintenance scheduling. |
| 12 | Worsening threshold `20%` | `drift_detection_service.py:220` | Half-to-half comparison | **Arbitrary** — Needs validation with real drift data. |
| 13 | Seasonal multipliers `0.8-3.0x` | `market_data_service.py:76-89` | Algarve tourism demand | **Approximately correct** — Jul/Aug peak at 3x seems aggressive. Real INE data suggests 2.0-2.5x. |
| 14 | Basil `€20/kg` | `market_data_service.py:50` | Market price | **High** — Wholesale basil in Portugal typically €12-18/kg. Retail could reach €20+. |
| 15 | Temperature rule thresholds `30/15°C` | `rules_config.json:44,62` | Alert triggers | **Generic** — Not variety-specific. Tomato tolerates up to 32°C; lettuce suffers above 27°C. |
| 16 | AC cooling trigger `28°C` | `rules_config.json:8` | AC control | **Reasonable** for lettuce greenhouses. |
| 17 | pH thresholds `5.5/7.0` | `rules_config.json:113,120` | Alert triggers | **Correct** for hydroponic critical limits. Optimal range is narrower (5.8-6.5). |
| 18 | EC thresholds `0.8/2.5` | `rules_config.json:130,139` | Alert triggers | **Static** — Should be stage-dependent. Seedling EC should be 0.5-1.0, maturity 1.5-2.5. |
| 19 | Water level threshold `20%` | `rules_config.json:149` | Low water alert | **Reasonable** for NFT systems. |

---

## 3. Cross-Module Dependency Map

### 3.1 Connected Paths (Working)

```
POST /api/data (server.py)
    ├──> InfluxDB write (raw storage)
    ├──> Redis cache (latest readings)
    ├──> sensor_analytics.ingest_reading()
    │       ├── VPD calculation
    │       ├── DLI accumulation
    │       ├── nutrient_score
    │       └── anomaly detection
    ├──> escalation_manager.should_send_alert()
    │       └── notifier.notify() ──> [console, ntfy, email, SMS, WhatsApp]
    ├──> weather_service (external context building)
    │       └── Used in rule_engine.evaluate(external_data=...)
    ├──> rule_engine.evaluate(sensor_data, external_data)
    │       ├── AC commands ──> Arduino polling queue
    │       ├── LED commands ──> Arduino polling queue
    │       └── Notifications ──> escalation_manager
    └──> growth_stage_manager.check_and_advance_stages() (periodic)

data_harvester (scheduled)
    ├── weather_source (15min) ──> InfluxDB weather_external + weather_forecast
    ├── solar_source (6h) ──> InfluxDB solar_times
    ├── electricity_source (1h) ──> InfluxDB electricity_price (OMIE/ENTSO-E)
    ├── market_price_source (24h) ──> SQLite manual prices
    └── tourism_source (24h) ──> InfluxDB tourism_index

etl_processor (hourly/daily)
    └── InfluxDB ──> PostgreSQL (7 schemas, watermark-based)
```

### 3.2 Underused Connections

| # | Data Available | Where | Not Used By | Impact |
|---|---------------|-------|-------------|--------|
| 1 | **Anomalies** detected | `sensor_analytics.py` | `notification_service.py` | Anomalies are calculated on every reading but **never trigger notifications**. They're returned in the API response but no alert is sent. |
| 2 | **Weather forecast** | `weather_service.py` | `rule_engine.py` | Forecast is fetched but compound rules for weather don't exist in `rules_config.json`. The external_condition mechanism exists but has zero configured rules. |
| 3 | **Electricity prices** | `electricity_source.py` | Any module | Cheapest 6 hours calculated, stored in InfluxDB, but not used for AC scheduling or cost optimization. |
| 4 | **Tourism index** | `tourism_source.py` | `crop_intelligence.py` | Tourism data collected but not fed into yield prediction or harvest timing. |
| 5 | **Drift detection** | `drift_detection_service.py` | `notification_service.py` | Drift alerts are formatted but the integration path to the notification service is manual. |
| 6 | **Stage-specific rules** | `growth_stage_manager.py` | `rule_engine.py` | Stage-specific rules are generated but **never injected** into the active rule engine. They exist as a separate return value. |

### 3.3 Disconnected Feedback Loops

| # | Missing Loop | Impact |
|---|-------------|--------|
| 1 | Harvest outcomes → growth optimization | Crop intelligence analyzes historical data but doesn't feed improvements back into rule thresholds or optimal ranges. Best-batch conditions should auto-tune targets. |
| 2 | Anomaly patterns → rule adjustment | Recurring anomalies (same sensor, same time) don't trigger rule threshold updates. |
| 3 | DLI shortfall → supplemental lighting action | DLI is tracked and classified but doesn't trigger automated LED rules. |
| 4 | Weather advisory → automated rule activation | Heat wave/cold snap advisories exist but don't dynamically activate/modify rules. |
| 5 | Market demand → planting recommendations | Seasonal multipliers exist but don't feed into automated batch creation suggestions. |

---

## 4. Gap Analysis

### 4.1 Logic Gaps

| # | Gap | Severity | Details |
|---|-----|----------|---------|
| **G1** | Anomalies never trigger alerts | **HIGH** | `sensor_analytics.detect_anomalies()` returns anomalies on every reading, but `server.py` doesn't forward them to `notification_service.notify()`. A sensor could flatline for 2+ minutes with zero alerts. |
| **G2** | No variety-specific VPD/DLI targets | **HIGH** | VPD optimal is hardcoded `0.8-1.2 kPa` (lettuce) for ALL varieties. Basil, mint, and tomato have different optimal ranges. Same for DLI `12-20 mol/m²/day`. |
| **G3** | EC thresholds are static, not stage-aware | **HIGH** | Rule engine uses fixed `0.8-2.5 mS/cm` but seedlings need 0.5-1.0 and mature plants need 1.5-2.5. `growth_stage_manager` generates stage-specific rules but they're never loaded into the rule engine. |
| **G4** | No compound weather rules configured | **MEDIUM** | `rule_engine.py` supports `external_condition` AND gates but zero rules in `rules_config.json` use this feature. Weather data is collected but not used in rule evaluation. |
| **G5** | Electricity prices not used for AC scheduling | **MEDIUM** | OMIE day-ahead prices are fetched hourly but AC cooling trigger (`>28°C`) is pure temperature-based. Could pre-cool during cheap hours, reduce during expensive hours. |
| **G6** | No EC × temperature interaction model | **MEDIUM** | EC and temperature are evaluated independently, but nutrient uptake efficiency changes with temperature. At >30°C, plants need lower EC. This interaction is not modeled. |
| **G7** | Jump detection threshold not per-sensor | **MEDIUM** | 10% jump threshold is universal. For pH (range 5-7), 10% = 0.6 which is a huge change. For light (range 0-10000), 10% = 1000 which is a normal cloud event. |
| **G8** | DLI photoperiod inconsistency | **LOW** | DLI projection uses 16h (`sensor_analytics.py:197`), solar advisory uses 14h (`weather_service.py:229`). Should be unified from variety config. |
| **G9** | Water consumption patterns not analyzed | **LOW** | Water level is tracked but no consumption rate calculation, no correlation with evapotranspiration from weather data, no refill prediction. |
| **G10** | Harvest outcome doesn't auto-tune targets | **LOW** | Best-performing batch conditions are analyzed (`crop_intelligence.py:43-132`) but insights aren't used to update optimal ranges or rule thresholds. |

### 4.2 Accuracy Concerns

| # | Concern | Details | Recommendation |
|---|---------|---------|----------------|
| **A1** | VPD ranges per variety | All varieties use lettuce optimal (0.8-1.2). Research suggests: Basil 0.8-1.4, Tomato 0.8-1.6, Mint 0.6-1.0, Arugula 0.8-1.3 | Add VPD ranges to variety configs |
| **A2** | DLI targets per variety | All use 12-20. Research: Basil 14-22, Tomato 20-30, Mint 10-16, Arugula 12-18, Lettuce 12-17 | Add DLI ranges to variety configs |
| **A3** | Health score weights | VPD gets only 10/100 despite being primary transpiration indicator. Research suggests VPD should be 20-25pts, reducing temp to 15-20pts (VPD already incorporates temp+humidity) | Rebalance weights |
| **A4** | Seasonal demand multipliers | Jul/Aug at 3.0x may be aggressive. INE data shows Algarve hotel stays peak at ~2.5x winter levels. Restaurant demand may be higher. | Validate with SIMA/INE data |
| **A5** | Market prices | Basil at €20/kg is retail-level. Wholesale in Portugal is €12-18/kg depending on quality and certification | Connect to SIMA wholesale prices |
| **A6** | LUX_TO_PPFD conversion | Fixed at 0.0185 (sunlight). LED grow lights use 0.012-0.020 depending on spectrum | Make configurable per light source |

### 4.3 Missing Automations

| # | Automation | What It Would Do |
|---|-----------|-----------------|
| **M1** | Anomaly → notification pipeline | Auto-alert on sensor spikes, flatlines, and sudden jumps (currently detected but silently logged) |
| **M2** | Weather-triggered rule modification | Auto-adjust AC thresholds and ventilation based on heat wave/cold snap forecasts |
| **M3** | DLI shortfall → LED automation | When projected DLI is below target, auto-trigger supplemental LED rules |
| **M4** | Electricity price → AC optimization | Schedule pre-cooling during cheap OMIE hours, reduce AC during expensive hours |
| **M5** | Auto planting recommendations | Based on seasonal demand + current crop inventory + growth cycle timing, suggest what/when to plant |

---

## 5. Improvement Suggestions (Ranked)

### Tier 1 — Quick Wins (No New APIs, Use Existing Data Better)

| Priority | Improvement | Effort | Impact | Files to Modify |
|----------|------------|--------|--------|----------------|
| **P1** | Wire anomaly detection → notifications | ~2h | **Critical** — Anomalies are detected but never alerted | `server.py` |
| **P2** | Add variety-specific VPD/DLI targets | ~3h | **High** — All varieties use lettuce defaults | `sensor_analytics.py`, variety configs |
| **P3** | Inject stage-specific rules into rule engine | ~2h | **High** — Stage rules exist but aren't loaded | `server.py`, `growth_stage_manager.py` |
| **P4** | Add warning_margin to pH and EC rules | ~30min | **Medium** — pH/EC have no preventive alerts | `rules_config.json` |
| **P5** | Per-sensor anomaly thresholds | ~2h | **Medium** — 10% jump is wrong for pH vs light | `sensor_analytics.py` |
| **P6** | Fix DLI photoperiod inconsistency | ~30min | **Low** — 16h vs 14h mismatch | `sensor_analytics.py`, `weather_service.py` |

### Tier 2 — New Integrations (Free APIs)

| Priority | Improvement | Effort | Impact | New Module Needed |
|----------|------------|--------|--------|------------------|
| **P7** | IPMA integration (Portuguese meteo, UV index) | ~6h | **High** — Better local data than Open-Meteo | `harvester/ipma_source.py` |
| **P8** | SIMA integration (real wholesale prices) | ~6h | **High** — Replace hardcoded market prices | `harvester/sima_source.py` |
| **P9** | Electricity price → AC scheduling | ~4h | **Medium** — Cost savings on HVAC | `sensors/ac_controller.py` modification |
| **P10** | Add compound weather rules | ~3h | **Medium** — Use existing external_condition feature | `rules_config.json`, `server.py` |
| **P11** | INE tourism data integration | ~4h | **Medium** — Real demand forecasting | `harvester/ine_source.py` |

### Tier 3 — Advanced Analytics (Need Historical Data)

| Priority | Improvement | Effort | Impact | Timeline |
|----------|------------|--------|--------|----------|
| **P12** | Dynamic EC × temperature model | ~6h | **High** — Nutrient uptake optimization | Start collecting interaction data now, model in 4-6 weeks |
| **P13** | Harvest feedback → auto-tuning | ~8h | **High** — Self-improving system | Needs 5+ harvests per variety |
| **P14** | Water consumption prediction | ~4h | **Medium** — Refill scheduling | Needs 2+ weeks of water level + weather data |
| **P15** | Seasonal baseline models | ~8h | **Medium** — Anomaly detection improvement | Needs 1+ year of data for seasonal patterns |

---

## 6. Implementation Plans (Top 10)

### P1: Wire Anomaly Detection → Notification System

**Problem:** `sensor_analytics.detect_anomalies()` runs on every reading and returns anomalies, but `server.py` never sends them to the notification system. A sensor could flatline for 2+ minutes with zero alerts.

**File:** `backend/api/server.py` — in the POST /api/data handler

**Logic to add:**
```python
# After: analytics_result = sensor_analytics.ingest_reading(data, sensor_id)
anomalies = analytics_result.get('anomalies', [])
for anomaly in anomalies:
    severity = anomaly.get('severity', 'medium')
    field = anomaly.get('field', 'unknown')
    anomaly_type = anomaly.get('type', 'unknown')

    # Map anomaly severity to notification severity
    notify_severity = 'critical' if severity == 'high' else 'warning'

    # Build descriptive message
    if anomaly_type == 'spike':
        msg = f"Sensor spike: {field} = {anomaly['value']} (z-score {anomaly['z_score']}, mean {anomaly['mean']})"
    elif anomaly_type == 'flatline':
        msg = f"Sensor flatline: {field} unchanged at {anomaly['value']} for {anomaly['consecutive_identical']}+ readings"
    elif anomaly_type == 'sudden_jump':
        msg = f"Sudden jump: {field} changed {anomaly['percent_change']:.1f}% ({anomaly['previous']} → {anomaly['value']})"
    else:
        msg = f"Anomaly: {anomaly_type} on {field}"

    # Use anomaly-specific rule_id to respect cooldown per anomaly type+field
    rule_id = f"anomaly_{anomaly_type}_{field}"
    notifier.notify(rule_id, notify_severity, msg, sensor_data=data)
```

**Effort:** ~2 hours | **Risk:** Low (additive change, won't break existing alerts)

---

### P2: Variety-Specific VPD and DLI Targets

**Problem:** `sensor_analytics.py` hardcodes VPD optimal as `0.8-1.2 kPa` and DLI as `12-20 mol/m²/day` for all varieties. This is only correct for lettuce.

**Files to modify:**
- `backend/api/crops/config/variety_*.json` — Add VPD and DLI ranges per variety
- `sensor_analytics.py` — Accept variety parameter in VPD and DLI methods

**Research-based targets:**

| Variety | VPD Range (kPa) | DLI Range (mol/m²/day) | Photoperiod (h) |
|---------|-----------------|----------------------|-----------------|
| rosso_premium | 0.8-1.2 | 12-17 | 14-16 |
| curly_green | 0.8-1.2 | 12-17 | 14-16 |
| arugula_rocket | 0.8-1.3 | 12-18 | 12-14 |
| basil_genovese | 0.8-1.4 | 14-22 | 14-16 |
| mint_spearmint | 0.6-1.0 | 10-16 | 14-16 |
| tomato_cherry | 0.8-1.6 | 20-30 | 12-16 |

**Changes to `sensor_analytics.py:calculate_vpd()`:**
```python
@staticmethod
def calculate_vpd(temp, humidity, variety=None):
    # ... existing VPD calculation ...

    # Variety-specific optimal ranges
    VPD_RANGES = {
        'rosso_premium':  (0.8, 1.2),
        'curly_green':    (0.8, 1.2),
        'arugula_rocket': (0.8, 1.3),
        'basil_genovese': (0.8, 1.4),
        'mint_spearmint':  (0.6, 1.0),
        'tomato_cherry':  (0.8, 1.6),
    }
    opt_min, opt_max = VPD_RANGES.get(variety, (0.8, 1.2))
    # Use opt_min/opt_max for classification instead of hardcoded values
```

**Effort:** ~3 hours | **Risk:** Low (backward-compatible with default values)

---

### P3: Inject Stage-Specific Rules into Rule Engine

**Problem:** `growth_stage_manager.get_stage_specific_rules()` generates variety+stage-aware EC rules, but they're never loaded into the active rule engine. The rule engine only sees the static `rules_config.json` rules.

**File:** `backend/api/server.py` — in the POST /api/data handler

**Logic:**
```python
# After rule_engine.evaluate(), also check stage-specific rules
for crop in growth_manager.db.get_active_crops():
    stage_rules = growth_manager.get_stage_specific_rules(crop['id'])
    for rule in stage_rules:
        # Evaluate each stage rule against current sensor data
        # Use rule_engine._check_condition logic but with stage thresholds
        sensor_key = rule['sensor']
        if sensor_key in data:
            value = float(data[sensor_key])
            threshold = float(rule['threshold'])
            condition = rule['condition']

            fired = (condition == 'above' and value > threshold) or \
                    (condition == 'below' and value < threshold)

            if fired:
                action = rule['action']
                if action.get('type') == 'notify':
                    notifier.notify(
                        rule['id'], action.get('severity', 'warning'),
                        action.get('message', ''), sensor_data=data,
                        recommended_action=action.get('recommended_action', '')
                    )
```

**Better approach:** Register stage rules as temporary rules in the rule engine (re-generated when crop advances stage).

**Effort:** ~2 hours | **Risk:** Medium (could cause duplicate alerts if not deduped with base rules)

---

### P4: Add Warning Margins to pH and EC Rules

**Problem:** pH and EC rules have no `warning_margin` — they go straight from "OK" to "CRITICAL" with no preventive alert.

**File:** `backend/api/rules/rules_config.json`

**Changes:**
```json
{
    "id": "notify_high_ph",
    "warning_margin": 0.3,
    "preventive_message": "pH rising toward alkaline threshold",
    "preventive_action": "Monitor pH buffer. Prepare pH down solution."
},
{
    "id": "notify_low_ph",
    "warning_margin": 0.3,
    "preventive_message": "pH dropping toward acidic threshold",
    "preventive_action": "Monitor pH buffer. Prepare pH up solution."
},
{
    "id": "notify_high_ec",
    "warning_margin": 0.3,
    "preventive_message": "EC rising toward maximum threshold",
    "preventive_action": "Prepare fresh water for dilution. Check nutrient dosing system."
},
{
    "id": "notify_low_ec",
    "warning_margin": 0.2,
    "preventive_message": "EC dropping below effective nutrient level",
    "preventive_action": "Prepare nutrient concentrate. Check for leaks or over-dilution."
}
```

**Effort:** ~30 minutes | **Risk:** None (additive, backward-compatible)

---

### P5: Per-Sensor Anomaly Detection Thresholds

**Problem:** The 10% jump detection threshold is universal but wrong for different sensors. pH jumping 10% (0.6 units) is catastrophic, while light jumping 10% (500 lux) is a normal cloud event.

**File:** `backend/api/sensor_analytics.py`

**Changes:**
```python
# Replace hardcoded thresholds with per-sensor configuration
ANOMALY_CONFIG = {
    'temperature': {'z_score': 2.5, 'flatline': 60, 'jump_pct': 10},
    'humidity':    {'z_score': 2.5, 'flatline': 60, 'jump_pct': 15},
    'ph':          {'z_score': 2.0, 'flatline': 120, 'jump_pct': 3},   # pH is very stable
    'ec':          {'z_score': 2.5, 'flatline': 120, 'jump_pct': 8},
    'water_level': {'z_score': 2.5, 'flatline': 300, 'jump_pct': 20},  # Changes slowly
    'light_level': {'z_score': 3.0, 'flatline': 60, 'jump_pct': 50},   # Very variable
}
```

**Rationale:**
- **pH**: Z-score 2.0 (more sensitive), flatline 120 (pH probes drift slowly), jump 3% (0.18 units is significant)
- **Water level**: Flatline 300 (10 min at 2s — water level changes very slowly), jump 20%
- **Light**: Z-score 3.0 (less sensitive to natural variation), jump 50% (clouds cause huge swings)

**Effort:** ~2 hours | **Risk:** Low

---

### P6: Fix DLI Photoperiod Inconsistency

**Problem:** `sensor_analytics.py:197` uses 16h photoperiod for DLI projection, but `weather_service.py:229` uses 14h for supplemental lighting calculation.

**Files:** `sensor_analytics.py`, `weather_service.py`

**Fix:** Both should read from a shared config, ideally variety-specific:
```python
# In sensor_analytics.py:197
# Change: projected_dli = round(current_dli * (16.0 / hours_elapsed), 2)
# To:     projected_dli = round(current_dli * (target_photoperiod / hours_elapsed), 2)
# Where target_photoperiod comes from variety config (default 14)
```

**Effort:** ~30 minutes | **Risk:** None

---

### P7: IPMA Integration (Portuguese Meteorological Institute)

**Problem:** Open-Meteo is good but IPMA provides Portuguese-specific data: UV index, fire risk warnings, and official Portuguese weather alerts that affect agricultural operations.

**New file:** `backend/api/harvester/ipma_source.py`

**API details:**
- **URL:** `https://api.ipma.pt/open-data/`
- **Auth:** None (free, public)
- **Rate limit:** Reasonable use
- **Data:**
  - Current weather by station (JSON): `https://api.ipma.pt/open-data/observation/meteorology/stations/observations.json`
  - Forecast by district (JSON): `https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/{district_id}.json`
  - UV index: `https://api.ipma.pt/open-data/forecast/meteorology/uv/uv.json`
  - Fire risk: `https://api.ipma.pt/open-data/forecast/meteorology/fire-risk/rcm-d0.json`
  - Weather warnings: `https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json`

**Integration points:**
- UV index → supplemental shading decisions (UV >8 → activate shade cloth)
- Fire risk → emergency ventilation protocols, water conservation
- Weather warnings → proactive greenhouse preparation
- IPMA temperature → cross-validate Open-Meteo data

**Effort:** ~6 hours | **Risk:** Low (additive, new harvester following existing pattern)

---

### P8: SIMA Integration (Portuguese Wholesale Market Prices)

**Problem:** Market prices are hardcoded (e.g., basil €20/kg, tomato €5/kg). SIMA provides real weekly wholesale prices from Portuguese agricultural markets.

**New file:** `backend/api/harvester/sima_source.py`

**API details:**
- **URL:** `https://www.gpp.pt/sima/` (data downloads)
- **Auth:** None (public data)
- **Data:** Weekly wholesale prices for fruits, vegetables, herbs from major Portuguese markets (Lisbon, Porto, Faro)
- **Format:** CSV/Excel downloads
- **Update frequency:** Weekly

**Integration:**
```python
class SIMASource(BaseHarvestSource):
    SCHEDULE_SECONDS = 86400  # Daily check (weekly data)

    def harvest(self):
        # Fetch latest SIMA weekly bulletin
        # Parse CSV for our product categories
        # Update market_data_service prices
        # Compare with our hardcoded prices
        # Generate alert if market price changed >15%
```

**Impact:** Replace guessed prices with real Portuguese market data, improving revenue estimates and harvest timing.

**Effort:** ~6 hours | **Risk:** Low (SIMA data format may change, need scraping resilience)

---

### P9: Electricity Price → AC Scheduling

**Problem:** OMIE day-ahead electricity prices are already fetched and stored in InfluxDB, but AC control is purely temperature-based (>28°C cool, <18°C off). During expensive hours, we could pre-cool or tolerate slightly higher temperatures.

**File to modify:** `backend/api/server.py` (AC control logic)

**Logic:**
```python
# In POST /api/data handler, before AC trigger:
cheapest_hours = electricity_data.get('cheapest_hours', [])
current_hour = datetime.now().hour
current_price = electricity_data.get('current_price_eur_mwh', 50)

# Dynamic AC threshold based on electricity cost
if current_hour in cheapest_hours:
    # Cheap electricity: pre-cool aggressively
    ac_threshold = 26.0  # Lower threshold, cool more
elif current_price > 100:  # Expensive hour (>100 EUR/MWh)
    # Expensive: tolerate slightly higher temp
    ac_threshold = 30.0  # Higher threshold, cool less
else:
    ac_threshold = 28.0  # Default
```

**Expected saving:** 10-20% on electricity costs during summer (high AC usage coincides with peak electricity prices).

**Effort:** ~4 hours | **Risk:** Medium (must ensure crop temperature never exceeds safe limits)

---

### P10: Add Compound Weather Rules

**Problem:** The rule engine supports `external_condition` AND gates but no rules are configured to use this feature. Weather data is available in the evaluation context.

**File:** `backend/api/rules/rules_config.json`

**New rules to add:**
```json
{
    "id": "ac_cooling_heatwave",
    "name": "Pre-cool: Heat Wave Forecast",
    "enabled": true,
    "sensor": "temperature",
    "condition": "above",
    "threshold": 25.0,
    "external_condition": {
        "source_field": "weather.forecast_max_temp",
        "condition": "above",
        "threshold": 35
    },
    "action": {
        "type": "ac",
        "command": "cool",
        "target_temp": 22
    }
},
{
    "id": "notify_ec_adjust_heat",
    "name": "Lower EC for Hot Weather",
    "enabled": true,
    "sensor": "ec",
    "condition": "above",
    "threshold": 1.8,
    "external_condition": {
        "source_field": "weather.temperature",
        "condition": "above",
        "threshold": 32
    },
    "action": {
        "type": "notify",
        "severity": "warning",
        "message": "Hot weather + high EC: reduce nutrients 10-15% to prevent plant stress",
        "recommended_action": "Dilute nutrient solution with fresh water. Target EC 1.4-1.6 during heat."
    }
}
```

**Also requires:** Populating `external_data` in `server.py` with weather forecast data (partially done, needs forecast_max_temp added).

**Effort:** ~3 hours | **Risk:** Low (rules are additive, won't affect existing behavior)

---

## 7. New Public Data Source Integrations

### 7.1 Portuguese Government APIs

| Source | Data | Update Freq | Free? | Integration Module |
|--------|------|------------|-------|-------------------|
| **IPMA** (api.ipma.pt) | UV index, fire risk, weather warnings, station data | 1-6h | Yes | `harvester/ipma_source.py` |
| **SIMA** (gpp.pt/sima) | Wholesale produce prices from Portuguese markets | Weekly | Yes | `harvester/sima_source.py` |
| **INE** (ine.pt) | Tourism statistics, hotel occupancy, arrivals | Monthly | Yes | `harvester/ine_source.py` |
| **SNIRH** (snirh.apambiente.pt) | Water quality, reservoir levels (Algarve) | Daily | Yes | `harvester/water_quality_source.py` |
| **APA** (qualar.apambiente.pt) | Air quality index, environmental alerts | Hourly | Yes | `harvester/air_quality_source.py` |
| **DGADR** | Irrigation advisories, pest alerts (Algarve region) | Weekly | Yes | `harvester/dgadr_source.py` |

### 7.2 European/International APIs

| Source | Data | Update Freq | Free? | Integration Module |
|--------|------|------------|-------|-------------------|
| **ENTSO-E Transparency** | Grid carbon intensity (gCO2/kWh) | Hourly | Yes (API key) | Extend `electricity_source.py` |
| **Copernicus Climate** (cds.climate.copernicus.eu) | Satellite vegetation indices, soil moisture | Daily | Yes (API key) | `harvester/copernicus_source.py` |
| **FAO AQUASTAT** | Water efficiency benchmarks for hydroponics | Static | Yes | Reference data in config |

### 7.3 Detailed Integration: IPMA (Highest Priority New API)

**Why:** IPMA is Portugal's official meteorological institute. It provides data Open-Meteo doesn't:
- Official Portuguese weather warnings (relevant for greenhouse operations)
- UV index forecasts (for shade cloth decisions)
- Fire risk index (important for Algarve summer — affects water availability)
- Station-level observations (more accurate than global models)

**Implementation:**
```python
# backend/api/harvester/ipma_source.py
class IPMASource(BaseHarvestSource):
    """IPMA - Portuguese Meteorological Institute"""

    SCHEDULE_SECONDS = 3600  # Hourly

    # Faro district ID = 8
    DISTRICT_ID = 8

    ENDPOINTS = {
        'observations': 'https://api.ipma.pt/open-data/observation/meteorology/stations/observations.json',
        'forecast': f'https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/{DISTRICT_ID}.json',
        'uv': 'https://api.ipma.pt/open-data/forecast/meteorology/uv/uv.json',
        'fire_risk': 'https://api.ipma.pt/open-data/forecast/meteorology/fire-risk/rcm-d0.json',
        'warnings': 'https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json',
    }

    def harvest(self):
        results = {}
        for key, url in self.ENDPOINTS.items():
            data = self._fetch_json(url)
            if data:
                results[key] = data
                self._write_to_influxdb(key, data)
        return results
```

**New automated decisions enabled:**
1. UV >8 → Auto-activate shade cloth (new rule)
2. Fire risk "very high" → Alert operator, conserve water, reduce ventilation
3. Weather warning "red" → Emergency greenhouse lockdown protocol
4. IPMA temp vs Open-Meteo → Cross-validation, alert on large discrepancies

---

## Summary Dashboard

### Quick Reference: All Priorities

| ID | Improvement | Tier | Effort | Impact | Status |
|----|------------|------|--------|--------|--------|
| P1 | Anomaly → notification pipeline | T1 | 2h | Critical | Not started |
| P2 | Variety-specific VPD/DLI targets | T1 | 3h | High | Not started |
| P3 | Stage-specific rules injection | T1 | 2h | High | Not started |
| P4 | Warning margins for pH/EC rules | T1 | 30min | Medium | Not started |
| P5 | Per-sensor anomaly thresholds | T1 | 2h | Medium | Not started |
| P6 | Fix DLI photoperiod inconsistency | T1 | 30min | Low | Not started |
| P7 | IPMA integration | T2 | 6h | High | Not started |
| P8 | SIMA wholesale prices | T2 | 6h | High | Not started |
| P9 | Electricity → AC scheduling | T2 | 4h | Medium | Not started |
| P10 | Compound weather rules | T2 | 3h | Medium | Not started |
| P11 | INE tourism data | T2 | 4h | Medium | Not started |
| P12 | Dynamic EC × temp model | T3 | 6h | High | Needs data |
| P13 | Harvest feedback auto-tuning | T3 | 8h | High | Needs harvests |
| P14 | Water consumption prediction | T3 | 4h | Medium | Needs data |
| P15 | Seasonal baseline models | T3 | 8h | Medium | Needs 1yr data |

**Total estimated effort:** ~54 hours across all tiers
- Tier 1 (quick wins): ~10 hours
- Tier 2 (new APIs): ~23 hours
- Tier 3 (advanced): ~26 hours (plus data collection time)

### Recommended Implementation Order

**Sprint 1 (Week 1): Foundation Fixes**
1. P4 — Warning margins for pH/EC (30min)
2. P6 — Fix DLI photoperiod (30min)
3. P1 — Anomaly → notifications (2h)
4. P5 — Per-sensor anomaly thresholds (2h)

**Sprint 2 (Week 2): Variety Intelligence**
5. P2 — Variety-specific VPD/DLI (3h)
6. P3 — Stage-specific rules (2h)
7. P10 — Compound weather rules (3h)

**Sprint 3 (Week 3-4): External Data**
8. P7 — IPMA integration (6h)
9. P8 — SIMA wholesale prices (6h)
10. P9 — Electricity AC scheduling (4h)

**Sprint 4 (Week 5+): Advanced Analytics**
11. P12 — EC × temperature model (6h)
12. P13 — Harvest feedback auto-tuning (8h)

---

*End of deep analysis. This document should be treated as a living reference — update status column as improvements are implemented.*
