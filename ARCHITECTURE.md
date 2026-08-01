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
| `app/core` | DB-agnostic model + sync orchestration | `Entity`, `Edge`, `EntityKind`, `EdgeKind`, `run_sync()`, `apply_label_rules()` | `app/adapters`, `app/store` |
| `app/adapters` | DB-specific introspection; ClickHouse is the only impl | `Introspector` protocol, `build_introspector()`, ClickHouse parsing | `app/core` |
| `app/store` | Persistence: SQLAlchemy models, upsert logic, read queries, schema migrations | `EntityRow`/`EdgeRow`/`LabelRow`, `sync_cluster()`, `sync_auto_labels()`, `graph_payload()`, `get_entity()`, `get_relations()`, `run_migrations()` | `app/core` |
| `app/migrations` | Alembic migration scripts, shipped inside the package (not repo-root `alembic/`) so they resolve from a non-editable install too | `env.py`, `versions/*.py` | `app/store` |
| `app/config.py` | Load `config.yaml` → typed config | `load_config()`, `AppConfig` | — |
| `app/cli.py` | `ohmydb sync\|serve\|mcp` entry point | `main()` | `app/config`, `app/core`, `app/api`, `app/mcp` |
| `app/api.py` | FastAPI HTTP surface (routes under `/api`); mounts MCP at `/mcp`; serves the static frontend (`app/web/`) at `/` | `create_app()` | `app/config`, `app/core`, `app/store`, `app/mcp` |
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
| Change what's stored per entity/edge | `app/core/models.py` + `app/store/db.py` (+ adapter that populates it) + `task db:revision -- "message"` to generate the Alembic migration |
| Add an API endpoint | `app/api.py`, reuse/extend `app/store/queries.py` |
| Add an MCP tool | `app/mcp.py`, reuse `app/store/queries.py` |
| Add an optional filter to a GET endpoint/tool | optional kwarg (default `None`/`False`) on the `app/store/queries.py` function, passthrough query param in `app/api.py` and/or arg in `app/mcp.py` — keep filter logic in queries.py only, so it stays DB-agnostic and shared |
| Change sync/upsert behavior | `app/store/repo.py` |
| Add/change config fields | `app/config.py` |

## Testing

Unit tests (`tests/`) cover parsing, repo upsert, queries, API, and MCP
against SQLite — no live DB needed. `tests/test_clickhouse_integration.py`
runs against a real dockerized ClickHouse and auto-skips when it's not
reachable; `tests/test_web_ui.py` drives the frontend with a headless
Chromium and auto-skips when Playwright's browser isn't installed
(`task test` runs all of them).

Gotchas, sharp edges, and past incidents: [docs/LEARNINGS.md](docs/LEARNINGS.md).
