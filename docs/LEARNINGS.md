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
  `docker compose up --wait` accepts one-shot containers exiting 0.

## Stack

- fastmcp tools are testable without a transport: `async with Client(mcp_instance)`
  runs in-memory; wrap in `asyncio.run()` — no pytest-asyncio needed.
- Postgres swap really is conn-string-only: SQLAlchemy JSON columns and all
  sync/label logic ran unmodified on `postgresql+psycopg://`.

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
