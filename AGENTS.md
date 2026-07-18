# oh-my-db

Schema catalog service: introspects databases (ClickHouse first), stores table
schemas + dependencies (MVs, views, dictionaries) as a graph, visualizes them,
and later serves them over API/MCP for AI agents.

## Documents

- `docs/PLAN.md` — implementation plan, milestones, design decisions. Keep in sync with reality.
- `docs/LEARNINGS.md` — gotchas and learnings discovered during implementation.

## Rules

1. **Self-improve**: after finishing an implementation task or milestone, append
   new gotchas/learnings to `docs/LEARNINGS.md`, then compact the file — merge
   duplicates, drop entries that became obvious or obsolete. Keep each entry one
   short paragraph max.
2. Update `docs/PLAN.md` when a design decision changes; don't let it drift.
3. Core (`ohmydb/core`, `ohmydb/store`) must stay database-agnostic. Anything
   ClickHouse-specific lives only in `ohmydb/adapters/clickhouse.py`.
4. Tiny and simple: no speculative abstractions, minimal test coverage (module
   not broken ≠ full coverage). Not a mission-critical service.

## Architecture

Layout: `pyproject.toml`, `.venv`, `tests/` in repo root; all app code in `app/`
(package importable as `app`).

- `app/core/models.py` — Entity/Column/Edge dataclasses, pure.
- `app/core/sync.py` — orchestrates: adapter → store, per cluster.
- `app/adapters/` — `base.py` Introspector protocol + per-DB adapters.
- `app/store/` — SQLAlchemy models + sync/upsert logic. SQLite now, Postgres later (conn string swap).
- `app/cli.py` — `ohmydb sync`, `ohmydb serve`, `ohmydb mcp`.
- `app/mcp.py` — fastmcp server (stdio) exposing catalog reads to AI agents.
- `app/store/queries.py` — shared read/label helpers used by API and MCP.
- `app/api.py` — FastAPI: `/graph`, `/entities/{cluster}/{db}/{name}`, serves `app/web/`.
- `app/web/` — `index.html` (Cytoscape + dagre graph, vendored JS in `vendor/`, no build step).
- `config.yaml` — clusters + storage url.
- `docker-compose.yaml` + `seed/` — local ClickHouse with sample schema for testing.

## Commands

```bash
uv sync                       # install deps
docker compose up -d          # local ClickHouse (seeded)
uv run ohmydb sync            # introspect → SQLite
uv run ohmydb serve           # visualization at http://127.0.0.1:8000
uv run ohmydb mcp             # MCP server (stdio) for AI agents
docker compose --profile postgres up -d   # optional Postgres backend
uv run pytest                 # unit tests; integration tests auto-skip without ClickHouse
```
