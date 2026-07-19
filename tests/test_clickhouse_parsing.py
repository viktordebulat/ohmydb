from app.adapters.clickhouse import _extract_sources, _extract_to_target, _parse_dict_source


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
