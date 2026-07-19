"""Integration test against the docker-compose ClickHouse (seeded).

Auto-skips when ClickHouse is not reachable on localhost:8123.
"""

import pytest

from app.adapters.clickhouse import ClickHouseIntrospector
from app.core.models import EdgeKind, EntityKind


def _reachable() -> bool:
    try:
        import clickhouse_connect

        clickhouse_connect.get_client(host="localhost", port=8123, password="ohmydb").query("SELECT 1")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _reachable(), reason="ClickHouse not running (docker compose up -d)")


@pytest.fixture(scope="module")
def introspected():
    return ClickHouseIntrospector(cluster="local", host="localhost", password="ohmydb").introspect()


def test_entity_kinds(introspected):
    entities, _ = introspected
    kinds = {(e.database, e.name): e.kind for e in entities}
    assert kinds[("app", "events")] == EntityKind.TABLE
    assert kinds[("app", "recent_events")] == EntityKind.VIEW
    assert kinds[("analytics", "events_hourly_mv")] == EntityKind.MAT_VIEW
    assert kinds[("app", "users_dict")] == EntityKind.DICTIONARY


def test_refreshable_attr(introspected):
    entities, _ = introspected
    daily = next(e for e in entities if e.name == "daily_counts")
    assert daily.attrs.get("refreshable") is True


def test_columns_and_comment(introspected):
    entities, _ = introspected
    events = next(e for e in entities if (e.database, e.name) == ("app", "events"))
    cols = {c.name: c for c in events.columns}
    assert cols["ts"].type == "DateTime"
    assert "click" in cols["event_type"].comment


def test_edges(introspected):
    _, edges = introspected
    triples = {(e.src[1:], e.dst[1:], e.kind) for e in edges}
    assert ((("analytics", "events_hourly_mv"), ("app", "events"), EdgeKind.READS_FROM)) in triples
    assert ((("analytics", "events_hourly_mv"), ("analytics", "events_hourly"), EdgeKind.WRITES_TO)) in triples
    assert ((("app", "recent_events"), ("app", "events"), EdgeKind.READS_FROM)) in triples
    assert ((("app", "users_dict"), ("app", "users"), EdgeKind.DICT_SOURCE)) in triples
    assert ((("analytics", "daily_counts"), ("app", "events"), EdgeKind.READS_FROM)) in triples
