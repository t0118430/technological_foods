// Daily Downsample Task
// Aggregates hourly data into daily statistics.
// Writes results back to InfluxDB "hydroponics_daily" bucket.
// The Python API cron job then pushes these to PostgreSQL bi.daily_sensor_agg.
//
// Schedule: every 1 day at 00:15 (after midnight, wait for late hourly data)

option task = {
    name: "daily_downsample",
    every: 1d,
    offset: 15m
}

sourceBucket = "hydroponics"
destBucket = "hydroponics_daily"

// Daily averages from raw data
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
        r._field == "light"
    )
    |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
    |> set(key: "_measurement", value: "sensor_daily_avg")
    |> to(bucket: destBucket)

// Daily min
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
    |> aggregateWindow(every: 1d, fn: min, createEmpty: false)
    |> set(key: "_measurement", value: "sensor_daily_min")
    |> to(bucket: destBucket)

// Daily max
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
    |> aggregateWindow(every: 1d, fn: max, createEmpty: false)
    |> set(key: "_measurement", value: "sensor_daily_max")
    |> to(bucket: destBucket)

// Daily standard deviation
from(bucket: sourceBucket)
    |> range(start: -task.every)
    |> filter(fn: (r) => r._measurement == "sensor_reading")
    |> filter(fn: (r) =>
        r._field == "temperature" or
        r._field == "humidity" or
        r._field == "ph" or
        r._field == "ec"
    )
    |> aggregateWindow(every: 1d, fn: stddev, createEmpty: false)
    |> set(key: "_measurement", value: "sensor_daily_stddev")
    |> to(bucket: destBucket)

// Daily reading count
from(bucket: sourceBucket)
    |> range(start: -task.every)
    |> filter(fn: (r) => r._measurement == "sensor_reading")
    |> filter(fn: (r) => r._field == "temperature")
    |> aggregateWindow(every: 1d, fn: count, createEmpty: false)
    |> set(key: "_measurement", value: "sensor_daily_count")
    |> set(key: "_field", value: "reading_count")
    |> to(bucket: destBucket)
