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


@dataclass
class AppConfig:
    storage_url: str
    clusters: list[ClusterConfig]


def load_config(path: str | Path) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text())
    return AppConfig(
        storage_url=StorageConfig(**raw["storage"]).resolve_url(),
        clusters=[ClusterConfig(**c) for c in raw["clusters"]],
    )
