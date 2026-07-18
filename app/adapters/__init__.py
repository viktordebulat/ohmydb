from app.adapters.base import Introspector


def build_introspector(cluster_cfg) -> Introspector:
    if cluster_cfg.type == "clickhouse":
        from app.adapters.clickhouse import ClickHouseIntrospector

        return ClickHouseIntrospector(
            cluster=cluster_cfg.name, host=cluster_cfg.host, port=cluster_cfg.port,
            username=cluster_cfg.username, password=cluster_cfg.password,
            databases=cluster_cfg.databases,
        )
    raise ValueError(f"unknown cluster type: {cluster_cfg.type}")
