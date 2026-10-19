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

ohmydb can also write back, only through merge/pull requests a human
reviews: agent proposals and stub files for new tables. See
[Write path](#write-path).

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
tables never get drift stubs). `_database.yaml`: `description`,
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

**Per-cluster mode**: put `{cluster}` in `path` (e.g. `path: "anno/{cluster}"`)
to give every cluster its own root, `anno/<cluster>/<db>/<table>.yaml`, with
**no shared root and no fallback**: each cluster reads its own `_global.yaml`,
`_database.yaml` and table files only, and drift stubs and new proposal files
land in that cluster's root. A cluster with no dir yet reads as unannotated
(reported in the pull errors; drift creates it). Can't be combined with
`cluster_paths`.

## Config

```yaml
annotations:
  enabled: false            # master flag; false = fully inert
  repo: https://gitlab.example.com/data/schema-annotations.git   # or a local dir
  ref: main                 # branch to read
  path: ""                  # shared root inside the repo/dir; "anno/{cluster}" = per-cluster mode
  cluster_paths: {}         # {cluster: root}, falls back to `path` per file
  pull_interval: 300        # serve only, seconds; 0 = no polling
  proposals: false          # MCP propose_annotation + HTTP proposals route
  drift_mr: false           # MR after each sync: stubs for new tables, removes orphan files
  author: "ohmydb <ohmydb@noreply.invalid>"   # bot commit identity
```

`repo`: `https://` or `file://` = git remote; no `://` = local directory, read
as-is (handy for local dev; `config.example.yaml` points at
`seed/annotations`). Any other scheme, credentials in the URL, an unknown
`cluster_paths` cluster, `{cluster}` in `path` together with `cluster_paths`,
a negative `pull_interval`, `proposals`/`drift_mr`
with a local dir, or an `author` that isn't `Name <email>` fail config load.

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

## Write path

Writes never touch the catalog or `ref` directly. Each one is a commit by
`author` on its own branch, pushed, then opened for review against `ref`
with labels `ohmydb` plus `ohmydb::proposal` or `ohmydb::drift` (scoped
labels on GitLab, created on first use; plain names on GitHub):

- **GitLab** (any host that isn't github.com): the push carries
  [push options](https://docs.gitlab.com/user/project/push_options/) that
  open the merge request and remove the source branch on merge. No API call.
- **GitHub** (`https://github.com/...` only, not GitHub Enterprise): one REST
  call after the push opens the pull request, or reuses the open one for
  the same branch and refreshes its title and description. Enable *Automatically delete head branches* in the repo
  settings to clean up merged branches. Labeling is best effort.

Nothing changes for readers until a human merges and the next pull runs.
"MR" below means either.

**Descriptions** are Markdown with a summary table, collapsible
`<details>` sections and a reviewer checklist. Proposals show the
rationale, the table and cluster, the file and the changed keys (no diff
preview: the Changes tab has it). Drift groups new tables and removed files per database. A
description is kept under about 60 KB (one GitLab push option is a single
git pkt-line, at most 65516 bytes; a GitHub PR body allows 65536 chars). A
bigger drift first caps each database's list (`… and N more`), then shows
counts only. The complete change is
always in the MR's Changes tab.

### Proposals (`proposals: true`)

MCP `propose_annotation(cluster, database, name, patch, rationale)` and
`POST /api/annotations/{cluster}/{database}/{name}/proposals` with body
`{"patch": {...}, "rationale": "..."}`. Both exist only while the flag is on.
The route sits behind `OHMYDB_AUTH_TOKEN` like the other writes; MCP has no
app-level auth (guard `/mcp` at the proxy).

1. The entity must exist in the catalog (`404` otherwise), `rationale` must
   be non-empty, and the names must be usable as a file path.
2. A fresh clone; the target is the file in effect for that cluster: its
   `cluster_paths` override if one exists, else the shared file, else a new
   shared file. In per-cluster mode always the cluster's own file.
3. `patch` is an [RFC 7386](https://www.rfc-editor.org/rfc/rfc7386) JSON
   merge patch: maps merge key by key, lists (hints, relationships,
   examples) are replaced whole, `null` deletes. The file is edited
   round-trip, so comments, key order and quoting of untouched lines stay
   byte-identical.
4. The result must fit the schema, and every column, relationship target,
   relationship column and `use_instead` must exist in that cluster. All
   problems come back at once (`422` over HTTP), including ones already in
   the file, so the caller can fix the patch and retry.
5. Unchanged text returns `{"status": "unchanged"}`. Otherwise one MR per
   proposal on `ohmydb/propose/<db>.<table>-<UTC time>-<rand>`; commit
   subject `annotations(<db>.<table>): <rationale line 1>`.

Returns `{status, branch, merge_request, path}`. `merge_request` is the URL
of the MR/PR (`null` if GitLab printed none on push).

#### Request examples

Against the seed schema (`task up`), with `OHMYDB_AUTH_TOKEN` set:

```bash
curl -X POST http://127.0.0.1:8080/api/annotations/local/analytics/events_hourly/proposals \
  -H "Authorization: Bearer $OHMYDB_AUTH_TOKEN" -H 'Content-Type: application/json' \
  -d @- <<'JSON'
{
  "patch": {
    "owner": "team-analytics",
    "query_hints": [
      "SummingMergeTree, rows may not be collapsed yet. Always use sum(cnt) with GROUP BY, never read cnt raw.",
      "Fed only by analytics.events_hourly_mv: rows exist from the MV creation time on, no backfill."
    ],
    "relationships": [
      {"to": "app.events", "from_columns": ["event_type"], "to_columns": ["event_type"],
       "cardinality": "one_to_many", "description": "Drill down from an hourly bucket to raw events"}
    ]
  },
  "rationale": "Hourly table has no backfill\nChecked the MV DDL: plain TO-table MV, no POPULATE, so history starts at MV creation."
}
JSON
```

`200`:

```json
{"status": "proposed",
 "branch": "ohmydb/propose/analytics.events_hourly-20261010T171957Z-81ca",
 "merge_request": "https://github.com/acme/schema-annotations/pull/4",
 "path": "analytics/events_hourly.yaml"}
```

The MR/PR adds `owner`, the second hint and the relationship. The first
hint was sent back unchanged (lists are replaced whole), so it stays as is.
Every other line of the file is untouched.

Patch recipes (the `patch` value only):

```jsonc
// describe a column, keep everything else
{"columns": {"cnt": {"description": "Events in the hour; partial until merged"}}}
// enum meanings (map form; a plain list of values works too)
{"columns": {"event_type": {"values": {"click": "element click", "view": "page view"}}}}
// deprecate in favor of another table (must exist in the cluster)
{"status": "deprecated", "use_instead": "analytics.daily_counts"}
// add a verified query: send the current examples too, or they are dropped
{"examples": [{"question": "Events per type yesterday", "sql": "SELECT event_type, sum(cnt) FROM ..."}]}
// delete a key / a column's annotation
{"owner": null, "columns": {"old_col": null}}
```

Errors (`detail` lists every problem, so fix them all and retry):

```text
401  {"detail": "missing or invalid bearer token"}
404  {"detail": ["entity not found: local/analytics/nope"]}
422  {"detail": ["rationale: required — say what you verified and how"]}
422  {"detail": ["columns.total: analytics.events_hourly has no such column",
                 "relationships.0.to: analytics.ghost not found in cluster local"]}
422  {"detail": ["status: Input should be '', 'active' or 'deprecated'"]}
```

The rationale and path checks run first, so their error comes back alone;
schema and catalog problems come back together. `{"status": "unchanged",
"path": ...}` (`200`, no MR) means the patch didn't change the file.

MCP takes the same arguments:

```json
{"tool": "propose_annotation",
 "arguments": {"cluster": "local", "database": "app", "name": "users",
               "patch": {"query_hints": ["Soft-deleted rows have deleted_at set."]},
               "rationale": "Read the users service code: deletes set deleted_at, rows stay"}}
```

A rejected MCP call is a tool error whose text holds the same messages, one
per line.

### Drift MR (`drift_mr: true`)

After every schema sync (`ohmydb sync`, `POST /api/sync`; not the poller,
not `annotations pull`), from the same clone as the pull:

- A stub is needed for each catalog table (any kind but `external`) with no
  file in its cluster's override root or the shared root, not matched by
  `ignore` in the `_global.yaml` in effect for that cluster (same fallback
  as reads). Files are checked on disk, so a
  file with errors still counts as present. Names starting with `.` or `_`
  are skipped.
- Stubs go into the shared root (per-cluster mode: one per cluster, into
  each cluster's root): a header comment, `description: ""`,
  `grain: ""` and every column with `description: ""`. An unfilled stub
  reads as unannotated.
- One rolling branch, `ohmydb/drift`, rebuilt from `ref` each time and
  force-pushed with a lease. No push when its content didn't change. If the
  branch head was committed by anyone other than `author`, the step is
  skipped, so human edits on it are never overwritten.
- **Orphan files are deleted**: a table file whose table is gone from every
  cluster that file serves (shared root: all clusters; override or
  per-cluster root: that cluster). A file served by a cluster with nothing
  in the catalog (never synced) is kept, since absence proves nothing there.
  Files with parse errors and `_database.yaml` files are never deleted. To
  keep a deleted file, restore it on the drift branch; ohmydb then stops
  updating the branch until it's merged or deleted.
- The MR description lists the new tables and removed files per database,
  plus stale columns (annotated, no longer in the table) as FYI. Those are
  never edited.

Other existing files are never touched. A drift failure is reported
(`drift=failed ...`) and doesn't undo the pull.

## Annotation repo CI and editors

```bash
ohmydb annotations validate annotations/            # exit 1 + file: key: message on any error
ohmydb annotations validate . --exclude clusters    # shared root holding override roots
ohmydb annotations validate clusters/prod           # each override root separately
ohmydb annotations validate anno/prod               # per-cluster mode: each cluster root
ohmydb annotations schema > annotations.schema.json # also: schema database|global
```

`validate` needs no config, so the repo's CI can run it in the ohmydb image.
For VS Code (redhat.vscode-yaml):

```json
"yaml.schemas": { "./annotations.schema.json": ["*/[!_]*.yaml"] }
```

## Git auth and security

### Token scopes

One token, in `OHMYDB_ANNOTATIONS_TOKEN`, for everything. Give it the least
the enabled features need:

| Host | Features on | Token | Scopes / permissions |
|---|---|---|---|
| GitLab | reads only | Project access token (Settings → Access tokens) | Role **Reporter**, scope **`read_repository`** |
| GitLab | `proposals` / `drift_mr` | Project access token | Role **Developer**, scope **`write_repository`**. No `api` scope: the push itself opens the MR (push options) |
| GitHub | reads only | Fine-grained PAT, *Only select repositories* → the annotation repo | **Contents: Read-only** (Metadata: Read-only is added automatically) |
| GitHub | `proposals` / `drift_mr` | Fine-grained PAT, same repo selection | **Contents: Read and write** + **Pull requests: Read and write**. No Issues permission needed; labeling is best effort, so if `ohmydb::drift` / `ohmydb::proposal` don't show up, create those labels once in the repo |

- Verified: GitHub reads and writes, private repo, 2026-10-10. GitLab reads
  and writes follow GitLab's docs but haven't been run against a real
  instance yet.
- Avoid broader tokens: a GitLab personal token or `api` scope, or a GitHub
  classic PAT (`repo` covers every private repo the user can see).
- On GitHub the token goes to git as Basic auth (`oauth2:<token>`; GitHub
  ignores the user name) and to `api.github.com` as `Bearer`, for the PR
  call only.
- **Protect `ref` for any write token**, or the bot can push to it directly.
  GitLab: protected branch with no push for Developers, approvals required,
  CODEOWNERS per db dir. GitHub: a branch ruleset on `ref` (require a pull
  request + approval, block force pushes, CODEOWNERS review). Rulesets and
  branch protection on a *private* GitHub repo need Pro/Team.
- If GitLab push rules check the commit email, set `author` to match.

### Transport and other notes

- **The token never appears in a URL, argv, on disk, or in logs.** git gets
  it as an HTTP header via env: `GIT_TERMINAL_PROMPT=0`,
  `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=http.<scheme://host[:port]>/.extraHeader`
  (scoped to the repo host), `GIT_CONFIG_VALUE_0=Authorization: Basic
  base64("oauth2:"+token)`. git stderr is therefore safe to show in errors.
  Needs `git >= 2.31`. Internal CA: `GIT_SSL_CAINFO`. Proxy: `HTTPS_PROXY`.
- A rejected or missing token fails with git's own message plus a hint to
  check `OHMYDB_ANNOTATIONS_TOKEN`.
- **Repo placement:** a dedicated repo gives least privilege. A subdir of
  the migrations repo (set `path`) lets schema and annotations change in one
  MR, but a write-enabled bot then has push rights there.
- **Prompt injection:** annotation text is served verbatim to LLM agents.
  Review-gated `main` is the control; proposals are agent-written text, so
  review them like code. Also keep the strict schema, the catalog checks on
  proposals and the `validate` CI. The frontend escapes everything.

## Ossie mapping (for a future exporter)

table → dataset (`source` = `db.table`), `query_hints` →
`ai_context.instructions`, `columns` → `fields`, `relationships` → same shape,
`examples` → `ai_context.examples`.
