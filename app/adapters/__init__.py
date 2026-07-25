import os
import re

from app.adapters.base import Introspector


def cluster_env_key(name: str) -> str:
    """Sanitize a cluster name into an env-var-safe key (see load_config's
    collision check for why this must be injective across configured clusters)."""
    return re.sub(r"[^A-Z0-9]", "_", name.upper())


def build_introspector(cluster_cfg) -> Introspector:
    if cluster_cfg.type == "clickhouse":
        from app.adapters.clickhouse import ClickHouseIntrospector

        # Precedence: per-cluster env > global env (single-cluster fallback) >
        # config.yaml. Keeps secrets out of the mounted config file (inject
        # via k8s secret / CLICKHOUSE_USER[__KEY], CLICKHOUSE_PASSWORD[__KEY]).
        key = cluster_env_key(cluster_cfg.name)
        username = (
            os.environ.get(f"CLICKHOUSE_USER__{key}")
            or os.environ.get("CLICKHOUSE_USER")
            or cluster_cfg.username
        )
        password = os.environ.get(f"CLICKHOUSE_PASSWORD__{key}")
        if password is None:
            password = os.environ.get("CLICKHOUSE_PASSWORD")
        if password is None:
            password = cluster_cfg.password
        return ClickHouseIntrospector(
            cluster=cluster_cfg.name, host=cluster_cfg.host, port=cluster_cfg.port,
            username=username, password=password,
            databases=cluster_cfg.databases, extra=cluster_cfg.extra,
        )
    raise ValueError(f"unknown cluster type: {cluster_cfg.type}")
