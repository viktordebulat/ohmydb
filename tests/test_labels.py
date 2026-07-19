from app.core.models import Entity, EntityKind
from app.store.db import make_session_factory
from app.store.queries import delete_label, get_entity, graph_payload, set_label
from app.store.repo import sync_cluster


def _entity(name):
    return Entity(cluster="c1", database="app", name=name, kind=EntityKind.TABLE)


def test_labels_visible_orphaned_and_revived(tmp_path):
    factory = make_session_factory(f"sqlite:///{tmp_path}/t.sqlite")
    with factory() as s:
        sync_cluster(s, "c1", [_entity("events")], [])
        set_label(s, "c1", "app", "events", "source", "vector")

        assert graph_payload(s)["nodes"][0]["labels"] == {"source": "vector"}
        assert get_entity(s, "c1", "app", "events")["labels"] == {"source": "vector"}

        # entity dropped -> label orphaned: hidden but not deleted
        sync_cluster(s, "c1", [_entity("other")], [])
        assert all(n["labels"] == {} for n in graph_payload(s)["nodes"])

        # entity recreated -> label reappears
        sync_cluster(s, "c1", [_entity("events")], [])
        assert graph_payload(s)["nodes"][0]["labels"] == {"source": "vector"}


def test_set_overwrites_and_delete(tmp_path):
    factory = make_session_factory(f"sqlite:///{tmp_path}/t.sqlite")
    with factory() as s:
        sync_cluster(s, "c1", [_entity("events")], [])
        set_label(s, "c1", "app", "events", "source", "vector")
        set_label(s, "c1", "app", "events", "source", "airflow")
        assert get_entity(s, "c1", "app", "events")["labels"] == {"source": "airflow"}
        assert delete_label(s, "c1", "app", "events", "source") is True
        assert delete_label(s, "c1", "app", "events", "source") is False
        assert get_entity(s, "c1", "app", "events")["labels"] == {}
