"""Read/label helpers shared by API and MCP. Orphan labels (no matching
entity) are excluded from all reads but kept in the table."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.store.db import EdgeRow, EntityRow, LabelRow


def _labels_for(session: Session, rows: list[EntityRow]) -> dict[tuple, dict]:
    identities = {(r.cluster, r.database, r.name) for r in rows}
    out: dict[tuple, dict] = {}
    for lab in session.scalars(select(LabelRow)).all():
        ident = (lab.cluster, lab.database, lab.table_name)
        if ident in identities:
            out.setdefault(ident, {})[lab.key] = lab.value
    return out


def graph_payload(session: Session) -> dict:
    entities = session.scalars(select(EntityRow)).all()
    edges = session.scalars(select(EdgeRow)).all()
    labels = _labels_for(session, entities)
    return {
        "nodes": [
            {
                "id": e.id,
                "cluster": e.cluster,
                "database": e.database,
                "name": e.name,
                "kind": e.kind,
                "engine": e.engine,
                "refreshable": bool((e.attrs or {}).get("refreshable")),
                "labels": labels.get((e.cluster, e.database, e.name), {}),
                "synced_at": e.synced_at.isoformat() if e.synced_at else None,
            }
            for e in entities
        ],
        "edges": [{"src": e.src_id, "dst": e.dst_id, "kind": e.kind} for e in edges],
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
        "ddl": row.ddl,
        "columns": row.columns,
        "attrs": row.attrs,
        "labels": labels.get((row.cluster, row.database, row.name), {}),
        "synced_at": row.synced_at.isoformat() if row.synced_at else None,
    }


def get_relations(session: Session, cluster: str, database: str, name: str) -> dict | None:
    """All entities related to one entity: transitive upstream (data sources)
    and downstream (consumers), plus the dependency edges among them.

    Stored edges are dependency-direction; here they are walked in data-flow
    direction: writes_to flows src→dst, reads_from/dict_source flow dst→src.
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

    entities = session.scalars(select(EntityRow)).all()
    edges = session.scalars(select(EdgeRow)).all()
    by_id = {r.id: r for r in entities}

    flow_out: dict[int, set[int]] = {}  # data flows from key to values
    flow_in: dict[int, set[int]] = {}
    for e in edges:
        frm, to = (e.src_id, e.dst_id) if e.kind == "writes_to" else (e.dst_id, e.src_id)
        flow_out.setdefault(frm, set()).add(to)
        flow_in.setdefault(to, set()).add(frm)

    def reachable(adj: dict[int, set[int]], start: int) -> set[int]:
        seen: set[int] = set()
        stack = [start]
        while stack:
            for nxt in adj.get(stack.pop(), ()):
                if nxt != start and nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return seen

    upstream = reachable(flow_in, target.id)
    downstream = reachable(flow_out, target.id)
    keep = upstream | downstream | {target.id}

    labels = _labels_for(session, [by_id[i] for i in keep])

    def brief(r: EntityRow) -> dict:
        return {
            "cluster": r.cluster,
            "database": r.database,
            "name": r.name,
            "kind": r.kind,
            "engine": r.engine,
            "labels": labels.get((r.cluster, r.database, r.name), {}),
        }

    def ident(r: EntityRow) -> str:
        return f"{r.cluster}/{r.database}/{r.name}"

    order = lambda i: (by_id[i].cluster, by_id[i].database, by_id[i].name)  # noqa: E731
    return {
        "entity": brief(target),
        "upstream": [brief(by_id[i]) for i in sorted(upstream, key=order)],
        "downstream": [brief(by_id[i]) for i in sorted(downstream, key=order)],
        "edges": [
            {"src": ident(by_id[e.src_id]), "dst": ident(by_id[e.dst_id]), "kind": e.kind}
            for e in edges
            if e.src_id in keep and e.dst_id in keep
        ],
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
