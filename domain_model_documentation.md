# Hydroponics IoT Platform - Domain Model

## Overview

This domain model represents the **business logic and rules** of the Hydroponics IoT Platform using **Domain-Driven Design (DDD)** principles. It focuses on:
- **What the business does** (not how it's stored)
- **Business rules and invariants**
- **Entity behaviors and responsibilities**
- **Domain events and workflows**

---

## Ubiquitous Language

### Core Terms

| Term | Definition | Business Meaning |
|------|------------|------------------|
| **Snapshot** | Batched sensor readings at 5-min interval | Single point-in-time environmental state |
| **VPD** | Vapor Pressure Deficit | Master metric controlling plant transpiration |
| **Grow Cycle** | Seed-to-harvest period | Complete crop lifecycle for ROI tracking |
| **Alert Rule** | Condition that triggers notification | Automated monitoring boundary |
| **Command** | Instruction to change actuator state | Remote control action |
| **Actuator** | Physical device controlled by Arduino | Equipment that changes environment (AC, pump, light) |
| **Metric** | One of 30 optimization measurements | KPI from the framework (temp, pH, yield, cost) |
| **Calibration** | Sensor accuracy verification | Ensures data quality and trustworthiness |
| **Optimal Range** | Species-specific target values | Golden zone for max crop performance |
| **Economic KPI** | Financial performance metric | Business outcome measurement ($/kg, ROI) |

---

## Bounded Contexts

The platform is divided into **6 bounded contexts**, each with clear boundaries and responsibilities:

```
┌─────────────────────────────────────────────────────────────┐
│                    ORGANIZATION CONTEXT                      │
│  Manages: Multi-tenancy, subscriptions, user access         │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
        ┌───────▼──────┐ ┌─▼──────────▼───┐ ┌────────────────┐
        │   DEVICE     │ │  ENVIRONMENTAL │ │    CONTROL &   │
        │  MANAGEMENT  │ │   MONITORING   │ │   AUTOMATION   │
        └──────────────┘ └────────────────┘ └────────────────┘
                │               │                    │
                └───────┬───────┴────────────────────┘
                        │
            ┌───────────┼───────────┐
            │                       │
    ┌───────▼──────┐        ┌──────▼────────┐
    │     CROP     │        │   ECONOMIC    │
    │  MANAGEMENT  │        │   ANALYSIS    │
    └──────────────┘        └───────────────┘
```

---

## Aggregate Roots

Aggregates are **transactional boundaries** - only the root can be accessed directly from outside. All business rules are enforced at the aggregate level.

### **1. Organization (Aggregate Root)**

**Responsibility:** Manages multi-tenant business structure

**Entities Within Aggregate:**
- `Facility` - Physical growing location
- `User` - Person with system access

**Value Objects:**
- `Subscription` - Tier, status, billing info
- `Address` - Location details

**Business Rules:**
```
✓ An Organization must have at least one Facility
✓ An Organization can have 1-100 Facilities (tier-dependent)
✓ Subscription status determines feature access:
  - STARTER: max 3 devices, 13 metrics
  - GROWTH: unlimited devices, all 30 metrics
  - ENTERPRISE: + dedicated support, custom SLAs
✓ Only ADMIN users can create/delete Facilities
✓ Organization cannot be deleted if active Grow Cycles exist
```

**Key Methods:**
```python
class Organization:
    def add_facility(self, name: str, area_sqm: float) -> Facility:
        """Creates a new facility within subscription limits"""
        if self.facilities.count() >= self.subscription.max_facilities:
            raise SubscriptionLimitExceeded()
        
        facility = Facility(name, area_sqm)
        self.facilities.append(facility)
        self.raise_event(FacilityCreated(facility.id))
        return facility
    
    def upgrade_subscription(self, new_tier: SubscriptionTier):
        """Changes subscription tier with immediate effect"""
        old_tier = self.subscription.tier
        self.subscription = Subscription(new_tier)
        self.raise_event(SubscriptionUpgraded(old_tier, new_tier))
```

**Domain Events:**
- `OrganizationCreated`
- `FacilityAdded`
- `UserInvited`
- `SubscriptionUpgraded`
- `SubscriptionCancelled`

---

### **2. Device (Aggregate Root)**

**Responsibility:** Represents a physical Arduino unit with cellular connectivity

**Entities Within Aggregate:**
- `Sensor` - Measures environmental/water parameters
- `Actuator` - Controls equipment (relay, valve, motor)

**Value Objects:**
- `DeviceHealth` - Battery, signal strength, uptime
- `Connectivity` - SIM card, carrier, IP address
- `Calibration` - Last/next calibration dates, drift

**Business Rules:**
```
✓ Device must have unique device_code within Facility
✓ Device cannot have duplicate sensors of same type on same pin
✓ Device is considered OFFLINE if no heartbeat for >10 minutes
✓ Sensors must be calibrated within their interval (e.g., pH: every 30 days)
✓ Actuators can only be controlled if Device is ONLINE
✓ Device must publish heartbeat every 5 minutes
✓ Battery-powered devices enter sleep mode between snapshots
```

**Key Methods:**
```python
class Device:
    def register_heartbeat(self, health: DeviceHealth):
        """Updates device online status and health metrics"""
        self.last_heartbeat = datetime.utcnow()
        self.health = health
        self.status = DeviceStatus.ONLINE
        
        if health.battery_level < 20:
            self.raise_event(LowBatteryWarning(self.device_code))
        
        if health.signal_strength < -90:  # Poor signal
            self.raise_event(PoorSignalWarning(self.device_code))
    
    def add_sensor(self, sensor_type: SensorType, pin: str) -> Sensor:
        """Adds a new sensor to the device"""
        if self._has_sensor_on_pin(pin):
            raise PinAlreadyInUse(pin)
        
        sensor = Sensor(sensor_type, pin)
        self.sensors.append(sensor)
        self.raise_event(SensorRegistered(sensor.sensor_code))
        return sensor
    
    def execute_command(self, command: Command) -> bool:
        """Executes a command on an actuator"""
        if self.status != DeviceStatus.ONLINE:
            raise DeviceOfflineError()
        
        actuator = self._find_actuator(command.actuator_id)
        previous_state = actuator.current_state
        
        actuator.change_state(command.desired_state)
        
        self.raise_event(ActuatorStateChanged(
            actuator.id, 
            previous_state, 
            command.desired_state,
            command.id
        ))
        
        return True
    
    def check_calibration_status(self):
        """Verifies all sensors are within calibration window"""
        for sensor in self.sensors:
            if sensor.needs_calibration():
                self.raise_event(CalibrationDue(sensor.sensor_code))
```

**Invariants:**
- A Device always has at least one Sensor
- Actuator state changes must be logged
- Device cannot be deleted if it has readings from last 7 days (data retention)

**Domain Events:**
- `DeviceRegistered`
- `DeviceHeartbeatReceived`
- `DeviceWentOffline`
- `SensorAdded`
- `ActuatorStateChanged`
- `CalibrationDue`
- `LowBatteryWarning`

---

### **3. DeviceSnapshot (Aggregate Root)**

**Responsibility:** Represents a point-in-time environmental state from all sensors on a device

**Value Objects:**
- `SensorReading` - Individual metric measurement
- `ReadingQuality` - Confidence score, anomaly flag

**Business Rules:**
```
✓ Snapshot must contain readings from all active sensors on the device
✓ Readings must be within physically possible ranges:
  - Temperature: -10°C to 50°C
  - Humidity: 0-100%
  - pH: 0-14
  - EC: 0-5 mS/cm
✓ VPD is calculated from temperature + humidity (not measured directly)
✓ Anomaly detection flags readings >3 standard deviations from 24hr avg
✓ Snapshots older than 90 days are archived to cold storage
✓ Missing sensor readings generate alert (sensor failure)
```

**Key Methods:**
```python
class DeviceSnapshot:
    def __init__(self, device_id: UUID, readings: List[SensorReading]):
        """Creates a snapshot with validation"""
        if len(readings) == 0:
            raise EmptySnapshotError()
        
        self.device_id = device_id
        self.timestamp = datetime.utcnow()
        self.readings = self._validate_readings(readings)
        self.calculated_metrics = self._calculate_derived_metrics()
    
    def _calculate_derived_metrics(self) -> Dict[str, float]:
        """Computes VPD, DLI, and other calculated metrics"""
        temp = self.get_reading_value(MetricType.TEMPERATURE)
        humidity = self.get_reading_value(MetricType.HUMIDITY)
        
        vpd = VPDCalculator.calculate(temp, humidity)
        
        return {
            'vpd': vpd,
            'dli': self._calculate_dli(),
            # ... other calculated metrics
        }
    
    def detect_anomalies(self, historical_stats: Dict[int, Statistics]):
        """Flags readings that deviate significantly from norm"""
        for reading in self.readings:
            stats = historical_stats.get(reading.metric_id)
            if stats and stats.is_anomalous(reading.value):
                reading.mark_as_anomaly(f"Value {reading.value} is {stats.std_devs_from_mean(reading.value)}σ from mean")
    
    def get_reading_value(self, metric_type: MetricType) -> float:
        """Retrieves value for a specific metric"""
        reading = next((r for r in self.readings if r.metric_type == metric_type), None)
        if not reading:
            raise MetricNotFound(metric_type)
        return reading.value
```

**Invariants:**
- Timestamp cannot be in the future
- All readings must have same timestamp (±1 second tolerance)
- Quality scores must be 0.0-1.0

**Domain Events:**
- `SnapshotReceived`
- `AnomalyDetected`
- `MetricThresholdViolated`
- `SensorMissing`

---

### **4. Alert (Aggregate Root)**

**Responsibility:** Monitors conditions and triggers notifications/automated actions

**Entities Within Aggregate:**
- `AlertRule` - Condition definition
- `Command` - Automated response

**Value Objects:**
- `Condition` - Threshold, duration, metric
- `CommandStatus` - Lifecycle state

**Business Rules:**
```
✓ Alert Rule must specify: metric, condition type, threshold, severity
✓ Rule can be facility-wide or device-specific
✓ Alert is only triggered if condition persists for specified duration:
  - Example: Temp > 30°C for 15 minutes (not instant)
✓ CRITICAL alerts cannot be dismissed, only RESOLVED
✓ One Alert Rule can trigger one automated Command
✓ Alerts are auto-resolved when condition returns to normal
✓ Alert fatigue prevention: Max 1 alert per rule per hour
✓ EMERGENCY alerts trigger immediate notification (SMS + email + push)
```

**Key Methods:**
```python
class Alert:
    def evaluate_condition(self, current_value: float, metric: Metric) -> bool:
        """Checks if alert condition is met"""
        condition = self.rule.condition
        
        if condition.type == ConditionType.ABOVE_THRESHOLD:
            return current_value > condition.threshold
        elif condition.type == ConditionType.BELOW_THRESHOLD:
            return current_value < condition.threshold
        elif condition.type == ConditionType.OUT_OF_RANGE:
            return not (condition.min_threshold <= current_value <= condition.max_threshold)
        
        return False
    
    def trigger(self, snapshot: DeviceSnapshot):
        """Triggers the alert and executes automated response"""
        self.status = AlertStatus.OPEN
        self.triggered_at = datetime.utcnow()
        self.current_value = snapshot.get_reading_value(self.rule.metric_type)
        
        # Execute automated command if configured
        if self.rule.auto_command_type:
            command = self._create_automated_command()
            self.command = command
            self.raise_event(AutomatedCommandIssued(command.id))
        
        # Send notifications based on severity
        self._send_notifications()
        
        self.raise_event(AlertTriggered(
            alert_id=self.id,
            severity=self.rule.severity,
            metric=self.rule.metric_type
        ))
    
    def acknowledge(self, user: User):
        """User acknowledges the alert"""
        if self.status != AlertStatus.OPEN:
            raise InvalidAlertState()
        
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_by = user.id
        self.acknowledged_at = datetime.utcnow()
        
        self.raise_event(AlertAcknowledged(self.id, user.id))
    
    def resolve(self, resolution_notes: str):
        """Marks alert as resolved when condition normalizes"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.utcnow()
        self.resolution_notes = resolution_notes
        
        self.raise_event(AlertResolved(self.id))
```

**Invariants:**
- Alert cannot be triggered if same alert already OPEN
- Resolved alerts cannot be reopened (create new alert)
- Command can only execute if Device is ONLINE

**Domain Events:**
- `AlertRuleCreated`
- `AlertTriggered`
- `AlertAcknowledged`
- `AlertResolved`
- `AutomatedCommandIssued`

---

### **5. GrowCycle (Aggregate Root)**

**Responsibility:** Tracks complete crop lifecycle from planting to harvest

**Entities Within Aggregate:**
- `CropVariety` - Species and optimal parameters
- `Performance` - Measured crop metrics (growth rate, yield)

**Value Objects:**
- `GrowthStage` - Seedling, vegetative, flowering, harvest
- `OptimalParameters` - Species-specific environmental targets

**Business Rules:**
```
✓ GrowCycle must have start_date and expected_harvest_date
✓ Actual harvest date cannot be before start date
✓ Only one active GrowCycle per facility zone at a time
✓ Growth stage transitions follow strict order:
  PLANNING → SEEDLING → VEGETATIVE → FLOWERING → HARVEST
✓ Performance metrics (metrics 20-25) are measured weekly
✓ Economic calculations run only after harvest completion
✓ Yield must be >0 kg to mark cycle as successful
✓ Cycle cannot be deleted after harvest (audit requirement)
```

**Key Methods:**
```python
class GrowCycle:
    def start_cycle(self, variety: CropVariety, area_sqm: float):
        """Begins a new growing cycle"""
        if self.status != CycleStatus.PLANNING:
            raise InvalidStateTransition()
        
        self.variety = variety
        self.growth_area_sqm = area_sqm
        self.start_date = date.today()
        self.status = CycleStatus.ACTIVE
        
        # Calculate expected harvest based on variety typical cycle time
        self.expected_harvest_date = self.start_date + timedelta(
            days=variety.typical_cycle_days
        )
        
        self.raise_event(GrowCycleStarted(self.id, variety.name))
    
    def advance_growth_stage(self, new_stage: GrowthStage):
        """Moves crop to next growth phase"""
        if not self._is_valid_stage_transition(new_stage):
            raise InvalidStageTransition(self.growth_stage, new_stage)
        
        previous_stage = self.growth_stage
        self.growth_stage = new_stage
        
        # Update optimal environmental targets based on growth stage
        self._update_target_parameters()
        
        self.raise_event(GrowthStageChanged(
            cycle_id=self.id,
            from_stage=previous_stage,
            to_stage=new_stage
        ))
    
    def record_performance(self, metric: Metric, value: float, measured_by: User):
        """Records crop performance measurement"""
        if metric.metric_number not in range(20, 26):  # Metrics 20-25
            raise InvalidPerformanceMetric()
        
        performance = Performance(
            metric=metric,
            value=value,
            measurement_date=date.today(),
            measured_by=measured_by
        )
        
        self.performance_records.append(performance)
        
        # Check if meeting expected targets
        if not self._is_meeting_targets(metric, value):
            self.raise_event(PerformanceUnderTarget(
                cycle_id=self.id,
                metric=metric.name,
                actual=value,
                expected=self.variety.get_expected_value(metric)
            ))
    
    def complete_harvest(self, actual_yield_kg: float):
        """Marks cycle complete and triggers economic analysis"""
        if self.status != CycleStatus.ACTIVE:
            raise InvalidCycleState()
        
        if actual_yield_kg <= 0:
            raise InvalidYieldValue()
        
        self.status = CycleStatus.HARVESTED
        self.actual_harvest_date = date.today()
        self.actual_yield_kg = actual_yield_kg
        
        # Trigger economic calculations
        self.raise_event(GrowCycleCompleted(
            cycle_id=self.id,
            yield_kg=actual_yield_kg,
            cycle_days=(self.actual_harvest_date - self.start_date).days
        ))
```

**Invariants:**
- Growth stage can only move forward, never backward
- Cannot harvest without recording at least one performance metric
- Plant count must match area (density rules)

**Domain Events:**
- `GrowCycleStarted`
- `GrowthStageChanged`
- `PerformanceRecorded`
- `PerformanceUnderTarget`
- `GrowCycleCompleted`
- `YieldCalculated`

---

### **6. EconomicReport (Aggregate Root)**

**Responsibility:** Calculates financial KPIs and ROI metrics (metrics 26-30)

**Entities Within Aggregate:**
- `ResourceCost` - Cost per unit for electricity, water, nutrients

**Value Objects:**
- `Calculation` - Formula, inputs, result
- `KPI` - Key performance indicator value

**Business Rules:**
```
✓ Economic calculations only run after GrowCycle completion
✓ Metrics 26-30 calculated as follows:
  26. Energy Cost/kg = (total kWh × rate) ÷ yield_kg
  27. Water Cost/kg = (total L × rate) ÷ yield_kg
  28. Nutrient Cost/kg = (total nutrient expense) ÷ yield_kg
  29. Labor Hours/Cycle = sum of manual interventions
  30. Revenue/m²/Year = (yield × price × cycles) ÷ area_sqm
✓ Historical costs must be used (not current rates)
✓ ROI calculations compare against baseline (first cycle)
✓ Target improvements from 30-metric framework are benchmarks
✓ Reports are immutable once generated (audit trail)
```

**Key Methods:**
```python
class EconomicReport:
    def generate_for_cycle(self, cycle: GrowCycle, facility: Facility):
        """Calculates all 30 metrics for a completed cycle"""
        if cycle.status != CycleStatus.HARVESTED:
            raise CycleNotComplete()
        
        # Get historical costs effective during cycle period
        costs = self._get_effective_costs(
            facility_id=facility.id,
            period=(cycle.start_date, cycle.actual_harvest_date)
        )
        
        # Calculate operational metrics (26-29)
        energy_cost_per_kg = self._calculate_energy_cost_per_kg(cycle, costs)
        water_cost_per_kg = self._calculate_water_cost_per_kg(cycle, costs)
        nutrient_cost_per_kg = self._calculate_nutrient_cost_per_kg(cycle, costs)
        labor_hours = self._calculate_labor_hours(cycle)
        
        # Calculate revenue metric (30)
        cycles_per_year = 365 / cycle.cycle_time_days
        revenue_per_sqm_per_year = (
            cycle.actual_yield_kg * 
            cycle.variety.market_price_per_kg * 
            cycles_per_year
        ) / cycle.growth_area_sqm
        
        # Compare to targets from framework
        improvements = self._calculate_improvements_vs_baseline(cycle)
        
        self.raise_event(EconomicReportGenerated(
            cycle_id=cycle.id,
            total_cost_per_kg=energy_cost_per_kg + water_cost_per_kg + nutrient_cost_per_kg,
            revenue_per_sqm=revenue_per_sqm_per_year,
            roi_vs_baseline=improvements['roi_percentage']
        ))
    
    def compare_to_target(self, metric: Metric) -> ComparisonResult:
        """Compares actual performance to target improvement"""
        target = metric.target_improvement_percentage
        actual = self.calculations[metric.metric_id]
        
        return ComparisonResult(
            metric_name=metric.name,
            target_improvement=target,
            actual_improvement=actual.improvement_vs_baseline,
            meets_target=(actual.improvement_vs_baseline >= target)
        )
```

**Invariants:**
- All 30 metrics must be calculated together (atomic operation)
- Calculations use snapshot of costs at time of cycle
- Reports cannot be modified after creation

**Domain Events:**
- `EconomicReportGenerated`
- `TargetImprovement Achieved`
- `TargetImprovementMissed`
- `ROICalculated`

---

## Domain Services

Domain Services contain **business logic that doesn't naturally fit in a single entity** and often coordinates multiple aggregates.

### **1. VPD Calculator (Domain Service)**

**Responsibility:** Calculates Vapor Pressure Deficit from temperature and humidity

**Why a Service?** VPD is calculated, not measured. The calculation logic is shared across multiple contexts.

```python
class VPDCalculator:
    @staticmethod
    def calculate(temperature_celsius: float, relative_humidity_percent: float) -> VPD:
        """
        Calculates VPD using standard formula:
        VPD = SVP × (1 - RH/100)
        where SVP = 0.6108 × e^((17.27 × T) / (T + 237.3))
        """
        if not (0 <= relative_humidity_percent <= 100):
            raise InvalidHumidityValue()
        
        # Saturated Vapor Pressure (kPa)
        svp = 0.6108 * math.exp(
            (17.27 * temperature_celsius) / (temperature_celsius + 237.3)
        )
        
        # Actual Vapor Pressure (kPa)
        avp = svp * (relative_humidity_percent / 100.0)
        
        # VPD (kPa)
        vpd_value = svp - avp
        
        return VPD(
            value=vpd_value,
            temperature=temperature_celsius,
            humidity=relative_humidity_percent
        )
    
    @staticmethod
    def get_optimal_range(growth_stage: GrowthStage) -> VPDRange:
        """Returns optimal VPD for growth stage"""
        optimal_ranges = {
            GrowthStage.SEEDLING: (0.4, 0.8),
            GrowthStage.VEGETATIVE: (0.8, 1.2),
            GrowthStage.FLOWERING: (1.0, 1.5)
        }
        return VPDRange(*optimal_ranges[growth_stage])
```

---

### **2. Alert Evaluator (Domain Service)**

**Responsibility:** Evaluates all alert rules against new snapshots

**Why a Service?** Coordinates multiple Alert aggregates and DeviceSnapshot

```python
class AlertEvaluator:
    def __init__(self, alert_repository, device_repository):
        self.alert_repo = alert_repository
        self.device_repo = device_repository
    
    def evaluate_snapshot(self, snapshot: DeviceSnapshot):
        """Checks all active alert rules against new snapshot"""
        device = self.device_repo.get(snapshot.device_id)
        active_rules = self.alert_repo.get_active_rules_for_device(device.id)
        
        for rule in active_rules:
            # Check if condition is met
            metric_value = snapshot.get_reading_value(rule.metric_type)
            
            if rule.evaluate(metric_value):
                # Check if condition has persisted long enough
                if self._has_persisted_for_duration(rule, device):
                    # Prevent alert fatigue
                    if not self._recently_triggered(rule):
                        alert = Alert.create_from_rule(rule, snapshot)
                        alert.trigger(snapshot)
                        self.alert_repo.save(alert)
    
    def _has_persisted_for_duration(self, rule: AlertRule, device: Device) -> bool:
        """Checks if condition has been true for required duration"""
        if rule.duration_minutes == 0:
            return True  # Instant trigger
        
        # Look at historical readings
        historical_snapshots = self.device_repo.get_recent_snapshots(
            device.id,
            minutes=rule.duration_minutes
        )
        
        # Condition must be true for ALL snapshots in duration
        return all(
            rule.evaluate(snap.get_reading_value(rule.metric_type))
            for snap in historical_snapshots
        )
```

---

### **3. Command Orchestrator (Domain Service)**

**Responsibility:** Manages command lifecycle from creation to execution

**Why a Service?** Coordinates Device, Actuator, and MQTT infrastructure

```python
class CommandOrchestrator:
    def __init__(self, device_repo, mqtt_client, command_repo):
        self.device_repo = device_repo
        self.mqtt_client = mqtt_client
        self.command_repo = command_repo
    
    def issue_command(
        self, 
        device: Device, 
        command_type: CommandType,
        parameters: dict,
        issued_by: User
    ) -> Command:
        """Creates and publishes a command to a device"""
        
        # Verify device is online
        if not device.is_online():
            raise DeviceOfflineError(device.device_code)
        
        # Create command
        command = Command(
            device_id=device.id,
            command_type=command_type,
            payload=parameters,
            issued_by=issued_by.id,
            priority=parameters.get('priority', 5)
        )
        
        # Save to database
        self.command_repo.save(command)
        
        # Publish to MQTT
        topic = f"devices/{device.device_code}/commands"
        self.mqtt_client.publish(
            topic=topic,
            payload=command.to_json(),
            qos=1
        )
        
        command.mark_as_sent()
        self.command_repo.save(command)
        
        return command
    
    def handle_command_acknowledgment(self, device_id: UUID, command_id: UUID, result: dict):
        """Processes command execution result from device"""
        command = self.command_repo.get(command_id)
        device = self.device_repo.get(device_id)
        
        if result['success']:
            command.mark_as_executed(result)
            device.execute_command(command)
        else:
            command.mark_as_failed(result['error'])
            
            # Retry logic
            if command.retry_count < 3:
                command.retry()
                self.issue_command(device, command.command_type, command.payload, command.issued_by)
        
        self.command_repo.save(command)
```

---

### **4. Economic Calculator (Domain Service)**

**Responsibility:** Computes all financial KPIs (metrics 26-30)

**Why a Service?** Requires data from multiple aggregates (GrowCycle, Resource Costs, Snapshots)

```python
class EconomicCalculator:
    def calculate_all_kpis(
        self, 
        cycle: GrowCycle, 
        facility: Facility
    ) -> EconomicReport:
        """Generates complete economic report for a cycle"""
        
        # Gather all resource consumption during cycle
        energy_consumption = self._get_total_energy(cycle)
        water_consumption = self._get_total_water(cycle)
        nutrient_consumption = self._get_total_nutrients(cycle)
        labor_hours = self._get_total_labor(cycle)
        
        # Get effective costs during cycle period
        costs = self._get_period_costs(facility, cycle.start_date, cycle.actual_harvest_date)
        
        # Calculate per-kg costs (metrics 26-28)
        energy_cost_per_kg = (energy_consumption.kwh * costs.electricity_rate) / cycle.actual_yield_kg
        water_cost_per_kg = (water_consumption.liters * costs.water_rate) / cycle.actual_yield_kg
        nutrient_cost_per_kg = nutrient_consumption.total_cost / cycle.actual_yield_kg
        
        # Calculate revenue (metric 30)
        cycles_per_year = 365 / cycle.cycle_time_days
        revenue_per_sqm = (
            cycle.actual_yield_kg * 
            cycle.variety.market_price * 
            cycles_per_year
        ) / cycle.growth_area_sqm
        
        # Create report
        report = EconomicReport(
            cycle_id=cycle.id,
            metrics={
                26: Calculation('Energy Cost/kg', energy_cost_per_kg),
                27: Calculation('Water Cost/kg', water_cost_per_kg),
                28: Calculation('Nutrient Cost/kg', nutrient_cost_per_kg),
                29: Calculation('Labor Hours', labor_hours),
                30: Calculation('Revenue/m²/year', revenue_per_sqm)
            }
        )
        
        return report
```

---

## Value Objects

Value objects are **immutable** and defined by their attributes, not identity.

### **Key Value Objects:**

```python
@dataclass(frozen=True)
class VPD:
    """Vapor Pressure Deficit - master environmental metric"""
    value: float  # kPa
    temperature: float  # °C
    humidity: float  # %
    
    def __post_init__(self):
        if not 0.0 <= self.value <= 5.0:
            raise InvalidVPDValue(self.value)
    
    def is_optimal_for_stage(self, stage: GrowthStage) -> bool:
        optimal_ranges = {
            GrowthStage.SEEDLING: (0.4, 0.8),
            GrowthStage.VEGETATIVE: (0.8, 1.2),
            GrowthStage.FLOWERING: (1.0, 1.5)
        }
        min_vpd, max_vpd = optimal_ranges[stage]
        return min_vpd <= self.value <= max_vpd


@dataclass(frozen=True)
class SensorReading:
    """Individual measurement from a sensor"""
    sensor_id: UUID
    metric_id: int
    value: float
    unit: str
    timestamp: datetime
    quality_score: float = 1.0
    is_anomaly: bool = False
    
    def __post_init__(self):
        if not 0.0 <= self.quality_score <= 1.0:
            raise InvalidQualityScore()


@dataclass(frozen=True)
class OptimalRange:
    """Target range for a metric"""
    metric_id: int
    min_value: float
    max_value: float
    critical_low: float
    critical_high: float
    
    def is_optimal(self, value: float) -> bool:
        return self.min_value <= value <= self.max_value
    
    def is_critical(self, value: float) -> bool:
        return value < self.critical_low or value > self.critical_high


@dataclass(frozen=True)
class CommandStatus:
    """Lifecycle state of a command"""
    state: str  # PENDING, SENT, DELIVERED, EXECUTED, FAILED
    timestamp: datetime
    details: Optional[str] = None
    
    def is_terminal(self) -> bool:
        return self.state in ['EXECUTED', 'FAILED', 'TIMEOUT']


@dataclass(frozen=True)
class ActuatorState:
    """Current state of an actuator"""
    actuator_id: UUID
    state: str  # ON, OFF, or numeric value (0-100 for dimmers)
    last_changed: datetime
    changed_by: Optional[UUID]  # Command or User that triggered
```

---

## Domain Events

Events represent **things that have happened** in the domain. They are immutable and past-tense.

### **Core Domain Events:**

```python
@dataclass(frozen=True)
class DeviceSnapshotReceived:
    """Device sent new sensor readings"""
    snapshot_id: UUID
    device_id: UUID
    timestamp: datetime
    reading_count: int
    vpd: float


@dataclass(frozen=True)
class AlertTriggered:
    """Alert condition was met"""
    alert_id: UUID
    rule_id: UUID
    device_id: UUID
    metric_type: MetricType
    severity: Severity
    current_value: float
    threshold_violated: float
    triggered_at: datetime


@dataclass(frozen=True)
class AutomatedCommandIssued:
    """System automatically sent command in response to alert"""
    command_id: UUID
    alert_id: UUID
    device_id: UUID
    command_type: str
    issued_at: datetime


@dataclass(frozen=True)
class GrowCycleCompleted:
    """Crop was harvested"""
    cycle_id: UUID
    variety_name: str
    actual_yield_kg: float
    cycle_days: int
    start_date: date
    harvest_date: date


@dataclass(frozen=True)
class TargetImprovementAchieved:
    """Economic target from 30-metric framework was met"""
    cycle_id: UUID
    metric_id: int
    target_improvement: float
    actual_improvement: float
    exceeded_by: float
```

---

## Business Workflows

### **Workflow 1: Environmental Monitoring & Automated Response**

```
1. Device.register_heartbeat() → DeviceHeartbeatReceived
2. Device publishes sensor snapshot to MQTT
3. DeviceSnapshot created → DeviceSnapshotReceived
4. VPDCalculator.calculate() → VPD value added to snapshot
5. AlertEvaluator.evaluate_snapshot() checks all rules
6. Alert.trigger() if threshold violated → AlertTriggered
7. If auto-command configured:
   - Alert creates Command → AutomatedCommandIssued
   - CommandOrchestrator.issue_command()
   - MQTT publishes to devices/{code}/commands
   - Device.execute_command()
   - Actuator state changes → ActuatorStateChanged
8. Alert.resolve() when condition normalizes → AlertResolved
```

### **Workflow 2: Grow Cycle with Economic Analysis**

```
1. Organization.add_facility() → FacilityCreated
2. GrowCycle.start_cycle(variety) → GrowCycleStarted
3. Weekly: GrowCycle.record_performance() → PerformanceRecorded
4. Continuous: DeviceSnapshots feed environmental data
5. GrowCycle.advance_growth_stage() → GrowthStageChanged
   - Updates optimal parameter targets
   - Adjusts VPD ranges, EC levels, light intensity
6. GrowCycle.complete_harvest() → GrowCycleCompleted
7. EconomicCalculator.calculate_all_kpis() → EconomicReportGenerated
8. Compare to baseline and targets → TargetImprovementAchieved/Missed
```

### **Workflow 3: Command with Retry Logic**

```
1. AlertEvaluator detects high temperature
2. CommandOrchestrator.issue_command(AC_ON)
3. Command.status = PENDING
4. MQTT publishes command
5. Command.status = SENT
6. Device offline → no acknowledgment within 60 seconds
7. Command.status = TIMEOUT
8. CommandOrchestrator retries (max 3 attempts)
9. On 2nd attempt, device online
10. Device.execute_command()
11. Actuator changes state
12. Device publishes acknowledgment
13. CommandOrchestrator.handle_acknowledgment()
14. Command.status = EXECUTED
```

---

## Aggregation Strategy

### **Transactional Boundaries:**

| Aggregate | Can Modify Directly | Must Use Domain Service |
|-----------|-------------------|------------------------|
| **Device** | Sensors, Actuators | Snapshots (separate aggregate) |
| **DeviceSnapshot** | Readings (value objects) | Alert triggering (AlertEvaluator) |
| **Alert** | AlertRule, Command | Device control (CommandOrchestrator) |
| **GrowCycle** | Performance records | Economic calculations (EconomicCalculator) |

**Rule:** Never modify entities across aggregate boundaries in the same transaction.

**Example - WRONG:**
```python
# DON'T DO THIS - crosses aggregate boundaries
def handle_high_temp(snapshot, device, alert):
    snapshot.mark_as_anomaly()  # ✗ Different aggregate
    alert.trigger()              # ✗ Different aggregate
    device.turn_on_ac()          # ✗ Different aggregate
    db.commit()  # All in one transaction - WRONG!
```

**Example - CORRECT:**
```python
# DO THIS - use domain events
def handle_high_temp(snapshot):
    # 1. Snapshot aggregate modifies itself
    if snapshot.is_anomalous():
        snapshot.mark_as_anomaly()
        snapshot.raise_event(AnomalyDetected(snapshot.id))
    
    # 2. Event handler triggers alert evaluation
    @handles(AnomalyDetected)
    def on_anomaly(event):
        AlertEvaluator.evaluate_snapshot(event.snapshot_id)
    
    # 3. Alert triggers command via service
    @handles(AlertTriggered)
    def on_alert(event):
        if event.auto_command:
            CommandOrchestrator.issue_command(...)
```

---

## Anti-Corruption Layer (ACL)

The ACL protects the domain model from external systems (MQTT, Arduino, APIs).

```python
class MQTTAdapter:
    """Translates MQTT messages to domain events"""
    
    def on_mqtt_message(self, topic: str, payload: bytes):
        """Entry point from MQTT broker"""
        
        if topic.startswith("sensors/snapshot"):
            # Parse Arduino JSON payload
            data = json.loads(payload)
            
            # Translate to domain objects
            snapshot = self._create_snapshot_from_mqtt(data)
            
            # Publish domain event
            self.event_bus.publish(DeviceSnapshotReceived(
                snapshot_id=snapshot.id,
                device_id=snapshot.device_id,
                timestamp=snapshot.timestamp,
                reading_count=len(snapshot.readings)
            ))
        
        elif topic.endswith("/ack"):
            # Command acknowledgment from device
            data = json.loads(payload)
            
            self.event_bus.publish(CommandAcknowledged(
                command_id=UUID(data['command_id']),
                success=data['success'],
                result=data.get('result')
            ))
    
    def _create_snapshot_from_mqtt(self, mqtt_data: dict) -> DeviceSnapshot:
        """Converts Arduino JSON to domain object"""
        
        readings = []
        for key, value in mqtt_data.items():
            if key in ['device_id', 'timestamp']:
                continue
            
            metric = self._map_arduino_key_to_metric(key)
            reading = SensorReading(
                sensor_id=self._get_sensor_id(mqtt_data['device_id'], key),
                metric_id=metric.id,
                value=value,
                unit=metric.unit,
                timestamp=datetime.fromisoformat(mqtt_data['timestamp'])
            )
            readings.append(reading)
        
        return DeviceSnapshot(
            device_id=UUID(mqtt_data['device_id']),
            readings=readings
        )
```

---

## Summary

This domain model provides:

✅ **Clear boundaries** - 6 bounded contexts with well-defined responsibilities  
✅ **Business rules enforcement** - Aggregates guard invariants  
✅ **Behavior-rich entities** - Not anemic data holders  
✅ **Ubiquitous language** - Terms match business domain  
✅ **Domain events** - Decoupled communication between aggregates  
✅ **Value objects** - Immutable, self-validating  
✅ **Domain services** - Complex logic that spans aggregates  
✅ **ACL** - Protection from external system details  

The model emphasizes **what the business does** (grow crops profitably with IoT optimization) over **how it's implemented** (databases, MQTT, Arduino).
