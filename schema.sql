-- =====================================================
-- Factory Environment Alarm
-- PostgreSQL Database Schema
-- =====================================================

CREATE TABLE IF NOT EXISTS sensor_data
(
    id BIGSERIAL PRIMARY KEY,

    measured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    temperature REAL NOT NULL,
    humidity REAL NOT NULL,
    light INTEGER NOT NULL,

    temp_alarm BOOLEAN NOT NULL DEFAULT FALSE,
    hum_alarm BOOLEAN NOT NULL DEFAULT FALSE,
    light_alarm BOOLEAN NOT NULL DEFAULT FALSE,

    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    alert_active BOOLEAN NOT NULL DEFAULT FALSE
);


CREATE TABLE IF NOT EXISTS alarm_event
(
    id BIGSERIAL PRIMARY KEY,

    event_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    event_type TEXT NOT NULL,

    message TEXT
);
