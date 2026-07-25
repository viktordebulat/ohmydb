"""Sync logic: replace one cluster's state with freshly introspected data."""

from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.models import Edge, EdgeKind, Entity, EntityKind, Identity
from app.store.db import EdgeRow, EntityRow, LabelRow


def _reachable(adj: dict[int, set[int]], start: int) -> set[int]:
    seen: set[int] = set()
    stack = [start]
    while stack:
        for nxt in adj.get(stack.pop(), ()):
            if nxt != start and nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def sync_cluster(session: Session, cluster: str, entities: list[Entity], edges: list[Edge]) -> dict:
    """One transaction: upsert entities, drop vanished ones, rebuild edges.

    Edge endpoints not present among entities get a stub row (kind=external).
    Labels are intentionally untouched. Returns summary counts.
    """
    now = datetime.now(timezone.utc)
    incoming: dict[Identity, Entity] = {e.identity: e for e in entities}

    rows = session.scalars(select(EntityRow).where(EntityRow.cluster == cluster)).all()
    by_identity: dict[Identity, EntityRow] = {(r.cluster, r.database, r.name): r for r in rows}

    # Old edges of this cluster die; they get rebuilt from scratch below.
    if rows:
        ids = [r.id for r in rows]
        session.execute(delete(EdgeRow).where(EdgeRow.src_id.in_(ids) | EdgeRow.dst_id.in_(ids)))

    created = updated = 0
    for identity, ent in incoming.items():
        row = by_identity.get(identity)
        if row is None:
            row = EntityRow(cluster=ent.cluster, database=ent.database, name=ent.name)
            session.add(row)
            by_identity[identity] = row
            created += 1
        else:
            updated += 1
        row.kind = ent.kind.value
        row.engine = ent.engine
        row.ddl = ent.ddl
        row.columns = [asdict(c) for c in ent.columns]
        row.attrs = ent.attrs
        row.synced_at = now

    deleted = 0
    for identity, row in list(by_identity.items()):
        if identity not in incoming:
            session.delete(row)  # includes stale external stubs
            del by_identity[identity]
            deleted += 1

    # Stubs for edge endpoints we didn't introspect (dropped or out-of-scope).
    for edge in edges:
        for identity in (edge.src, edge.dst):
            if identity not in by_identity:
                c, db, name = identity
                stub = EntityRow(
                    cluster=c, database=db, name=name,
                    kind=EntityKind.EXTERNAL.value, synced_at=now,
                )
                session.add(stub)
                by_identity[identity] = stub

    session.flush()  # assign ids before wiring edges

    for edge in edges:
        session.add(EdgeRow(
            src_id=by_identity[edge.src].id,
            dst_id=by_identity[edge.dst].id,
            kind=edge.kind.value,
        ))

    # Precompute transitive relations so reads (get_relations) are a lookup,
    # not a per-call BFS. Data-flow direction: writes_to flows src->dst,
    # reads_from/dict_source flow dst->src (mirrors store/queries.py's old
    # in-request walk, moved here since sync is infrequent and reads aren't).
    flow_out: dict[int, set[int]] = {}
    flow_in: dict[int, set[int]] = {}
    for edge in edges:
        src_id, dst_id = by_identity[edge.src].id, by_identity[edge.dst].id
        frm, to = (src_id, dst_id) if edge.kind == EdgeKind.WRITES_TO else (dst_id, src_id)
        flow_out.setdefault(frm, set()).add(to)
        flow_in.setdefault(to, set()).add(frm)

    for row in by_identity.values():
        row.upstream = sorted(_reachable(flow_in, row.id))
        row.downstream = sorted(_reachable(flow_out, row.id))

    session.commit()
    return {"created": created, "updated": updated, "deleted": deleted, "edges": len(edges)}


def sync_auto_labels(session: Session, cluster: str, auto_labels: list[tuple[Identity, str, str]]) -> None:
    """Replace this cluster's `source=auto` labels with the given
    (identity, key, value) triples (from app.core.labeling.apply_label_rules).
    Skips a key that already has a manual label for that identity — manual
    edits always win. Commits."""
    manual_keys = {
        (row.database, row.table_name, row.key)
        for row in session.scalars(
            select(LabelRow).where(LabelRow.cluster == cluster, LabelRow.source == "manual")
        ).all()
    }
    session.execute(delete(LabelRow).where(LabelRow.cluster == cluster, LabelRow.source == "auto"))
    for identity, key, value in auto_labels:
        _, database, name = identity
        if (database, name, key) in manual_keys:
            continue
        session.add(LabelRow(
            cluster=cluster, database=database, table_name=name,
            key=key, value=value, source="auto",
        ))
    session.commit()
