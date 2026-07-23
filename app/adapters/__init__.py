import os

from app.adapters.base import Introspector


def build_introspector(cluster_cfg) -> Introspector:
    if cluster_cfg.type == "clickhouse":
        from app.adapters.clickhouse import ClickHouseIntrospector

        # Env wins over config so secrets stay out of the mounted config file
        # (inject via k8s secret / CLICKHOUSE_USER, CLICKHOUSE_PASSWORD).
        username = os.environ.get("CLICKHOUSE_USER") or cluster_cfg.username
        password = os.environ.get("CLICKHOUSE_PASSWORD")
        if password is None:
            password = cluster_cfg.password
        return ClickHouseIntrospector(
            cluster=cluster_cfg.name, host=cluster_cfg.host, port=cluster_cfg.port,
            username=username, password=password,
            databases=cluster_cfg.databases, extra=cluster_cfg.extra,
        )
    raise ValueError(f"unknown cluster type: {cluster_cfg.type}")
