import asyncio
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient
from fastmcp import Client

from app.annotations import gitrepo, mrtext
from app.annotations.model import FatalTreeError, dump_rt, load_rt, load_tree, merge_patch, render_stub
from app.annotations.service import _drift_title, pull, sync_annotations
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


def test_per_cluster_roots_no_fallback(tmp_path):
    url, factory = _catalog(tmp_path)
    repo = _tree(tmp_path / "repo", {"anno/c1/app/events.yaml": "description: c1 events\n"})  # no anno/c2 yet
    cfg = _cfg(url, repo, path="anno/{cluster}")
    assert cfg.annotations.root_for("c2") == "anno/c2"
    result = pull(cfg, factory)
    assert result["files"] == 1 and result["errors"] == ["anno/c2: cluster root not found (no annotations for it)"]
    client = TestClient(create_app(cfg))
    assert client.get("/api/entities/c1/app/events").json()["annotation"]["description"] == "c1 events"
    assert "annotation" not in client.get("/api/entities/c2/app/events").json()  # c1's file doesn't leak


def test_fatal_pull_keeps_last_good_copy(pulled):
    url, repo, cfg = pulled
    (repo / "_global.yaml").write_text("version: 2\n")
    with pytest.raises(FatalTreeError):
        pull(cfg, make_session_factory(url))
    e = TestClient(create_app(cfg)).get("/api/entities/c1/app/events").json()
    assert "annotation" in e


needs_git = pytest.mark.skipif(not shutil.which("git"), reason="git not installed")


def _git(*args, cwd=None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def remote(tmp_path):
    """Bare repo seeded with _base_tree, reachable over file:// like a real
    remote. advertisePushOptions: the write path pushes with GitLab -o options."""
    bare, work = tmp_path / "remote.git", tmp_path / "work"
    _git("init", "--bare", "--initial-branch=main", str(bare))
    _git("config", "receive.advertisePushOptions", "true", cwd=bare)
    _git("init", "--initial-branch=main", str(work))
    _base_tree(work)
    _git("add", ".", cwd=work)
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "init", cwd=work)
    _git("push", str(bare), "main", cwd=work)
    return bare


@needs_git
def test_pull_from_bare_remote(tmp_path, remote):
    url, factory = _catalog(tmp_path)
    result = pull(_cfg(url, f"file://{remote}"), factory)
    assert len(result["sha"]) == 40 and result["files"] == 4
    e = TestClient(create_app(_cfg(url, f"file://{remote}"))).get("/api/entities/c1/app/events").json()
    assert e["annotation"]["status"] == "deprecated"


# --- write path (M24) ---

def test_merge_patch_keeps_untouched_lines():
    text = "# owned by team-web\ndescription: Events  # keep me\ncolumns:\n  ts: {description: \"UTC\"}\n"
    doc = merge_patch(load_rt(text), {"grain": "one row per event", "columns": {"ts": None, "id": {"description": "pk"}}})
    out = dump_rt(doc)
    assert out.startswith("# owned by team-web\ndescription: Events  # keep me\n")
    assert load_rt(out) == {"description": "Events", "columns": {"id": {"description": "pk"}}, "grain": "one row per event"}


def _branches(bare) -> list[str]:
    return _git("for-each-ref", "--format=%(refname:short)", "refs/heads", cwd=bare).split()


@needs_git
def test_propose_via_mcp_opens_branch(tmp_path, remote):
    url, _ = _catalog(tmp_path)
    cfg = _cfg(url, f"file://{remote}", proposals=True)

    async def go():
        async with Client(create_mcp(cfg)) as client:
            return (await client.call_tool("propose_annotation", {
                "cluster": "c1", "database": "app", "name": "users",
                "patch": {"description": "Registered users", "columns": {"id": {"description": "User id"}}},
                "rationale": "Checked app code\nids come from the signup service",
            })).data

    result = asyncio.run(go())
    assert result["status"] == "proposed" and result["path"] == "app/users.yaml"
    assert result["branch"].startswith("ohmydb/propose/app.users-") and result["branch"] in _branches(remote)
    shown = _git("show", f"{result['branch']}:app/users.yaml", cwd=remote)
    assert load_rt(shown) == {"description": "Registered users", "columns": {"id": {"description": "User id"}}}
    msg = _git("log", "-1", "--format=%an <%ae>%n%B", result["branch"], cwd=remote)
    assert msg.startswith("ohmydb <ohmydb@noreply.invalid>\nannotations(app.users): Checked app code\n")
    assert "via MCP" in msg


@needs_git
def test_propose_rejects_hallucinations_over_http(tmp_path, remote):
    url, _ = _catalog(tmp_path)
    client = TestClient(create_app(_cfg(url, f"file://{remote}", proposals=True)))
    r = client.post("/api/annotations/c1/app/events/proposals", json={
        "patch": {"columns": {"nope": {"description": "x"}},
                  "relationships": [{"to": "app.ghost", "from_columns": ["ts"], "to_columns": ["id"]}]},
        "rationale": "guess",
    })
    assert r.status_code == 422
    errors = "\n".join(r.json()["detail"])
    assert "columns.nope" in errors and "app.ghost not found" in errors
    assert "use_instead: app.events_v2" in errors  # pre-existing problems are reported too
    assert client.post("/api/annotations/c1/app/nope/proposals",
                       json={"patch": {}, "rationale": "x"}).status_code == 404
    assert _branches(remote) == ["main"]


def test_github_pr_reuses_open_pr(monkeypatch):
    assert gitrepo._github_repo("https://github.com/acme/ann.git") == "acme/ann"
    assert gitrepo._github_repo("https://gitlab.example.com/acme/ann.git") is None
    calls = []

    def fake_api(method, path, token, body=None):
        calls.append((method, path))
        if method == "POST" and path.endswith("/pulls"):
            raise gitrepo.GitError("GitHub API POST /repos/acme/ann/pulls failed: HTTP 422 already exists")
        if method == "GET":
            return [{"number": 7, "html_url": "https://github.com/acme/ann/pull/7"}]
        if method == "PATCH":
            return {}
        raise gitrepo.GitError("HTTP 403 labels")  # labeling is best effort

    monkeypatch.setattr(gitrepo, "_github_api", fake_api)
    assert gitrepo._github_pr("acme/ann", "t", "ohmydb/drift", "main", "title", "body", ("ohmydb",)) == \
        "https://github.com/acme/ann/pull/7"
    assert calls[1] == ("GET", "/repos/acme/ann/pulls?state=open&head=acme%3Aohmydb/drift")
    assert calls[2] == ("PATCH", "/repos/acme/ann/pulls/7")  # reused PR gets the fresh title/body


def test_gitlab_options_carry_all_labels():
    opts = gitrepo._gitlab_options("main", "t", "a\nb", ("ohmydb", "ohmydb::drift"))
    assert "merge_request.description=a\\nb" in opts
    assert [o for o in opts if o.startswith("merge_request.label=")] == \
        ["merge_request.label=ohmydb", "merge_request.label=ohmydb::drift"]


def test_drift_description_small_and_huge():
    text = mrtext.drift_description([("app", "events", None), ("app", "users", None)], ["app/old.yaml"],
                                    [("app/x.yaml", ["gone"])])
    assert "<details><summary><b>app</b> — 2</summary>\n\n- `app.events`" in text
    assert "| 🆕 New tables (stubs added) | 2 |" in text and "- `app/old.yaml`" in text
    assert "- `app/x.yaml`: `gone`" in text and "- [ ] Removed files" in text

    stubs = [(f"db_{i % 30}", f"table_🚀_{i:05}", "prod") for i in range(5000)]
    text = mrtext.drift_description(stubs, [], [])
    assert mrtext.fits(text) and "more (see the Changes tab)" in text
    assert all(f"— {n}</summary>" in text for n in (167, 166))  # every per-db count kept


def test_proposal_description():
    text = mrtext.proposal_description("c1", "app", "t", "app/t.yaml", True,
                                       {"use_instead": None, "columns": {"ts": {"description": "UTC"}}},
                                       "Checked\n\nwith a query", "MCP")
    assert "`use_instead` (removed), `columns.ts`" in text and "(new file)" in text
    assert "> Checked\n>\n> with a query" in text and "diff" not in text
    huge = mrtext.proposal_description("c1", "app", "t", "app/t.yaml", False, {}, "x" * 100_000, "HTTP")
    assert mrtext.fits(huge) and huge.endswith("</sub>")


def test_proposals_off_or_unauthorized(tmp_path):
    url, _ = _catalog(tmp_path)
    path, body = "/api/annotations/c1/app/users/proposals", {"patch": {}, "rationale": "x"}
    off = _cfg(url, "file:///nowhere")
    assert TestClient(create_app(off)).post(path, json=body).status_code in (404, 405)

    async def tools(cfg):
        async with Client(create_mcp(cfg)) as client:
            return {t.name for t in await client.list_tools()}

    assert "propose_annotation" not in asyncio.run(tools(off))
    on = _cfg(url, "file:///nowhere", proposals=True)
    assert "propose_annotation" in asyncio.run(tools(on))
    on.auth_token = "s3cr3t"
    assert TestClient(create_app(on)).post(path, json=body).status_code == 401


@needs_git
def test_drift_per_cluster_stubs(tmp_path, remote):
    url, factory = _catalog(tmp_path)
    cfg = _cfg(url, f"file://{remote}", drift_mr=True, path="anno/{cluster}")
    drift = sync_annotations(cfg, factory)["drift"]
    assert drift["status"] == "pushed" and drift["tables"] == 3
    files = _git("ls-tree", "-r", "--name-only", "ohmydb/drift", "anno", cwd=remote).split()
    assert files == ["anno/c1/app/events.yaml", "anno/c1/app/users.yaml", "anno/c2/app/events.yaml"]


@needs_git
def test_drift_removes_orphans(tmp_path, remote):
    url, factory = _catalog(tmp_path)
    with factory() as s:  # app.users dropped from c1 (c2 never had it)
        sync_cluster(s, "c1", [Entity(cluster="c1", database="app", name="events", kind=EntityKind.TABLE,
                                      columns=[Column("ts", "DateTime"), Column("kind", "UInt8")])], [])
    cfg = _cfg(url, f"file://{remote}", drift_mr=True)
    cfg.clusters.append(ClusterConfig(name="c3", host="localhost"))  # never synced: proves nothing
    assert sync_annotations(cfg, factory)["drift"]["status"] == "none"

    cfg.clusters.pop()
    drift = sync_annotations(cfg, factory)["drift"]
    assert drift["status"] == "pushed" and drift["tables"] == 0 and drift["removed"] == 1
    files = _git("ls-tree", "-r", "--name-only", "ohmydb/drift", cwd=remote).split()
    assert "app/users.yaml" not in files and "app/events.yaml" in files
    assert _drift_title(0, 1) == "ohmydb: remove 1 orphan annotation file"
    assert _drift_title(2, 3) == "ohmydb: annotation stubs for 2 tables, remove 3 orphan files"
    assert _drift_title(1, 0) == "ohmydb: annotation stubs for 1 table"


@needs_git
def test_drift_mr_lifecycle(tmp_path, remote):
    url, factory = _catalog(tmp_path)
    with factory() as s:  # c2 gains a table no annotation file covers
        sync_cluster(s, "c2", [
            Entity(cluster="c2", database="app", name="events", kind=EntityKind.TABLE, columns=[Column("ts", "DateTime")]),
            Entity(cluster="c2", database="app", name="sessions", kind=EntityKind.TABLE,
                   columns=[Column("sid", "UUID"), Column("weird col", "String")]),
        ], [])
    cfg = _cfg(url, f"file://{remote}", drift_mr=True)

    drift = sync_annotations(cfg, factory)["drift"]
    assert drift["status"] == "pushed" and drift["tables"] == 1
    stub = _git("show", "ohmydb/drift:app/sessions.yaml", cwd=remote)
    assert stub == render_stub("app", "sessions", ["sid", "weird col"]) and '"weird col"' in stub
    _, errors = load_tree(_tree(tmp_path / "check", {"app/sessions.yaml": stub}))
    assert errors == []

    assert sync_annotations(cfg, factory)["drift"]["status"] == "unchanged"  # nothing new: no push

    work = tmp_path / "human"
    _git("clone", "--quiet", "--branch", "ohmydb/drift", f"file://{remote}", str(work))
    (work / "app/sessions.yaml").write_text("description: Web sessions\n")
    _git("-c", "user.name=h", "-c", "user.email=human@example.com", "commit", "-qam", "fill", cwd=work)
    _git("push", "--quiet", "origin", "ohmydb/drift", cwd=work)
    assert sync_annotations(cfg, factory)["drift"]["status"] == "skipped"
