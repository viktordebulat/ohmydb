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

Storage schema, sync algorithm, and ClickHouse edge-extraction rules are no
longer described here — read the code (`app/store/db.py`, `app/store/repo.py`,
`app/adapters/clickhouse.py`, all short) plus `LEARNINGS.md` for the
non-obvious parts. This doc stays forward-looking from here down.

## Backlog

Each entry below is written to be picked up by another agent with no other
context than this repo. Where a design decision is genuinely open, a
recommendation is given — take it unless you find a concrete reason not to.

### 1. Extend ClickHouse engine coverage beyond `_KIND_BY_ENGINE`

**Current state** (`app/adapters/clickhouse.py`): `_KIND_BY_ENGINE` maps only
`MaterializedView`, `View`, `Dictionary`; every other engine (the whole
MergeTree family, `Distributed`, `Kafka`, `RabbitMQ`, `S3`, `URL`, `MySQL`,
`PostgreSQL`, `HDFS`, `ODBC`, `Merge`, `Buffer`, `WindowView`, `LiveView`, ...)
falls through to `EntityKind.TABLE`. `engine` (the raw string) is preserved on
every `Entity` either way, so nothing is silently lost — but two things are:

- **Lineage for `WindowView`/`LiveView`**: these are continuous-query engines
  like MVs, but since they don't map to `MAT_VIEW`/`VIEW`, the `FROM`/`JOIN`
  regex fallback (gated on `kind in (MAT_VIEW, VIEW)`) never runs for them —
  they lose `reads_from` edges entirely. Fix: add both to `_KIND_BY_ENGINE` →
  `EntityKind.VIEW`. Reuses the existing lineage code path, no new `EntityKind`
  needed.
- **`Distributed` proxies**: `ENGINE = Distributed(cluster, database, table[, sharding_key])`
  encodes its target as engine params, not in `FROM`/`JOIN`, so today it
  produces zero edges to the underlying local table. Needs a small parser
  (mirrors `_extract_to_target`) plus one new edge per `Distributed` table.
  Reuse `EdgeKind.READS_FROM` for it — don't add a new edge kind for one
  engine (rule: tiny and simple).
- **External-storage engines** (`S3`, `URL`, `MySQL`, `PostgreSQL`, `HDFS`,
  `ODBC`, `JDBC`, `Iceberg`, `DeltaLake`, `Hudi`, `ExternalDistributed`):
  already correctly typed as `TABLE` with `engine` preserved; consider setting
  `attrs.external = True` for a small allowlist so API/MCP consumers don't
  need to hardcode engine names client-side. Cheap, optional.
- **`Merge` engine** (unions tables matching a regex over a database): target
  tables aren't statically resolvable from DDL params — document as a known
  gap in `LEARNINGS.md`, don't try to resolve it.

Touches: `app/adapters/clickhouse.py` only (core stays agnostic — rule 3).
Extend `tests/test_clickhouse_parsing.py` with a case per engine added.
Verify against real DDL samples (docker seed or a live cluster) before
shipping, since misparsed edges are a silent-correctness risk.

### 2. Per-cluster credentials (account → cluster mapping)

**Current state** (`app/adapters/__init__.py: build_introspector`): a single
global `CLICKHOUSE_USER`/`CLICKHOUSE_PASSWORD` env pair is applied to *every*
cluster, overriding each cluster's config value identically. Doesn't work once
clusters use separate accounts.

**Recommendation: name-keyed env vars**, not the index-suffix (`_0`, `_1`)
scheme floated verbally — an index ties credentials to *array position* in
`config.yaml`, so reordering the `clusters:` list silently reassigns
credentials to the wrong cluster, and a k8s Secret keyed by index is
undebuggable. Name-keyed is self-documenting and reorder-safe:

```
CLICKHOUSE_USER__<CLUSTER_KEY>
CLICKHOUSE_PASSWORD__<CLUSTER_KEY>
```
where `CLUSTER_KEY = re.sub(r'[^A-Z0-9]', '_', cluster_cfg.name.upper())`.

Precedence per cluster: per-cluster env > global `CLICKHOUSE_USER`/
`CLICKHOUSE_PASSWORD` env (kept as a fallback for the single-cluster case) >
`config.yaml` value. Implement the lookup in `build_introspector`, not
`app/config.py` (keeps env-resolution logic next to the adapter, matching
today's pattern — see LEARNINGS "Docker" entry on why this lives in the CH
adapter builder).

**Open question to resolve, don't skip**: two cluster names can sanitize to
the same key (`prod-eu` vs `prod_eu`). Fail fast: validate for key collisions
in `load_config()` and raise with both offending cluster names.

Touches: `app/adapters/__init__.py`, `app/config.py` (collision check),
`config.example.yaml` (document the env naming convention),
`docs/LEARNINGS.md` (once shipped, note the sanitization rule as a gotcha).

### 3. Cluster-scoped `/graph`, cluster discovery, and MCP token cost

Three related changes:

- **`GET /graph` must take a cluster**, matching the existing
  `/entities/{cluster}/{database}/{name}` convention instead of dumping every
  cluster's full graph in one call. Recommend a path param —
  `GET /graph/{cluster}` — for consistency with the entity routes, required
  (no "all clusters" fallback). `graph_payload()` in `app/store/queries.py`
  needs a `cluster` filter argument. Mirror the change in MCP:
  `get_schema_graph(cluster: str)`.
- **New cluster-discovery route**, since callers now need a valid cluster name
  before they can call `/graph/{cluster}`: `GET /clusters` → configured
  cluster names (from `cfg.clusters`, not the DB — works even pre-sync), plus
  an MCP tool `list_clusters()`. Cheap, no schema change.
- **Precompute relations at sync time instead of walking the graph per read**:
  `get_relations()` (`app/store/queries.py`) currently does a full BFS over
  every entity/edge in the store on *every* call. Since sync is infrequent
  (manual/CI-triggered) and reads happen per MCP tool call, move the BFS into
  `sync_cluster()` (`app/store/repo.py`): after upserting entities/edges,
  compute each entity's transitive upstream/downstream **id sets** once and
  store them (new JSON columns on `EntityRow`, e.g. `upstream`/`downstream`).
  `get_relations()` becomes a lookup + label join, no traversal.
  - **Schema-change caveat**: there's no migration framework (Alembic) here —
    `Base.metadata.create_all()` only creates missing *tables*, it won't add
    columns to an existing `entities` table. Given the "latest state only,
    sync replaces" decision already locked above, recommend documenting
    "drop and resync the catalog" (`task clean` + resync) as the upgrade path
    for this kind of schema change rather than introducing Alembic — matches
    the "tiny and simple" rule. Flag this tradeoff explicitly to whoever ships
    it; don't silently pick it.

**MCP token-usage optimization** (the "research in parallel" ask):

#### Findings

- Scoping `get_schema_graph()` by cluster (see above) is the single biggest
  lever — bigger than any per-field trim, since it cuts payload by cluster
  count rather than a constant factor. Do it as part of this same change, not
  separately.
- Drop `synced_at` from the graph-listing node dict (`graph_payload` in
  `app/store/queries.py`) — dead weight for "what exists"/"what feeds this"
  reasoning, keep it only in `get_entity`'s full-detail payload. `id`,
  `cluster`, `database`, `name`, `kind`, `engine`, `labels` are load-bearing;
  `id` specifically is what lets edges reference nodes as ints instead of
  repeating identity triples (contrast `get_relations`'s `ident()`, which
  embeds full strings — fine at lineage-subgraph scale, wrong at full-graph
  scale).
- **Typing tool returns as pydantic/TypedDict does not shrink the wire
  payload** — confirmed in fastmcp source (`tools/base.py: convert_result`):
  a plain `dict` return already emits both a JSON-text block and an identical
  `structured_content` object today, regardless of annotation. Typing only
  affects the one-time `output_schema` advertised at session start. Don't
  spend effort here expecting per-call savings.
- MCP protocol pagination (`cursor`/`PaginatedRequestParams`) is for
  `list_tools`/`list_resources`/`list_prompts` only, not tool *call results* —
  no framework pagination to lean on for `get_schema_graph`; any limit/offset
  scheme is hand-rolled, same effort as the cluster-scoping change above so
  just do that instead of building a separate pagination layer.
- Array-of-arrays/CSV-style encoding (drop the ~9 repeated dict keys per
  node) only pays off once per-cluster entity counts are genuinely in the
  hundreds+; needs `output_schema=None` or a `{columns, rows}` wrapper since
  fastmcp's auto schema requires an object. Not worth it until scoping +
  field-trimming prove insufficient — treat as a follow-up, not part of this
  change.
- Drive-by fix, not token-related: `find_tables` (`app/mcp.py`) calls the
  full `graph_payload()` (fetches every edge too) just to discard edges —
  wasteful DB work, fix opportunistically.
- Matches Anthropic's published tool-design guidance: default to a concise
  response, make full detail opt-in (`get_table` already serves that role),
  paginate with a sane default rather than truncate silently.

#### Action items (ranked, do in this order)

1. `get_schema_graph(cluster: str)` required param + drop `synced_at` from
   the listing dict — bundle with the `/graph/{cluster}` API change above,
   one PR.
2. Fix `find_tables` to query nodes only (skip edges) — trivial, bundle in.
3. Revisit array/CSV encoding only if real per-cluster entity counts turn out
   to be in the hundreds+ after (1) ships.

Touches: `app/api.py`, `app/mcp.py`, `app/store/queries.py`, `app/store/repo.py`,
`app/store/db.py` (new columns), `docs/LEARNINGS.md` (schema-change caveat).

### 4. Unit-test gate as its own Dockerfile stage

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

### 5. Config-driven auto-labeling during sync

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
(`LabelRow.source` column — same migration caveat as item 3), `app/store/repo.py`,
`app/store/queries.py` (labels reads should probably expose `source` too).
