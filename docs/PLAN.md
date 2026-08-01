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
| Viz | **Restarted 2026-07-31** (see Planned below). First Cytoscape+dagre attempt dropped 2026-07-19 (chaotic layout, unreadable). Second attempt: mind-elixir-core (vanilla JS, no build step), served as a static page from `app/web/`, FastAPI-mounted at `/`. |
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
- **M10 (2026-07-26)**: MCP token-cost reduction. `get_schema_graph` and
  `find_tables` (`app/mcp.py`) now return `{columns, rows}` (array-of-arrays)
  instead of one dict per node/match — cuts repeated key-name tokens at scale
  (confirmed no external consumers of the old dict-keyed shape, so no
  versioning needed). `get_schema_graph` additionally drops `cluster` (the
  caller already passed it — same redundancy class as M5's `synced_at` hoist)
  and `id` (internal PK, meaningless to any tool — all lookups go by
  cluster/database/name) from each row. Transform lives only in the MCP
  wrapper, not `graph_payload`/`list_entities`, which still back plain HTTP
  with self-describing dicts. `get_table_relations` left as-is — its
  upstream/downstream lists are small in practice, not the hundreds-scale
  case this was gated on.
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

- **M11 (2026-07-31)**: optional GET filters — `get_relations` gained
  `direct_only` (`GET /entities/{...}/relations?direct=`, MCP
  `get_table_relations(direct=)`) restricting upstream/downstream to 1-hop
  neighbors instead of the full transitive closure. `graph_payload` and MCP
  `find_tables` gained a shared `q` filter (`store/queries.py: _matches`):
  substring across name/database/label key/value, or an exact `key:value`
  label lookup when `q` contains a colon (`find_tables`'s inline substring
  check was lifted into this shared helper, dropping the duplicate). Convention
  for future filters (see `ARCHITECTURE.md`'s common-changes table): optional
  kwarg on the `store/queries.py` function, passthrough param in `api.py`/
  `mcp.py` — filter logic stays in `store/queries.py` only, so it's
  automatically DB-agnostic and shared between HTTP and MCP.

- **M12 (2026-07-31)**: REST endpoints moved under `/api` (`app/api.py`:
  `APIRouter(prefix="/api")`, `app.include_router(api)`) — `/clusters`,
  `/graph/{cluster}`, `/entities/...`, `/labels/...`, `/sync` are now
  `/api/...`. MCP mount (`/mcp`) untouched — separate protocol, and moving it
  would break `.mcp.json.example`/deployed configs. Done ahead of the
  frontend work below so the static page can be served from `/` without
  colliding with API routes.
- **M13 (2026-07-31)**: filter panel — `app/web/index.html`, single static
  page (no build step), served by `app/api.py`'s new `GET /` (`FileResponse`,
  mirrors the dropped Cytoscape page's serving pattern). Cluster selector
  hits `GET /api/graph/{cluster}`; database/name/kind/engine/refreshable/
  label filters run client-side over the fetched node list — no backend
  changes (see rationale in Planned section below, still accurate for
  M14). Row click is a stub pending M14. Verified with a real headless
  browser against `task up`'s seeded ClickHouse: each filter dimension
  exercised, row counts confirmed correct, no console errors, screenshots
  checked.
- **M14 (2026-08-01)**: direct-relations view. Row click fetches
  `GET /api/entities/{cluster}/{database}/{name}/relations?direct=true` and
  renders a mind-elixir tree via the vendored `app/web/vendor/mind-elixir.js`/
  `.css` (MIT, from `mind-elixir` npm's ESM `dist/MindElixir.js` build —
  self-contained, no bare imports); `app/api.py` gained
  `app.mount("/vendor", StaticFiles(...))` to serve it. Root = the selected
  entity (`name`/`kind`/`engine` in the label), two child branches
  "Upstream (n)"/"Downstream (n)" populated from the response. Clicking a
  rendered entity node re-centers (refetches that node's own direct
  relations, `mind.refresh()`s the tree) via mind-elixir's `selectNodes` bus
  event, filtered to ids prefixed `e:` (group nodes "Upstream"/"Downstream"
  use a `g:` prefix and are inert, so clicking them is a no-op). Verified
  with a headless browser against `task up`'s seeded ClickHouse: rendered
  root/branch/leaf text cross-checked against the same entity's raw
  `relations?direct=true` JSON, re-centering confirmed by clicking a leaf
  node, zero console errors.
- **M15 (2026-08-01)**: frontend UI pass. `app/web/index.html` split into
  `app.css`/`app.js` (thin HTML shell); `app/api.py`'s serving simplified to
  one `app.mount("/", StaticFiles(directory=WEB_DIR, html=True))` —
  supersedes M13/M14's custom index route + separate `/vendor` mount
  (`StaticFiles` serves nested dirs and `html=True` covers `/` → `index.html`
  on its own). Header reordered: refresh button is now the rightmost
  element, synced-at immediately left of it. Relations panel gained a close
  button (`×`, hides the panel; the `mind` instance stays alive for cheap
  reopening). Graph node labels show `database` instead of `kind` (kind was
  redundant with the branch grouping; database wasn't shown anywhere in the
  tree before). Layout rebuilt as a fixed-height app shell (`body{overflow:
  hidden}`, `#split` flex column) so the browse pane (filters+table) and the
  relations pane can be resized against each other via a `row-resize` drag
  handle (`#split-handle`, plain pointer events, no library — the handle
  only appears once relations is open, and dragging just sets an explicit
  px `flex-basis` on the browse pane while the relations pane keeps
  `flex:1` to fill the remainder). `#filters` capped at `max-height:200px`
  with its own scroll so a long label-filter list can't push the rest of
  the page around. `render()` still has no pagination/limit — the browse
  pane scrolls independently so the full filtered result set is always in
  the DOM. Verified with a headless browser against `task up`: asset
  content-types confirmed, header order, database-in-label, drag-resize
  (measured browse-pane height change), close-then-reopen, zero console
  errors.
- **M16 (2026-08-01)**: light/dark/auto theme switch, top-right corner of
  the header (rightmost — after the M15 refresh button). Page CSS vars
  restructured to a 3-way selector split: base `:root` = light, `@media
  (prefers-color-scheme: dark) { :root:not([data-theme]) {...} }` = auto
  following the OS, `:root[data-theme="dark"] {...}` = explicit override
  independent of OS (explicit "light" needs no separate block — it's just
  the base `:root` values with `:not([data-theme])` no longer matching, so
  the media-query override is skipped). Choice persisted to
  `localStorage["oh-my-db-theme"]`; a small inline script in `index.html`'s
  `<head>` applies a saved non-auto choice before first paint (avoids a
  flash of the wrong theme) — its hardcoded key literal has to match
  `THEME_KEY` in `app.js` (documented in both places, no clean way to share
  a constant between an inline `<head>` script and an ES module without
  more machinery than this is worth).
  - Gotcha caught after first pass: mind-elixir renders into its own
    `.map-container` with its own theme object (bgcolor/text color per
    node) — it does not inherit the page's CSS custom properties, so the
    graph stayed light while the rest of the page went dark. Fixed by
    passing `theme: MindElixir.THEME`/`DARK_THEME` at construction and
    calling `mind.changeTheme(...)` from `applyTheme()` on every switch
    click, plus a `prefers-color-scheme` `MediaQueryList` change listener
    so "auto" also reacts to a live OS theme flip (mind-elixir only
    auto-detects the OS preference once, at construction).
  - Verified with a headless browser against `task up`: OS=dark defaults
    to dark with no saved choice; explicit "light" click overrides OS=dark;
    choice survives reload; explicit "dark" click confirmed via the mind
    map's own computed `background-color` (not just the page chrome) to
    catch exactly the gotcha above; back to "auto" clears the `data-theme`
    attribute; fresh OS=light context defaults to light.
- **M17 (2026-08-01)**: UI smoke tests, `tests/test_web_ui.py`. `playwright`
  added as a dev dependency (`uv add --group dev playwright`, one-time
  `uv run playwright install chromium`) — auto-skips like
  `test_clickhouse_integration.py` when Chromium isn't installed (checked by
  actually launching+closing it once), so `Dockerfile.example`'s test stage
  (no browser, no network) still passes. A `live_server` fixture runs
  `uvicorn.Server` in a background thread on a random port — `TestClient`
  can't be pointed to by a real browser, it's in-process HTTP only — seeded
  with the same events→mv fixture shape as `test_api.py`. Two tests: table
  renders both seeded entities; clicking a row renders the mind-elixir tree
  with the right root topic (`mv\nanalytics`, confirming M15's
  database-over-kind label) and branch counts (`Upstream (1)`,
  `Downstream (0)`). Deliberately just a smoke pass, not full UI coverage —
  matches AGENTS.md's "minimal test coverage" rule; the manual
  headless-browser pass per milestone still exists for anything deeper.
- **M18 (2026-08-01)**: labels on the graph. Node topics switched from plain
  text to HTML (`app/web/app.js`: `new MindElixir({..., markdown: (text) =>
  text, ...})` — an identity function is enough to opt into mind-elixir's
  `innerHTML` topic path instead of `textContent`) so each entity's labels
  render as one swatch+value line per label, colored by key. Colors come
  from the dataviz skill's validated default categorical palette
  (`references/palette.md` — same slots this page's own light/dark surface
  vars already use); a label key is assigned the next unused palette slot
  the first time it's seen and keeps it for the session (`labelKeyOrder` in
  `app.js`), never reassigned. A small translucent legend block floats
  top-left over the graph (`#legend`, `position: absolute`, background
  `color-mix(in srgb, var(--surface) 70%, transparent)`) mapping key →
  swatch; nodes show only the label *value* next to the matching swatch
  (key isn't repeated on the node — it's a `title` tooltip instead), per
  the dataviz skill's "identity is carried by the mark, text stays in
  normal ink" rule. A `lastRel` cache lets a theme switch rebuild the
  current tree's topics/legend from cached data (no refetch) so swatch
  colors track light/dark too — `mind.refresh()` alone doesn't push a
  theme change, so `renderTree`'s reuse branch also calls
  `mind.changeTheme()` explicitly (gap found and fixed the same pass).
  Also fixed a pre-existing stored-XSS gap noticed while adding HTML
  escaping for the new label swatches: the browse-pane table's `innerHTML`
  interpolated entity/label values unescaped — labels are attacker-settable
  via `PUT /api/labels` with no validation. All of `render()`'s
  interpolation now goes through a shared `escapeHtml()`.
  - Real bug caught only by measuring live (not by eyeballing a static
    screenshot): dragging the split handle to grow the relations pane left
    the mind-elixir canvas its *original* size, background included — a
    visible seam of the wrong shade below the frozen map. Root cause: the
    new `#mindmap-area` wrapper (added this milestone so `#legend` could
    float over the graph) sized `#mindmap` via `position: absolute;
    inset: 0`, but mind-elixir's own constructor unconditionally sets
    `style.position = "relative"` on whatever element it's given — an
    inline style, so it silently wins over the stylesheet's `absolute` and
    `inset: 0` does nothing. Fix: `#mindmap-area` became `display: flex`
    and `#mindmap` just `flex: 1` — flex sizing doesn't care about the
    `position` property, so it fills correctly regardless of mind-elixir's
    override. Confirmed via `getBoundingClientRect()` on `#mindmap-area`,
    `#mindmap`, and `.map-container` before/mid/after a scripted drag (all
    three now track exactly), not just a background-color check (which
    passed even on the broken version, since `#mindmap-area`'s own
    background was fine — mind-elixir's inner canvas is what wasn't
    resizing).
  - Verified with a headless browser: multi-label/multi-key rendering
    (legend + node swatches, colors match between the two), value-only node
    display, light/dark swatch recolor on theme switch, and the drag-resize
    fix above.

Storage schema, sync algorithm, and ClickHouse edge-extraction rules are no
longer described here — read the code (`app/store/db.py`, `app/store/repo.py`,
`app/adapters/clickhouse.py`, all short) plus `LEARNINGS.md` for the
non-obvious parts. This doc stays forward-looking from here down.

## Planned: frontend visualization

Restarting FE work dropped 2026-07-19 (see Decisions above). Library
evaluated: **mind-elixir-core** (vanilla JS mind-map renderer, no framework/
build dependency) over its **mindmapcn** wrapper (rejected — pulls in
React+Tailwind+shadcn+bundler, this repo has no build tooling and stays
"tiny and simple" per AGENTS.md). Served as a static page in `app/web/`
(vendored JS, same pattern as the dropped Cytoscape attempt), mounted by
`app/api.py` at `/` — safe now that all REST routes moved to `/api` (M12).

mind-elixir's data model is a strict single-root tree (parent → children),
not a DAG. Resolution for when that matters (an entity that's a shared
upstream/downstream of several others, rendered together): render it once
per branch (duplicated) and draw a dashed cross-link between the duplicate
instances via mind-elixir's node-linking feature, rather than switching
renderers. Not needed for M13/M14 below — a single entity's *direct* (1-hop)
upstream/downstream can't contain the same entity twice, so it's a clean
tree already. Becomes relevant once a milestone renders multiple entities'
relations together (transitive/multi-hop graph) — deferred to backlog.

No backend/API changes needed for M13 or M14: `graph_payload` node briefs
already carry every field the filter panel needs (cluster is the endpoint
param; database, name, kind, engine, refreshable, labels are per-node), and
`GET /api/entities/.../relations?direct=true` already returns exactly the
1-hop upstream/downstream set M14 renders. Filtering is client-side JS over
an already-fetched cluster payload.

M13 (filter panel) and M14 (direct-relations view) both shipped — see
Shipped list above. Nothing left planned here; the multi-entity/DAG case
this section flagged is tracked in Backlog below.

## Backlog

- **Frontend: transitive/multi-entity graph view**: expand M14 beyond one
  entity's direct relations — full filtered graph rendering, multi-hop
  walks, or overlaying several entities at once. This is where the
  mind-elixir tree-vs-DAG mismatch (see Planned section above) actually
  bites; needs the cross-link-overlay approach (or a different renderer)
  implemented, not just decided.
- **Auth for API/MCP (optional)**: opt-in auth (e.g. bearer token via config)
  guarding mutating endpoints (`POST /sync`, `PUT`/`DELETE /labels`) and
  reads. Off by default — most deployments are localhost-only; a config flag
  turns it on for anything exposed past that.
- **`find_tables`/`q` scale**: `app/store/queries.py: list_entities` loads
  every entity across all clusters into memory and filters in Python (via
  `_matches`), no limit/pagination. Fine at current catalog size; add a
  result limit (and maybe cluster-scoping) once it isn't.
- **`Merge` engine edges**: `Merge(db, regex)` has no statically resolvable
  target from DDL params (known gap, see LEARNINGS.md). Resolve the regex
  against catalog tables at sync time to emit best-effort `reads_from` edges.
- **Sync scheduler (config-gated)**: optional periodic re-sync (interval in
  config), off by default — current model is CLI/POST-triggered only
  (locked decision above). Lets the catalog stay fresh without relying on an
  external cron/CI trigger being wired up.
- **Observability**: structured logging + basic metrics around sync
  (duration, per-cluster success/failure) and API/MCP calls. Right now a
  sync failure only surfaces as `str(e)` in the `/sync` HTTP response — no
  visibility if nothing is actively calling it.

Touches for the last resolved item (M10, array/CSV encoding for
`get_schema_graph`/`find_tables`): `app/mcp.py` only (see above — not
`graph_payload`).
