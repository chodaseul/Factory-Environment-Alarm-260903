-- =====================================================
-- Factory Environment Alarm
-- Database Schema
-- =====================================================


-- 센서 측정값
CREATE TABLE IF NOT EXISTS sensor_data
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    measured_at TEXT NOT NULL,

    temperature REAL NOT NULL,
    humidity REAL NOT NULL,
    light INTEGER NOT NULL,

    temp_alarm INTEGER NOT NULL DEFAULT 0,
    hum_alarm INTEGER NOT NULL DEFAULT 0,
    light_alarm INTEGER NOT NULL DEFAULT 0,

    acknowledged INTEGER NOT NULL DEFAULT 0,
    alert_active INTEGER NOT NULL DEFAULT 0
);


-- 알람 이벤트 이력
CREATE TABLE IF NOT EXISTS alarm_event
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    event_at TEXT NOT NULL,

    event_type TEXT NOT NULL,

    message TEXT
);