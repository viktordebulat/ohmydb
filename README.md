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
| `get_schema_graph` | `cluster` | Catalog nodes for one cluster (tables, views, MVs, dictionaries + labels) and the cluster's last `synced_at`. No edges — see `get_table_relations`. |
| `get_table` | `cluster`, `database`, `name` | One entity in full: columns with types/comments, raw DDL, engine, attrs, labels. |
| `get_table_relations` | `cluster`, `database`, `name`, `direct` (optional, default `False`) | The entity plus its upstream sources and downstream consumers — transitive by default, or just 1-hop neighbors when `direct=True` (no separate edge list — membership in upstream/downstream already implies direction). |
| `find_tables` | `query` | Brief matches (identity + kind + labels) by substring of name, database, or label — or an exact `key:value` label lookup when `query` contains a colon. |

## HTTP API

Same host, no `/mcp/` suffix. Same Pomerium auth applies.

All paths below are under `/api`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/clusters` | Configured cluster names. |
| `GET` | `/api/graph/{cluster}?q=` | Catalog nodes for one cluster + `synced_at`. Same no-edges shape as `get_schema_graph`. Optional `q` filters by substring of name/database/label, or exact `key:value` label lookup. |
| `GET` | `/api/entities/{cluster}/{database}/{name}` | One entity in full. |
| `GET` | `/api/entities/{cluster}/{database}/{name}/relations?direct=` | Upstream/downstream relations for an entity — transitive by default, 1-hop only when `direct=true`. |
| `PUT` | `/api/labels/{cluster}/{database}/{table}` | Set a label. Body: `{"key": "...", "value": "..."}`. Always marks it `manual` (see below). |
| `DELETE` | `/api/labels/{cluster}/{database}/{table}/{key}` | Remove a label. |
| `POST` | `/api/sync` | Re-introspect clusters. Optional `?cluster=<name>`. |

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
