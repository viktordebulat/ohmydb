from app.adapters import build_introspector, cluster_env_key
from app.config import ClusterConfig


def _cluster(name="prod-eu", username="cfg_user", password="cfg_pass"):
    return ClusterConfig(name=name, host="localhost", username=username, password=password)


def test_cluster_env_key_sanitizes():
    assert cluster_env_key("prod-eu") == "PROD_EU"
    assert cluster_env_key("Prod EU 1") == "PROD_EU_1"


def test_config_used_when_no_env(monkeypatch):
    monkeypatch.delenv("CLICKHOUSE_USER", raising=False)
    monkeypatch.delenv("CLICKHOUSE_PASSWORD", raising=False)
    intro = build_introspector(_cluster())
    assert intro.username == "cfg_user" and intro.password == "cfg_pass"


def test_global_env_overrides_config(monkeypatch):
    monkeypatch.setenv("CLICKHOUSE_USER", "global_user")
    monkeypatch.setenv("CLICKHOUSE_PASSWORD", "global_pass")
    intro = build_introspector(_cluster())
    assert intro.username == "global_user" and intro.password == "global_pass"


def test_per_cluster_env_overrides_global(monkeypatch):
    monkeypatch.setenv("CLICKHOUSE_USER", "global_user")
    monkeypatch.setenv("CLICKHOUSE_PASSWORD", "global_pass")
    monkeypatch.setenv("CLICKHOUSE_USER__PROD_EU", "eu_user")
    monkeypatch.setenv("CLICKHOUSE_PASSWORD__PROD_EU", "eu_pass")
    intro = build_introspector(_cluster(name="prod-eu"))
    assert intro.username == "eu_user" and intro.password == "eu_pass"

    # A differently-named cluster is unaffected by the PROD_EU-keyed env.
    other = build_introspector(_cluster(name="prod-us"))
    assert other.username == "global_user" and other.password == "global_pass"
