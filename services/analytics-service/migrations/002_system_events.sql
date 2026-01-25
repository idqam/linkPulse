-- Migration to add generic events table
CREATE TABLE IF NOT EXISTS system_events (
    id BIGSERIAL,
    event_type VARCHAR(50) NOT NULL,
    user_id BIGINT,
    data JSONB,
    occurred_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id, occurred_at)
);

SELECT create_hypertable('system_events', 'occurred_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events (event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_events_user ON system_events (user_id, occurred_at DESC);
