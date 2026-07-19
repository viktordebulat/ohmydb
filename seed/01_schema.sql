-- Sample schema exercising every entity kind and edge type.
-- Executed by the clickhouse-init container on every startup: keep idempotent.

CREATE DATABASE IF NOT EXISTS app;
CREATE DATABASE IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS app.events (
    ts DateTime,
    user_id UInt64,
    event_type LowCardinality(String) COMMENT 'click, view, purchase...',
    payload String
) ENGINE = MergeTree ORDER BY ts;

CREATE TABLE IF NOT EXISTS app.users (
    id UInt64,
    email String,
    created_at DateTime
) ENGINE = MergeTree ORDER BY id;

-- Aggregation target + cross-database MV (writes_to + reads_from edges)
CREATE TABLE IF NOT EXISTS analytics.events_hourly (
    hour DateTime,
    event_type LowCardinality(String),
    cnt UInt64
) ENGINE = SummingMergeTree ORDER BY (hour, event_type);

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.events_hourly_mv TO analytics.events_hourly AS
SELECT toStartOfHour(ts) AS hour, event_type, count() AS cnt
FROM app.events GROUP BY hour, event_type;

-- Plain view (reads_from via regex fallback)
CREATE VIEW IF NOT EXISTS app.recent_events AS
SELECT * FROM app.events WHERE ts > now() - INTERVAL 1 DAY;

-- Dictionary (dict_source edge)
CREATE DICTIONARY IF NOT EXISTS app.users_dict (
    id UInt64,
    email String
) PRIMARY KEY id
SOURCE(CLICKHOUSE(DB 'app' TABLE 'users'))
LIFETIME(MIN 60 MAX 120)
LAYOUT(HASHED());

-- Refreshable MV (attrs.refreshable = true)
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.daily_counts
REFRESH EVERY 1 HOUR
ENGINE = MergeTree ORDER BY day AS
SELECT toDate(ts) AS day, count() AS cnt
FROM app.events GROUP BY day;
