# ohmydb

Schema catalog service: introspects databases (ClickHouse first), stores table
schemas + dependencies (MVs, views, dictionaries) as a graph, and serves them
over API/MCP for AI agents. No frontend for now (research deferred).

## Documents

- **`ARCHITECTURE.md` — read this first.** Module map, data flow, layering
  rule. Keep its module table in sync in the *same change* that adds,
  renames, or removes a module, or changes a module's responsibility —
  `task docs:verify` (part of `task check`) enforces this; it's a guardrail,
  not a suggestion.
- `docs/PLAN.md` — implementation plan, milestones, design decisions. Keep in sync with reality.
- `docs/LEARNINGS.md` — gotchas and learnings discovered during implementation.
  Consult before touching adapters/store/docker; add an entry when you hit a
  new one.

## Rules

1. **Self-improve**: after finishing an implementation task or milestone, append
   new gotchas/learnings to `docs/LEARNINGS.md`, then compact the file — merge
   duplicates, drop entries that became obvious or obsolete. Keep each entry one
   short paragraph max.
2. Update `docs/PLAN.md` when a design decision changes; update
   `ARCHITECTURE.md` when structure changes — don't let either drift.
3. Core (`app/core`, `app/store`) must stay database-agnostic. Anything
   ClickHouse-specific lives only in `app/adapters/clickhouse.py`.
4. Tiny and simple: no speculative abstractions, minimal test coverage (module
   not broken ≠ full coverage). Not a mission-critical service.

## Architecture

See `ARCHITECTURE.md` for the module map, data flow, and layering rule.
Layout: `pyproject.toml`, `.venv`, `tests/` in repo root; all app code in
`app/` (package importable as `app`).

Config/deploy notes not covered there:

- `config.example.yaml` — local-dev template (clusters + storage url + optional
  per-cluster `extra` dict spread into the DB client, e.g. `{secure: true,
  verify: false, connect_timeout: 30}`). Real config is gitignored `config.yaml`.
  Config path resolves `--config` flag > `OHMYDB_CONFIG` env > `config.yaml`.
  `CLICKHOUSE_USER`/`CLICKHOUSE_PASSWORD` env override the config's per-cluster
  values (keep secrets out of the mounted file). Prod: mount config (configmap),
  set `OHMYDB_CONFIG`, inject the CH env secrets — nothing is baked into the image.
  `storage` block: `type: sqlite` (local debug, set `url`) or `type: postgres`
  (prod, set `host`/`port`/`username`/`password`/`database`); `POSTGRES_USER`/
  `POSTGRES_PASSWORD` env override the postgres secrets, same pattern as CH.
- `.mcp.json.example` — MCP registration for AI coding agents: `cp .mcp.json.example .mcp.json` (`.mcp.json` itself is gitignored). Two entries: `ohmydb` (stdio, spawns `uv run ohmydb mcp`; add `--project <path>` to `args` when registering globally) and `ohmydb-http` (connects to a running `serve` at `http://127.0.0.1:8080/mcp/`). Keep one, drop the other.
- `docker-compose.yaml` + `seed/` — local ClickHouse with sample schema for testing.

## Commands

```bash
task up      # full local stack: seeded ClickHouse + sync + API on :8080 (MCP at /mcp)
task serve   # service only, no ClickHouse (API + MCP at /mcp, existing catalog sqlite)
task sync    # re-introspect clusters
task demo:build # build docs/demo/, the static GitHub Pages snapshot of the frontend
task mcp     # MCP server over stdio (alternative to the HTTP /mcp mount)
task test    # tests; integration auto-skips without ClickHouse
task check   # tests + docs:verify (ARCHITECTURE.md drift check) — source of truth for "is it green"
task down    # stop containers   (task clean: also drop volumes + catalog)
task db:revision -- "message"  # autogenerate Alembic migration from db.py model changes
```

Prefer `task <name>` over the raw command behind it (e.g. `task db:revision` not
`uv run alembic revision --autogenerate`) — tasks wrap the right flags/env for
this repo.

Raw commands behind the tasks: `uv sync`, `docker compose up -d --wait clickhouse`,
`docker compose run --rm clickhouse-init`, `uv run ohmydb sync|serve|mcp`,
`uv run pytest`, `./scripts/check-docs.sh`. Optional Postgres:
`docker compose --profile postgres up -d`.
