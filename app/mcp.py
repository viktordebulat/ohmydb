"""MCP server for AI agents: same catalog reads as the HTTP API."""

import asyncio
from typing import Literal

from fastmcp import FastMCP

from app.annotations.service import ProposalError, propose
from app.config import AppConfig
from app.store.db import make_session_factory
from app.store.queries import get_entity, get_relations, graph_payload, list_entities


def create_mcp(cfg: AppConfig) -> FastMCP:
    factory = make_session_factory(cfg.storage_url)
    mcp = FastMCP("ohmydb")
    annotated = cfg.annotations.enabled
    # Annotation summary/status ride along in listings only when the
    # annotation layer is on (see docs/ANNOTATIONS.md).
    brief_extra = ["summary", "status"] if annotated else []

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

        When human-curated annotations are configured, rows also carry
        `summary` (what the table is) and `status` (`active`/`deprecated`,
        "" = unannotated), and a top-level `annotations` block carries
        global and per-database `query_hints` — read them before writing
        SQL. Prefer non-deprecated tables; follow `use_instead` (see
        get_table).

        Rows encoded as `columns` + `rows` (array-of-arrays) instead of one
        dict per node, to cut repeated key names at scale — zip(columns, row)
        to get a node dict back. `cluster`/`id` are omitted per row: cluster
        is the argument you just passed, id has no meaning to any other tool
        (all lookups are by cluster/database/name)."""
        with factory() as s:
            payload = graph_payload(s, cluster, with_annotations=annotated)
        columns = ["database", "name", "kind", "engine", "refreshable", "labels", *brief_extra]
        out = {
            "synced_at": payload["synced_at"],
            "columns": columns,
            "rows": [[n[c] for c in columns] for n in payload["nodes"]],
        }
        if "annotations" in payload:
            out["annotations"] = payload["annotations"]
        return out

    @mcp.tool
    def get_table(cluster: str, database: str, name: str) -> dict:
        """Full detail for one entity: columns with types/comments, raw DDL,
        engine, attrs, labels.

        If the entity is annotated, `annotation` holds human-curated
        semantics: description, grain, status/use_instead, owner,
        query_hints (gotchas: FINAL, sorting-key filters, units, dedup),
        relationships (join paths — ClickHouse has no foreign keys) and
        verified `examples` (question -> SQL). Read hints, relationships and
        examples before writing SQL. Columns may carry `description` and
        `values` (enum meanings) — these take precedence over guessing from
        names. Deprecated: switch to `use_instead`."""
        with factory() as s:
            payload = get_entity(s, cluster, database, name, with_annotations=annotated)
        if payload is None:
            raise ValueError(f"entity not found: {cluster}/{database}/{name}")
        return payload

    @mcp.tool
    def get_table_relations(cluster: str, database: str, name: str, direct: bool = False) -> dict:
        """All entities related to one table: transitive upstream data sources
        and transitive downstream consumers (MVs, views, aggregates,
        dictionaries). Set direct=True for only the immediate 1-hop
        neighbors."""
        with factory() as s:
            payload = get_relations(s, cluster, database, name, direct_only=direct)
        if payload is None:
            raise ValueError(f"entity not found: {cluster}/{database}/{name}")
        return payload

    @mcp.tool
    def find_tables(
        query: str | None = None,
        column: list[str] | None = None,
        column_type: str | None = None,
        match: Literal["all", "any"] = "all",
        kind: str | None = None,
        cluster: str | None = None,
    ) -> dict:
        """Search entities across all clusters (or one, via `cluster`). All
        filters optional and ANDed; give at least one.

        - `query`: `key:value` (colon present) does an exact label lookup;
          otherwise substring match against name, database, any label
          key/value, or the annotation summary (if annotations are on).
        - `column`: case-insensitive globs on column names (`user_id`,
          `*_id`, `*time*`). `match="all"` (default) requires every pattern
          to hit a column, `match="any"` at least one.
        - `column_type`: exact column type (`DateTime`, `UInt64`,
          `Nullable(String)`), bound to the same column as each `column`
          pattern; alone, matches entities having any column of that type.
        - `kind`: exact entity kind (table, view, mat_view, dictionary,
          external).

        Examples: tables with both user_id and ts:
        `column=["user_id", "ts"]`; any `*_at` column typed DateTime:
        `column=["*_at"], column_type="DateTime"`.

        Rows encoded as `columns` + `rows` (array-of-arrays) instead of one
        dict per match, to cut repeated key names at scale — zip(columns,
        row) to get a match dict back. A `matched_columns` column (names of
        the columns that hit) is added when a column filter is given.
        With annotations on, `summary` and `status` columns are included
        too — prefer non-deprecated matches."""
        if query is None and not column and column_type is None and kind is None:
            raise ValueError("give at least one of query, column, column_type, kind")
        with factory() as s:
            matches = list_entities(s, cluster, query, column, column_type, match, kind, with_annotations=annotated)
        columns = ["cluster", "database", "name", "kind", "labels", *brief_extra]
        if column or column_type is not None:
            columns.append("matched_columns")
        return {
            "columns": columns,
            "rows": [[n[c] for c in columns] for n in matches],
        }

    if annotated and cfg.annotations.proposals:

        @mcp.tool
        async def propose_annotation(cluster: str, database: str, name: str, patch: dict, rationale: str) -> dict:
            """Propose a change to a table's human-curated annotation. Opens a
            merge request in the annotation repo; a human reviews it and
            nothing changes until it is merged.

            Use it when you learned something non-obvious that future queries
            need and that isn't already in get_table's `annotation`: what a
            column means, units, enum values, join keys, a gotcha (FINAL,
            dedup, partial data), or a query you verified by running it.

            `patch` is a JSON merge patch (RFC 7386) against the annotation
            file — same shape as get_table's `annotation` plus `columns`:
            {"columns": {"amount": {"description": "Order total, cents"}},
             "query_hints": [...]}. Maps merge key by key; lists (query_hints,
            relationships, examples, list-style values) are REPLACED wholesale,
            so send the full list including the current entries from
            get_table; null deletes a key. Columns, relationship targets and
            use_instead are checked against the live catalog; on rejection
            the error lists every problem (also ones already in the file) —
            fix the patch and retry.

            `rationale`: the evidence — what you checked and how (query run,
            result seen, source). First line becomes the commit subject.

            Returns {status: proposed|unchanged, branch, merge_request (URL or
            null), path}."""
            try:
                return await asyncio.to_thread(
                    propose, cfg, factory, cluster, database, name, patch, rationale, "MCP"
                )
            except ProposalError as e:
                raise ValueError("\n".join(e.errors)) from None

    return mcp
