import pytest

from app.config import load_config


def _write(tmp_path, cluster_names):
    clusters = "\n".join(
        f"  - name: {n}\n    host: localhost\n" for n in cluster_names
    )
    path = tmp_path / "config.yaml"
    path.write_text(f"storage:\n  type: sqlite\n  url: sqlite:///x.sqlite\nclusters:\n{clusters}")
    return path


def test_load_config_ok(tmp_path):
    cfg = load_config(_write(tmp_path, ["prod-eu", "prod-us"]))
    assert [c.name for c in cfg.clusters] == ["prod-eu", "prod-us"]


def test_load_config_rejects_colliding_cluster_keys(tmp_path):
    with pytest.raises(ValueError, match="prod-eu.*prod_eu|prod_eu.*prod-eu"):
        load_config(_write(tmp_path, ["prod-eu", "prod_eu"]))


def test_load_config_parses_global_and_per_cluster_label_rules(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("""
storage:
  type: sqlite
  url: sqlite:///x.sqlite
label_rules:
  - match: {kind: dictionary}
    label: {key: source, value: dictionary}
clusters:
  - name: prod
    host: localhost
    label_rules:
      - match: {engine: Kafka}
        label: {key: source, value: streaming}
""")
    cfg = load_config(path)
    assert cfg.label_rules == [{"match": {"kind": "dictionary"}, "label": {"key": "source", "value": "dictionary"}}]
    assert cfg.clusters[0].label_rules == [
        {"match": {"engine": "Kafka"}, "label": {"key": "source", "value": "streaming"}}
    ]


def test_load_config_rejects_unknown_label_rule_match_key(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("""
storage:
  type: sqlite
  url: sqlite:///x.sqlite
label_rules:
  - match: {name: events}
    label: {key: a, value: b}
clusters:
  - name: prod
    host: localhost
""")
    with pytest.raises(ValueError, match="unknown match key"):
        load_config(path)
