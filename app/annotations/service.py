"""Annotation orchestration: pull the repo into the catalog (store), poll it
for changes while serving, and (M24) write back through merge/pull requests
(GitLab or GitHub) — agent proposals and schema-drift stubs. Entry points call this; it calls
app/store and never app/adapters."""

import asyncio
import difflib
import hashlib
import logging
import re
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parseaddr
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

from pydantic import ValidationError
from ruamel.yaml.error import YAMLError
from sqlalchemy.orm import Session, sessionmaker

from app.annotations import gitrepo, mrtext
from app.annotations.model import (
    TableAnnotation,
    Tree,
    dump_rt,
    format_errors,
    load_rt,
    load_tree,
    merge_patch,
    render_stub,
    summary_of,
)
from app.config import AnnotationsConfig, AppConfig
from app.store.queries import catalog_columns
from app.store.repo import replace_annotations

log = logging.getLogger(__name__)


def _dir_hash(root: Path) -> str:
    """Version of a local-dir repo: hash of sorted (relpath, bytes), .git skipped."""
    h = hashlib.sha256()
    files = sorted(
        (p.relative_to(root).as_posix(), p)
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(root).parts
    )
    for rel, p in files:
        h.update(rel.encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()[:40]


def remote_version(cfg: AppConfig) -> str:
    a = cfg.annotations
    if a.is_local:
        return _dir_hash(Path(a.repo))
    return gitrepo.ls_remote(a.repo, a.ref, a.token)


def _root(path: str) -> str:
    return str(PurePosixPath(path))


def _roots_for(a: AnnotationsConfig, cluster: str) -> set[str]:
    """Roots a cluster's files may come from: its own, plus the shared
    fallback unless in per-cluster mode."""
    return {a.root_for(cluster)} if a.per_cluster else {a.root_for(cluster), a.path}


def _load_trees(cfg: AppConfig, workdir: Path) -> tuple[dict[str, Tree], list[str]]:
    """Shared root + each distinct cluster root. Entry paths are rewritten
    to be repo-relative (root prefix included). Per-cluster mode: a cluster
    without a dir yet reads as empty (drift creates it) and is reported as
    an error, not fatal, so a typo'd `path` still shows up."""
    a = cfg.annotations
    trees: dict[str, Tree] = {}
    errors: list[str] = []
    roots = {_root(a.root_for(c.name)) for c in cfg.clusters}
    if not a.per_cluster:
        roots.add(_root(a.path))
    for root in sorted(roots):
        if a.per_cluster and not (workdir / root).is_dir():
            trees[root] = Tree()
            errors.append(f"{root}: cluster root not found (no annotations for it)")
            continue
        # An override root nested inside this one (e.g. shared "" holding
        # clusters/prod) is not a database dir here.
        nested = frozenset(
            PurePosixPath(o).relative_to(root).parts[0]
            for o in roots
            if o != root and PurePosixPath(o).is_relative_to(root)
        )
        tree, errs = load_tree(workdir / root, nested)

        def at(entry):
            doc, rel = entry
            return doc, str(PurePosixPath(root) / rel)

        tree.global_ = at(tree.global_) if tree.global_ else None
        tree.databases = {k: at(e) for k, e in tree.databases.items()}
        tree.tables = {k: at(e) for k, e in tree.tables.items()}
        trees[root] = tree
        errors += [f"{root}/{e}" if root != "." else e for e in errs]
    return trees, errors


def _rows(cfg: AppConfig, trees: dict[str, Tree]) -> list[dict]:
    """Per configured cluster, file-level fallback: a file in the cluster's
    override root wins over the same file in the shared root. One row per
    non-empty doc (an unfilled stub reads as unannotated)."""
    a = cfg.annotations
    shared = trees.get(_root(a.path), Tree())  # per-cluster mode: none, no fallback
    rows = []
    for c in cfg.clusters:
        override = trees[_root(a.root_for(c.name))]
        entries = []
        if g := override.global_ or shared.global_:
            entries.append(("", "", g))
        entries += [(db, "", e) for db, e in {**shared.databases, **override.databases}.items()]
        entries += [(db, t, e) for (db, t), e in {**shared.tables, **override.tables}.items()]
        for database, table, (doc, path) in entries:
            if not doc:
                continue
            rows.append({
                "cluster": c.name, "database": database, "table_name": table, "doc": doc, "path": path,
                "summary": summary_of(doc) if table else "",
                "status": doc.get("status", "active") if table else "",
            })
    return rows


@contextmanager
def _checkout(a: AnnotationsConfig) -> Iterator[tuple[Path, str]]:
    """(working tree, version). A git remote gets a fresh shallow clone into a
    temp dir each time: no persistent cache dir, nothing to lock."""
    if a.is_local:
        yield Path(a.repo), _dir_hash(Path(a.repo))
        return
    with TemporaryDirectory(prefix="ohmydb-annotations-") as tmp:
        yield Path(tmp), gitrepo.clone(a.repo, a.ref, Path(tmp), a.token)


def _store(cfg: AppConfig, factory: sessionmaker[Session], workdir: Path, sha: str) -> tuple[dict, dict[str, Tree]]:
    trees, errors = _load_trees(cfg, workdir)
    with factory() as s:
        replace_annotations(s, _rows(cfg, trees), sha)
    files = sum(len(t.tables) + len(t.databases) + bool(t.global_) for t in trees.values())
    return {"sha": sha, "files": files, "errors": errors}, trees


def pull(cfg: AppConfig, factory: sessionmaker[Session]) -> dict:
    """Fetch + parse the annotation repo and replace the catalog copy.
    Per-file errors skip that file and are returned; a fatal error (clone
    failure, missing root, unsupported version) raises before anything is
    written, so the last good copy stays. Returns {sha, files, errors}."""
    with _checkout(cfg.annotations) as (workdir, sha):
        return _store(cfg, factory, workdir, sha)[0]


def sync_annotations(cfg: AppConfig, factory: sessionmaker[Session]) -> dict:
    """Post-sync annotation step (`ohmydb sync`, POST /api/sync): pull, then
    with `drift_mr` the drift MR from the same clone. A drift failure lands
    in result["drift"] — the pull already succeeded and stays."""
    a = cfg.annotations
    with _checkout(a) as (workdir, sha):
        result, trees = _store(cfg, factory, workdir, sha)
        if a.drift_mr:
            try:
                result["drift"] = _drift(cfg, factory, workdir, trees)
            except Exception as e:
                result["drift"] = {"status": "failed", "detail": str(e)}
    return result


def format_result(result: dict) -> str:
    line = f"annotations: sha={result['sha'][:12]} files={result['files']} errors={len(result['errors'])}"
    if d := result.get("drift"):
        line += f" drift={d['status']}"
        line += "".join(f" {d[k]}" for k in ("merge_request", "detail") if d.get(k))
    return line


async def poll_forever(cfg: AppConfig, factory: sessionmaker[Session]) -> None:
    """serve-only background loop: cheap version check every pull_interval,
    full pull only when it changed. First check runs immediately. Never
    raises (except cancellation) — a failed poll is a warning, not a crash."""
    last = None
    while True:
        try:
            version = await asyncio.to_thread(remote_version, cfg)
            if version != last:
                result = await asyncio.to_thread(pull, cfg, factory)
                last = result["sha"]
                log.info(format_result(result))
                for e in result["errors"]:
                    log.warning("annotations: %s", e)
        except Exception as e:
            log.warning("annotations poll failed: %s", e)
        await asyncio.sleep(cfg.annotations.pull_interval)


# --- write path (M24) ---

DRIFT_BRANCH = "ohmydb/drift"
_BAD_NAME_CHARS = re.compile(r"[/\\\0]")


def _safe_name(name: str) -> bool:
    """Usable as a path segment of <db>/<table>.yaml. A leading "." or "_"
    would make load_tree skip or reject the file, so it's refused too."""
    return bool(name) and not _BAD_NAME_CHARS.search(name) and name[0] not in "._"


def _orphans_and_stale(cfg: AppConfig, trees: dict[str, Tree],
                       catalog: dict) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Orphans: table files (repo-relative paths) whose table is gone from
    every cluster the file serves — the drift MR deletes them. A file served
    by a cluster with nothing in the catalog (never synced) is never an
    orphan: absence there proves nothing. Stale: (path, columns) for
    annotated columns that no longer exist (reported only, never edited)."""
    a = cfg.annotations
    synced = {c for c, _, _ in catalog}
    orphans, stale_files = [], []
    for root, tree in trees.items():
        shared = not a.per_cluster and root == _root(a.path)
        served = [c.name for c in cfg.clusters if shared or root == _root(a.root_for(c.name))]
        for (db, name), (doc, path) in sorted(tree.tables.items()):
            hits = [catalog[(c, db, name)] for c in served if catalog.get((c, db, name), ("external",))[0] != "external"]
            if not hits:
                if served and all(c in synced for c in served):
                    orphans.append(path)
            elif stale := sorted(set(doc.get("columns", {})) - {col for _, cols in hits for col in cols}):
                stale_files.append((path, stale))
    return orphans, stale_files


def _drift_title(stubs: int, removed: int) -> str:
    def n(count: int, noun: str) -> str:
        return f"{count} {noun}{'s' if count != 1 else ''}"

    if not removed:
        return f"ohmydb: annotation stubs for {n(stubs, 'table')}"
    if not stubs:
        return f"ohmydb: remove {n(removed, 'orphan annotation file')}"
    return f"ohmydb: annotation stubs for {n(stubs, 'table')}, remove {n(removed, 'orphan file')}"


def _drift(cfg: AppConfig, factory: sessionmaker[Session], workdir: Path, trees: dict[str, Tree]) -> dict:
    """Rolling MR on DRIFT_BRANCH adding stub files for catalog tables that
    have no annotation file anywhere and deleting files whose table is gone
    (see _orphans_and_stale); other existing files are never touched. Stubs
    go to the shared root (per-cluster mode: each cluster's root). Skipped
    when a human pushed to the branch."""
    a = cfg.annotations
    with factory() as s:
        catalog = catalog_columns(s)
    shared = trees.get(_root(a.path), Tree())
    # `ignore` resolves like reads: the cluster's _global.yaml, else the shared one.
    ignore: dict[str, list[re.Pattern]] = {}
    for c in cfg.clusters:
        g = trees[_root(a.root_for(c.name))].global_ or shared.global_
        if g is None and any((workdir / r / "_global.yaml").is_file() for r in _roots_for(a, c.name)):
            return {"status": "skipped", "detail": "_global.yaml has errors (its ignore list is unknown)"}
        ignore[c.name] = [re.compile(p) for p in (g or ({}, ""))[0].get("ignore", [])]

    stubs: dict[tuple[str, str, str], tuple[str, list[str]]] = {}
    for (cluster, db, name), (kind, columns) in sorted(catalog.items()):
        if cluster not in ignore or kind == "external" or not (_safe_name(db) and _safe_name(name)):
            continue
        if any(p.search(f"{db}.{name}") for p in ignore[cluster]):
            continue
        # On disk, not the parsed tree: a file with errors still exists and
        # must not be overwritten by a stub.
        if any((workdir / r / db / f"{name}.yaml").exists() for r in _roots_for(a, cluster)):
            continue
        target = a.root_for(cluster) if a.per_cluster else a.path
        stubs.setdefault((target, db, name), (cluster, columns))
    orphans, stale = _orphans_and_stale(cfg, trees, catalog)
    if not stubs and not orphans:
        return {"status": "none"}

    seen = gitrepo.remote_sha(a.repo, DRIFT_BRANCH, a.token)
    if seen is not None:
        gitrepo.fetch(workdir, a.repo, DRIFT_BRANCH, a.token)
        if gitrepo.head_author_email(workdir, "FETCH_HEAD") != parseaddr(a.author)[1]:
            return {"status": "skipped", "detail": f"{DRIFT_BRANCH} has commits by someone else"}

    for (target, db, name), (_, columns) in stubs.items():
        path = workdir / target / db / f"{name}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_stub(db, name, columns))
    for rel in orphans:
        (workdir / rel).unlink()
    tables = [f"{db}.{name}" + (f" ({cluster})" if a.per_cluster else "") for (_, db, name), (cluster, _) in stubs.items()]
    counts = {"tables": len(tables), "removed": len(orphans)}
    gitrepo.commit(workdir, f"annotations: stubs for {len(tables)} new table(s), {len(orphans)} orphan(s) removed\n\n"
                            + "\n".join([*tables, *(f"removed {rel}" for rel in orphans)]), a.author)
    if seen is not None and gitrepo.rev_parse(workdir, "FETCH_HEAD^{tree}") == gitrepo.rev_parse(workdir, "HEAD^{tree}"):
        return {"status": "unchanged", **counts}

    description = mrtext.drift_description(
        [(db, name, cluster if a.per_cluster else None) for (_, db, name), (cluster, _) in stubs.items()],
        orphans, stale)
    url = gitrepo.publish(workdir, a.repo, DRIFT_BRANCH, seen or "", a.ref, _drift_title(len(tables), len(orphans)),
                          description, a.token, labels=(gitrepo.LABEL, f"{gitrepo.LABEL}::drift"))
    return {"status": "pushed", **counts, "merge_request": url}


class ProposalError(Exception):
    """Rejected proposal. `status`: 404 unknown entity, 422 invalid input —
    `errors` lists every problem so an agent can fix the patch and retry."""

    def __init__(self, status: int, errors: list[str]):
        super().__init__("; ".join(errors))
        self.status = status
        self.errors = errors


def _check_against_catalog(doc, cluster: str, database: str, name: str, catalog: dict) -> list[str]:
    """The guard against hallucinated columns and tables: the patched doc
    must fit the schema and only reference what exists in this cluster."""
    try:
        model = TableAnnotation.model_validate(doc)
    except ValidationError as e:
        return format_errors(e)
    columns = set(catalog[(cluster, database, name)][1])
    errors = [f"columns.{c}: {database}.{name} has no such column" for c in model.columns if c not in columns]

    def target(ref: str) -> tuple[str, list[str]] | None:
        return catalog.get((cluster, *ref.split(".", 1)))

    for i, r in enumerate(model.relationships):
        if (t := target(r.to)) is None:
            errors.append(f"relationships.{i}.to: {r.to} not found in cluster {cluster}")
            continue
        errors += [f"relationships.{i}.from_columns: {database}.{name} has no column {c}"
                   for c in r.from_columns if c not in columns]
        errors += [f"relationships.{i}.to_columns: {r.to} has no column {c}" for c in r.to_columns if c not in t[1]]
    if model.use_instead and ("." not in model.use_instead or target(model.use_instead) is None):
        errors.append(f"use_instead: {model.use_instead} not found in cluster {cluster} (expected db.table)")
    return errors


def propose(cfg: AppConfig, factory: sessionmaker[Session], cluster: str, database: str, name: str,
            patch: dict, rationale: str, via: str) -> dict:
    """Apply a JSON merge patch to the table's annotation file (the one in
    effect for `cluster`: its override file, else the shared one, else a new
    shared file) and open one MR for it on a unique branch. Nothing changes
    until a human merges. Raises ProposalError."""
    a = cfg.annotations
    with factory() as s:
        catalog = catalog_columns(s)
    if catalog.get((cluster, database, name), ("external",))[0] == "external":
        raise ProposalError(404, [f"entity not found: {cluster}/{database}/{name}"])
    if not rationale.strip():
        raise ProposalError(422, ["rationale: required — say what you verified and how"])
    if not (_safe_name(database) and _safe_name(name)):
        raise ProposalError(422, [f"{database}.{name}: name can't be used as an annotation file path"])

    rel_in_root = PurePosixPath(database) / f"{name}.yaml"
    with TemporaryDirectory(prefix="ohmydb-annotations-") as tmp:
        workdir = Path(tmp)
        gitrepo.clone(a.repo, a.ref, workdir, a.token)
        root = a.root_for(cluster)
        if a.per_cluster or (workdir / root / rel_in_root).is_file():
            rel = str(PurePosixPath(root) / rel_in_root)
        else:
            rel = str(PurePosixPath(a.path) / rel_in_root)
        path = workdir / rel
        if not path.resolve().is_relative_to(workdir.resolve()):
            raise ProposalError(422, [f"{rel}: path escapes the repo"])

        current = path.read_text() if path.is_file() else ""
        try:
            doc = merge_patch(load_rt(current), patch)
        except (YAMLError, ValueError) as e:
            raise ProposalError(422, [f"{rel} (current file): {e}"]) from None
        if errors := _check_against_catalog(doc, cluster, database, name, catalog):
            raise ProposalError(422, errors)
        text = dump_rt(doc) if doc else ""
        if text == current:
            return {"status": "unchanged", "path": rel}

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        branch = f"ohmydb/propose/{database}.{name}-{ts}-{secrets.token_hex(2)}"
        rationale = rationale.strip()
        gitrepo.commit(workdir, f"annotations({database}.{name}): {rationale.splitlines()[0]}\n\n"
                                f"{rationale}\n\nvia {via}", a.author)
        diff = difflib.unified_diff(current.splitlines(), text.splitlines(), "/dev/null" if not current else rel,
                                    rel, lineterm="")
        description = mrtext.proposal_description(cluster, database, name, rel, not current, patch, rationale,
                                                  list(diff), via)
        url = gitrepo.publish(workdir, a.repo, branch, "", a.ref, f"ohmydb: annotate {database}.{name}", description,
                              a.token, labels=(gitrepo.LABEL, f"{gitrepo.LABEL}::proposal"))
    return {"status": "proposed", "branch": branch, "merge_request": url, "path": rel}
