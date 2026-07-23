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
  config.yaml` and the config is mounted there. `CLICKHOUSE_USER/PASSWORD` env
  override per-cluster config (resolved in the CH adapter builder, not core
  config.py, to keep core db-agnostic). Per-cluster `extra` dict is spread into
  `clickhouse_connect.get_client(**extra)` for secure/verify/timeout tuning.

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
