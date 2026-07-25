"""Orchestrate: introspect each cluster via its adapter, replace stored state."""

from app.adapters import build_introspector
from app.config import AppConfig
from app.core.labeling import apply_label_rules
from app.store.db import make_session_factory
from app.store.repo import sync_auto_labels, sync_cluster


def run_sync(cfg: AppConfig, only_cluster: str | None = None) -> dict[str, dict]:
    factory = make_session_factory(cfg.storage_url)
    results = {}
    for cluster_cfg in cfg.clusters:
        if only_cluster and cluster_cfg.name != only_cluster:
            continue
        introspector = build_introspector(cluster_cfg)
        entities, edges = introspector.introspect()
        auto_labels = apply_label_rules(entities, cfg.label_rules + cluster_cfg.label_rules)
        with factory() as session:
            results[cluster_cfg.name] = sync_cluster(session, cluster_cfg.name, entities, edges)
            sync_auto_labels(session, cluster_cfg.name, auto_labels)
    return results
