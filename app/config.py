"""Load config.yaml: storage url + cluster connection list."""

import os
from dataclasses import dataclass, field
from pathlib import Path

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
class AppConfig:
    storage_url: str
    clusters: list[ClusterConfig]
    # Global auto-labeling rules, applied to every cluster before its own
    # label_rules (additive — see app/core/labeling.py).
    label_rules: list[dict] = field(default_factory=list)


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
    )


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
