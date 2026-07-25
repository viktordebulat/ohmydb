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

Storage schema, sync algorithm, and ClickHouse edge-extraction rules are no
longer described here — read the code (`app/store/db.py`, `app/store/repo.py`,
`app/adapters/clickhouse.py`, all short) plus `LEARNINGS.md` for the
non-obvious parts. This doc stays forward-looking from here down.

## Backlog

Each entry below is written to be picked up by another agent with no other
context than this repo. Where a design decision is genuinely open, a
recommendation is given — take it unless you find a concrete reason not to.

### 1. Array/CSV encoding for `get_schema_graph` (MCP token cost, follow-up)

Deferred from M5's cluster-scoping work (see LEARNINGS.md "Stack" for the
rest of that token-cost research — typed returns don't shrink payload size,
no MCP-protocol pagination exists for tool *results*, only for
`list_tools`/`list_resources`). What's left:

Array-of-arrays/CSV-style encoding (drop the ~9 repeated dict keys per node
in `graph_payload`'s `nodes` list) only pays off once real per-cluster entity
counts are genuinely in the hundreds+ — cluster-scoping (shipped M5) already
cut payload by cluster count, which was the bigger lever. **Don't build this
speculatively** — first check real per-cluster entity counts against a
production catalog after M5 has been running a while; only pick this up if
counts are actually in the hundreds+ and scoping proves insufficient on its
own. Needs `output_schema=None` or a `{columns, rows}` wrapper since fastmcp's
auto schema requires an object.

Touches: `app/store/queries.py: graph_payload`, `app/mcp.py`.

### 2. Unit-test gate as its own Dockerfile stage

**Goal**: `docker build` must fail if unit tests fail — not just CI running
`task test` separately, the *image build itself* should refuse to produce an
artifact from broken code.

**Design** (`Dockerfile.example`): add a `test` stage between `builder` and
the final runtime stage. It installs dev deps (drop `--no-dev`) on top of the
builder's venv, copies in `tests/`, runs `pytest`, and on success touches a
zero-byte marker file. The final stage then does
`COPY --from=test /tmp/tests-passed /tmp/tests-passed` — a throwaway file
whose only purpose is to force BuildKit to build and pass the `test` stage
before the final stage can complete, without pulling dev dependencies or test
files into the shipped image (final still copies the venv `--from=builder`,
which stays `--no-dev`).

```dockerfile
FROM builder AS test
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-editable --reinstall-package ohmydb
COPY tests/ ./tests/
RUN uv run pytest && touch /tmp/tests-passed

FROM python:3.12-slim
...
COPY --from=test /tmp/tests-passed /tmp/tests-passed
COPY --from=builder --chown=app:app /opt/venv /opt/venv
...
```

Integration tests (`tests/test_clickhouse_integration.py`) auto-skip without
a reachable ClickHouse, so they're a no-op inside the build sandbox — no
special-casing needed.

Touches: `Dockerfile.example` only.

### 3. Config-driven auto-labeling during sync

**Goal**: derive labels automatically from entity properties (engine, kind,
name/database pattern) instead of only manual `PUT /labels/...` calls.

**Config shape** (new optional section, per-cluster and/or global):
```yaml
clusters:
  - name: prod
    ...
    label_rules:
      - match: {engine: Kafka}
        label: {key: source, value: streaming}
      - match: {kind: dictionary}
        label: {key: source, value: dictionary}
      - match: {name_pattern: "^raw_"}
        label: {key: layer, value: raw}
```
Matchers: `engine` (exact match), `kind`, `name_pattern`/`database_pattern`
(regex — stay consistent with the adapter's own regex-heavy style). All
conditions in one rule AND together. **All matching rules apply** (labels
accumulate across rules); if two rules set the same key, last rule in the
list wins — documented, not silently ambiguous.

**Manual vs. auto labels must not clobber each other.** Add a `source`
column to `LabelRow` (`manual` default — what `PUT /labels` writes — or
`auto`). Sync re-derives all `auto` labels for a cluster every run (delete
`source=auto` rows for that cluster, reinsert from the current rule
evaluation — same replace-per-cluster pattern already used for edges in
`sync_cluster`), but **skips writing an auto label for a key that already has
a manual label** for that identity, so a user's manual edit always wins.

**Where it lives**: matching itself is DB-agnostic (operates on `Entity.kind`/
`engine`/`database`/`name`, all core fields) — put the rule engine in
`app/core` (e.g. `app/core/labeling.py: apply_label_rules(entities, rules) -> list[(Identity, key, value)]`),
called from `run_sync()`/`sync_cluster()`. Config parsing addition in
`app/config.py` (`ClusterConfig.label_rules`, plus an optional top-level
global list applied to every cluster before the per-cluster list).

**Open question**: global rules vs. per-cluster rules both apply in v1, with
no override semantics between them (global runs first, per-cluster can add
more matching labels but not suppress a global one) — keep it additive-only
until there's a concrete need for overrides.

Touches: `app/config.py`, `app/core/` (new module), `app/store/db.py`
(`LabelRow.source` column — same no-Alembic migration caveat as M5's
`upstream`/`downstream` columns, see LEARNINGS.md "Stack"), `app/store/repo.py`,
`app/store/queries.py` (labels reads should probably expose `source` too).
