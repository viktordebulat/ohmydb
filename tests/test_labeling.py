import pytest

from app.core.labeling import apply_label_rules, validate_label_rules
from app.core.models import Entity, EntityKind
from app.store.db import LabelRow, make_session_factory
from app.store.queries import set_label
from app.store.repo import sync_auto_labels, sync_cluster
from sqlalchemy import select


def _entity(db, name, kind=EntityKind.TABLE, engine=""):
    return Entity(cluster="c1", database=db, name=name, kind=kind, engine=engine)


def test_validate_label_rules_rejects_unknown_match_key():
    with pytest.raises(ValueError, match="name"):
        validate_label_rules([{"match": {"name": "events"}, "label": {"key": "a", "value": "b"}}])


def test_validate_label_rules_accepts_known_keys():
    validate_label_rules([
        {"match": {"engine": "Kafka", "kind": "table", "name_pattern": "x", "database_pattern": "y"},
         "label": {"key": "a", "value": "b"}},
    ])


def test_apply_label_rules_matches_and_accumulates():
    entities = [
        _entity("app", "events_kafka", engine="Kafka"),
        _entity("raw", "users", kind=EntityKind.TABLE),
        _entity("app", "d", kind=EntityKind.DICTIONARY),
    ]
    rules = [
        {"match": {"engine": "Kafka"}, "label": {"key": "source", "value": "streaming"}},
        {"match": {"database_pattern": "^raw$"}, "label": {"key": "layer", "value": "raw"}},
        {"match": {"kind": "dictionary"}, "label": {"key": "source", "value": "dictionary"}},
    ]
    out = {(ident, key): value for ident, key, value in apply_label_rules(entities, rules)}
    assert out[(("c1", "app", "events_kafka"), "source")] == "streaming"
    assert out[(("c1", "raw", "users"), "layer")] == "raw"
    assert out[(("c1", "app", "d"), "source")] == "dictionary"


def test_apply_label_rules_last_match_wins_same_key():
    entities = [_entity("app", "t", engine="Kafka")]
    rules = [
        {"match": {"engine": "Kafka"}, "label": {"key": "source", "value": "streaming"}},
        {"match": {"name_pattern": "^t$"}, "label": {"key": "source", "value": "overridden"}},
    ]
    out = apply_label_rules(entities, rules)
    assert out == [(("c1", "app", "t"), "source", "overridden")]


def test_sync_auto_labels_skips_manual_and_replaces_stale_auto():
    factory = make_session_factory("sqlite://")
    with factory() as s:
        sync_cluster(s, "c1", [_entity("app", "t")], [])
        set_label(s, "c1", "app", "t", "owner", "team-a")  # manual

        sync_auto_labels(s, "c1", [
            (("c1", "app", "t"), "owner", "auto-owner"),  # manual already set this key -> skipped
            (("c1", "app", "t"), "layer", "raw"),
        ])
        rows = {(r.key, r.source): r.value for r in s.scalars(select(LabelRow)).all()}
        assert rows == {("owner", "manual"): "team-a", ("layer", "auto"): "raw"}

        # next sync stops matching "layer" -> stale auto row is dropped, manual untouched
        sync_auto_labels(s, "c1", [])
        rows = {(r.key, r.source): r.value for r in s.scalars(select(LabelRow)).all()}
        assert rows == {("owner", "manual"): "team-a"}


def test_manual_put_overrides_prior_auto_label():
    factory = make_session_factory("sqlite://")
    with factory() as s:
        sync_cluster(s, "c1", [_entity("app", "t")], [])
        sync_auto_labels(s, "c1", [(("c1", "app", "t"), "source", "auto-value")])
        set_label(s, "c1", "app", "t", "source", "manual-value")
        row = s.scalar(select(LabelRow).where(LabelRow.key == "source"))
        assert row.value == "manual-value" and row.source == "manual"
