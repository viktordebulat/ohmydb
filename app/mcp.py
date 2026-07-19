"""MCP server for AI agents: same catalog reads as the HTTP API."""

from fastmcp import FastMCP

from app.config import AppConfig
from app.store.db import make_session_factory
from app.store.queries import get_entity, get_relations, graph_payload


def create_mcp(cfg: AppConfig) -> FastMCP:
    factory = make_session_factory(cfg.storage_url)
    mcp = FastMCP("oh-my-db")

    @mcp.tool
    def get_schema_graph() -> dict:
        """Full catalog graph: nodes (tables, views, materialized views,
        dictionaries, with labels) and dependency edges (reads_from,
        writes_to, dict_source)."""
        with factory() as s:
            return graph_payload(s)

    @mcp.tool
    def get_table(cluster: str, database: str, name: str) -> dict:
        """Full detail for one entity: columns with types/comments, raw DDL,
        engine, attrs, labels."""
        with factory() as s:
            payload = get_entity(s, cluster, database, name)
        if payload is None:
            raise ValueError(f"entity not found: {cluster}/{database}/{name}")
        return payload

    @mcp.tool
    def get_table_relations(cluster: str, database: str, name: str) -> dict:
        """All entities related to one table: transitive upstream data sources,
        transitive downstream consumers (MVs, views, aggregates, dictionaries),
        and the dependency edges among them."""
        with factory() as s:
            payload = get_relations(s, cluster, database, name)
        if payload is None:
            raise ValueError(f"entity not found: {cluster}/{database}/{name}")
        return payload

    @mcp.tool
    def find_tables(query: str) -> list[dict]:
        """Search entities by substring of name, database, or label value.
        Returns brief matches (identity + kind + labels)."""
        q = query.lower()
        with factory() as s:
            nodes = graph_payload(s)["nodes"]
        return [
            {k: n[k] for k in ("cluster", "database", "name", "kind", "labels")}
            for n in nodes
            if q in n["name"].lower() or q in n["database"].lower()
            or any(q in v.lower() or q in k.lower() for k, v in n["labels"].items())
        ]

    return mcp
