# ohmydb

Schema catalog service. Introspects databases (ClickHouse), stores table schemas
and their dependencies (materialized views, views, dictionaries) as a graph, and
serves them over API/MCP so AI agents can reason about your data model.

## Connect MCP

The catalog is exposed as an MCP server at `/mcp/`:

```json
{
  "mcpServers": {
    "ohmydb-dev": {
      "type": "http",
      "url": "{{YOUR_HOST_HERE}}/mcp/",
      "headers": {
        "Authorization": "{{PUT YOUR AUTHORIZATION TOKEN HERE}}"
      }
    }
  }
}
```

## MCP tools

| Tool | Arguments | Returns |
|------|-----------|---------|
| `list_clusters` | — | Configured cluster names. Call first — `get_schema_graph` needs one. |
| `get_schema_graph` | `cluster` | Catalog nodes for one cluster (tables, views, MVs, dictionaries + labels) and the cluster's last `synced_at`. No edges — see `get_table_relations`. With [annotations](#annotations) on: `summary`/`status` columns and an `annotations` block (global + per-database query hints). |
| `get_table` | `cluster`, `database`, `name` | One entity in full: columns with types/comments, raw DDL, engine, attrs, labels. With annotations on: `annotation` (description, grain, status/use_instead, owner, query_hints, relationships, examples) and per-column `description`/`values`. |
| `get_table_relations` | `cluster`, `database`, `name`, `direct` (optional, default `False`) | The entity plus its upstream sources and downstream consumers — transitive by default, or just 1-hop neighbors when `direct=True` (no separate edge list — membership in upstream/downstream already implies direction). |
| `find_tables` | `query`, `column`, `column_type`, `match`, `kind`, `cluster` (all optional, ≥1 required, ANDed) | Brief matches (identity + kind + labels). `query`: substring of name, database, or label — or exact `key:value` label lookup when it contains a colon. `column`: list of case-insensitive name globs (`*_id`); `match="all"` (default) needs every pattern to hit, `"any"` one. `column_type`: exact type, bound to the same column as each pattern. Adds `matched_columns` when a column filter is given. With annotations on: `query` also matches the summary; `summary`/`status` columns. |
| `propose_annotation` | `cluster`, `database`, `name`, `patch`, `rationale` | Only with `annotations.proposals` on. JSON merge patch against the table's annotation (maps merge, lists replace, `null` deletes), checked against the catalog, opened as a GitLab MR / GitHub PR for human review → `{status, branch, merge_request, path}`. |

## HTTP API

Same host, no `/mcp/` suffix. Same Pomerium auth applies.

All paths below are under `/api`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/clusters` | Configured cluster names. |
| `GET` | `/api/graph/{cluster}?q=&column=&column_type=&match=&kind=` | Catalog nodes for one cluster + `synced_at`. Same no-edges shape as `get_schema_graph`. Optional filters, same semantics as `find_tables` (`column` repeatable). |
| `GET` | `/api/search?q=&column=&column_type=&match=&kind=&cluster=` | Cross-cluster search, HTTP twin of `find_tables` → `{"nodes": [...]}`. At least one filter required (else `400`). E.g. `?column=user_id&column=ts&match=all`. |
| `GET` | `/api/entities/{cluster}/{database}/{name}` | One entity in full. |
| `GET` | `/api/entities/{cluster}/{database}/{name}/relations?direct=` | Upstream/downstream relations for an entity — transitive by default, 1-hop only when `direct=true`. |
| `PUT` | `/api/labels/{cluster}/{database}/{table}` | Set a label. Body: `{"key": "...", "value": "..."}`. Always marks it `manual` (see below). |
| `DELETE` | `/api/labels/{cluster}/{database}/{table}/{key}` | Remove a label. |
| `POST` | `/api/sync` | Re-introspect clusters. Optional `?cluster=<name>`. |
| `POST` | `/api/annotations/{cluster}/{database}/{name}/proposals` | Only with `annotations.proposals` on; twin of `propose_annotation`. Body: `{"patch": {...}, "rationale": "..."}`. `422` lists every validation problem. |

### Auth

Off by default — fine for localhost-only dev. Set `OHMYDB_AUTH_TOKEN` (env
var only, never in `config.yaml`) to require a bearer token on the
mutating routes above (`PUT`/`DELETE /api/labels/...`, `POST /api/sync`,
`POST /api/annotations/.../proposals`).
Reads (`GET /api/...`) and MCP are never gated by this token, even when
it's set — separate concern, guard those at the network/proxy layer
(e.g. Pomerium, above) if they need to be private too.

```bash
export OHMYDB_AUTH_TOKEN=s3cr3t
uv run ohmydb serve

curl -X POST http://127.0.0.1:8080/api/sync \
  -H "Authorization: Bearer $OHMYDB_AUTH_TOKEN"
```

A missing or wrong token gets `401`.

## Frontend

`GET /` serves a small static page (`app/web/index.html`, no build step)
for browsing the catalog: pick a cluster, filter entities by database/
name/kind/engine/refreshable/labels, click one to see its direct
upstream/downstream relations as a mind map (via the vendored
[mind-elixir](https://github.com/SSShooter/mind-elixir-core)). Click any
node in the map to re-center on it.

## Annotations

Optional, off by default. Human-curated YAML in a git repo (reviewed in MRs)
adds what introspection can't know: what a table is, grain, units, enum
values, join keys, deprecations, query gotchas and verified example queries.
ohmydb pulls it on every sync and polls it while serving. Optionally it
writes back via merge/pull requests only (GitLab or github.com): agent proposals (`proposals: true`) and
stub files for new tables (`drift_mr: true`).

```yaml
annotations:
  enabled: true
  repo: https://gitlab.example.com/data/schema-annotations.git   # or a local dir
  ref: main
  pull_interval: 300      # serve polling, seconds; 0 = only on sync
```

Token for private repos: `OHMYDB_ANNOTATIONS_TOKEN` env only (GitLab: project
access token, Reporter + `read_repository`; for writes Developer +
`write_repository`. GitHub: fine-grained PAT, Contents, plus Pull requests
for writes. Protect `ref` so the bot can only open MRs/PRs); the image ships
`git`. CLI:
`ohmydb annotations pull`, `ohmydb annotations validate DIR` (CI for the
annotation repo), `ohmydb annotations schema` (JSON Schema for editors).
Format, cluster overrides and security notes:
[docs/ANNOTATIONS.md](docs/ANNOTATIONS.md).

## Labels: manual vs. auto

Labels can be set by hand (`PUT /labels`) or derived automatically at sync
time from `label_rules` in config (global list, applied before each
cluster's own list — both are additive, not overridable). Every reachable
entity is checked against every rule; a rule matches when **all** of its
`match` fields hold:

| Field | Match |
|-------|-------|
| `engine` | exact string (e.g. `Kafka`) |
| `kind` | exact string (`table`, `view`, `mat_view`, `dictionary`) |
| `name_pattern` | regex against entity name |
| `database_pattern` | regex against database name |

All matching rules apply — labels from different rules accumulate. If two
rules set the same key for the same entity, the later rule in the list
wins. A manual label always beats an auto one for the same `(entity, key)`,
even across resyncs — auto labels are recomputed and replaced every sync,
manual ones are left alone. Only `name_pattern`/`database_pattern` exist for
name matching (no bare `name` field) — an unrecognized `match` key raises at
config load, before any cluster is synced.
