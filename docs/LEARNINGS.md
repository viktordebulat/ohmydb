# Learnings

Gotchas discovered during implementation. Append after each task, then compact
(merge duplicates, drop obsolete). One short paragraph max per entry.

## ClickHouse

- `system.tables.dependencies_database/dependencies_table` (reverse deps) only
  track insert-trigger MVs — plain views and refreshable MVs are absent. Adapter
  keeps a regex `FROM/JOIN db.table` fallback for those; dedupe via edge set.
- `system.dictionaries.source` is empty while status=NOT_LOADED (dictionaries
  load lazily). Parse `SOURCE(CLICKHOUSE(DB 'x' TABLE 'y'))` from
  `create_table_query` instead — always populated.
- `clickhouse/clickhouse-server:25.5` image refuses default user without
  password: must set `CLICKHOUSE_USER`/`CLICKHOUSE_PASSWORD` env in compose.
- clickhouse-connect uses client-side `%(name)s` substitution only when
  `parameters` is non-empty — a literal `%` (e.g. `LIKE '.inner%'`) breaks
  depending on whether params are passed. Avoid `%` in SQL: `startsWith()`.
- `Merge` engine (unions tables matching a regex over a database) has no
  statically resolvable target from DDL params — known gap, not parsed.
- `Distributed(cluster, database, table[, sharding_key])`: `database` param
  is frequently `currentDatabase()` (a function call, not a literal) or `''`
  — a naive "stop at first `)`" regex truncates on the nested call's own
  paren. Parse with a balanced-paren scan instead. Verified against a live
  25.5 server: `create_table_query` always normalizes args to quoted string
  literals regardless of how they were written in the original `CREATE`.
- `WINDOW VIEW` couldn't be verified against a live server: ClickHouse 25.5's
  default query analyzer rejects the experimental feature outright
  (`UNSUPPORTED_METHOD`, needs `allow_experimental_analyzer=0`). The
  `_KIND_BY_ENGINE` mapping itself is a static one-line lookup (no parsing
  risk), so this was accepted unverified live — flag if upgrading past the
  engine's experimental phase.

- `/docker-entrypoint-initdb.d` scripts run only on an empty data dir. Seeding
  instead uses a one-shot `clickhouse-init` compose service running
  `clickhouse-client --queries-file` (multiquery) after healthcheck — runs on
  every `up`, so seed SQL must stay idempotent (`IF NOT EXISTS` everywhere).
- `docker compose up -d --wait` FAILS (exit 1) when a one-shot service exits,
  even with code 0 — and a trailing `| tail` masks the exit code, which hid
  this for a while. Wait only on long-running services
  (`up -d --wait clickhouse`) and run one-shots via `compose run --rm`.

## Stack

- fastmcp tools are testable without a transport: `async with Client(mcp_instance)`
  runs in-memory; wrap in `asyncio.run()` — no pytest-asyncio needed.
- Postgres swap really is conn-string-only: SQLAlchemy JSON columns and all
  sync/label logic ran unmodified on `postgresql+psycopg://`.
- API + MCP on one host: `mcp.http_app(path="/")` → `app.mount("/mcp", it)`, and
  pass `mcp_app.lifespan` to `FastAPI(lifespan=...)` — without the lifespan the
  streamable-http session manager never starts and every `/mcp` call 500s. Probe
  with a POST carrying `Accept: application/json, text/event-stream`; endpoint is
  `/mcp/` (trailing slash). stdio `ohmydb mcp` stays for local-process clients.
- No Alembic here: adding `EntityRow.upstream`/`downstream` columns needed a
  `task clean`-equivalent (drop `ohmydb.sqlite` + resync) locally —
  `Base.metadata.create_all()` only creates missing *tables*, it won't add
  columns to an existing one. Matches the "latest state only, sync replaces"
  decision — flagged explicitly rather than adding a migration framework for
  a non-mission-critical service. Next schema-adding change (e.g. backlog
  item 3's `LabelRow.source`) hits the same wall.

## Docker

- `uv sync` installs the project **editable** by default (a `.pth` pointing at the
  build dir); in a copy-out multi-stage image the source dir is gone → `No module
  named 'app'`. Use `uv sync --no-editable` so the package lands in site-packages
  and the venv is self-contained (can then drop the `COPY app/` from the final stage).
- python:3.12-slim ships a system pip at `/usr/local/bin/pip` outside the venv;
  copying only the venv doesn't remove it. `RUN python -m pip uninstall -y pip
  setuptools` in the final stage to truly drop it.
- `create_all` opens/creates the sqlite file at startup, so WORKDIR must be
  writable by the non-root user (`chown app /app`) or serve crashes with
  "unable to open database file".
- `uv sync --no-editable` caches the built project wheel keyed on **version**,
  and the `--mount=type=cache` uv cache survives `docker build --no-cache` — so
  code edits without a version bump silently ship a stale wheel. Add
  `--reinstall-package <name>` on the project sync step to force a rebuild.
- Config not baked into the image: default path resolves `--config` >
  `OHMYDB_CONFIG` env > `config.yaml`; image sets `OHMYDB_CONFIG=/etc/ohmydb/
  config.yaml` and the config is mounted there. `CLICKHOUSE_USER/PASSWORD[__KEY]`
  env override per-cluster config (resolved in the CH adapter builder, not core
  config.py, to keep core db-agnostic — `cluster_env_key()` sanitization lives
  next to that lookup; `load_config()` only calls it to fail fast on a
  collision, e.g. `prod-eu` and `prod_eu` both sanitizing to `PROD_EU`).
  Per-cluster `extra` dict is spread into `clickhouse_connect.get_client(**extra)`
  for secure/verify/timeout tuning.

## Web/UI (removed 2026-07-19, notes kept for future FE work)

- Headless UI smoke-testing without installing browsers: playwright pip pkg +
  `executable_path` to system Chrome. For canvas graphs (cytoscape) expose the
  instance on `window` and drive nodes via `.emit('tap')` — no DOM to click.
- First Cytoscape+dagre attempt judged not user-facing ready: chaotic node
  placement, unreadable on big schemas. Next attempt needs real layout research
  (ELK? grouping by database? collapsing?), not just a dagre default.

## Environment

- colima VM can leave stale disk lock after crash ("in use by instance");
  `colima stop -f` then `colima start` releases it.
- `uv run <cmd> &` backgrounded then `kill`ed by its captured `$!`: that PID is
  the `uv run` wrapper, not the actual server process — the child survives
  and keeps the port bound. Killing left a stale `ohmydb serve` alive on
  :8080 that silently served pre-change code while a second `serve` failed
  to bind and exited. Find the real PID via `lsof -i :<port>` (or `pgrep -f`)
  before trusting `kill $!`, especially when manually re-verifying a change
  against a live server between edits.
