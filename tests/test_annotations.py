import asyncio
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient
from fastmcp import Client

from app.annotations.model import FatalTreeError, load_tree
from app.annotations.service import pull
from app.api import create_app
from app.config import AnnotationsConfig, AppConfig, ClusterConfig
from app.core.models import Column, Entity, EntityKind
from app.mcp import create_mcp
from app.store.db import make_session_factory
from app.store.repo import sync_cluster

EVENTS = """\
description: |
  Raw user events, checkout included.
  Second line is not part of the summary.
status: deprecated
use_instead: app.events_v2
query_hints: [Always filter on ts.]
columns:
  ts: {description: "Event time, UTC"}
  kind:
    description: Interaction kind
    values: {1: click, 2: view}
  gone: {description: column that no longer exists}
relationships:
  - {to: app.users, from_columns: [user_id], to_columns: [id], cardinality: many_to_one}
"""


def _tree(root, files):
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


def _base_tree(root):
    return _tree(root, {
        "README.md": "ignored",
        "_global.yaml": "version: 1\nquery_hints: [All times UTC.]\n",
        "app/_database.yaml": "description: App data\nquery_hints: [Filter on sorting key.]\n",
        "app/events.yaml": EVENTS,
        "app/users.yaml": 'description: ""\ncolumns:\n  id: {description: ""}\n',  # unfilled stub
    })


# --- format ---

def test_load_tree_valid(tmp_path):
    tree, errors = load_tree(_base_tree(tmp_path))
    assert errors == []
    assert tree.global_ == ({"query_hints": ["All times UTC."]}, "_global.yaml")
    assert tree.databases["app"][0]["description"] == "App data"
    events, path = tree.tables[("app", "events")]
    assert path == "app/events.yaml"
    assert events["columns"]["kind"]["values"] == {"1": "click", "2": "view"}  # numeric keys -> str
    assert tree.tables[("app", "users")] == ({}, "app/users.yaml")  # stub: exists, but empty


@pytest.mark.parametrize("rel, text, err", [
    ("app/t.yaml", "descripton: x\n", "app/t.yaml: descripton: Extra inputs"),
    ("app/t.yml", "description: x\n", "app/t.yml: use the .yaml"),
    ("app/_db.yaml", "description: x\n", "unknown special file"),
    ("app/t.yaml", "relationships: [{to: users, from_columns: [a], to_columns: [b]}]\n", "db.table"),
    ("app/t.yaml", "relationships: [{to: a.b, from_columns: [a, b], to_columns: [c]}]\n", "same length"),
])
def test_load_tree_per_file_errors(tmp_path, rel, text, err):
    tree, errors = load_tree(_tree(tmp_path, {rel: text, "app/ok.yaml": "description: fine\n"}))
    assert len(errors) == 1 and err in errors[0]
    assert ("app", "ok") in tree.tables  # other files still load


def test_load_tree_fatal(tmp_path):
    with pytest.raises(FatalTreeError, match="not found"):
        load_tree(tmp_path / "missing")
    with pytest.raises(FatalTreeError, match="version"):
        load_tree(_tree(tmp_path, {"_global.yaml": "version: 2\n"}))


# --- pull + reads ---

def _catalog(tmp_path):
    url = f"sqlite:///{tmp_path}/t.sqlite"
    factory = make_session_factory(url)
    with factory() as s:
        sync_cluster(s, "c1", [
            Entity(cluster="c1", database="app", name="events", kind=EntityKind.TABLE,
                   columns=[Column("ts", "DateTime"), Column("kind", "UInt8")]),
            Entity(cluster="c1", database="app", name="users", kind=EntityKind.TABLE,
                   columns=[Column("id", "UInt64")]),
        ], [])
        sync_cluster(s, "c2", [
            Entity(cluster="c2", database="app", name="events", kind=EntityKind.TABLE,
                   columns=[Column("ts", "DateTime")]),
        ], [])
    return url, factory


def _cfg(url, repo, enabled=True, **kw):
    return AppConfig(
        storage_url=url,
        clusters=[ClusterConfig(name="c1", host="localhost"), ClusterConfig(name="c2", host="localhost")],
        annotations=AnnotationsConfig(enabled=enabled, repo=str(repo), pull_interval=0, **kw),
    )


@pytest.fixture
def pulled(tmp_path):
    url, factory = _catalog(tmp_path)
    repo = _base_tree(tmp_path / "repo")
    # override root nested in the shared one: must not be read as a database
    _tree(repo, {"clusters/c2/app/events.yaml": "description: c2 override\n"})
    cfg = _cfg(url, repo, cluster_paths={"c2": "clusters/c2"})
    result = pull(cfg, factory)
    assert result["errors"] == []
    return url, repo, cfg


def test_entity_annotation_and_column_merge(pulled):
    _, _, cfg = pulled
    e = TestClient(create_app(cfg)).get("/api/entities/c1/app/events").json()
    ann = e["annotation"]
    assert ann["status"] == "deprecated" and ann["use_instead"] == "app.events_v2"
    assert ann["path"] == "app/events.yaml" and "columns" not in ann
    assert ann["relationships"][0]["to"] == "app.users"
    assert e["columns"] == [
        {"name": "ts", "type": "DateTime", "comment": "", "description": "Event time, UTC"},
        {"name": "kind", "type": "UInt8", "comment": "", "description": "Interaction kind",
         "values": {"1": "click", "2": "view"}},
    ]  # `gone` dropped
    # stub table reads as unannotated
    assert "annotation" not in TestClient(create_app(cfg)).get("/api/entities/c1/app/users").json()


def test_cluster_path_override_wins_with_fallback(pulled):
    _, _, cfg = pulled
    client = TestClient(create_app(cfg))
    e = client.get("/api/entities/c2/app/events").json()
    assert e["annotation"] == {"description": "c2 override", "path": "clusters/c2/app/events.yaml"}
    # _global.yaml / _database.yaml absent from the c2 root -> shared root's
    g = client.get("/api/graph/c2").json()
    assert g["annotations"]["query_hints"] == ["All times UTC."]


def test_briefs_search_and_graph_hints(pulled):
    _, _, cfg = pulled
    client = TestClient(create_app(cfg))
    g = client.get("/api/graph/c1").json()
    by_name = {n["name"]: n for n in g["nodes"]}
    assert (by_name["events"]["summary"], by_name["events"]["status"]) == (
        "Raw user events, checkout included.", "deprecated")
    assert (by_name["users"]["summary"], by_name["users"]["status"]) == ("", "")
    assert g["annotations"] == {
        "query_hints": ["All times UTC."],
        "databases": {"app": {"description": "App data", "query_hints": ["Filter on sorting key."]}},
    }
    hits = client.get("/api/search", params={"q": "checkout", "cluster": "c1"}).json()["nodes"]
    assert [n["name"] for n in hits] == ["events"]


def test_flag_off_keeps_pre_feature_shape(pulled):
    url, repo, _ = pulled
    client = TestClient(create_app(_cfg(url, repo, enabled=False)))
    g = client.get("/api/graph/c1").json()
    assert set(g) == {"synced_at", "nodes"}
    assert set(g["nodes"][0]) == {"id", "cluster", "database", "name", "kind", "engine", "refreshable", "labels"}
    e = client.get("/api/entities/c1/app/events").json()
    assert "annotation" not in e
    assert e["columns"][0] == {"name": "ts", "type": "DateTime", "comment": ""}
    assert client.get("/api/search", params={"q": "checkout"}).json()["nodes"] == []


def test_mcp_columns(pulled):
    url, repo, _ = pulled

    async def go(c, enabled):
        async with Client(create_mcp(_cfg(url, repo, enabled=enabled))) as client:
            graph = (await client.call_tool("get_schema_graph", {"cluster": c})).data
            found = (await client.call_tool("find_tables", {"query": "events", "column": ["ts"]})).data
            return graph, found

    graph, found = asyncio.run(go("c1", True))
    assert graph["columns"][-2:] == ["summary", "status"]
    assert graph["annotations"]["query_hints"] == ["All times UTC."]
    assert found["columns"][-3:] == ["summary", "status", "matched_columns"]

    graph, found = asyncio.run(go("c1", False))
    assert "summary" not in graph["columns"] and "annotations" not in graph
    assert "summary" not in found["columns"]


def test_fatal_pull_keeps_last_good_copy(pulled):
    url, repo, cfg = pulled
    (repo / "_global.yaml").write_text("version: 2\n")
    with pytest.raises(FatalTreeError):
        pull(cfg, make_session_factory(url))
    e = TestClient(create_app(cfg)).get("/api/entities/c1/app/events").json()
    assert "annotation" in e


@pytest.mark.skipif(not shutil.which("git"), reason="git not installed")
def test_pull_from_bare_remote(tmp_path):
    url, factory = _catalog(tmp_path)
    bare, work = tmp_path / "remote.git", tmp_path / "work"

    def git(*args, cwd=None):
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)

    git("init", "--bare", "--initial-branch=main", str(bare))
    git("init", "--initial-branch=main", str(work))
    _base_tree(work)
    git("add", ".", cwd=work)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "init", cwd=work)
    git("push", str(bare), "main", cwd=work)

    result = pull(_cfg(url, f"file://{bare}"), factory)
    assert len(result["sha"]) == 40 and result["files"] == 4
    e = TestClient(create_app(_cfg(url, f"file://{bare}"))).get("/api/entities/c1/app/events").json()
    assert e["annotation"]["status"] == "deprecated"
