-- TimescaleDB Schema for Analytics Service
-- Run this against your TimescaleDB instance

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Clicks hypertable
CREATE TABLE IF NOT EXISTS clicks (
    id BIGSERIAL,
    url_code VARCHAR(12) NOT NULL,
    clicked_at TIMESTAMPTZ NOT NULL,
    ip_hash VARCHAR(64),
    country VARCHAR(2),
    city VARCHAR(100),
    device_type VARCHAR(20),
    browser VARCHAR(50),
    os VARCHAR(50),
    referrer_domain VARCHAR(255),
    PRIMARY KEY (id, clicked_at)
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('clicks', 'clicked_at', if_not_exists => TRUE);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_clicks_url_code ON clicks (url_code, clicked_at DESC);
CREATE INDEX IF NOT EXISTS idx_clicks_country ON clicks (country, clicked_at DESC);

-- Continuous aggregate for hourly clicks
CREATE MATERIALIZED VIEW IF NOT EXISTS clicks_hourly
WITH (timescaledb.continuous) AS
SELECT
    url_code,
    time_bucket('1 hour', clicked_at) AS bucket,
    COUNT(*) AS click_count,
    COUNT(DISTINCT ip_hash) AS unique_visitors
FROM clicks
GROUP BY url_code, bucket
WITH NO DATA;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('clicks_hourly',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Daily aggregate
CREATE MATERIALIZED VIEW IF NOT EXISTS clicks_daily
WITH (timescaledb.continuous) AS
SELECT
    url_code,
    time_bucket('1 day', clicked_at) AS bucket,
    COUNT(*) AS click_count,
    COUNT(DISTINCT ip_hash) AS unique_visitors
FROM clicks
GROUP BY url_code, bucket
WITH NO DATA;

SELECT add_continuous_aggregate_policy('clicks_daily',
    start_offset => INTERVAL '30 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Retention policy: keep raw data for 90 days
SELECT add_retention_policy('clicks', INTERVAL '90 days', if_not_exists => TRUE);
