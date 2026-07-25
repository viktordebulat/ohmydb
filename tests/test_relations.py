from app.core.models import Edge, EdgeKind, Entity, EntityKind
from app.store.db import make_session_factory
from app.store.queries import get_relations
from app.store.repo import sync_cluster


def _e(db, name, kind=EntityKind.TABLE):
    return Entity(cluster="c1", database=db, name=name, kind=kind)


def _id(db, name):
    return ("c1", db, name)


def _setup(tmp_path):
    """Chain: raw -> mv (reads raw, writes agg) -> agg -> view (reads agg);
    dict reads users; users unrelated to the chain."""
    factory = make_session_factory(f"sqlite:///{tmp_path}/t.sqlite")
    entities = [
        _e("app", "raw"),
        _e("an", "mv", EntityKind.MAT_VIEW),
        _e("an", "agg"),
        _e("an", "view", EntityKind.VIEW),
        _e("app", "users"),
        _e("app", "dict", EntityKind.DICTIONARY),
    ]
    edges = [
        Edge(_id("an", "mv"), _id("app", "raw"), EdgeKind.READS_FROM),
        Edge(_id("an", "mv"), _id("an", "agg"), EdgeKind.WRITES_TO),
        Edge(_id("an", "view"), _id("an", "agg"), EdgeKind.READS_FROM),
        Edge(_id("app", "dict"), _id("app", "users"), EdgeKind.DICT_SOURCE),
    ]
    with factory() as s:
        sync_cluster(s, "c1", entities, edges)
    return factory


def test_transitive_downstream_and_upstream(tmp_path):
    factory = _setup(tmp_path)
    with factory() as s:
        rel = get_relations(s, "c1", "app", "raw")
        assert rel["upstream"] == []
        assert [d["name"] for d in rel["downstream"]] == ["agg", "mv", "view"]

        rel = get_relations(s, "c1", "an", "agg")
        assert {u["name"] for u in rel["upstream"]} == {"mv", "raw"}
        assert {d["name"] for d in rel["downstream"]} == {"view"}


def test_unrelated_and_missing(tmp_path):
    factory = _setup(tmp_path)
    with factory() as s:
        rel = get_relations(s, "c1", "app", "users")
        assert rel["upstream"] == []
        assert [d["name"] for d in rel["downstream"]] == ["dict"]
        assert get_relations(s, "c1", "app", "nope") is None
