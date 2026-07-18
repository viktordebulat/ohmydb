# Implementation Plan

## Goal

Replace grepping a huge `database_name.sql` schema dump with a small service that
stores table schemas and their interconnections (MVs, views, dictionaries,
refreshable MVs, aggregation tables), visualizes them, and serves them to AI
agents over API/MCP.

## Decisions (locked)

| Topic | Decision |
|---|---|
| Ingestion | Live DB introspection via `system.tables` etc. CI triggers re-sync after migrations. |
| History | Latest state only; sync replaces. History lives in git dumps. |
| Labels | Stored in separate identity-keyed table (cluster, database, table_name) — survives entity drop/recreate; orphan labels hidden from output, not deleted. |
| Viz | Static HTML + Cytoscape.js (vendored), FastAPI serves page + graph JSON. No build step. |
| Storage | SQLite first via SQLAlchemy; Postgres later = connection string swap. |
| Sync trigger | CLI command + POST /sync endpoint (same code path). No scheduler. |
| Scope | Multi-cluster from day one. Entities namespaced by cluster. |
| Detail | Structured columns (name/type/comment) + raw DDL + attrs (engine, keys, refreshable). |

## DB-agnostic design

Core model knows only `Entity(kind: table|view|mat_view|dictionary|external)` and
`Edge(kind: reads_from|writes_to|dict_source)`. Adapters implement
`Introspector.introspect() -> (entities, edges)` and are the only place with
DB-specific knowledge. Adapter chosen by `type:` field in cluster config.

## Storage schema

- `entities`: id, cluster, database, name, kind, engine, ddl, columns(JSON), attrs(JSON), synced_at. Unique(cluster, database, name).
- `edges`: src_id, dst_id, kind. Missing edge target → stub entity kind=`external`.
- `labels`: cluster, database, table_name, key, value. Identity-keyed, no FK.

## Sync algorithm

Per cluster, one transaction: delete cluster edges → upsert entities by identity
→ delete entities no longer present (incl. old stubs) → create stubs for unknown
edge endpoints → insert edges. Labels untouched. `synced_at` = staleness signal.

## ClickHouse edge extraction

- `reads_from`: `system.tables.dependencies_database/dependencies_table` arrays
  (views that depend on a table) + regex FROM/JOIN fallback for plain views.
- `writes_to`: regex `TO db.table` from MV `create_table_query`.
- `dict_source`: parse `SOURCE(CLICKHOUSE(DB 'x' TABLE 'y'))` from dictionary DDL
  (`system.dictionaries.source` is empty until dictionary loads — see LEARNINGS).
- Refreshable MV: `REFRESH` in DDL → `attrs.refreshable = true`.

## Milestones

- **M1 — DONE (2026-07-18)**: core models, ClickHouse adapter, SQLite store, CLI,
  docker-compose + seed schema, tests (15). Verified: `ohmydb sync` against
  dockerized seeded ClickHouse → 7 entities (all kinds), 5 edges (all kinds),
  idempotent re-sync.
- **M2 — DONE (2026-07-18)**: FastAPI `/graph` + `/entities/{...}` + static
  Cytoscape/dagre page (`ohmydb serve`). Node color+shape by kind, dashed border
  = refreshable, edges rendered in data-flow direction, click → columns+DDL
  panel, search + cluster filter, light/dark. Verified via API tests + curl.
- **M3 — DONE (2026-07-18)**: labels CRUD (`PUT /labels/{cluster}/{db}/{table}`
  body `{key, value}`, `DELETE /labels/.../{key}`), labels in graph/entity
  payloads + panel editor + label filter in UI, `POST /sync[?cluster=]` for CI
  (502 when introspection fails), `ohmydb mcp` fastmcp stdio server (tools:
  `get_schema_graph`, `get_table`, `find_tables`), Postgres via compose profile
  `postgres` — verified sync+labels against it, swap is conn-string-only.

## Fetch format

`GET /graph` → `{nodes: [...], edges: [...]}` JSON — feeds both Cytoscape and
future MCP. `GET /entities/{cluster}/{db}/{name}` → full detail incl. DDL.
