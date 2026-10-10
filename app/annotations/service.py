"""Annotation orchestration: pull the repo into the catalog (store), poll it
for changes while serving. Entry points call this; it calls app/store and
never app/adapters."""

import asyncio
import hashlib
import logging
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

from sqlalchemy.orm import Session, sessionmaker

from app.annotations import gitrepo
from app.annotations.model import Tree, load_tree, summary_of
from app.config import AnnotationsConfig, AppConfig
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


def _load_trees(a: AnnotationsConfig, workdir: Path) -> tuple[dict[str, Tree], list[str]]:
    """Shared root + each distinct override root. Entry paths are rewritten
    to be repo-relative (root prefix included)."""
    trees: dict[str, Tree] = {}
    errors: list[str] = []
    roots = {str(PurePosixPath(r)) for r in (a.path, *a.cluster_paths.values())}
    for root in sorted(roots):
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
    shared = trees[str(PurePosixPath(a.path))]
    rows = []
    for c in cfg.clusters:
        override = trees[str(PurePosixPath(a.cluster_paths.get(c.name, a.path)))]
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


def pull(cfg: AppConfig, factory: sessionmaker[Session]) -> dict:
    """Fetch + parse the annotation repo and replace the catalog copy.
    Per-file errors skip that file and are returned; a fatal error (clone
    failure, missing root, unsupported version) raises before anything is
    written, so the last good copy stays. Returns {sha, files, errors}."""
    a = cfg.annotations
    if a.is_local:
        sha = _dir_hash(Path(a.repo))
        trees, errors = _load_trees(a, Path(a.repo))
    else:
        # Fresh shallow clone each time: no persistent cache dir, nothing to lock.
        with TemporaryDirectory(prefix="ohmydb-annotations-") as tmp:
            sha = gitrepo.clone(a.repo, a.ref, Path(tmp), a.token)
            trees, errors = _load_trees(a, Path(tmp))
    rows = _rows(cfg, trees)
    with factory() as s:
        replace_annotations(s, rows, sha)
    files = sum(len(t.tables) + len(t.databases) + bool(t.global_) for t in trees.values())
    return {"sha": sha, "files": files, "errors": errors}


def sync_annotations(cfg: AppConfig, factory: sessionmaker[Session]) -> dict:
    """Post-sync annotation step (`ohmydb sync`, POST /api/sync). M23: pull only."""
    return pull(cfg, factory)


def format_result(result: dict) -> str:
    return f"annotations: sha={result['sha'][:12]} files={result['files']} errors={len(result['errors'])}"


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
