from sqlalchemy import select

from app.core.models import Column, Edge, EdgeKind, Entity, EntityKind
from app.store.db import EdgeRow, EntityRow, make_session_factory
from app.store.repo import sync_cluster


def _factory():
    return make_session_factory("sqlite://")  # in-memory


def _entity(db, name, kind=EntityKind.TABLE, **kw):
    return Entity(cluster="c1", database=db, name=name, kind=kind, **kw)


def test_sync_creates_entities_edges_and_stubs():
    factory = _factory()
    entities = [
        _entity("app", "events", columns=[Column("ts", "DateTime")]),
        _entity("analytics", "mv", EntityKind.MAT_VIEW, attrs={"refreshable": True}),
    ]
    edges = [
        Edge(("c1", "analytics", "mv"), ("c1", "app", "events"), EdgeKind.READS_FROM),
        # target never introspected -> stub
        Edge(("c1", "analytics", "mv"), ("c1", "analytics", "gone"), EdgeKind.WRITES_TO),
    ]
    with factory() as s:
        summary = sync_cluster(s, "c1", entities, edges)
    assert summary == {"created": 2, "updated": 0, "deleted": 0, "edges": 2}

    with factory() as s:
        rows = s.scalars(select(EntityRow)).all()
        assert {(r.name, r.kind) for r in rows} == {
            ("events", "table"), ("mv", "mat_view"), ("gone", "external"),
        }
        mv = next(r for r in rows if r.name == "mv")
        assert mv.attrs == {"refreshable": True}
        events = next(r for r in rows if r.name == "events")
        assert events.columns == [{"name": "ts", "type": "DateTime", "comment": ""}]
        assert len(s.scalars(select(EdgeRow)).all()) == 2


def test_resync_upserts_deletes_and_rebuilds():
    factory = _factory()
    with factory() as s:
        sync_cluster(s, "c1", [_entity("app", "a"), _entity("app", "b")],
                     [Edge(("c1", "app", "a"), ("c1", "app", "b"), EdgeKind.READS_FROM)])
    # b vanished, a changed engine, c appeared; no edges anymore
    with factory() as s:
        summary = sync_cluster(s, "c1", [_entity("app", "a", engine="MergeTree"),
                                         _entity("app", "c")], [])
    assert summary == {"created": 1, "updated": 1, "deleted": 1, "edges": 0}
    with factory() as s:
        rows = s.scalars(select(EntityRow)).all()
        assert {r.name for r in rows} == {"a", "c"}
        assert next(r for r in rows if r.name == "a").engine == "MergeTree"
        assert s.scalars(select(EdgeRow)).all() == []


def test_sync_ignores_other_clusters():
    factory = _factory()
    with factory() as s:
        sync_cluster(s, "c1", [_entity("app", "a")], [])
        e2 = Entity(cluster="c2", database="app", name="z", kind=EntityKind.TABLE)
        sync_cluster(s, "c2", [e2], [])
    with factory() as s:
        sync_cluster(s, "c1", [], [])  # wipe c1
        assert {r.cluster for r in s.scalars(select(EntityRow)).all()} == {"c2"}
