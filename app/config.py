"""Load config.yaml: storage url + cluster connection list."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


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


@dataclass
class AppConfig:
    storage_url: str
    clusters: list[ClusterConfig]


def load_config(path: str | Path) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text())
    return AppConfig(
        storage_url=raw["storage"]["url"],
        clusters=[ClusterConfig(**c) for c in raw["clusters"]],
    )
