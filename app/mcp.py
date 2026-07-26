"""MCP server for AI agents: same catalog reads as the HTTP API."""

from fastmcp import FastMCP

from app.config import AppConfig
from app.store.db import make_session_factory
from app.store.queries import get_entity, get_relations, graph_payload, list_entities


def create_mcp(cfg: AppConfig) -> FastMCP:
    factory = make_session_factory(cfg.storage_url)
    mcp = FastMCP("ohmydb")

    @mcp.tool
    def list_clusters() -> list[str]:
        """Configured cluster names. Call this first — get_schema_graph
        requires one of these."""
        return [c.name for c in cfg.clusters]

    @mcp.tool
    def get_schema_graph(cluster: str) -> dict:
        """Catalog nodes for one cluster: tables, views, materialized views,
        dictionaries, with labels. No dependency edges — call
        get_table_relations for one entity's upstream/downstream. Call
        list_clusters() first for valid values.

        Rows encoded as `columns` + `rows` (array-of-arrays) instead of one
        dict per node, to cut repeated key names at scale — zip(columns, row)
        to get a node dict back. `cluster`/`id` are omitted per row: cluster
        is the argument you just passed, id has no meaning to any other tool
        (all lookups are by cluster/database/name)."""
        with factory() as s:
            payload = graph_payload(s, cluster)
        columns = ["database", "name", "kind", "engine", "refreshable", "labels"]
        return {
            "synced_at": payload["synced_at"],
            "columns": columns,
            "rows": [[n[c] for c in columns] for n in payload["nodes"]],
        }

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
        """All entities related to one table: transitive upstream data sources
        and transitive downstream consumers (MVs, views, aggregates,
        dictionaries)."""
        with factory() as s:
            payload = get_relations(s, cluster, database, name)
        if payload is None:
            raise ValueError(f"entity not found: {cluster}/{database}/{name}")
        return payload

    @mcp.tool
    def find_tables(query: str) -> dict:
        """Search entities by substring of name, database, or label value,
        across all clusters. Rows encoded as `columns` + `rows`
        (array-of-arrays) instead of one dict per match, to cut repeated key
        names at scale — zip(columns, row) to get a match dict back."""
        q = query.lower()
        with factory() as s:
            nodes = list_entities(s)
        matches = [
            n
            for n in nodes
            if q in n["name"].lower()
            or q in n["database"].lower()
            or any(q in v.lower() or q in k.lower() for k, v in n["labels"].items())
        ]
        columns = ["cluster", "database", "name", "kind", "labels"]
        return {
            "columns": columns,
            "rows": [[n[c] for c in columns] for n in matches],
        }

    return mcp
