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
