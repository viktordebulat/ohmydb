"""Read/label helpers shared by API and MCP. Orphan labels (no matching
entity) are excluded from all reads but kept in the table."""

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.core.models import EdgeKind
from app.store.db import EdgeRow, EntityRow, LabelRow


def _labels_for(session: Session, rows: list[EntityRow]) -> dict[tuple, dict]:
    identities = {(r.cluster, r.database, r.name) for r in rows}
    out: dict[tuple, dict] = {}
    for lab in session.scalars(select(LabelRow)).all():
        ident = (lab.cluster, lab.database, lab.table_name)
        if ident in identities:
            out.setdefault(ident, {})[lab.key] = lab.value
    return out


def _node_briefs(session: Session, entities: list[EntityRow]) -> list[dict]:
    labels = _labels_for(session, entities)
    return [
        {
            "id": e.id,
            "cluster": e.cluster,
            "database": e.database,
            "name": e.name,
            "kind": e.kind,
            "engine": e.engine,
            "refreshable": bool((e.attrs or {}).get("refreshable")),
            "labels": labels.get((e.cluster, e.database, e.name), {}),
        }
        for e in entities
    ]


def _matches(node: dict, q: str) -> bool:
    """Match rule shared by any endpoint/tool searching entities. `key:value`
    (colon present) does an exact label lookup — key and value must both
    match exactly. Otherwise: substring match against name, database, or any
    label key/value."""
    if ":" in q:
        key, _, value = q.partition(":")
        return node["labels"].get(key) == value
    q = q.lower()
    return (
        q in node["name"].lower()
        or q in node["database"].lower()
        or any(q in k.lower() or q in v.lower() for k, v in node["labels"].items())
    )


def list_entities(session: Session, cluster: str | None = None, q: str | None = None) -> list[dict]:
    """Node listing, no edges — used by search (find_tables) which scans
    across all clusters and doesn't need the full graph. `q` filters via
    _matches (see there for substring vs key:value semantics)."""
    stmt = select(EntityRow)
    if cluster is not None:
        stmt = stmt.where(EntityRow.cluster == cluster)
    entities = session.scalars(stmt).all()
    briefs = _node_briefs(session, entities)
    if q is not None:
        briefs = [n for n in briefs if _matches(n, q)]
    return briefs


def graph_payload(session: Session, cluster: str, q: str | None = None) -> dict:
    # No edges list — redundant with per-entity upstream/downstream
    # (see get_relations); a caller wanting dependency direction for one
    # entity should call that instead of walking edges here.
    entities = session.scalars(select(EntityRow).where(EntityRow.cluster == cluster)).all()
    # One value for the whole graph, not per node — a sync writes the same
    # timestamp to every entity of a cluster in one transaction.
    synced_at = max((e.synced_at for e in entities if e.synced_at), default=None)
    nodes = _node_briefs(session, entities)
    if q is not None:
        nodes = [n for n in nodes if _matches(n, q)]
    return {
        "synced_at": synced_at.isoformat() if synced_at else None,
        "nodes": nodes,
    }


def get_entity(session: Session, cluster: str, database: str, name: str) -> dict | None:
    row = session.scalar(
        select(EntityRow).where(
            EntityRow.cluster == cluster,
            EntityRow.database == database,
            EntityRow.name == name,
        )
    )
    if row is None:
        return None
    labels = _labels_for(session, [row])
    return {
        "cluster": row.cluster,
        "database": row.database,
        "name": row.name,
        "kind": row.kind,
        "engine": row.engine,
        "engine_full": row.engine_full,
        "sorting_key": row.sorting_key,
        "primary_key": row.primary_key,
        "ddl": row.ddl,
        "columns": row.columns,
        "attrs": row.attrs,
        "labels": labels.get((row.cluster, row.database, row.name), {}),
        "synced_at": row.synced_at.isoformat() if row.synced_at else None,
    }


def get_relations(
    session: Session, cluster: str, database: str, name: str, direct_only: bool = False
) -> dict | None:
    """All entities related to one entity: transitive upstream (data sources)
    and downstream (consumers), or just the 1-hop neighbors when
    `direct_only` is set. No separate edges list — membership in
    upstream/downstream already implies the dependency direction (writes_to
    and reads_from/dict_source both fold into these two sets at sync time).
    Each entry is also flagged `direct` (immediate 1-hop neighbor vs reached
    through an intermediate) by checking this entity's own edges.

    upstream/downstream are precomputed at sync time (store/repo.py:
    sync_cluster) — this is a lookup + label join, not a graph walk.
    """
    target = session.scalar(
        select(EntityRow).where(
            EntityRow.cluster == cluster,
            EntityRow.database == database,
            EntityRow.name == name,
        )
    )
    if target is None:
        return None

    # Direct (1-hop) neighbors: this entity's own edges, same direction
    # convention as repo.py's flow_out/flow_in (writes_to flows src->dst,
    # reads_from/dict_source flow dst->src).
    direct_upstream: set[int] = set()
    direct_downstream: set[int] = set()
    own_edges = session.scalars(
        select(EdgeRow).where(or_(EdgeRow.src_id == target.id, EdgeRow.dst_id == target.id))
    ).all()
    for e in own_edges:
        frm, to = (e.src_id, e.dst_id) if e.kind == EdgeKind.WRITES_TO.value else (e.dst_id, e.src_id)
        if frm == target.id:
            direct_downstream.add(to)
        if to == target.id:
            direct_upstream.add(frm)

    if direct_only:
        upstream_ids, downstream_ids = direct_upstream, direct_downstream
    else:
        upstream_ids, downstream_ids = set(target.upstream), set(target.downstream)

    keep = upstream_ids | downstream_ids | {target.id}
    rows = session.scalars(select(EntityRow).where(EntityRow.id.in_(keep))).all()
    by_id = {r.id: r for r in rows}
    labels = _labels_for(session, rows)

    def brief(r: EntityRow, direct_ids: set[int]) -> dict:
        return {
            "cluster": r.cluster,
            "database": r.database,
            "name": r.name,
            "kind": r.kind,
            "engine": r.engine,
            "labels": labels.get((r.cluster, r.database, r.name), {}),
            "direct": r.id in direct_ids,
        }

    order = lambda i: (by_id[i].cluster, by_id[i].database, by_id[i].name)  # noqa: E731
    return {
        "entity": brief(target, set()),
        "upstream": [brief(by_id[i], direct_upstream) for i in sorted(upstream_ids, key=order)],
        "downstream": [brief(by_id[i], direct_downstream) for i in sorted(downstream_ids, key=order)],
    }


def set_label(session: Session, cluster: str, database: str, table: str, key: str, value: str) -> None:
    row = session.scalar(
        select(LabelRow).where(
            LabelRow.cluster == cluster,
            LabelRow.database == database,
            LabelRow.table_name == table,
            LabelRow.key == key,
        )
    )
    if row is None:
        row = LabelRow(cluster=cluster, database=database, table_name=table, key=key)
        session.add(row)
    row.value = value
    row.source = "manual"  # an explicit PUT always overrides a prior auto label
    session.commit()


def delete_label(session: Session, cluster: str, database: str, table: str, key: str) -> bool:
    result = session.execute(
        delete(LabelRow).where(
            LabelRow.cluster == cluster,
            LabelRow.database == database,
            LabelRow.table_name == table,
            LabelRow.key == key,
        )
    )
    session.commit()
    return result.rowcount > 0
