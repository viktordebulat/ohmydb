from app.adapters.clickhouse import (
    _EXTERNAL_ENGINES,
    _extract_dict_gets,
    _extract_sources,
    _extract_to_target,
    _KIND_BY_ENGINE,
    _parse_dict_source,
    _parse_distributed_target,
)
from app.core.models import EntityKind


def test_to_target_qualified():
    ddl = "CREATE MATERIALIZED VIEW analytics.mv TO analytics.events_hourly AS SELECT 1"
    assert _extract_to_target(ddl, "analytics") == ("analytics", "events_hourly")


def test_to_target_unqualified_uses_default_db():
    ddl = "CREATE MATERIALIZED VIEW analytics.mv TO target AS SELECT 1"
    assert _extract_to_target(ddl, "analytics") == ("analytics", "target")


def test_to_target_absent_and_ignores_select_body():
    ddl = "CREATE MATERIALIZED VIEW db.mv ENGINE = MergeTree ORDER BY x AS SELECT castTO(x) FROM t"
    assert _extract_to_target(ddl, "db") is None


def test_extract_sources_from_and_join():
    ddl = ("CREATE VIEW v AS SELECT * FROM app.events e "
           "JOIN app.users u ON e.user_id = u.id WHERE x IN (SELECT id FROM other.t)")
    assert set(_extract_sources(ddl)) == {("app", "events"), ("app", "users"), ("other", "t")}


def test_extract_sources_skips_unqualified():
    assert _extract_sources("CREATE VIEW v AS SELECT * FROM events") == []


def test_parse_dict_source():
    ddl = "CREATE DICTIONARY app.d (`id` UInt64) PRIMARY KEY id SOURCE(CLICKHOUSE(DB 'app' TABLE 'users')) LAYOUT(HASHED())"
    assert _parse_dict_source(ddl, "app") == ("app", "users")


def test_parse_dict_source_defaults_db():
    ddl = "CREATE DICTIONARY app.d (`id` UInt64) PRIMARY KEY id SOURCE(CLICKHOUSE(TABLE 'users')) LAYOUT(FLAT())"
    assert _parse_dict_source(ddl, "app") == ("app", "users")


def test_parse_dict_source_non_clickhouse():
    ddl = "CREATE DICTIONARY app.d (`id` UInt64) PRIMARY KEY id SOURCE(MYSQL(TABLE 'users')) LAYOUT(FLAT())"
    assert _parse_dict_source(ddl, "app") is None


def test_extract_dict_gets_qualified():
    ddl = "CREATE VIEW v AS SELECT dictGetOrDefault('app.d1', 'name', id, '') AS name FROM app.t"
    assert _extract_dict_gets(ddl, "other") == [("app", "d1")]


def test_extract_dict_gets_unqualified_uses_default_db():
    ddl = "CREATE VIEW v AS SELECT dictGet('d1', 'name', id) AS name FROM app.t"
    assert _extract_dict_gets(ddl, "app") == [("app", "d1")]


def test_extract_dict_gets_multiple():
    ddl = ("CREATE VIEW v AS SELECT dictGetOrDefault('app.d1', 'a', id, '') AS a, "
           "dictGet('app.d2', 'b', id) AS b FROM app.t")
    assert _extract_dict_gets(ddl, "app") == [("app", "d1"), ("app", "d2")]


def test_extract_dict_gets_none():
    assert _extract_dict_gets("CREATE VIEW v AS SELECT * FROM app.t", "app") == []


def test_window_and_live_view_map_to_view():
    assert _KIND_BY_ENGINE["WindowView"] == EntityKind.VIEW
    assert _KIND_BY_ENGINE["LiveView"] == EntityKind.VIEW


def test_distributed_target_qualified():
    ddl = "CREATE TABLE app.events_all ENGINE = Distributed('my_cluster', app, events, rand())"
    assert _parse_distributed_target(ddl, "app") == ("app", "events")


def test_distributed_target_quoted_parts():
    ddl = "CREATE TABLE app.events_all ENGINE = Distributed('my_cluster', 'app', 'events')"
    assert _parse_distributed_target(ddl, "other") == ("app", "events")


def test_distributed_target_current_database_defaults():
    ddl = "CREATE TABLE app.events_all ENGINE = Distributed('my_cluster', currentDatabase(), events)"
    assert _parse_distributed_target(ddl, "app") == ("app", "events")


def test_distributed_target_empty_database_defaults():
    ddl = "CREATE TABLE app.events_all ENGINE = Distributed('my_cluster', '', events)"
    assert _parse_distributed_target(ddl, "app") == ("app", "events")


def test_distributed_target_absent():
    assert _parse_distributed_target("CREATE TABLE app.t ENGINE = MergeTree ORDER BY x", "app") is None


def test_external_engines_flagged():
    assert "S3" in _EXTERNAL_ENGINES
    assert "PostgreSQL" in _EXTERNAL_ENGINES
    assert "Kafka" in _EXTERNAL_ENGINES
    assert "RabbitMQ" in _EXTERNAL_ENGINES
    assert "MergeTree" not in _EXTERNAL_ENGINES
    assert "EmbeddedRocksDB" not in _EXTERNAL_ENGINES
