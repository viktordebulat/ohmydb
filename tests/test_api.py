from fastapi.testclient import TestClient

from app.api import create_app
from app.config import AppConfig
from app.core.models import Column, Edge, EdgeKind, Entity, EntityKind
from app.store.db import make_session_factory
from app.store.repo import sync_cluster


def _client(tmp_path):
    url = f"sqlite:///{tmp_path}/test.sqlite"
    factory = make_session_factory(url)
    with factory() as s:
        sync_cluster(s, "c1", [
            Entity(cluster="c1", database="app", name="events", kind=EntityKind.TABLE,
                   engine="MergeTree", ddl="CREATE TABLE app.events ...",
                   columns=[Column("ts", "DateTime", "event time")]),
            Entity(cluster="c1", database="analytics", name="mv", kind=EntityKind.MAT_VIEW),
        ], [Edge(("c1", "analytics", "mv"), ("c1", "app", "events"), EdgeKind.READS_FROM)])
    return TestClient(create_app(AppConfig(storage_url=url, clusters=[])))


def test_graph(tmp_path):
    g = _client(tmp_path).get("/graph").json()
    assert {n["name"] for n in g["nodes"]} == {"events", "mv"}
    assert len(g["edges"]) == 1
    assert g["edges"][0]["kind"] == "reads_from"
    node = next(n for n in g["nodes"] if n["name"] == "events")
    assert node["kind"] == "table" and node["synced_at"]


def test_entity_detail_and_404(tmp_path):
    client = _client(tmp_path)
    r = client.get("/entities/c1/app/events")
    assert r.status_code == 200
    body = r.json()
    assert body["engine"] == "MergeTree"
    assert body["columns"] == [{"name": "ts", "type": "DateTime", "comment": "event time"}]
    assert client.get("/entities/c1/app/nope").status_code == 404


def test_index_served(tmp_path):
    r = _client(tmp_path).get("/")
    assert r.status_code == 200
    assert "cytoscape" in r.text


def test_labels_crud(tmp_path):
    client = _client(tmp_path)
    assert client.put("/labels/c1/app/events", json={"key": "source", "value": "vector"}).status_code == 200
    assert client.get("/entities/c1/app/events").json()["labels"] == {"source": "vector"}
    node = next(n for n in client.get("/graph").json()["nodes"] if n["name"] == "events")
    assert node["labels"] == {"source": "vector"}
    assert client.delete("/labels/c1/app/events/source").status_code == 200
    assert client.delete("/labels/c1/app/events/source").status_code == 404
    assert client.get("/entities/c1/app/events").json()["labels"] == {}


def test_sync_endpoint(tmp_path, monkeypatch):
    import app.api as api_mod

    monkeypatch.setattr(api_mod, "run_sync", lambda cfg, only_cluster=None: {"local": {"created": 1}})
    client = _client(tmp_path)
    assert client.post("/sync").json() == {"local": {"created": 1}}

    monkeypatch.setattr(api_mod, "run_sync", lambda cfg, only_cluster=None: {})
    assert client.post("/sync?cluster=nope").status_code == 404

    def boom(cfg, only_cluster=None):
        raise ConnectionError("cluster down")
    monkeypatch.setattr(api_mod, "run_sync", boom)
    assert client.post("/sync").status_code == 502
