# Hydroponics IoT Platform - Database Design Documentation

## Executive Overview

This relational database model integrates the **30-Metric Optimization Framework** with **Arduino-based IoT infrastructure** using cellular connectivity and MQTT bidirectional communication. The design supports:

- Real-time environmental monitoring from Arduino devices
- 5-minute sensor snapshot batching
- Bidirectional MQTT communication (sensor data IN, commands OUT)
- Automated alert generation and command execution
- Complete crop lifecycle tracking
- Economic performance calculations
- Multi-tenant architecture with role-based access

---

## Core Design Principles

### 1. **Time-Series Optimization**
- Sensor readings are the highest-volume table (millions of rows)
- Partitioning strategy by month for `sensor_readings`
- Pre-calculated aggregations (hourly/daily) for dashboard performance
- Indexed on (sensor_id, timestamp) for fast queries

### 2. **Real-Time IoT Integration**
- Device heartbeat tracking (`last_heartbeat`)
- MQTT message logging for debugging
- Command status lifecycle (PENDING → SENT → DELIVERED → EXECUTED)
- Device health monitoring with battery/signal strength

### 3. **Business Intelligence**
- Economic metrics (26-30) calculated from operational data
- Crop performance tied directly to environmental conditions
- ROI tracking per grow cycle
- Cost per kg produced for electricity, water, nutrients

### 4. **Automation & Control**
- Alert rules trigger automated commands
- VPD calculation function for environmental optimization
- Actuator state logging for compliance/audit
- Command retry logic with expiration

---

## Database Architecture

### **Tier 1: Core Business Entities**

```
organizations → facilities → users
```

**Multi-tenant structure:**
- Each organization has multiple facilities
- Users belong to one organization with role-based permissions
- Subscription tiers determine feature access (STARTER, GROWTH, ENTERPRISE)

### **Tier 2: Device Infrastructure**

```
facilities → devices → {sensors, actuators, device_snapshots}
                   ↓
                mqtt_messages
```

**Key Features:**
- `devices` table tracks Arduino units with SIM cards
- Each device has multiple sensors and actuators
- `device_snapshots` stores the complete JSON payload every 5 minutes
- `mqtt_messages` logs all inbound/outbound MQTT traffic

**Critical Fields:**
- `device_code`: Unique identifier (e.g., "arduino-01")
- `mqtt_client_id`: MQTT connection identifier
- `sim_card_number`: Cellular connectivity tracking
- `last_heartbeat`: Device online/offline detection
- `battery_level`: For battery-powered devices

### **Tier 3: Sensor & Metrics Framework**

```
sensor_types → sensors → sensor_readings
                      ↓
                   metrics (30 framework metrics)
```

**The 30 Metrics:**
- **Metrics 1-6**: Environmental Control (temp, humidity, VPD, CO₂, light)
- **Metrics 7-13**: Water Quality & Nutrients (pH, EC, DO, flow rate)
- **Metrics 14-19**: System Performance (energy, water, pump runtime, HVAC)
- **Metrics 20-25**: Crop Performance (growth rate, yield, quality, Brix)
- **Metrics 26-30**: Economic KPIs (cost per kg, revenue per m²)

**Key Relationships:**
- Each sensor is of a specific `sensor_type`
- Each reading is tagged with both `sensor_id` and `metric_id`
- Calculated metrics (e.g., VPD) have `is_calculated = TRUE`
- Automated metrics (e.g., pH dosing) have `is_automated = TRUE`

### **Tier 4: Command & Control**

```
alert_rules → alerts → device_commands → actuator_state_log
                            ↓
                      command_types
```

**Bidirectional Flow:**

**INBOUND (Arduino → Cloud):**
1. Arduino reads sensors
2. Batches data into JSON snapshot
3. Publishes to MQTT topic `sensors/snapshot`
4. Cloud stores in `device_snapshots` and parses into `sensor_readings`
5. Alert rules evaluated against new readings
6. If threshold violated → create `alert`

**OUTBOUND (Cloud → Arduino):**
1. Alert triggers automated response OR user issues manual command
2. Command created in `device_commands` table with status = PENDING
3. Python service publishes to MQTT topic `devices/{device_code}/commands`
4. Arduino subscribes to this topic, receives command
5. Arduino executes command (e.g., turn on AC relay)
6. Updates `actuator_state_log`
7. Sends confirmation back to cloud
8. Command status updated to EXECUTED

**Example Command Payload:**
```json
{
  "command_type": "AC_ON",
  "actuator_id": "ac-relay-01",
  "parameters": {
    "target_temp": 24.0
  },
  "issued_at": "2026-01-28T10:30:00Z"
}
```

### **Tier 5: Crop Management**

```
crop_varieties → grow_cycles → {crop_performance_records, economic_calculations}
```

**Lifecycle Tracking:**
- Each `grow_cycle` represents one planting from seed to harvest
- Performance records (metrics 20-25) manually recorded at intervals
- Economic calculations (metrics 26-30) computed at harvest
- Optimal ranges from `crop_varieties` used for alert rules

**Economic Calculations Example:**
- **Energy Cost per kg** = (Total kWh × cost_per_unit) ÷ harvest_yield
- **Revenue per m² per Year** = (yield × price × cycles) ÷ area_sqm
- Stored in `economic_calculations` with breakdown in JSONB

---

## Key Tables Deep Dive

### **sensor_readings** (Time-Series Core)

**Purpose:** Store every sensor measurement (5-minute intervals)

**Schema Highlights:**
```sql
sensor_id UUID         -- Links to specific sensor
metric_id INTEGER      -- Links to one of 30 metrics
timestamp TIMESTAMP    -- Server receive time
value DECIMAL(15,6)    -- Measurement value
quality_score DECIMAL  -- 0.0-1.0 confidence score
is_anomaly BOOLEAN     -- Flagged by ML/rules
metadata JSONB         -- snapshot_id, calibration info
```

**Volume Estimation:**
- 1 device with 10 sensors
- 5-minute snapshots = 12 readings/hour/sensor
- 10 sensors × 12 × 24 hours = **2,880 readings/day/device**
- 100 devices = **288,000 readings/day**
- 1 year = **105 million rows**

**Optimization:**
- Monthly partitioning
- Aggressive indexing on (sensor_id, timestamp)
- Pre-aggregated hourly/daily tables for dashboards
- Archive old data to cold storage after 90 days

### **device_commands** (Control System)

**Purpose:** Track all commands sent to Arduino devices

**Status Lifecycle:**
```
PENDING → SENT → DELIVERED → EXECUTED
                      ↓
                   FAILED / TIMEOUT
```

**Key Features:**
- `mqtt_topic`: Where command was published
- `expires_at`: Auto-fail if not executed by this time
- `retry_count`: Automatic retry logic for failed commands
- `execution_result`: JSON response from Arduino
- `priority`: 1-10 scale for queue ordering

**Critical for:**
- Audit trails (who turned on AC when?)
- Retry logic for unstable cellular connections
- Performance tracking (command latency)

### **device_snapshots** (Batch Optimization)

**Purpose:** Store the complete JSON payload from Arduino's 5-minute snapshots

**Why Separate from sensor_readings?**
1. **Atomic record** of what device sent
2. **Debugging** - see raw MQTT payload
3. **Replay capability** - reprocess if parsing logic changes
4. **Faster ingestion** - one write instead of 10

**Example Payload:**
```json
{
  "device_id": "arduino-01",
  "timestamp": "2026-01-28T10:30:00Z",
  "temperature": 22.5,
  "humidity": 65.2,
  "ph": 6.1,
  "ec": 1.8,
  "water_temp": 20.1,
  "dissolved_oxygen": 7.2,
  "light_ppfd": 450,
  "co2_ppm": 1100,
  "battery_level": 85.3,
  "signal_strength": -75
}
```

**Processing Flow:**
1. Arduino publishes to MQTT
2. Python service receives, stores in `device_snapshots`
3. Background job parses JSON, creates rows in `sensor_readings`
4. `processing_status` updated to PROCESSED

### **alerts** and **alert_rules**

**alert_rules:** Define conditions that trigger alerts

**Example Rule:**
```sql
rule_name: "High Temperature Alert"
metric_id: 1 (Air Temperature)
condition_type: ABOVE_THRESHOLD
threshold_value: 30.0
duration_minutes: 15  -- Must persist for 15 min
severity: CRITICAL
auto_command_type_id: 2  -- Auto-trigger "AC_ON" command
```

**alerts:** Generated when rules violated

**Workflow:**
1. New sensor reading comes in (temp = 31°C)
2. Alert engine checks all active `alert_rules`
3. Finds temperature rule violated
4. Creates `alert` with status = OPEN
5. If `auto_command_type_id` is set:
   - Creates `device_command` automatically
   - Links command to alert via `command_id`
6. Sends notifications to users based on `notification_preferences`
7. User acknowledges or resolves alert
8. Status changes to ACKNOWLEDGED or RESOLVED

---

## MQTT Integration Architecture

### **Topic Structure**

**Inbound (Arduino → Cloud):**
```
sensors/snapshot                          # All sensor data batched
devices/{device_code}/health              # Heartbeat/status
devices/{device_code}/alerts              # Device-level alerts
devices/{device_code}/ack                 # Command acknowledgments
```

**Outbound (Cloud → Arduino):**
```
devices/{device_code}/commands            # Control commands
devices/{device_code}/config              # Configuration updates
```

### **Message Flow Example**

**Arduino sends snapshot:**
```python
# Arduino publishes (C++)
mqtt.publish("sensors/snapshot", json_payload)

# Python service receives
def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    
    # Store in device_snapshots
    snapshot = DeviceSnapshot(
        device_id=data['device_id'],
        snapshot_data=data,
        reading_count=len(data.keys()) - 2  # Exclude device_id, timestamp
    )
    db.add(snapshot)
    
    # Parse into individual sensor_readings
    for key, value in data.items():
        if key in SENSOR_MAPPINGS:
            reading = SensorReading(
                sensor_id=get_sensor_id(device_id, key),
                metric_id=get_metric_id(key),
                value=value,
                timestamp=data['timestamp']
            )
            db.add(reading)
    
    db.commit()
```

**Cloud sends command:**
```python
# Alert triggers command
if temperature > 30:
    command = DeviceCommand(
        device_id=device_id,
        command_type_id=get_command_type('AC_ON'),
        mqtt_topic=f"devices/{device_code}/commands",
        command_payload={"action": "AC_ON"},
        status='PENDING'
    )
    db.add(command)
    db.commit()
    
    # Publish to MQTT
    mqtt_client.publish(
        f"devices/{device_code}/commands",
        json.dumps({"command_id": command.command_id, "action": "AC_ON"}),
        qos=1,
        retain=False
    )
    
    command.status = 'SENT'
    command.sent_at = datetime.utcnow()
    db.commit()
```

---

## Performance Optimization Strategies

### **1. Partitioning**
```sql
-- Partition sensor_readings by month
CREATE TABLE sensor_readings_2026_01 PARTITION OF sensor_readings
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

### **2. Aggregation Tables**
Pre-calculate for dashboards to avoid scanning millions of rows:

```sql
-- hourly_aggregates example
INSERT INTO hourly_aggregates (sensor_id, metric_id, hour_start, avg_value, ...)
SELECT 
    sensor_id,
    metric_id,
    date_trunc('hour', timestamp) as hour_start,
    AVG(value),
    MIN(value),
    MAX(value),
    STDDEV(value),
    COUNT(*)
FROM sensor_readings
WHERE timestamp >= '2026-01-28 00:00:00'
  AND timestamp < '2026-01-28 01:00:00'
GROUP BY sensor_id, metric_id, hour_start;
```

Run via cron job every hour.

### **3. Materialized Views**
```sql
CREATE MATERIALIZED VIEW mv_device_dashboard AS
SELECT 
    d.device_id,
    d.device_code,
    f.name as facility_name,
    COUNT(DISTINCT s.sensor_id) as sensor_count,
    MAX(sr.timestamp) as last_reading,
    AVG(CASE WHEN m.metric_id = 1 THEN sr.value END) as avg_temperature,
    AVG(CASE WHEN m.metric_id = 2 THEN sr.value END) as avg_humidity
FROM devices d
JOIN sensors s ON d.device_id = s.device_id
JOIN sensor_readings sr ON s.sensor_id = sr.sensor_id
JOIN metrics m ON sr.metric_id = m.metric_id
WHERE sr.timestamp > NOW() - INTERVAL '1 hour'
GROUP BY d.device_id, d.device_code, f.name;

-- Refresh every 5 minutes
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_device_dashboard;
```

### **4. Indexing Strategy**
```sql
-- High-cardinality first
CREATE INDEX idx_sensor_readings_sensor_time 
    ON sensor_readings(sensor_id, timestamp DESC);

-- Partial indexes for common filters
CREATE INDEX idx_alerts_open 
    ON alerts(device_id, triggered_at DESC) 
    WHERE status = 'OPEN';

-- GIN index for JSONB queries
CREATE INDEX idx_device_snapshots_data 
    ON device_snapshots USING GIN(snapshot_data);
```

---

## Query Examples

### **1. Get Latest Reading for Each Sensor on a Device**
```sql
SELECT DISTINCT ON (s.sensor_id)
    s.sensor_code,
    m.metric_name,
    sr.value,
    sr.unit,
    sr.timestamp
FROM sensors s
JOIN sensor_readings sr ON s.sensor_id = sr.sensor_id
JOIN metrics m ON sr.metric_id = m.metric_id
WHERE s.device_id = 'xxx-device-uuid'
ORDER BY s.sensor_id, sr.timestamp DESC;
```

### **2. Find All Devices with Temperature Above Threshold**
```sql
SELECT 
    d.device_code,
    f.name as facility,
    sr.value as temperature,
    sr.timestamp
FROM devices d
JOIN facilities f ON d.facility_id = f.facility_id
JOIN sensors s ON d.device_id = s.device_id
JOIN sensor_readings sr ON s.sensor_id = sr.sensor_id
JOIN metrics m ON sr.metric_id = m.metric_id
WHERE m.metric_name = 'Air Temperature'
  AND sr.value > 30.0
  AND sr.timestamp > NOW() - INTERVAL '15 minutes'
ORDER BY sr.value DESC;
```

### **3. Calculate VPD from Recent Readings**
```sql
WITH latest_readings AS (
    SELECT DISTINCT ON (s.device_id, m.metric_name)
        s.device_id,
        m.metric_name,
        sr.value
    FROM sensors s
    JOIN sensor_readings sr ON s.sensor_id = sr.sensor_id
    JOIN metrics m ON sr.metric_id = m.metric_id
    WHERE m.metric_name IN ('Air Temperature', 'Relative Humidity')
      AND sr.timestamp > NOW() - INTERVAL '10 minutes'
    ORDER BY s.device_id, m.metric_name, sr.timestamp DESC
)
SELECT 
    device_id,
    calculate_vpd(
        MAX(CASE WHEN metric_name = 'Air Temperature' THEN value END),
        MAX(CASE WHEN metric_name = 'Relative Humidity' THEN value END)
    ) as calculated_vpd
FROM latest_readings
GROUP BY device_id;
```

### **4. Pending Commands for a Device**
```sql
SELECT 
    dc.command_id,
    ct.name as command_type,
    dc.issued_at,
    dc.status,
    dc.command_payload,
    u.full_name as issued_by_user
FROM device_commands dc
JOIN command_types ct ON dc.command_type_id = ct.command_type_id
LEFT JOIN users u ON dc.issued_by = u.user_id
WHERE dc.device_id = 'xxx-device-uuid'
  AND dc.status IN ('PENDING', 'SENT')
ORDER BY dc.priority ASC, dc.issued_at ASC;
```

### **5. Economic Performance by Grow Cycle**
```sql
SELECT 
    gc.cycle_name,
    cv.name as crop_variety,
    gc.start_date,
    gc.actual_harvest_date,
    gc.plant_count,
    gc.growth_area_sqm,
    (SELECT value FROM economic_calculations 
     WHERE cycle_id = gc.cycle_id AND metric_id = 21) as harvest_yield_kg,
    (SELECT value FROM economic_calculations 
     WHERE cycle_id = gc.cycle_id AND metric_id = 26) as energy_cost_per_kg,
    (SELECT value FROM economic_calculations 
     WHERE cycle_id = gc.cycle_id AND metric_id = 30) as revenue_per_sqm_per_year
FROM grow_cycles gc
JOIN crop_varieties cv ON gc.variety_id = cv.variety_id
WHERE gc.status = 'HARVESTED'
ORDER BY gc.actual_harvest_date DESC;
```

---

## Security & Access Control

### **Role-Based Permissions**

| Role | Permissions |
|------|-------------|
| **ADMIN** | Full access: manage users, configure devices, view all data |
| **MANAGER** | View all data, issue commands, acknowledge alerts |
| **OPERATOR** | View assigned facilities, respond to alerts, manual data entry |
| **VIEWER** | Read-only access to dashboards and reports |

### **Row-Level Security (PostgreSQL RLS)**
```sql
-- Enable RLS on facilities table
ALTER TABLE facilities ENABLE ROW LEVEL SECURITY;

-- Policy: Users only see facilities from their organization
CREATE POLICY facility_org_policy ON facilities
    FOR ALL
    TO authenticated_user
    USING (organization_id = current_setting('app.current_org_id')::UUID);
```

### **Audit Trail**
All critical actions logged in `audit_log`:
- User logins
- Command issuance
- Configuration changes
- Alert acknowledgments

---

## Scalability Considerations

### **Current Design Supports:**
- **100 facilities**
- **1,000 devices**
- **10,000 sensors**
- **500M+ readings per year**

### **Scaling Strategies:**

**Horizontal Scaling (Sharding):**
```
Shard by facility_id or organization_id
- Shard 1: Facilities A-M
- Shard 2: Facilities N-Z
```

**Vertical Scaling:**
- Time-series database (TimescaleDB, InfluxDB) for `sensor_readings`
- PostgreSQL for relational data
- Redis for device heartbeat cache

**Archival Strategy:**
```sql
-- Move readings older than 90 days to archive table
INSERT INTO sensor_readings_archive
SELECT * FROM sensor_readings
WHERE timestamp < NOW() - INTERVAL '90 days';

DELETE FROM sensor_readings
WHERE timestamp < NOW() - INTERVAL '90 days';
```

---

## Implementation Roadmap

### **Phase 1: Core Infrastructure (Weeks 1-2)**
- Set up PostgreSQL with schema
- Deploy MQTT broker (Mosquitto/HiveMQ)
- Implement device registration API
- Basic sensor reading ingestion

### **Phase 2: Real-Time Monitoring (Weeks 3-4)**
- Alert engine with rule evaluation
- Device command system
- Dashboard with latest readings view
- Actuator control integration

### **Phase 3: Analytics & Optimization (Weeks 5-6)**
- Aggregation jobs (hourly/daily)
- VPD calculation and automated control
- Economic metrics calculation
- Historical trend analysis

### **Phase 4: Advanced Features (Weeks 7-8)**
- ML-based anomaly detection
- Predictive maintenance
- Automated optimization recommendations
- Mobile app integration

---

## Technology Stack Recommendations

### **Database:**
- **PostgreSQL 15+** with TimescaleDB extension for time-series
- Connection pooling via PgBouncer
- Streaming replication for HA

### **MQTT Broker:**
- **Mosquitto** (open-source, lightweight)
- **HiveMQ** (enterprise features, cloud-native)

### **Backend API:**
- **Python FastAPI** for REST API
- **Paho MQTT Client** for message handling
- **SQLAlchemy** ORM with async support
- **Celery** for background jobs (aggregations, alerts)

### **Frontend:**
- **React** with real-time updates via WebSockets
- **Chart.js** or **Recharts** for time-series visualization
- **Mapbox** for facility locations

### **DevOps:**
- **Docker** & **Docker Compose** for local development
- **Kubernetes** for production orchestration
- **GitHub Actions** for CI/CD
- **Prometheus + Grafana** for infrastructure monitoring

---

## Conclusion

This database design provides a **robust, scalable foundation** for the Hydroponics IoT Platform, seamlessly integrating:

✅ **30-metric optimization framework** for data-driven decisions  
✅ **Arduino cellular IoT infrastructure** with 5-minute snapshots  
✅ **Bidirectional MQTT communication** for real-time control  
✅ **Automated alert and command system** for autonomous operation  
✅ **Comprehensive crop and economic tracking** for ROI validation  
✅ **Multi-tenant architecture** with enterprise-grade security  

The schema balances **normalization for data integrity** with **denormalization for performance**, ensuring fast queries on time-series data while maintaining referential integrity across business entities.

---

**Questions or need clarification on any part of the design? Let me know!**
