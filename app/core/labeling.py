"""Config-driven label derivation: match entities by engine/kind/name against
rules from config.yaml, produce labels to store alongside manual ones."""

import re

from app.core.models import Entity, Identity


def _matches(entity: Entity, match: dict) -> bool:
    if "engine" in match and entity.engine != match["engine"]:
        return False
    if "kind" in match and entity.kind.value != match["kind"]:
        return False
    if "name_pattern" in match and not re.search(match["name_pattern"], entity.name):
        return False
    if "database_pattern" in match and not re.search(match["database_pattern"], entity.database):
        return False
    return True


def apply_label_rules(entities: list[Entity], rules: list[dict]) -> list[tuple[Identity, str, str]]:
    """All matching rules apply (labels accumulate); if two rules set the
    same key for the same entity, the later rule in `rules` wins."""
    out: dict[tuple[Identity, str], str] = {}
    for rule in rules:
        match = rule.get("match", {})
        label = rule["label"]
        for entity in entities:
            if _matches(entity, match):
                out[(entity.identity, label["key"])] = label["value"]
    return [(identity, key, value) for (identity, key), value in out.items()]
