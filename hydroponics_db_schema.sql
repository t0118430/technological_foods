-- ============================================================================
-- HYDROPONICS IOT PLATFORM - DATABASE SCHEMA
-- 30-Metric Optimization Framework with Arduino/MQTT Integration
-- ============================================================================

-- ============================================================================
-- CORE ENTITIES: Organizations, Facilities, Users
-- ============================================================================

CREATE TABLE organizations (
    organization_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subscription_tier VARCHAR(50) NOT NULL CHECK (subscription_tier IN ('STARTER', 'GROWTH', 'ENTERPRISE')),
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED', 'CANCELLED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE facilities (
    facility_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    area_sqm DECIMAL(10,2), -- Square meters of production area
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_facility_name UNIQUE (organization_id, name)
);

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL CHECK (role IN ('ADMIN', 'MANAGER', 'OPERATOR', 'VIEWER')),
    phone VARCHAR(50),
    notification_preferences JSONB, -- Email, SMS, push preferences
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- ============================================================================
-- DEVICE MANAGEMENT: Arduino devices with cellular connectivity
-- ============================================================================

CREATE TABLE devices (
    device_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(facility_id) ON DELETE CASCADE,
    device_code VARCHAR(100) NOT NULL UNIQUE, -- e.g., "arduino-01"
    device_type VARCHAR(50) NOT NULL, -- 'ARDUINO_MKR_NB_1500', 'ESP32_SIM7000', etc.
    firmware_version VARCHAR(50),
    sim_card_number VARCHAR(50),
    cellular_carrier VARCHAR(100),
    mqtt_client_id VARCHAR(255),
    ip_address INET,
    status VARCHAR(20) DEFAULT 'OFFLINE' CHECK (status IN ('ONLINE', 'OFFLINE', 'MAINTENANCE', 'ERROR')),
    last_heartbeat TIMESTAMP,
    last_data_received TIMESTAMP,
    battery_level DECIMAL(5,2), -- Percentage if battery-powered
    signal_strength INTEGER, -- Cellular signal strength
    location_description VARCHAR(255), -- "Greenhouse A, Zone 3"
    installed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE device_health_log (
    log_id BIGSERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    battery_level DECIMAL(5,2),
    signal_strength INTEGER,
    uptime_seconds BIGINT,
    memory_usage_percent DECIMAL(5,2),
    error_message TEXT,
    metadata JSONB
);

-- ============================================================================
-- SENSOR CONFIGURATION: Physical sensors attached to devices
-- ============================================================================

CREATE TABLE sensor_types (
    sensor_type_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE, -- 'DHT22_TEMP_HUMIDITY', 'PH_SENSOR', 'EC_SENSOR', etc.
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    measurement_unit VARCHAR(50), -- '°C', '%', 'ppm', 'mS/cm', etc.
    metric_category VARCHAR(50) NOT NULL CHECK (metric_category IN (
        'ENVIRONMENTAL',
        'WATER_QUALITY',
        'SYSTEM_PERFORMANCE',
        'CROP_PERFORMANCE',
        'ECONOMIC'
    )),
    calibration_required BOOLEAN DEFAULT FALSE,
    calibration_interval_days INTEGER,
    expected_range_min DECIMAL(10,4),
    expected_range_max DECIMAL(10,4),
    description TEXT
);

CREATE TABLE sensors (
    sensor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    sensor_type_id INTEGER NOT NULL REFERENCES sensor_types(sensor_type_id),
    sensor_code VARCHAR(100) NOT NULL, -- e.g., "temp-sensor-01"
    pin_number VARCHAR(20), -- Arduino pin (A0, D2, etc.)
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'CALIBRATING', 'FAULTY')),
    last_calibration_date DATE,
    next_calibration_date DATE,
    installed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_sensor_code UNIQUE (device_id, sensor_code)
);

-- ============================================================================
-- METRIC DEFINITIONS: The 30 metrics from the framework
-- ============================================================================

CREATE TABLE metrics (
    metric_id SERIAL PRIMARY KEY,
    metric_number INTEGER NOT NULL UNIQUE, -- 1-30 from the document
    metric_name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL CHECK (category IN (
        'ENVIRONMENTAL',
        'WATER_QUALITY',
        'SYSTEM_PERFORMANCE',
        'CROP_PERFORMANCE',
        'ECONOMIC'
    )),
    measurement_unit VARCHAR(50),
    optimal_range_min DECIMAL(10,4),
    optimal_range_max DECIMAL(10,4),
    critical_low_threshold DECIMAL(10,4),
    critical_high_threshold DECIMAL(10,4),
    calculation_formula TEXT, -- For calculated metrics (e.g., VPD, economic KPIs)
    related_metrics INTEGER[], -- Array of related metric_ids
    target_improvement_percentage DECIMAL(5,2),
    optimization_strategy TEXT,
    is_automated BOOLEAN DEFAULT FALSE, -- Can be automatically controlled
    is_calculated BOOLEAN DEFAULT FALSE, -- Calculated from other metrics
    description TEXT
);

-- ============================================================================
-- SENSOR READINGS: Time-series data (5-minute snapshots)
-- ============================================================================

CREATE TABLE sensor_readings (
    reading_id BIGSERIAL PRIMARY KEY,
    sensor_id UUID NOT NULL REFERENCES sensors(sensor_id) ON DELETE CASCADE,
    metric_id INTEGER NOT NULL REFERENCES metrics(metric_id),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    value DECIMAL(15,6) NOT NULL,
    unit VARCHAR(50),
    quality_score DECIMAL(3,2), -- 0.00-1.00, confidence in reading accuracy
    is_anomaly BOOLEAN DEFAULT FALSE,
    anomaly_reason TEXT,
    device_timestamp TIMESTAMP, -- Timestamp from Arduino (may differ from server time)
    metadata JSONB -- Additional context (e.g., {"snapshot_id": "xyz", "batch": 123})
);

-- Partition by month for better performance
CREATE INDEX idx_sensor_readings_sensor_time ON sensor_readings(sensor_id, timestamp DESC);
CREATE INDEX idx_sensor_readings_metric_time ON sensor_readings(metric_id, timestamp DESC);
CREATE INDEX idx_sensor_readings_timestamp ON sensor_readings(timestamp DESC);

-- ============================================================================
-- DEVICE SNAPSHOTS: Grouped readings from all sensors on a device
-- ============================================================================

CREATE TABLE device_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    snapshot_data JSONB NOT NULL, -- Complete JSON payload from Arduino
    reading_count INTEGER NOT NULL,
    processing_status VARCHAR(20) DEFAULT 'PENDING' CHECK (processing_status IN ('PENDING', 'PROCESSED', 'FAILED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_device_snapshots_device_time ON device_snapshots(device_id, timestamp DESC);

-- ============================================================================
-- COMMANDS & CONTROL: Bidirectional communication (Arduino ← Cloud)
-- ============================================================================

CREATE TABLE command_types (
    command_type_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE, -- 'AC_ON', 'AC_OFF', 'SET_TARGET_TEMP', etc.
    category VARCHAR(50) NOT NULL CHECK (category IN ('HVAC', 'LIGHTING', 'IRRIGATION', 'NUTRIENT', 'SYSTEM')),
    description TEXT,
    parameters_schema JSONB, -- JSON Schema for command parameters
    requires_confirmation BOOLEAN DEFAULT FALSE
);

CREATE TABLE device_commands (
    command_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    command_type_id INTEGER NOT NULL REFERENCES command_types(command_type_id),
    issued_by UUID REFERENCES users(user_id), -- User or system that issued command
    issued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    mqtt_topic VARCHAR(255), -- Topic where command was published
    command_payload JSONB NOT NULL,
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10), -- 1=highest
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SENT', 'DELIVERED', 'EXECUTED', 'FAILED', 'TIMEOUT')),
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    executed_at TIMESTAMP,
    execution_result JSONB, -- Response from device
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    expires_at TIMESTAMP, -- Command expires if not executed by this time
    metadata JSONB
);

CREATE INDEX idx_device_commands_device_status ON device_commands(device_id, status, issued_at DESC);

-- ============================================================================
-- ACTUATORS: Physical equipment controlled by Arduino
-- ============================================================================

CREATE TABLE actuators (
    actuator_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    actuator_type VARCHAR(50) NOT NULL, -- 'RELAY', 'VALVE', 'MOTOR', 'DIMMER'
    name VARCHAR(255) NOT NULL,
    pin_number VARCHAR(20), -- Arduino pin controlling the actuator
    controls_equipment VARCHAR(100), -- 'AC_UNIT', 'PUMP', 'GROW_LIGHT', 'HEATER', etc.
    current_state VARCHAR(20) DEFAULT 'OFF', -- 'ON', 'OFF', or numeric value for dimmers
    last_state_change TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'FAULTY')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE actuator_state_log (
    log_id BIGSERIAL PRIMARY KEY,
    actuator_id UUID NOT NULL REFERENCES actuators(actuator_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    previous_state VARCHAR(20),
    new_state VARCHAR(20) NOT NULL,
    command_id UUID REFERENCES device_commands(command_id),
    triggered_by VARCHAR(50), -- 'MANUAL', 'AUTOMATED', 'ALERT'
    metadata JSONB
);

-- ============================================================================
-- CROP MANAGEMENT: Growing cycles and crop performance
-- ============================================================================

CREATE TABLE crop_varieties (
    variety_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    scientific_name VARCHAR(255),
    crop_type VARCHAR(100), -- 'LETTUCE', 'TOMATO', 'HERB', etc.
    optimal_vpd_min DECIMAL(4,2),
    optimal_vpd_max DECIMAL(4,2),
    optimal_temp_day DECIMAL(4,1),
    optimal_temp_night DECIMAL(4,1),
    optimal_ph_min DECIMAL(3,1),
    optimal_ph_max DECIMAL(3,1),
    optimal_ec_min DECIMAL(4,2),
    optimal_ec_max DECIMAL(4,2),
    optimal_dli DECIMAL(5,1),
    typical_cycle_days INTEGER,
    expected_yield_kg_per_sqm DECIMAL(6,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE grow_cycles (
    cycle_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(facility_id) ON DELETE CASCADE,
    variety_id UUID NOT NULL REFERENCES crop_varieties(variety_id),
    cycle_name VARCHAR(255),
    start_date DATE NOT NULL,
    expected_harvest_date DATE,
    actual_harvest_date DATE,
    growth_area_sqm DECIMAL(10,2),
    plant_count INTEGER,
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('PLANNING', 'ACTIVE', 'HARVESTED', 'ABORTED')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE crop_performance_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id UUID NOT NULL REFERENCES grow_cycles(cycle_id) ON DELETE CASCADE,
    metric_id INTEGER NOT NULL REFERENCES metrics(metric_id), -- Metrics 20-25
    measurement_date DATE NOT NULL,
    value DECIMAL(15,4) NOT NULL,
    unit VARCHAR(50),
    measured_by UUID REFERENCES users(user_id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- ALERTS & NOTIFICATIONS: Automated monitoring and warnings
-- ============================================================================

CREATE TABLE alert_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID REFERENCES facilities(facility_id) ON DELETE CASCADE,
    metric_id INTEGER NOT NULL REFERENCES metrics(metric_id),
    rule_name VARCHAR(255) NOT NULL,
    condition_type VARCHAR(50) NOT NULL CHECK (condition_type IN (
        'ABOVE_THRESHOLD',
        'BELOW_THRESHOLD',
        'OUT_OF_RANGE',
        'RATE_OF_CHANGE',
        'DEVICE_OFFLINE',
        'SENSOR_FAILURE'
    )),
    threshold_value DECIMAL(15,4),
    threshold_min DECIMAL(15,4),
    threshold_max DECIMAL(15,4),
    duration_minutes INTEGER DEFAULT 0, -- Alert only if condition persists
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL', 'EMERGENCY')),
    auto_command_type_id INTEGER REFERENCES command_types(command_type_id), -- Optional automated response
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID REFERENCES alert_rules(rule_id) ON DELETE SET NULL,
    device_id UUID REFERENCES devices(device_id) ON DELETE CASCADE,
    sensor_id UUID REFERENCES sensors(sensor_id) ON DELETE CASCADE,
    metric_id INTEGER REFERENCES metrics(metric_id),
    triggered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    current_value DECIMAL(15,4),
    threshold_violated DECIMAL(15,4),
    status VARCHAR(20) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'DISMISSED')),
    acknowledged_by UUID REFERENCES users(user_id),
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    automated_action_taken BOOLEAN DEFAULT FALSE,
    command_id UUID REFERENCES device_commands(command_id), -- If auto-command was triggered
    metadata JSONB
);

CREATE INDEX idx_alerts_status_severity ON alerts(status, severity, triggered_at DESC);

-- ============================================================================
-- ECONOMIC TRACKING: Financial metrics (metrics 26-30)
-- ============================================================================

CREATE TABLE resource_costs (
    cost_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(facility_id) ON DELETE CASCADE,
    resource_type VARCHAR(50) NOT NULL CHECK (resource_type IN ('ELECTRICITY', 'WATER', 'NUTRIENTS', 'LABOR', 'OTHER')),
    cost_per_unit DECIMAL(10,4) NOT NULL,
    unit VARCHAR(50) NOT NULL, -- 'kWh', 'L', 'kg', 'hour'
    currency VARCHAR(3) DEFAULT 'USD',
    effective_from DATE NOT NULL,
    effective_to DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE economic_calculations (
    calculation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id UUID NOT NULL REFERENCES grow_cycles(cycle_id) ON DELETE CASCADE,
    metric_id INTEGER NOT NULL REFERENCES metrics(metric_id), -- Metrics 26-30
    calculation_date DATE NOT NULL,
    value DECIMAL(15,4) NOT NULL,
    unit VARCHAR(50),
    calculation_details JSONB, -- Breakdown of how value was calculated
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- AGGREGATED DATA: Pre-calculated statistics for performance
-- ============================================================================

CREATE TABLE hourly_aggregates (
    aggregate_id BIGSERIAL PRIMARY KEY,
    sensor_id UUID NOT NULL REFERENCES sensors(sensor_id) ON DELETE CASCADE,
    metric_id INTEGER NOT NULL REFERENCES metrics(metric_id),
    hour_start TIMESTAMP NOT NULL,
    avg_value DECIMAL(15,6),
    min_value DECIMAL(15,6),
    max_value DECIMAL(15,6),
    stddev_value DECIMAL(15,6),
    reading_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_hourly_aggregate UNIQUE (sensor_id, metric_id, hour_start)
);

CREATE INDEX idx_hourly_aggregates_time ON hourly_aggregates(hour_start DESC);

CREATE TABLE daily_aggregates (
    aggregate_id BIGSERIAL PRIMARY KEY,
    sensor_id UUID NOT NULL REFERENCES sensors(sensor_id) ON DELETE CASCADE,
    metric_id INTEGER NOT NULL REFERENCES metrics(metric_id),
    date DATE NOT NULL,
    avg_value DECIMAL(15,6),
    min_value DECIMAL(15,6),
    max_value DECIMAL(15,6),
    stddev_value DECIMAL(15,6),
    reading_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_daily_aggregate UNIQUE (sensor_id, metric_id, date)
);

CREATE INDEX idx_daily_aggregates_date ON daily_aggregates(date DESC);

-- ============================================================================
-- MQTT INTEGRATION: Message queue tracking
-- ============================================================================

CREATE TABLE mqtt_messages (
    message_id BIGSERIAL PRIMARY KEY,
    device_id UUID REFERENCES devices(device_id) ON DELETE SET NULL,
    topic VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    qos INTEGER DEFAULT 1 CHECK (qos BETWEEN 0 AND 2),
    retained BOOLEAN DEFAULT FALSE,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('INBOUND', 'OUTBOUND')),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    processing_error TEXT
);

CREATE INDEX idx_mqtt_messages_device_time ON mqtt_messages(device_id, timestamp DESC);
CREATE INDEX idx_mqtt_messages_processed ON mqtt_messages(processed) WHERE NOT processed;

-- ============================================================================
-- SYSTEM CONFIGURATION: Platform settings
-- ============================================================================

CREATE TABLE system_config (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES users(user_id)
);

-- ============================================================================
-- AUDIT LOG: Track all important actions
-- ============================================================================

CREATE TABLE audit_log (
    log_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    changes JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_user ON audit_log(user_id, timestamp DESC);

-- ============================================================================
-- VIEWS: Convenient queries for common operations
-- ============================================================================

-- Current device status overview
CREATE VIEW v_device_status AS
SELECT 
    d.device_id,
    d.device_code,
    d.status,
    d.last_heartbeat,
    d.battery_level,
    d.signal_strength,
    f.name as facility_name,
    COUNT(DISTINCT s.sensor_id) as sensor_count,
    COUNT(DISTINCT a.actuator_id) as actuator_count,
    MAX(sr.timestamp) as last_reading_time
FROM devices d
JOIN facilities f ON d.facility_id = f.facility_id
LEFT JOIN sensors s ON d.device_id = s.device_id AND s.status = 'ACTIVE'
LEFT JOIN actuators a ON d.device_id = a.device_id AND a.status = 'ACTIVE'
LEFT JOIN sensor_readings sr ON s.sensor_id = sr.sensor_id
GROUP BY d.device_id, d.device_code, d.status, d.last_heartbeat, 
         d.battery_level, d.signal_strength, f.name;

-- Latest sensor readings per device
CREATE VIEW v_latest_readings AS
SELECT DISTINCT ON (sr.sensor_id)
    sr.sensor_id,
    s.sensor_code,
    st.name as sensor_type,
    m.metric_name,
    sr.value,
    sr.unit,
    sr.timestamp,
    d.device_code,
    d.device_id
FROM sensor_readings sr
JOIN sensors s ON sr.sensor_id = s.sensor_id
JOIN sensor_types st ON s.sensor_type_id = st.sensor_type_id
JOIN metrics m ON sr.metric_id = m.metric_id
JOIN devices d ON s.device_id = d.device_id
ORDER BY sr.sensor_id, sr.timestamp DESC;

-- Active alerts by severity
CREATE VIEW v_active_alerts AS
SELECT 
    a.alert_id,
    a.title,
    a.message,
    a.severity,
    a.triggered_at,
    a.current_value,
    d.device_code,
    f.name as facility_name,
    m.metric_name
FROM alerts a
JOIN devices d ON a.device_id = d.device_id
JOIN facilities f ON d.facility_id = f.facility_id
LEFT JOIN metrics m ON a.metric_id = m.metric_id
WHERE a.status = 'OPEN'
ORDER BY 
    CASE a.severity
        WHEN 'EMERGENCY' THEN 1
        WHEN 'CRITICAL' THEN 2
        WHEN 'WARNING' THEN 3
        WHEN 'INFO' THEN 4
    END,
    a.triggered_at DESC;

-- ============================================================================
-- FUNCTIONS: Utility functions
-- ============================================================================

-- Function to calculate VPD from temperature and humidity
CREATE OR REPLACE FUNCTION calculate_vpd(
    temperature_celsius DECIMAL,
    relative_humidity_percent DECIMAL
) RETURNS DECIMAL AS $$
DECLARE
    svp DECIMAL;
    avp DECIMAL;
    vpd DECIMAL;
BEGIN
    -- Saturated Vapor Pressure (kPa)
    svp := 0.6108 * EXP((17.27 * temperature_celsius) / (temperature_celsius + 237.3));
    -- Actual Vapor Pressure (kPa)
    avp := svp * (relative_humidity_percent / 100.0);
    -- VPD (kPa)
    vpd := svp - avp;
    RETURN vpd;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to check if value is within optimal range for a metric
CREATE OR REPLACE FUNCTION is_value_optimal(
    p_metric_id INTEGER,
    p_value DECIMAL
) RETURNS BOOLEAN AS $$
DECLARE
    v_min DECIMAL;
    v_max DECIMAL;
BEGIN
    SELECT optimal_range_min, optimal_range_max 
    INTO v_min, v_max
    FROM metrics 
    WHERE metric_id = p_metric_id;
    
    IF v_min IS NULL OR v_max IS NULL THEN
        RETURN NULL;
    END IF;
    
    RETURN p_value BETWEEN v_min AND v_max;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS: Automated updates
-- ============================================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_facilities_updated_at BEFORE UPDATE ON facilities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_devices_updated_at BEFORE UPDATE ON devices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_grow_cycles_updated_at BEFORE UPDATE ON grow_cycles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- INITIAL DATA: Core metrics from the 30-metric framework
-- ============================================================================

-- This would be populated with the 30 metrics from your document
-- Example for first few metrics:

INSERT INTO metrics (metric_number, metric_name, category, measurement_unit, 
                    optimal_range_min, optimal_range_max, 
                    target_improvement_percentage, optimization_strategy, is_automated) VALUES
(1, 'Air Temperature', 'ENVIRONMENTAL', '°C', 20, 26, 20.0, 'Maintain species-specific optimal range with day/night differential. Automate HVAC based on growth stage and VPD targets.', TRUE),
(2, 'Relative Humidity', 'ENVIRONMENTAL', '%', 60, 70, 15.0, 'Control RH to achieve optimal VPD. Coordinate dehumidification with air circulation.', TRUE),
(3, 'VPD (Vapor Pressure Deficit)', 'ENVIRONMENTAL', 'kPa', 0.8, 1.2, 20.0, 'Master control variable: optimize VPD for growth stage. Automate temp/humidity adjustments.', TRUE),
(4, 'CO₂ Concentration', 'ENVIRONMENTAL', 'ppm', 1000, 1200, 25.0, 'Enrich to 1000-1200 ppm during photoperiod with adequate ventilation.', TRUE),
(5, 'Light Intensity (PPFD)', 'ENVIRONMENTAL', 'μmol/m²/s', 200, 800, 15.0, 'Provide species-optimal PPFD. Implement sunrise/sunset dimming.', TRUE),
(6, 'Daily Light Integral (DLI)', 'ENVIRONMENTAL', 'mol/m²/day', 12, 20, 15.0, 'Target optimal DLI. Extend/reduce photoperiod vs. intensity based on energy costs.', TRUE),
(7, 'pH Level', 'WATER_QUALITY', 'pH', 5.5, 6.5, 20.0, 'Maintain 5.5-6.5 range for optimal nutrient availability. Auto-dosing with deadband control.', TRUE),
(8, 'EC (Electrical Conductivity)', 'WATER_QUALITY', 'mS/cm', 1.2, 2.4, 20.0, 'Adjust EC by growth stage. Monitor uptake rate to optimize feeding schedule.', TRUE),
(9, 'Water Temperature', 'WATER_QUALITY', '°C', 18, 22, 5.0, 'Maintain 18-22°C to maximize dissolved oxygen and prevent root disease.', TRUE),
(10, 'Dissolved Oxygen', 'WATER_QUALITY', 'mg/L', 6, NULL, 10.0, 'Maintain >6 mg/L through aeration and temperature control.', TRUE);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Additional performance indexes
CREATE INDEX idx_sensor_readings_quality ON sensor_readings(quality_score) WHERE quality_score < 0.8;
CREATE INDEX idx_sensor_readings_anomaly ON sensor_readings(sensor_id, timestamp) WHERE is_anomaly = TRUE;
CREATE INDEX idx_devices_status ON devices(status) WHERE status != 'ONLINE';
CREATE INDEX idx_alerts_open ON alerts(device_id, triggered_at DESC) WHERE status = 'OPEN';
CREATE INDEX idx_commands_pending ON device_commands(device_id, issued_at DESC) WHERE status IN ('PENDING', 'SENT');

-- ============================================================================
-- COMMENTS: Documentation
-- ============================================================================

COMMENT ON TABLE devices IS 'Arduino and other IoT devices with cellular connectivity';
COMMENT ON TABLE sensor_readings IS 'Time-series sensor data - 5 minute snapshots from devices';
COMMENT ON TABLE device_commands IS 'Commands sent to devices (e.g., AC_ON, AC_OFF) via MQTT';
COMMENT ON TABLE metrics IS '30-metric optimization framework for hydroponics';
COMMENT ON COLUMN devices.last_heartbeat IS 'Last time device sent health ping via MQTT';
COMMENT ON COLUMN device_commands.mqtt_topic IS 'MQTT topic where command was published (e.g., devices/arduino-01/commands)';
COMMENT ON COLUMN sensor_readings.quality_score IS 'Confidence in reading accuracy (0.0-1.0)';

-- End of schema
