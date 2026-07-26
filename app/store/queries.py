"""Read/label helpers shared by API and MCP. Orphan labels (no matching
entity) are excluded from all reads but kept in the table."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.store.db import EntityRow, LabelRow


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


def list_entities(session: Session, cluster: str | None = None) -> list[dict]:
    """Node listing, no edges — used by search (find_tables) which scans
    across all clusters and doesn't need the full graph."""
    stmt = select(EntityRow)
    if cluster is not None:
        stmt = stmt.where(EntityRow.cluster == cluster)
    entities = session.scalars(stmt).all()
    return _node_briefs(session, entities)


def graph_payload(session: Session, cluster: str) -> dict:
    # No edges list — redundant with per-entity upstream/downstream
    # (see get_relations); a caller wanting dependency direction for one
    # entity should call that instead of walking edges here.
    entities = session.scalars(select(EntityRow).where(EntityRow.cluster == cluster)).all()
    # One value for the whole graph, not per node — a sync writes the same
    # timestamp to every entity of a cluster in one transaction.
    synced_at = max((e.synced_at for e in entities if e.synced_at), default=None)
    return {
        "synced_at": synced_at.isoformat() if synced_at else None,
        "nodes": _node_briefs(session, entities),
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


def get_relations(session: Session, cluster: str, database: str, name: str) -> dict | None:
    """All entities related to one entity: transitive upstream (data sources)
    and downstream (consumers). No separate edges list — membership in
    upstream/downstream already implies the dependency direction (writes_to
    and reads_from/dict_source both fold into these two sets at sync time).

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

    keep = set(target.upstream) | set(target.downstream) | {target.id}
    rows = session.scalars(select(EntityRow).where(EntityRow.id.in_(keep))).all()
    by_id = {r.id: r for r in rows}
    labels = _labels_for(session, rows)

    def brief(r: EntityRow) -> dict:
        return {
            "cluster": r.cluster,
            "database": r.database,
            "name": r.name,
            "kind": r.kind,
            "engine": r.engine,
            "labels": labels.get((r.cluster, r.database, r.name), {}),
        }

    order = lambda i: (by_id[i].cluster, by_id[i].database, by_id[i].name)  # noqa: E731
    return {
        "entity": brief(target),
        "upstream": [brief(by_id[i]) for i in sorted(target.upstream, key=order)],
        "downstream": [brief(by_id[i]) for i in sorted(target.downstream, key=order)],
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
