# Architecture

> **Read this first.** Enforced by `task docs:verify` (part of `task check`):
> the module table below must name every real module under `app/`. When you
> add, rename, or remove a module — or change what one is responsible for —
> update this file in the *same* change. Gotchas/decisions go in
> [docs/LEARNINGS.md](docs/LEARNINGS.md), not here.

## What this is

Schema catalog service: introspects databases (ClickHouse first), stores
table schemas + dependencies (views, materialized views, dictionaries) as a
graph, and serves them over HTTP API and MCP for AI agents.

## Data flow

1. `cli.py` / `api.py` (`POST /sync`) call `core/sync.py: run_sync(cfg)`.
2. Per cluster, `adapters/*` picks the adapter by `cluster.type` and returns
   `(Entity[], Edge[])` — all DB-specific parsing happens here.
3. `store/repo.py: sync_cluster()` upserts entities/edges into SQLAlchemy
   (SQLite or Postgres), replacing that cluster's prior state; labels
   untouched.
4. Reads (`api.py`, `mcp.py`) go through `store/queries.py` to build JSON
   (`graph_payload`, `get_entity`, `get_relations`) served over HTTP or as
   MCP tools.

## Modules

| Module | Responsibility | Key types/entry points | Depends on |
|---|---|---|---|
| `app/core` | DB-agnostic model + sync orchestration | `Entity`, `Edge`, `EntityKind`, `EdgeKind`, `run_sync()` | `app/adapters`, `app/store` |
| `app/adapters` | DB-specific introspection; ClickHouse is the only impl | `Introspector` protocol, `build_introspector()`, ClickHouse parsing | `app/core` |
| `app/store` | Persistence: SQLAlchemy models, upsert logic, read queries | `EntityRow`/`EdgeRow`/`LabelRow`, `sync_cluster()`, `graph_payload()`, `get_entity()`, `get_relations()` | `app/core` |
| `app/config.py` | Load `config.yaml` → typed config | `load_config()`, `AppConfig` | — |
| `app/cli.py` | `ohmydb sync\|serve\|mcp` entry point | `main()` | `app/config`, `app/core`, `app/api`, `app/mcp` |
| `app/api.py` | FastAPI HTTP surface; mounts MCP at `/mcp` | `create_app()` | `app/config`, `app/core`, `app/store`, `app/mcp` |
| `app/mcp.py` | fastmcp server (stdio or mounted over HTTP) | `create_mcp()` | `app/config`, `app/store` |

## Layering rule

Entry points (`cli`, `api`, `mcp`) → `core` → {`adapters`, `store`} → `core`
models. `adapters` and `store` never import each other. Anything
ClickHouse-specific stays inside `app/adapters/clickhouse.py` — everything
else must stay database-agnostic (see AGENTS.md rule).

## Where to make common changes

| Task | Module |
|---|---|
| Support a new database engine | new file in `app/adapters/`, implement `Introspector` |
| Change what's stored per entity/edge | `app/core/models.py` + `app/store/db.py` (+ adapter that populates it) |
| Add an API endpoint | `app/api.py`, reuse/extend `app/store/queries.py` |
| Add an MCP tool | `app/mcp.py`, reuse `app/store/queries.py` |
| Change sync/upsert behavior | `app/store/repo.py` |
| Add/change config fields | `app/config.py` |

## Testing

Unit tests (`tests/`) cover parsing, repo upsert, queries, API, and MCP
against SQLite — no live DB needed. `tests/test_clickhouse_integration.py`
runs against a real dockerized ClickHouse and auto-skips when it's not
reachable (`task test` runs both).

Gotchas, sharp edges, and past incidents: [docs/LEARNINGS.md](docs/LEARNINGS.md).
