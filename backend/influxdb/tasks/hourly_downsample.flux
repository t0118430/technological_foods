// Hourly Downsample Task
// Aggregates raw sensor readings into hourly statistics.
// Writes results back to InfluxDB "hydroponics_hourly" bucket.
// The Python API cron job then pushes these to PostgreSQL bi.hourly_sensor_agg.
//
// Schedule: every 1 hour, offset 5 minutes (wait for late data)

option task = {
    name: "hourly_downsample",
    every: 1h,
    offset: 5m
}

// Source bucket with raw sensor readings
sourceBucket = "hydroponics"
destBucket = "hydroponics_hourly"

// Aggregate all numeric fields from sensor_reading measurement
from(bucket: sourceBucket)
    |> range(start: -task.every)
    |> filter(fn: (r) => r._measurement == "sensor_reading")
    |> filter(fn: (r) =>
        r._field == "temperature" or
        r._field == "humidity" or
        r._field == "ph" or
        r._field == "ec" or
        r._field == "water_level" or
        r._field == "water_temp" or
        r._field == "light" or
        r._field == "temperature_secondary" or
        r._field == "humidity_secondary"
    )
    |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
    |> set(key: "_measurement", value: "sensor_hourly_avg")
    |> to(bucket: destBucket)

// Min values
from(bucket: sourceBucket)
    |> range(start: -task.every)
    |> filter(fn: (r) => r._measurement == "sensor_reading")
    |> filter(fn: (r) =>
        r._field == "temperature" or
        r._field == "humidity" or
        r._field == "ph" or
        r._field == "ec" or
        r._field == "water_temp"
    )
    |> aggregateWindow(every: 1h, fn: min, createEmpty: false)
    |> set(key: "_measurement", value: "sensor_hourly_min")
    |> to(bucket: destBucket)

// Max values
from(bucket: sourceBucket)
    |> range(start: -task.every)
    |> filter(fn: (r) => r._measurement == "sensor_reading")
    |> filter(fn: (r) =>
        r._field == "temperature" or
        r._field == "humidity" or
        r._field == "ph" or
        r._field == "ec" or
        r._field == "water_temp"
    )
    |> aggregateWindow(every: 1h, fn: max, createEmpty: false)
    |> set(key: "_measurement", value: "sensor_hourly_max")
    |> to(bucket: destBucket)

// Reading count per hour
from(bucket: sourceBucket)
    |> range(start: -task.every)
    |> filter(fn: (r) => r._measurement == "sensor_reading")
    |> filter(fn: (r) => r._field == "temperature")
    |> aggregateWindow(every: 1h, fn: count, createEmpty: false)
    |> set(key: "_measurement", value: "sensor_hourly_count")
    |> set(key: "_field", value: "reading_count")
    |> to(bucket: destBucket)
