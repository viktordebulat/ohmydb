import asyncio
import json

from fastmcp import Client

from app.config import AppConfig, ClusterConfig
from app.core.models import Entity, EntityKind
from app.mcp import create_mcp
from app.store.db import make_session_factory
from app.store.queries import set_label
from app.store.repo import sync_cluster


def _mcp(tmp_path):
    url = f"sqlite:///{tmp_path}/t.sqlite"
    factory = make_session_factory(url)
    with factory() as s:
        sync_cluster(s, "c1", [
            Entity(cluster="c1", database="app", name="events", kind=EntityKind.TABLE),
            Entity(cluster="c1", database="app", name="users", kind=EntityKind.TABLE),
        ], [])
        set_label(s, "c1", "app", "events", "source", "vector")
    cfg = AppConfig(storage_url=url, clusters=[ClusterConfig(name="c1", host="localhost")])
    return create_mcp(cfg)


def _payload(result):
    if getattr(result, "data", None) is not None:
        return result.data
    return json.loads(result.content[0].text)


def test_mcp_tools(tmp_path):
    mcp = _mcp(tmp_path)

    async def go():
        async with Client(mcp) as c:
            clusters = _payload(await c.call_tool("list_clusters", {}))
            assert clusters == ["c1"]

            graph = _payload(await c.call_tool("get_schema_graph", {"cluster": "c1"}))
            names_idx = graph["columns"].index("name")
            assert {row[names_idx] for row in graph["rows"]} == {"events", "users"}

            detail = _payload(await c.call_tool(
                "get_table", {"cluster": "c1", "database": "app", "name": "events"}))
            assert detail["labels"] == {"source": "vector"}

            found = _payload(await c.call_tool("find_tables", {"query": "vector"}))
            name_idx = found["columns"].index("name")
            assert [row[name_idx] for row in found["rows"]] == ["events"]

            found = _payload(await c.call_tool("find_tables", {"query": "source:vector"}))
            assert [row[name_idx] for row in found["rows"]] == ["events"]
            found = _payload(await c.call_tool("find_tables", {"query": "source:vec"}))
            assert found["rows"] == []

            rel = _payload(await c.call_tool(
                "get_table_relations", {"cluster": "c1", "database": "app", "name": "events"}))
            assert rel["entity"]["name"] == "events"
            assert rel["upstream"] == [] and rel["downstream"] == []

    asyncio.run(go())
