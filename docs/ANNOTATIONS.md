# Annotations

Introspection tells an agent names, types, DDL, column `COMMENT`s and lineage.
It doesn't say what a row means, which units a column uses, what an enum value
stands for, how tables join (ClickHouse has no foreign keys), which table is
deprecated, or that a `SummingMergeTree` needs `sum()`. Agents guess, and the
guesses produce wrong SQL.

The annotation layer fills that gap with **human-curated YAML kept in a git
repo**: changes go through MR review, with history and CODEOWNERS. ohmydb
pulls the repo into its catalog and serves it over MCP, the HTTP API and the
frontend. Everything is off unless `annotations.enabled` is true.

Write path (agent proposals as MRs, drift stubs for new tables) is milestone
M24 and not shipped yet.

## Repo layout

```
<root>/                      # repo subdir `path` (default "" = repo root)
  _global.yaml               # optional: version, query_hints, ignore
  <db>/_database.yaml        # optional: description, query_hints
  <db>/<table>.yaml          # one file per table / view / mat_view / dictionary
```

The file path is the identity: `app/events.yaml` annotates `app.events`.
Other files at the root (README, CODEOWNERS) are ignored, as are dot-dirs.
Inside a db dir, `*.yml` (use `.yaml`), any `_*.yaml` other than
`_database.yaml`, and nested directories are errors. Sample tree:
[`seed/annotations/`](../seed/annotations/).

## Table file

```yaml
# app/events.yaml
description: |              # FIRST LINE = summary (listings, searched by q / find_tables)
  Raw user interaction events from the web app.
  ~2B rows/day, 90d TTL.
grain: one row per client event
status: active              # active | deprecated
use_instead: ""             # db.table to prefer (for deprecated or expensive tables)
owner: team-web
query_hints:                # gotchas: FINAL, partition/sorting-key filters, units, dedup
  - Always filter on ts (sorting key).
  - For hourly counts use analytics.events_hourly.
columns:                    # mapping keyed by column name
  ts: {description: "Event time, UTC"}
  event_type:
    description: Interaction kind
    values: {click: element click, view: page view, purchase: checkout done}  # or a plain list
relationships:              # join paths, same cluster
  - to: app.users           # must be db.table
    from_columns: [user_id] # same length as to_columns
    to_columns: [id]
    cardinality: many_to_one   # optional: many_to_one|one_to_many|one_to_one|many_to_many
    description: ""            # optional
examples:                   # verified question -> SQL pairs
  - question: Purchases per day, last 7 days
    sql: |
      SELECT toDate(ts) AS d, count() FROM app.events
      WHERE event_type = 'purchase' AND ts >= today() - 7 GROUP BY d ORDER BY d
```

Every field is optional. Empty strings, lists and maps are dropped on load, so
a file that is empty after that (an unfilled stub) counts as unannotated.

`_global.yaml`: `version: 1` (optional; any other value aborts the pull),
`query_hints: [str]`, `ignore: [regex]` (`re.search` against `db.table`; such
tables never get drift stubs — M24). `_database.yaml`: `description`,
`query_hints`.

### YAML pitfalls

- **Commas in flow maps split the value.** `{description: Event time, UTC}`
  parses as two keys, and the strict schema rejects `UTC`. Quote the value
  (`{description: "Event time, UTC"}`) or use block style.
- Unknown keys are errors (typos must fail, not vanish silently).
- Numeric enum keys (`1: active`) load as strings. Booleans (`true`) and dates
  (`2024-01-01`) do not; quote them. Files are read as YAML 1.2, so `yes`/`on`
  stay strings.

## Clusters

One shared root (`path`) serves every cluster. `cluster_paths` gives a
cluster its own root with **file-level fallback**: a file missing there is
taken from the shared root (this applies to `_global.yaml` and
`_database.yaml` too). An override root may live inside the shared root, e.g.
`path: ""` with `cluster_paths: {prod: clusters/prod}`; the shared scan then
skips the `clusters/` dir. Don't name a database like such a dir.

## Config

```yaml
annotations:
  enabled: false            # master flag; false = fully inert
  repo: https://gitlab.example.com/data/schema-annotations.git   # or a local dir
  ref: main                 # branch to read
  path: ""                  # shared root inside the repo/dir
  cluster_paths: {}         # {cluster: root}, falls back to `path` per file
  pull_interval: 300        # serve only, seconds; 0 = no polling
```

`repo`: `https://` or `file://` = git remote; no `://` = local directory, read
as-is (handy for local dev; `config.example.yaml` points at
`seed/annotations`). Any other scheme, credentials in the URL, an unknown
`cluster_paths` cluster, or a negative `pull_interval` fail config load.

Token: env `OHMYDB_ANNOTATIONS_TOKEN` only (empty = unset). A `token:` key in
the config is rejected.

## Refresh

- `ohmydb sync` and `POST /api/sync` pull after the schema sync. An
  annotation failure is reported (stderr / server log) but never fails the
  schema sync, and the `/api/sync` response doesn't change.
- `ohmydb serve` polls in the background: `git ls-remote` (or a hash of the
  local dir) every `pull_interval`, full pull only when it changed. Errors are
  logged and retried next interval. stdio `ohmydb mcp` doesn't poll.
- `ohmydb annotations pull` pulls now.

Each pull is a fresh shallow clone into a temp dir (no persistent cache). A
file with errors is skipped and reported; the rest loads. A fatal error
(clone failure, missing root, unsupported `version`) keeps the last good
catalog copy untouched.

## What agents see

- `get_table` / `GET /api/entities/...`: `annotation` (the doc without
  `columns`, plus the repo `path`); each column gains `description`/`values`.
  Annotations for columns that no longer exist are ignored.
- `get_schema_graph`, `find_tables`, `/api/graph`, `/api/search`: each row
  gains `summary` (`""` if unannotated) and `status` (`active`/`deprecated`,
  `""` if unannotated); `q` / `query` also matches `summary`.
- `get_schema_graph` / `/api/graph`: top-level `annotations: {query_hints,
  databases: {db: {description, query_hints}}}`, when non-empty.
- Frontend: the schema panel shows the annotation block and a `description`
  column.

With the flag off, every payload is exactly the pre-feature shape.

## Annotation repo CI and editors

```bash
ohmydb annotations validate annotations/            # exit 1 + file: key: message on any error
ohmydb annotations validate . --exclude clusters    # shared root holding override roots
ohmydb annotations validate clusters/prod           # each override root separately
ohmydb annotations schema > annotations.schema.json # also: schema database|global
```

`validate` needs no config, so the repo's CI can run it in the ohmydb image.
For VS Code (redhat.vscode-yaml):

```json
"yaml.schemas": { "./annotations.schema.json": ["*/[!_]*.yaml"] }
```

## Git auth and security

- **The token never appears in a URL, argv, on disk, or in logs.** git gets
  it as an HTTP header via env: `GIT_TERMINAL_PROMPT=0`,
  `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=http.<scheme://host[:port]>/.extraHeader`
  (scoped to the repo host), `GIT_CONFIG_VALUE_0=Authorization: Basic
  base64("oauth2:"+token)`. git stderr is therefore safe to show in errors.
  Needs `git >= 2.31`. Internal CA: `GIT_SSL_CAINFO`. Proxy: `HTTPS_PROXY`.
- **GitLab, read-only:** project access token, role Reporter, scope
  `read_repository`.
- **GitHub, read-only (verified):** fine-grained PAT, *Only select
  repositories* → the annotation repo, Repository permissions → Contents:
  Read-only. GitHub ignores the `oauth2` username. Reads work with any git
  host that accepts HTTP basic auth with a token; writes (M24) need GitLab.
- A rejected or missing token fails with git's own message plus a hint to
  check `OHMYDB_ANNOTATIONS_TOKEN`.
- **Repo placement:** a dedicated repo gives least privilege. A subdir of
  the migrations repo (set `path`) lets schema and annotations change in one
  MR, but a write-enabled bot (M24) then has push rights there.
- **Prompt injection:** annotation text is served verbatim to LLM agents.
  Review-gated `main` is the control; also keep the strict schema and the
  `validate` CI. The frontend escapes everything.

## Ossie mapping (for a future exporter)

table → dataset (`source` = `db.table`), `query_hints` →
`ai_context.instructions`, `columns` → `fields`, `relationships` → same shape,
`examples` → `ai_context.examples`.
