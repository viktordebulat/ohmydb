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


def test_load_config_auth_token_from_env_only(tmp_path, monkeypatch):
    path = _write(tmp_path, ["prod"])

    monkeypatch.delenv("OHMYDB_AUTH_TOKEN", raising=False)
    assert load_config(path).auth_token is None

    monkeypatch.setenv("OHMYDB_AUTH_TOKEN", "s3cr3t")
    assert load_config(path).auth_token == "s3cr3t"

    monkeypatch.setenv("OHMYDB_AUTH_TOKEN", "")  # empty env var == unset, not an empty-string token
    assert load_config(path).auth_token is None


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


def _write_annotations(tmp_path, block):
    path = tmp_path / "config.yaml"
    path.write_text(
        "storage:\n  type: sqlite\n  url: sqlite:///x.sqlite\n"
        "clusters:\n  - name: prod\n    host: localhost\n"
        f"annotations:\n{block}"
    )
    return path


def test_annotations_default_off(tmp_path):
    assert load_config(_write(tmp_path, ["prod"])).annotations.enabled is False


def test_annotations_token_from_env_only(tmp_path, monkeypatch):
    path = _write_annotations(tmp_path, "  enabled: true\n  repo: https://git.example.com/a.git\n")
    monkeypatch.setenv("OHMYDB_ANNOTATIONS_TOKEN", "tok")
    a = load_config(path).annotations
    assert a.token == "tok" and "tok" not in repr(a)
    monkeypatch.setenv("OHMYDB_ANNOTATIONS_TOKEN", "")
    assert load_config(path).annotations.token is None


@pytest.mark.parametrize("block, err", [
    ("  enabled: true\n", "repo is empty"),
    ("  repo: https://u:p@git.example.com/a.git\n", "OHMYDB_ANNOTATIONS_TOKEN"),
    ("  repo: ssh://git.example.com/a.git\n", "unsupported scheme"),
    ("  repo: some/dir\n  proposals: true\n", "git remote"),
    ("  repo: some/dir\n  cluster_paths: {nope: x}\n", "unknown cluster"),
    ("  repo: some/dir\n  pull_interval: -1\n", ">= 0"),
    ("  repo: some/dir\n  token: x\n", "OHMYDB_ANNOTATIONS_TOKEN"),
    ("  repo: some/dir\n  author: ohmydb\n", "Name <email>"),
])
def test_annotations_config_rejects(tmp_path, block, err):
    with pytest.raises(ValueError, match=err):
        load_config(_write_annotations(tmp_path, block))
