# Implementation Plan

## Goal

Replace grepping a huge `database_name.sql` schema dump with a small service that
stores table schemas and their interconnections (MVs, views, dictionaries,
refreshable MVs, aggregation tables), visualizes them, and serves them to AI
agents over API/MCP.

Structure/data-flow/module map: see [ARCHITECTURE.md](../ARCHITECTURE.md).
Gotchas: see [LEARNINGS.md](LEARNINGS.md).

## Decisions (locked)

| Topic | Decision |
|---|---|
| Ingestion | Live DB introspection via `system.tables` etc. CI triggers re-sync after migrations. |
| History | Latest state only; sync replaces. History lives in git dumps. |
| Labels | Stored in separate identity-keyed table (cluster, database, table_name) — survives entity drop/recreate; orphan labels hidden from output, not deleted. |
| Viz | **Dropped 2026-07-19**: first Cytoscape page not user-facing ready. Service is API+MCP only; FE research/implementation deferred. |
| Storage | SQLite first via SQLAlchemy; Postgres later = connection string swap (done). |
| Sync trigger | CLI command + POST /sync endpoint (same code path). No scheduler. |
| Scope | Multi-cluster from day one. Entities namespaced by cluster. |
| Detail | Structured columns (name/type/comment) + raw DDL + attrs (engine, keys, refreshable). |

## Shipped (milestones)

- **M1 (2026-07-18)**: core models, ClickHouse adapter, SQLite store, CLI, docker-compose + seed, tests.
- **M2 (2026-07-18)**: FastAPI `/graph` + `/entities/{...}`; viz page dropped 2026-07-19 (not user-facing ready).
- **M3 (2026-07-18)**: labels CRUD, `POST /sync[?cluster=]`, `ohmydb mcp` stdio server, Postgres backend via compose profile.
- **M4 (2026-07-19)**: transitive upstream/downstream relations — `GET /entities/{...}/relations`, MCP `get_table_relations`.
- **M5 (2026-07-25)**: ClickHouse engine coverage (`WindowView`/`LiveView` →
  `VIEW`, `Distributed` → `reads_from` edge, `attrs.external` allowlist);
  per-cluster credentials (`CLICKHOUSE_USER__<KEY>`/`PASSWORD__<KEY>` env,
  collision check in `load_config`); cluster-scoped `/graph/{cluster}` +
  `GET /clusters` + MCP `list_clusters()`; relations precomputed at sync
  time (`EntityRow.upstream`/`downstream`, `get_relations` now a lookup);
  `find_tables` no longer fetches edges; `graph_payload` gained a
  cluster-level `synced_at` (one value, not per node); `get_relations`
  dropped its `edges` list (redundant — membership in upstream/downstream
  already implies the dependency direction).
- **M6 (2026-07-25)**: unit-test gate as its own `Dockerfile.example` stage —
  `docker build` now fails on a broken test, not just CI. Verified locally:
  clean build runs the full suite inside the `test` stage (integration tests
  auto-skip, no live ClickHouse in the build sandbox); an injected failing
  test aborts the build with the pytest failure in the error output.
- **M7 (2026-07-25)**: Alembic replaces `Base.metadata.create_all()` —
  supersedes the "drop and resync the catalog" upgrade path from M5/M6
  (that caveat no longer applies; schema changes are now a migration, not a
  wipe). `app/store/db.py: run_migrations()` runs `alembic upgrade head` on
  the engine's own connection (required for in-memory sqlite — a second,
  separately-opened `sqlite://` connection is a different empty database)
  and is called from `make_session_factory()`, so `sync`/`serve`/`mcp`/tests
  all auto-migrate with no separate step. `task db:revision -- "message"`
  autogenerates new migrations from `app/store/db.py` model changes (must be
  run against a catalog already at head — an empty/fresh db just re-diffs
  the full schema). One baseline revision (`app/migrations/versions/`)
  captures the schema as of M5. Migration scripts live inside the `app`
  package (`app/migrations/`, not the repo-root `alembic/` convention `init`
  scaffolds by default) so they resolve from a non-editable install too —
  Dockerfile.example's final stage only ships the built venv, not the repo
  checkout; a `Path(__file__).parents[N]`-style repo-root lookup would have
  broken there. `alembic.ini` at the repo root still exists, purely for the
  dev CLI (`task db:revision`, manual `alembic upgrade head`). Verified end to end, not just unit-tested: seeded a real
  sqlite file via `make_session_factory`, wrote a scratch "add a column"
  migration, re-opened the same file, and confirmed the new column existed
  *and* the seeded row survived — the thing `create_all` could never do.
- **M8 (2026-07-25)**: `graph_payload` (`GET /graph/{cluster}`, MCP
  `get_schema_graph`) dropped its `edges` list — same redundancy already
  resolved for `get_relations` in M5: an entity's dependency direction is
  fully captured by its own `upstream`/`downstream` fields, so a caller
  needing that for one entity should call `get_table_relations` instead of
  walking a graph-wide edge list. `/graph` now returns node briefs only.
- **M9 (2026-07-25)**: config-driven auto-labeling. New optional
  `label_rules` config key, global (`AppConfig.label_rules`) and per-cluster
  (`ClusterConfig.label_rules`), matched via `app/core/labeling.py:
  apply_label_rules()` (engine/kind exact match, name_pattern/database_pattern
  regex; all matching rules apply and accumulate; same-key conflicts resolve
  last-rule-wins). `LabelRow` gained a `source` column (`manual` default,
  `auto` for rule-derived rows — migration `6ab50cc9755f`, existing rows
  backfilled `manual` via `server_default`). `run_sync()` computes auto
  labels from the introspected entities and calls `store/repo.py:
  sync_auto_labels()`, which replaces the cluster's `source=auto` rows every
  sync but skips any key that already has a `source=manual` row for that
  identity — a manual `PUT /labels` always wins, and re-applies `source=
  "manual"` even if it's overwriting a previously auto-derived row. Reads
  (`get_entity`, `graph_payload`, `get_relations`) still return labels as a
  flat `{key: value}` dict — `source` isn't surfaced there; exposing it would
  change the label shape everywhere labels appear, so it's left for a
  follow-up if a caller actually needs to distinguish auto vs. manual.
  Verified end to end against the seeded local ClickHouse: global +
  per-cluster rules both applied on `ohmydb sync`, and a manual label set via
  `set_label` survived a second sync where its rule-derived value differed.

Storage schema, sync algorithm, and ClickHouse edge-extraction rules are no
longer described here — read the code (`app/store/db.py`, `app/store/repo.py`,
`app/adapters/clickhouse.py`, all short) plus `LEARNINGS.md` for the
non-obvious parts. This doc stays forward-looking from here down.

## Backlog

Each entry below is written to be picked up by another agent with no other
context than this repo. Where a design decision is genuinely open, a
recommendation is given — take it unless you find a concrete reason not to.

### 1. Array/CSV encoding for `get_schema_graph` (MCP token cost, on hold)

Deferred from M5's cluster-scoping work (see LEARNINGS.md "Stack" for the
rest of that token-cost research — typed returns don't shrink payload size,
no MCP-protocol pagination exists for tool *results*, only for
`list_tools`/`list_resources`).

**Entity-count gate is now satisfied**: production clusters expect 200+
tables across 2 clusters, each with multiple upstream/downstream deps — the
hundreds+ threshold this item was waiting on. **But a second, harder blocker
surfaced on review (2026-07-25) and isn't resolved**: other agents/clients
may already depend on `get_schema_graph`'s current dict-keyed node shape.
Positional array encoding is a breaking wire-format change for anyone already
integrated — swapping it silently risks correctness (silent misread of a
shifted column) for consumers we don't control, not just a client-side
update. Before picking this up: identify who/what currently calls
`get_schema_graph` in practice, and design either a versioned/opt-in tool
variant or confirm there are no external consumers yet. Don't just re-check
entity counts and proceed — that gate is cleared, this one isn't.

Also still true: array-of-arrays/CSV-style encoding needs `output_schema=None`
or a `{columns, rows}` wrapper since fastmcp's auto schema requires an object.
Apply the transform only in the MCP wrapper (`app/mcp.py`), not inside
`graph_payload()` itself — that function also backs `GET /graph/{cluster}`
over plain HTTP, which has no token-cost reason to lose its self-describing
dict shape.

Touches: `app/mcp.py` only (see above — not `graph_payload`).

