"""Load config.yaml: storage url + cluster connection list."""

import os
from dataclasses import dataclass, field
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import urlsplit

import yaml


@dataclass
class StorageConfig:
    # sqlite (local debug): set `url`. postgres (prod): set the fields below.
    type: str = "sqlite"
    url: str = ""
    host: str = "localhost"
    port: int = 5432
    username: str = "ohmydb"
    password: str = ""
    database: str = "ohmydb"

    def resolve_url(self) -> str:
        if self.type == "sqlite":
            return self.url
        if self.type == "postgres":
            # Env wins over config so secrets stay out of the mounted config file
            # (inject via k8s secret / POSTGRES_USER, POSTGRES_PASSWORD).
            user = os.environ.get("POSTGRES_USER") or self.username
            password = os.environ.get("POSTGRES_PASSWORD")
            if password is None:
                password = self.password
            return f"postgresql+psycopg://{user}:{password}@{self.host}:{self.port}/{self.database}"
        raise ValueError(f"unknown storage type: {self.type}")


@dataclass
class ClusterConfig:
    name: str
    host: str
    type: str = "clickhouse"
    port: int = 8123
    username: str = "default"
    password: str = ""
    databases: list[str] = field(default_factory=list)
    # Extra keyword args passed straight to the DB client, e.g.
    # {secure: true, verify: false, connect_timeout: 30}. Adapter-specific.
    extra: dict = field(default_factory=dict)
    # Auto-labeling rules for this cluster, applied after the global list
    # (see AppConfig.label_rules and app/core/labeling.py). Each entry:
    # {match: {engine|kind|name_pattern|database_pattern: ...}, label: {key, value}}.
    label_rules: list[dict] = field(default_factory=list)


@dataclass
class AnnotationsConfig:
    """Repo-backed annotation layer (see docs/ANNOTATIONS.md, app/annotations/).
    `enabled: false` (the default) makes the feature fully inert."""

    enabled: bool = False
    # https:// or file:// = git remote (file:// mostly for tests); no "://" =
    # local directory, read as-is (read-only, no git needed).
    repo: str = ""
    ref: str = "main"  # branch read + MR target
    # Shared root inside the repo/dir. With a "{cluster}" placeholder (e.g.
    # "anno/{cluster}") every cluster gets its own root instead: no shared
    # root, no fallback, writes land there too. Excludes cluster_paths.
    path: str = ""
    # {cluster: root} per-cluster override root; a file missing there falls
    # back to the same file under `path`.
    cluster_paths: dict[str, str] = field(default_factory=dict)
    pull_interval: int = 300  # serve only, seconds; 0 = no polling
    proposals: bool = False  # MCP propose_annotation + HTTP proposals route (GitLab MRs)
    drift_mr: bool = False  # rolling stub MR on branch ohmydb/drift after each sync
    # Commit identity of the bot; the drift step also uses its email to tell
    # its own commits from human ones on the drift branch.
    author: str = "ohmydb <ohmydb@noreply.invalid>"
    # Git HTTPS token: env-only (OHMYDB_ANNOTATIONS_TOKEN), never a yaml key;
    # repr=False keeps it out of logs/tracebacks.
    token: str | None = field(default=None, repr=False)

    @property
    def is_local(self) -> bool:
        return "://" not in self.repo

    @property
    def per_cluster(self) -> bool:
        return "{cluster}" in self.path

    def root_for(self, cluster: str) -> str:
        """The annotation root in effect for `cluster` (shared mode: its
        override root, else the shared one)."""
        if self.per_cluster:
            return self.path.replace("{cluster}", cluster)
        return self.cluster_paths.get(cluster, self.path)


@dataclass
class AppConfig:
    storage_url: str
    clusters: list[ClusterConfig]
    # Global auto-labeling rules, applied to every cluster before its own
    # label_rules (additive — see app/core/labeling.py).
    label_rules: list[dict] = field(default_factory=list)
    # Bearer token guarding mutating HTTP endpoints (POST /sync, PUT/DELETE
    # /labels, annotation proposals) — see app/api.py: require_token. None (the default, no yaml
    # field for it) means auth is off — env-only, like the CH/PG secrets,
    # so a token never ends up in a mounted config file.
    auth_token: str | None = None
    annotations: AnnotationsConfig = field(default_factory=AnnotationsConfig)


def load_config(path: str | Path) -> AppConfig:
    from app.core.labeling import validate_label_rules

    raw = yaml.safe_load(Path(path).read_text())
    clusters = [ClusterConfig(**c) for c in raw["clusters"]]
    _check_cluster_key_collisions(clusters)
    label_rules = raw.get("label_rules", [])
    validate_label_rules(label_rules)
    for c in clusters:
        validate_label_rules(c.label_rules)
    return AppConfig(
        storage_url=StorageConfig(**raw["storage"]).resolve_url(),
        clusters=clusters,
        label_rules=label_rules,
        auth_token=os.environ.get("OHMYDB_AUTH_TOKEN") or None,
        annotations=_load_annotations(raw.get("annotations") or {}, clusters),
    )


def _load_annotations(raw: dict, clusters: list[ClusterConfig]) -> AnnotationsConfig:
    if "token" in raw:
        raise ValueError("annotations.token is not a config key — set OHMYDB_ANNOTATIONS_TOKEN env instead")
    a = AnnotationsConfig(**raw)
    a.token = os.environ.get("OHMYDB_ANNOTATIONS_TOKEN") or None
    if a.enabled and not a.repo:
        raise ValueError("annotations.enabled is true but annotations.repo is empty")
    if not a.is_local:
        parts = urlsplit(a.repo)
        if parts.scheme not in ("https", "file"):
            raise ValueError(f"annotations.repo: unsupported scheme {parts.scheme!r} (use https:// or file://)")
        if parts.username or parts.password:
            raise ValueError(
                "annotations.repo must not embed credentials — set OHMYDB_ANNOTATIONS_TOKEN env instead"
            )
    elif a.proposals or a.drift_mr:
        raise ValueError("annotations.proposals/drift_mr need a git remote, not a local dir")
    unknown = set(a.cluster_paths) - {c.name for c in clusters}
    if unknown:
        raise ValueError(f"annotations.cluster_paths: unknown cluster(s) {sorted(unknown)}")
    if a.per_cluster and a.cluster_paths:
        raise ValueError("annotations.path with {cluster} and cluster_paths are mutually exclusive")
    if a.pull_interval < 0:
        raise ValueError("annotations.pull_interval must be >= 0")
    if "@" not in parseaddr(a.author)[1]:
        raise ValueError(f"annotations.author must look like 'Name <email>', got {a.author!r}")
    return a


def _check_cluster_key_collisions(clusters: list[ClusterConfig]) -> None:
    """Two cluster names can sanitize to the same per-cluster credential env
    key (see app/adapters/__init__.py: cluster_env_key), e.g. `prod-eu` vs
    `prod_eu` — fail fast instead of silently mixing up credentials."""
    from app.adapters import cluster_env_key

    seen: dict[str, str] = {}
    for c in clusters:
        key = cluster_env_key(c.name)
        if key in seen and seen[key] != c.name:
            raise ValueError(
                f"cluster names {seen[key]!r} and {c.name!r} both sanitize to "
                f"the same credential env key {key!r} — rename one"
            )
        seen[key] = c.name
