# oh-my-db

Schema catalog service: introspects databases (ClickHouse first), stores table
schemas + dependencies (MVs, views, dictionaries) as a graph, and serves them
over API/MCP for AI agents. No frontend for now (research deferred).

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
- `app/api.py` — FastAPI: `/graph`, `/entities/{cluster}/{db}/{name}` (+`/relations`), labels, `/sync`.
- `config.yaml` — clusters + storage url.
- `.mcp.json.example` — MCP registration for AI coding agents: `cp .mcp.json.example .mcp.json` (`.mcp.json` itself is gitignored); works as-is from repo root, add `--project <path>` to `args` when registering globally.
- `docker-compose.yaml` + `seed/` — local ClickHouse with sample schema for testing.

## Commands

```bash
task up      # full local stack: seeded ClickHouse + sync + API on :8000
task serve   # service only, no ClickHouse (existing catalog sqlite)
task sync    # re-introspect clusters
task mcp     # MCP server (stdio) for AI agents
task test    # tests; integration auto-skips without ClickHouse
task down    # stop containers   (task clean: also drop volumes + catalog)
```

Raw commands behind the tasks: `uv sync`, `docker compose up -d --wait clickhouse`,
`docker compose run --rm clickhouse-init`, `uv run ohmydb sync|serve|mcp`,
`uv run pytest`. Optional Postgres: `docker compose --profile postgres up -d`.
