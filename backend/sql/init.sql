-- ============================================================================
-- AGRITECH HYDROPONICS - PROFESSIONAL DATA ARCHITECTURE
-- Nursery-to-Harvest Tracking + Business Intelligence
-- 7 Schemas | ~35 Tables | Partitioned BI Layer
-- ============================================================================

-- ============================================================================
-- SCHEMA CREATION
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS core;      -- Organizations, facilities, users, zones
CREATE SCHEMA IF NOT EXISTS iot;       -- Devices, sensors, calibrations, commands
CREATE SCHEMA IF NOT EXISTS crop;      -- Varieties, batches, growth stages, harvests
CREATE SCHEMA IF NOT EXISTS business;  -- Clients, subscriptions, payments, leads
CREATE SCHEMA IF NOT EXISTS alert;     -- Rules, alerts, escalations, notifications
CREATE SCHEMA IF NOT EXISTS bi;        -- Aggregated metrics, materialized views
CREATE SCHEMA IF NOT EXISTS audit;     -- Event log, data retention tracking

-- ============================================================================
-- UTILITY: updated_at trigger function
-- ============================================================================
CREATE OR REPLACE FUNCTION core.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CORE SCHEMA: Organizations, Facilities, Users, Zones
-- ============================================================================

CREATE TABLE core.organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    subscription_tier VARCHAR(50) NOT NULL DEFAULT 'bronze'
        CHECK (subscription_tier IN ('bronze', 'silver', 'gold', 'platinum')),
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active', 'suspended', 'cancelled')),
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_organizations_updated
    BEFORE UPDATE ON core.organizations
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at();

CREATE TABLE core.facilities (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    area_sqm DECIMAL(10,2),
    timezone VARCHAR(50) DEFAULT 'Europe/Lisbon',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, name)
);

CREATE TRIGGER trg_facilities_updated
    BEFORE UPDATE ON core.facilities
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at();

CREATE TABLE core.users (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'operator'
        CHECK (role IN ('admin', 'manager', 'operator', 'viewer')),
    phone VARCHAR(50),
    notification_preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

CREATE TABLE core.zones (
    id SERIAL PRIMARY KEY,
    facility_id INTEGER NOT NULL REFERENCES core.facilities(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    zone_type VARCHAR(50),                -- nft_channel, dwc_tank, soil_bed, nursery_tray
    area_sqm DECIMAL(8,2),
    max_plant_count INTEGER,
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'maintenance')),
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(facility_id, name)
);

CREATE TRIGGER trg_zones_updated
    BEFORE UPDATE ON core.zones
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at();

CREATE TABLE core.system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- IOT SCHEMA: Devices, Sensors, Calibrations, Commands
-- ============================================================================

CREATE TABLE iot.devices (
    id SERIAL PRIMARY KEY,
    facility_id INTEGER NOT NULL REFERENCES core.facilities(id) ON DELETE CASCADE,
    device_code VARCHAR(100) NOT NULL UNIQUE,
    device_type VARCHAR(50) NOT NULL,     -- arduino_mkr_nb_1500, esp32_sim7000
    firmware_version VARCHAR(50),
    mqtt_client_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'offline'
        CHECK (status IN ('online', 'offline', 'maintenance', 'error')),
    last_heartbeat TIMESTAMPTZ,
    last_data_received TIMESTAMPTZ,
    battery_level DECIMAL(5,2),
    signal_strength INTEGER,
    location_description VARCHAR(255),
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_devices_updated
    BEFORE UPDATE ON iot.devices
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at();

CREATE TABLE iot.sensor_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    measurement_unit VARCHAR(50),
    metric_category VARCHAR(50) NOT NULL
        CHECK (metric_category IN ('environmental', 'water_quality', 'system_performance', 'crop_performance', 'economic')),
    calibration_required BOOLEAN DEFAULT FALSE,
    calibration_interval_days INTEGER,
    expected_range_min DECIMAL(10,4),
    expected_range_max DECIMAL(10,4),
    description TEXT
);

CREATE TABLE iot.sensors (
    id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL REFERENCES iot.devices(id) ON DELETE CASCADE,
    sensor_type_id INTEGER NOT NULL REFERENCES iot.sensor_types(id),
    sensor_code VARCHAR(100) NOT NULL,
    pin_number VARCHAR(20),
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'calibrating', 'faulty')),
    last_calibration_date DATE,
    next_calibration_date DATE,
    installed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id, sensor_code)
);

CREATE TABLE iot.calibrations (
    id SERIAL PRIMARY KEY,
    sensor_id INTEGER NOT NULL REFERENCES iot.sensors(id) ON DELETE CASCADE,
    calibration_date TIMESTAMPTZ NOT NULL,
    next_due_date DATE,
    performed_by VARCHAR(100),
    reference_values JSONB,               -- buffer solutions used, standard values
    pre_calibration_offset DECIMAL(10,4),
    post_calibration_offset DECIMAL(10,4),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE iot.command_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL
        CHECK (category IN ('hvac', 'lighting', 'irrigation', 'nutrient', 'system')),
    description TEXT,
    parameters_schema JSONB
);

CREATE TABLE iot.device_commands (
    id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL REFERENCES iot.devices(id) ON DELETE CASCADE,
    command_type_id INTEGER NOT NULL REFERENCES iot.command_types(id),
    issued_by INTEGER REFERENCES core.users(id),
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    command_payload JSONB NOT NULL,
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'sent', 'delivered', 'executed', 'failed', 'timeout')),
    executed_at TIMESTAMPTZ,
    execution_result JSONB,
    error_message TEXT,
    expires_at TIMESTAMPTZ
);

CREATE INDEX idx_device_commands_pending ON iot.device_commands(device_id, issued_at DESC)
    WHERE status IN ('pending', 'sent');

CREATE TABLE iot.actuators (
    id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL REFERENCES iot.devices(id) ON DELETE CASCADE,
    actuator_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    pin_number VARCHAR(20),
    controls_equipment VARCHAR(100),
    current_state VARCHAR(20) DEFAULT 'off',
    last_state_change TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'faulty')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- CROP SCHEMA: Varieties, Batches, Growth Stages, Harvests
-- ============================================================================

CREATE TABLE crop.varieties (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,           -- rosso_premium, basil_genovese
    name VARCHAR(100) NOT NULL,                 -- Rosso Premium
    category VARCHAR(50) NOT NULL,              -- lettuce, herb, fruit, microgreen
    scientific_name VARCHAR(100),
    difficulty VARCHAR(20),                     -- easy, medium, hard
    market_position VARCHAR(20),                -- standard, premium, specialty
    typical_cycle_days INTEGER,
    yield_kg_per_sqm DECIMAL(6,2),
    config_json JSONB,                          -- Full variety config from JSON files
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE crop.growth_stage_definitions (
    id SERIAL PRIMARY KEY,
    variety_id INTEGER NOT NULL REFERENCES crop.varieties(id) ON DELETE CASCADE,
    stage_order INTEGER NOT NULL,
    stage_name VARCHAR(50) NOT NULL,            -- germination, seedling, transplant, vegetative, flowering, fruiting, maturity, harvest_ready
    min_days INTEGER,
    max_days INTEGER,
    optimal_temp_min DECIMAL(4,1),
    optimal_temp_max DECIMAL(4,1),
    optimal_humidity_min DECIMAL(4,1),
    optimal_humidity_max DECIMAL(4,1),
    optimal_ph_min DECIMAL(3,1),
    optimal_ph_max DECIMAL(3,1),
    optimal_ec_min DECIMAL(4,2),
    optimal_ec_max DECIMAL(4,2),
    light_hours INTEGER,
    nutrient_formula JSONB,
    notes TEXT,
    UNIQUE(variety_id, stage_order),
    UNIQUE(variety_id, stage_name)
);

CREATE TABLE crop.batches (
    id SERIAL PRIMARY KEY,
    batch_code VARCHAR(50) UNIQUE NOT NULL,     -- RP-2026-02-001
    variety_id INTEGER NOT NULL REFERENCES crop.varieties(id),
    zone_id INTEGER REFERENCES core.zones(id),
    client_id INTEGER,                          -- FK added after business.clients created
    plant_date DATE NOT NULL,
    expected_harvest_date DATE,
    actual_harvest_date DATE,
    plant_count INTEGER,
    seed_lot VARCHAR(100),
    nursery_zone_id INTEGER REFERENCES core.zones(id),
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active', 'harvested', 'failed', 'aborted')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_batches_updated
    BEFORE UPDATE ON crop.batches
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at();

CREATE INDEX idx_batches_status ON crop.batches(status);
CREATE INDEX idx_batches_variety ON crop.batches(variety_id);
CREATE INDEX idx_batches_zone ON crop.batches(zone_id);

CREATE TABLE crop.batch_stages (
    id SERIAL PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES crop.batches(id) ON DELETE CASCADE,
    stage_def_id INTEGER NOT NULL REFERENCES crop.growth_stage_definitions(id),
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,                       -- NULL = current stage
    auto_advanced BOOLEAN DEFAULT FALSE,
    conditions_score DECIMAL(5,2),              -- % time in optimal range
    notes TEXT
);

CREATE INDEX idx_batch_stages_active ON crop.batch_stages(batch_id) WHERE ended_at IS NULL;
CREATE INDEX idx_batch_stages_batch ON crop.batch_stages(batch_id, started_at);

CREATE TABLE crop.harvests (
    id SERIAL PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES crop.batches(id) ON DELETE CASCADE,
    harvest_date DATE NOT NULL,
    weight_kg DECIMAL(8,3),
    plant_count_harvested INTEGER,
    quality_grade VARCHAR(20),                  -- premium, standard, low, reject
    market_price_per_kg DECIMAL(8,2),
    total_revenue DECIMAL(10,2),
    destination VARCHAR(100),
    harvested_by VARCHAR(100),
    photos_url TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_harvests_batch ON crop.harvests(batch_id);
CREATE INDEX idx_harvests_date ON crop.harvests(harvest_date DESC);

CREATE TABLE crop.nutrient_solutions (
    id SERIAL PRIMARY KEY,
    zone_id INTEGER REFERENCES core.zones(id),
    measured_at TIMESTAMPTZ NOT NULL,
    ph DECIMAL(4,2),
    ec DECIMAL(5,3),
    water_temp DECIMAL(4,1),
    nutrient_a_ml DECIMAL(8,2),
    nutrient_b_ml DECIMAL(8,2),
    ph_up_ml DECIMAL(8,2),
    ph_down_ml DECIMAL(8,2),
    water_added_liters DECIMAL(8,2),
    notes TEXT
);

CREATE INDEX idx_nutrient_solutions_zone ON crop.nutrient_solutions(zone_id, measured_at DESC);

CREATE TABLE crop.zone_sensor_assignments (
    id SERIAL PRIMARY KEY,
    zone_id INTEGER NOT NULL REFERENCES core.zones(id),
    sensor_id INTEGER NOT NULL REFERENCES iot.sensors(id),
    assigned_from TIMESTAMPTZ NOT NULL,
    assigned_until TIMESTAMPTZ,                 -- NULL = currently assigned
    UNIQUE(zone_id, sensor_id, assigned_from)
);

CREATE INDEX idx_zone_sensor_active ON crop.zone_sensor_assignments(zone_id)
    WHERE assigned_until IS NULL;

-- ============================================================================
-- BUSINESS SCHEMA: Clients, Subscriptions, Payments, Leads
-- ============================================================================

CREATE TABLE business.clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    address TEXT,
    subscription_tier VARCHAR(50) DEFAULT 'bronze'
        CHECK (subscription_tier IN ('bronze', 'silver', 'gold', 'platinum')),
    subscription_start_date DATE NOT NULL,
    subscription_end_date DATE,
    auto_renew BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active', 'suspended', 'cancelled', 'lead')),
    total_revenue DECIMAL(12,2) DEFAULT 0,
    health_score INTEGER DEFAULT 100 CHECK (health_score BETWEEN 0 AND 100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_clients_updated
    BEFORE UPDATE ON business.clients
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at();

CREATE INDEX idx_clients_tier ON business.clients(subscription_tier);
CREATE INDEX idx_clients_status ON business.clients(status);

-- Add FK from crop.batches to business.clients
ALTER TABLE crop.batches
    ADD CONSTRAINT fk_batches_client
    FOREIGN KEY (client_id) REFERENCES business.clients(id);

CREATE TABLE business.site_visits (
    id SERIAL PRIMARY KEY,
    visit_date DATE NOT NULL DEFAULT CURRENT_DATE,
    inspector_name VARCHAR(255) NOT NULL,
    client_id INTEGER REFERENCES business.clients(id),
    facility_name VARCHAR(255),
    visit_type VARCHAR(20) NOT NULL CHECK (visit_type IN ('routine','emergency','follow_up','audit')),
    zones_inspected JSONB DEFAULT '[]',
    crop_batches_checked JSONB DEFAULT '[]',
    sensor_readings_snapshot JSONB DEFAULT '{}',
    observations TEXT,
    issues_found JSONB DEFAULT '[]',
    actions_taken TEXT,
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_date DATE,
    follow_up_notes TEXT,
    follow_up_completed BOOLEAN DEFAULT FALSE,
    overall_rating INTEGER DEFAULT 3 CHECK (overall_rating BETWEEN 1 AND 5),
    photo_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_site_visits_updated
    BEFORE UPDATE ON business.site_visits
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at();

CREATE INDEX idx_biz_site_visits_date ON business.site_visits(visit_date);
CREATE INDEX idx_biz_site_visits_client ON business.site_visits(client_id);
CREATE INDEX idx_biz_site_visits_type ON business.site_visits(visit_type);
CREATE INDEX idx_biz_site_visits_followup ON business.site_visits(follow_up_required, follow_up_completed);

CREATE TABLE business.client_sensors (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES business.clients(id) ON DELETE CASCADE,
    sensor_type VARCHAR(100) NOT NULL,
    sensor_model VARCHAR(100),
    serial_number VARCHAR(100),
    installation_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    last_calibration DATE,
    next_calibration_due DATE,
    notes TEXT
);

CREATE INDEX idx_client_sensors_client ON business.client_sensors(client_id);

CREATE TABLE business.payments (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES business.clients(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    payment_date DATE NOT NULL,
    payment_method VARCHAR(50),
    tier VARCHAR(50) NOT NULL,
    period_start DATE,
    period_end DATE,
    status VARCHAR(20) DEFAULT 'completed'
        CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payments_client ON business.payments(client_id);
CREATE INDEX idx_payments_date ON business.payments(payment_date DESC);

CREATE TABLE business.sensor_recommendations (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES business.clients(id) ON DELETE CASCADE,
    sensor_type VARCHAR(100) NOT NULL,
    recommended_date DATE NOT NULL,
    reason TEXT,
    expected_improvement TEXT,
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'accepted', 'declined', 'expired')),
    responded_date DATE,
    response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE business.feature_usage (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES business.clients(id) ON DELETE CASCADE,
    feature_name VARCHAR(100) NOT NULL,
    usage_date DATE NOT NULL,
    usage_count INTEGER DEFAULT 1,
    metadata JSONB
);

CREATE INDEX idx_feature_usage_client ON business.feature_usage(client_id, usage_date DESC);

CREATE TABLE business.support_tickets (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES business.clients(id) ON DELETE CASCADE,
    severity VARCHAR(20) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'open'
        CHECK (status IN ('open', 'in_progress', 'waiting', 'resolved', 'closed')),
    assigned_to VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    response_time_hours DECIMAL(8,2)
);

CREATE INDEX idx_support_tickets_client ON business.support_tickets(client_id);
CREATE INDEX idx_support_tickets_status ON business.support_tickets(status)
    WHERE status NOT IN ('resolved', 'closed');

-- ============================================================================
-- ALERT SCHEMA: Rules, Alerts, Escalations, Notifications
-- ============================================================================

CREATE TABLE alert.rules (
    id SERIAL PRIMARY KEY,
    facility_id INTEGER REFERENCES core.facilities(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    sensor_type VARCHAR(100),
    condition_type VARCHAR(50) NOT NULL
        CHECK (condition_type IN ('above', 'below', 'out_of_range', 'rate_of_change', 'device_offline')),
    threshold DECIMAL(15,4),
    threshold_min DECIMAL(15,4),
    threshold_max DECIMAL(15,4),
    warning_margin DECIMAL(10,4),
    duration_minutes INTEGER DEFAULT 0,
    severity VARCHAR(20) NOT NULL DEFAULT 'warning'
        CHECK (severity IN ('info', 'warning', 'critical', 'emergency')),
    auto_command_type_id INTEGER REFERENCES iot.command_types(id),
    is_active BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_alert_rules_updated
    BEFORE UPDATE ON alert.rules
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at();

CREATE TABLE alert.alerts (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER REFERENCES alert.rules(id) ON DELETE SET NULL,
    device_id INTEGER REFERENCES iot.devices(id) ON DELETE CASCADE,
    sensor_id INTEGER REFERENCES iot.sensors(id) ON DELETE CASCADE,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    current_value DECIMAL(15,4),
    threshold_violated DECIMAL(15,4),
    status VARCHAR(20) DEFAULT 'open'
        CHECK (status IN ('open', 'acknowledged', 'resolved', 'dismissed')),
    acknowledged_by INTEGER REFERENCES core.users(id),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    escalation_level INTEGER DEFAULT 0,
    metadata JSONB
);

CREATE INDEX idx_alerts_status ON alert.alerts(status, severity, triggered_at DESC);
CREATE INDEX idx_alerts_open ON alert.alerts(device_id, triggered_at DESC) WHERE status = 'open';

CREATE TABLE alert.escalations (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER NOT NULL REFERENCES alert.alerts(id) ON DELETE CASCADE,
    escalation_level INTEGER NOT NULL,
    escalated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    escalated_to VARCHAR(255),            -- user email or group
    method VARCHAR(50),                   -- email, sms, whatsapp, phone_call
    message TEXT,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ
);

CREATE TABLE alert.notification_log (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES business.clients(id),
    alert_id INTEGER REFERENCES alert.alerts(id),
    notification_type VARCHAR(50) NOT NULL,
    channel VARCHAR(50) NOT NULL,         -- email, sms, whatsapp, ntfy, console
    subject VARCHAR(255),
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    delivered BOOLEAN,
    tier_restricted BOOLEAN DEFAULT FALSE,
    metadata JSONB
);

CREATE INDEX idx_notification_log_client ON alert.notification_log(client_id, sent_at DESC);

-- ============================================================================
-- BI SCHEMA: Aggregated Metrics, Pre-calculated Tables
-- ============================================================================

CREATE TABLE bi.batch_performance (
    id SERIAL PRIMARY KEY,
    batch_id INTEGER UNIQUE REFERENCES crop.batches(id),
    batch_code VARCHAR(50),
    variety_code VARCHAR(50),
    variety_category VARCHAR(50),
    client_id INTEGER,
    zone_name VARCHAR(100),
    plant_date DATE,
    harvest_date DATE,
    cycle_days INTEGER,
    total_yield_kg DECIMAL(8,3),
    yield_per_plant_kg DECIMAL(6,4),
    yield_per_sqm_kg DECIMAL(6,3),
    quality_grade VARCHAR(20),
    revenue DECIMAL(10,2),
    cost_estimate DECIMAL(10,2),
    profit_margin DECIMAL(5,2),
    avg_temp DECIMAL(4,1),
    avg_humidity DECIMAL(4,1),
    avg_ph DECIMAL(3,1),
    avg_ec DECIMAL(4,2),
    conditions_score DECIMAL(5,2),        -- % time in optimal conditions
    computed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Partitioned daily sensor aggregates (partitioned by month)
CREATE TABLE bi.daily_sensor_agg (
    id BIGSERIAL,
    sensor_id INTEGER NOT NULL,
    zone_id INTEGER,
    metric_date DATE NOT NULL,
    avg_value DECIMAL(10,4),
    min_value DECIMAL(10,4),
    max_value DECIMAL(10,4),
    stddev_value DECIMAL(10,4),
    reading_count INTEGER,
    time_in_optimal_pct DECIMAL(5,2),
    time_in_critical_pct DECIMAL(5,2),
    PRIMARY KEY (id, metric_date)
) PARTITION BY RANGE (metric_date);

-- Create partitions for current year and next year
CREATE TABLE bi.daily_sensor_agg_2025 PARTITION OF bi.daily_sensor_agg
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE bi.daily_sensor_agg_2026 PARTITION OF bi.daily_sensor_agg
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
CREATE TABLE bi.daily_sensor_agg_2027 PARTITION OF bi.daily_sensor_agg
    FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');

CREATE INDEX idx_daily_sensor_agg_sensor ON bi.daily_sensor_agg(sensor_id, metric_date DESC);
CREATE INDEX idx_daily_sensor_agg_zone ON bi.daily_sensor_agg(zone_id, metric_date DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_daily_sensor_metric
    ON bi.daily_sensor_agg (sensor_id, metric_date);

-- Hourly sensor aggregates (non-partitioned, rolls off after 90 days)
CREATE TABLE bi.hourly_sensor_agg (
    id BIGSERIAL PRIMARY KEY,
    sensor_id INTEGER NOT NULL,
    zone_id INTEGER,
    hour_start TIMESTAMPTZ NOT NULL,
    avg_value DECIMAL(10,4),
    min_value DECIMAL(10,4),
    max_value DECIMAL(10,4),
    stddev_value DECIMAL(10,4),
    reading_count INTEGER,
    UNIQUE(sensor_id, hour_start)
);

CREATE INDEX idx_hourly_sensor_agg_time ON bi.hourly_sensor_agg(hour_start DESC);

CREATE TABLE bi.monthly_revenue (
    id SERIAL PRIMARY KEY,
    month DATE NOT NULL,                  -- first of month
    client_id INTEGER,
    subscription_revenue DECIMAL(10,2),
    service_revenue DECIMAL(10,2),
    harvest_revenue DECIMAL(10,2),
    total_revenue DECIMAL(10,2),
    active_batches INTEGER,
    total_yield_kg DECIMAL(10,3),
    avg_yield_per_sqm DECIMAL(6,3),
    UNIQUE(month, client_id)
);

-- ============================================================================
-- AUDIT SCHEMA: Event Log, Data Retention
-- ============================================================================

CREATE TABLE audit.events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) DEFAULT 'info',
    entity_type VARCHAR(50),
    entity_id INTEGER,
    user_id INTEGER REFERENCES core.users(id),
    message TEXT,
    data JSONB,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_events_type ON audit.events(event_type, created_at DESC);
CREATE INDEX idx_audit_events_entity ON audit.events(entity_type, entity_id);

CREATE TABLE audit.data_retention (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    retention_days INTEGER NOT NULL,
    last_purge_at TIMESTAMPTZ,
    rows_purged BIGINT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- VIEWS: Convenient queries
-- ============================================================================

-- Active batches with current stage
CREATE VIEW crop.v_active_batches AS
SELECT
    b.id AS batch_id,
    b.batch_code,
    v.code AS variety_code,
    v.name AS variety_name,
    v.category,
    z.name AS zone_name,
    b.plant_date,
    b.expected_harvest_date,
    b.plant_count,
    b.status,
    gsd.stage_name AS current_stage,
    bs.started_at AS stage_started_at,
    EXTRACT(EPOCH FROM (NOW() - bs.started_at)) / 86400 AS days_in_stage,
    gsd.optimal_temp_min,
    gsd.optimal_temp_max,
    gsd.optimal_ph_min,
    gsd.optimal_ph_max,
    gsd.optimal_ec_min,
    gsd.optimal_ec_max,
    gsd.light_hours
FROM crop.batches b
JOIN crop.varieties v ON b.variety_id = v.id
LEFT JOIN core.zones z ON b.zone_id = z.id
LEFT JOIN crop.batch_stages bs ON b.id = bs.batch_id AND bs.ended_at IS NULL
LEFT JOIN crop.growth_stage_definitions gsd ON bs.stage_def_id = gsd.id
WHERE b.status = 'active';

-- Latest harvest performance per variety
CREATE VIEW bi.v_variety_performance AS
SELECT
    v.code AS variety_code,
    v.name AS variety_name,
    v.category,
    COUNT(DISTINCT bp.batch_id) AS total_batches,
    AVG(bp.cycle_days) AS avg_cycle_days,
    AVG(bp.total_yield_kg) AS avg_yield_kg,
    AVG(bp.yield_per_sqm_kg) AS avg_yield_per_sqm,
    AVG(bp.conditions_score) AS avg_conditions_score,
    SUM(bp.revenue) AS total_revenue,
    AVG(bp.profit_margin) AS avg_profit_margin
FROM bi.batch_performance bp
JOIN crop.varieties v ON bp.variety_code = v.code
GROUP BY v.code, v.name, v.category;

-- Active alerts by severity
CREATE VIEW alert.v_active_alerts AS
SELECT
    a.id AS alert_id,
    a.title,
    a.message,
    a.severity,
    a.triggered_at,
    a.current_value,
    a.escalation_level,
    d.device_code,
    s.sensor_code
FROM alert.alerts a
LEFT JOIN iot.devices d ON a.device_id = d.id
LEFT JOIN iot.sensors s ON a.sensor_id = s.id
WHERE a.status = 'open'
ORDER BY
    CASE a.severity
        WHEN 'emergency' THEN 1
        WHEN 'critical' THEN 2
        WHEN 'warning' THEN 3
        WHEN 'info' THEN 4
    END,
    a.triggered_at DESC;

-- ============================================================================
-- FUNCTIONS: Utility functions
-- ============================================================================

-- Calculate VPD from temperature and humidity
CREATE OR REPLACE FUNCTION core.calculate_vpd(
    temperature_celsius DECIMAL,
    relative_humidity_percent DECIMAL
) RETURNS DECIMAL AS $$
DECLARE
    svp DECIMAL;
    avp DECIMAL;
BEGIN
    svp := 0.6108 * EXP((17.27 * temperature_celsius) / (temperature_celsius + 237.3));
    avp := svp * (relative_humidity_percent / 100.0);
    RETURN svp - avp;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Generate batch code: {variety_prefix}-{year}-{month}-{seq}
CREATE OR REPLACE FUNCTION crop.generate_batch_code(
    p_variety_code VARCHAR
) RETURNS VARCHAR AS $$
DECLARE
    prefix VARCHAR;
    year_str VARCHAR;
    month_str VARCHAR;
    seq INTEGER;
    code VARCHAR;
BEGIN
    -- Create prefix from variety code (first 2 chars uppercase)
    prefix := UPPER(LEFT(p_variety_code, 2));
    year_str := TO_CHAR(NOW(), 'YYYY');
    month_str := TO_CHAR(NOW(), 'MM');

    -- Find next sequence for this month
    SELECT COALESCE(MAX(
        CAST(SPLIT_PART(batch_code, '-', 4) AS INTEGER)
    ), 0) + 1
    INTO seq
    FROM crop.batches
    WHERE batch_code LIKE prefix || '-' || year_str || '-' || month_str || '-%';

    code := prefix || '-' || year_str || '-' || month_str || '-' || LPAD(seq::TEXT, 3, '0');
    RETURN code;
END;
$$ LANGUAGE plpgsql;

-- Compute batch performance after harvest
CREATE OR REPLACE FUNCTION bi.compute_batch_performance(p_batch_id INTEGER)
RETURNS VOID AS $$
DECLARE
    v_batch RECORD;
    v_harvest RECORD;
    v_zone RECORD;
BEGIN
    SELECT b.*, v.code AS variety_code, v.category AS variety_category,
           z.name AS zone_name, z.area_sqm
    INTO v_batch
    FROM crop.batches b
    JOIN crop.varieties v ON b.variety_id = v.id
    LEFT JOIN core.zones z ON b.zone_id = z.id
    WHERE b.id = p_batch_id;

    IF NOT FOUND THEN RETURN; END IF;

    SELECT SUM(h.weight_kg) AS total_kg,
           SUM(h.total_revenue) AS total_rev,
           MAX(h.quality_grade) AS grade,
           MAX(h.harvest_date) AS last_harvest
    INTO v_harvest
    FROM crop.harvests h
    WHERE h.batch_id = p_batch_id;

    INSERT INTO bi.batch_performance (
        batch_id, batch_code, variety_code, variety_category, client_id,
        zone_name, plant_date, harvest_date, cycle_days,
        total_yield_kg, yield_per_plant_kg, yield_per_sqm_kg,
        quality_grade, revenue, computed_at
    ) VALUES (
        p_batch_id, v_batch.batch_code, v_batch.variety_code, v_batch.variety_category,
        v_batch.client_id, v_batch.zone_name, v_batch.plant_date,
        v_harvest.last_harvest,
        COALESCE(v_harvest.last_harvest - v_batch.plant_date, 0),
        COALESCE(v_harvest.total_kg, 0),
        CASE WHEN COALESCE(v_batch.plant_count, 0) > 0
            THEN v_harvest.total_kg / v_batch.plant_count ELSE NULL END,
        CASE WHEN COALESCE(v_batch.area_sqm, 0) > 0
            THEN v_harvest.total_kg / v_batch.area_sqm ELSE NULL END,
        v_harvest.grade,
        COALESCE(v_harvest.total_rev, 0),
        NOW()
    )
    ON CONFLICT (batch_id) DO UPDATE SET
        harvest_date = EXCLUDED.harvest_date,
        cycle_days = EXCLUDED.cycle_days,
        total_yield_kg = EXCLUDED.total_yield_kg,
        yield_per_plant_kg = EXCLUDED.yield_per_plant_kg,
        yield_per_sqm_kg = EXCLUDED.yield_per_sqm_kg,
        quality_grade = EXCLUDED.quality_grade,
        revenue = EXCLUDED.revenue,
        computed_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA: Default configuration
-- ============================================================================

-- Default organization for single-tenant setup
INSERT INTO core.organizations (name, subscription_tier) VALUES
    ('AgriTech Hydroponics', 'platinum');

-- Default facility
INSERT INTO core.facilities (organization_id, name, location, timezone) VALUES
    (1, 'Main Greenhouse', 'Algarve, Portugal', 'Europe/Lisbon');

-- Default zones
INSERT INTO core.zones (facility_id, name, zone_type, area_sqm) VALUES
    (1, 'Nursery Tray A', 'nursery_tray', 2.0),
    (1, 'NFT Channel 1', 'nft_channel', 10.0),
    (1, 'NFT Channel 2', 'nft_channel', 10.0),
    (1, 'DWC Tank 1', 'dwc_tank', 5.0);

-- Default sensor types
INSERT INTO iot.sensor_types (name, manufacturer, model, measurement_unit, metric_category, calibration_required, calibration_interval_days) VALUES
    ('DHT20_TEMPERATURE', 'Aosong', 'DHT20', '°C', 'environmental', FALSE, 365),
    ('DHT20_HUMIDITY', 'Aosong', 'DHT20', '%', 'environmental', FALSE, 365),
    ('PH_SENSOR', 'DFRobot', 'SEN0161', 'pH', 'water_quality', TRUE, 30),
    ('EC_SENSOR', 'DFRobot', 'SEN0244', 'mS/cm', 'water_quality', TRUE, 30),
    ('WATER_LEVEL', 'Generic', 'HC-SR04', '%', 'system_performance', FALSE, 180),
    ('WATER_TEMP', 'Dallas', 'DS18B20', '°C', 'water_quality', FALSE, 365),
    ('LIGHT_LUX', 'VEML7700', 'VEML7700', 'lux', 'environmental', FALSE, 365);

-- Data retention policies
INSERT INTO audit.data_retention (table_name, retention_days) VALUES
    ('bi.hourly_sensor_agg', 90),
    ('alert.notification_log', 365),
    ('audit.events', 730);

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON SCHEMA core IS 'Core entities: organizations, facilities, users, zones';
COMMENT ON SCHEMA iot IS 'IoT layer: devices, sensors, calibrations, commands';
COMMENT ON SCHEMA crop IS 'Crop lifecycle: varieties, batches, growth stages, harvests';
COMMENT ON SCHEMA business IS 'Business layer: clients, subscriptions, payments';
COMMENT ON SCHEMA alert IS 'Alerting: rules, alerts, escalations, notifications';
COMMENT ON SCHEMA bi IS 'Business intelligence: aggregated metrics, pre-calculated tables';
COMMENT ON SCHEMA audit IS 'Audit trail: event log, data retention tracking';

COMMENT ON TABLE crop.growth_stage_definitions IS 'Stage templates per variety: germination -> seedling -> transplant -> vegetative -> flowering -> fruiting -> maturity -> harvest_ready';
COMMENT ON TABLE crop.batch_stages IS 'Actual stage transitions per batch, with conditions scoring';
COMMENT ON TABLE bi.daily_sensor_agg IS 'Partitioned by month. Populated by hourly cron from InfluxDB data';
COMMENT ON TABLE bi.batch_performance IS 'Denormalized harvest analytics. Recomputed on harvest via bi.compute_batch_performance()';
