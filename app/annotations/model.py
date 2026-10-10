"""Annotation repo format (v1): pydantic models + tree loader.

Layout (see docs/ANNOTATIONS.md):
    <root>/_global.yaml          optional: version, query_hints, ignore
    <root>/<db>/_database.yaml   optional: description, query_hints
    <root>/<db>/<table>.yaml     one per table/view/mat_view/dictionary

Field names follow Apache Ossie/OSI where they overlap, so an exporter stays
cheap later. Models forbid unknown keys: a typo'd key must fail, not be
silently dropped (same lesson as label_rules in docs/LEARNINGS.md).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

SUMMARY_MAX = 200


class FatalTreeError(Exception):
    """The whole tree is unusable (missing root, unsupported version) —
    callers keep the last good catalog copy and write nothing."""


class _Model(BaseModel):
    # coerce_numbers_to_str: YAML `1: active` enum keys load as ints.
    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True)


class ColumnAnnotation(_Model):
    description: str = ""
    values: dict[str, str] | list[str] = []


class Relationship(_Model):
    to: str
    from_columns: list[str]
    to_columns: list[str]
    cardinality: Literal["", "many_to_one", "one_to_many", "one_to_one", "many_to_many"] = ""
    description: str = ""

    @field_validator("to")
    @classmethod
    def _to_is_db_table(cls, v: str) -> str:
        if v.count(".") != 1 or not all(v.split(".")):
            raise ValueError("must be db.table")
        return v

    @model_validator(mode="after")
    def _same_length(self) -> "Relationship":
        if len(self.from_columns) != len(self.to_columns):
            raise ValueError("from_columns and to_columns must have the same length")
        return self


class Example(_Model):
    question: str
    sql: str


class TableAnnotation(_Model):
    description: str = ""  # first line = summary (listings, search)
    grain: str = ""
    status: Literal["", "active", "deprecated"] = ""
    use_instead: str = ""
    owner: str = ""
    query_hints: list[str] = []
    columns: dict[str, ColumnAnnotation] = {}
    relationships: list[Relationship] = []
    examples: list[Example] = []


class DatabaseAnnotation(_Model):
    description: str = ""
    query_hints: list[str] = []


class GlobalAnnotation(_Model):
    version: Literal[1] = 1
    query_hints: list[str] = []
    ignore: list[str] = []  # regexes (re.search on "db.table"), excluded from drift stubs

    @field_validator("ignore")
    @classmethod
    def _valid_regexes(cls, v: list[str]) -> list[str]:
        for pattern in v:
            re.compile(pattern)
        return v


Entry = tuple[dict, str]  # (normalized doc, path relative to the tree root)


@dataclass
class Tree:
    global_: Entry | None = None
    databases: dict[str, Entry] = field(default_factory=dict)
    # Kept even when the doc normalizes to {} (an unfilled stub): such a file
    # exists (no drift stub needed) but the table reads as unannotated.
    tables: dict[tuple[str, str], Entry] = field(default_factory=dict)


def _prune(value):
    if isinstance(value, dict):
        pruned = {k: _prune(v) for k, v in value.items()}
        return {k: v for k, v in pruned.items() if v not in ("", [], {}, None)}
    if isinstance(value, list):
        pruned = [_prune(v) for v in value]
        return [v for v in pruned if v not in ("", [], {}, None)]
    return value


def normalize(model: BaseModel) -> dict:
    """Dump, then recursively drop empty strings/lists/dicts."""
    return _prune(model.model_dump())


def summary_of(doc: dict) -> str:
    """First non-empty line of `description`, capped at SUMMARY_MAX chars."""
    for line in doc.get("description", "").splitlines():
        if line.strip():
            return line.strip()[:SUMMARY_MAX]
    return ""


_yaml = YAML(typ="safe", pure=True)


def _read(path: Path) -> dict:
    raw = _yaml.load(path.read_text())
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("expected a mapping at the top level")
    return raw


def _parse(path: Path, rel: str, model: type[BaseModel], errors: list[str]) -> dict | None:
    try:
        return normalize(model.model_validate(_read(path)))
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"]) or "(root)"
            errors.append(f"{rel}: {loc}: {err['msg']}")
    except (YAMLError, ValueError) as e:
        errors.append(f"{rel}: {e}")
    return None


def load_tree(root: Path, exclude: frozenset[str] = frozenset()) -> tuple[Tree, list[str]]:
    """Parse one annotation root. Per-file problems are collected in `errors`
    (that file is skipped); a missing root or unsupported version raises
    FatalTreeError. Root-level files other than _global.yaml are ignored
    (README, CODEOWNERS); dot-dirs (.git, .gitlab) too. `exclude`: top-level
    dir names that aren't databases (they hold a per-cluster override root
    nested inside this one)."""
    if not root.is_dir():
        raise FatalTreeError(f"annotation root not found: {root}")
    tree, errors = Tree(), []

    global_path = root / "_global.yaml"
    if global_path.is_file():
        try:
            version = _read(global_path).get("version", 1)
        except (YAMLError, ValueError):
            version = 1  # reported by _parse below
        if version != 1:
            raise FatalTreeError(f"_global.yaml: unsupported version {version!r} (this ohmydb reads 1)")
        doc = _parse(global_path, "_global.yaml", GlobalAnnotation, errors)
        if doc is not None:
            doc.pop("version", None)
            tree.global_ = (doc, "_global.yaml")

    db_dirs = (p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name not in exclude)
    for db_dir in sorted(db_dirs):
        db = db_dir.name
        for f in sorted(db_dir.iterdir()):
            rel = f.relative_to(root).as_posix()
            if f.name.startswith("."):
                continue
            if f.is_dir():
                errors.append(f"{rel}: nested directories are not allowed")
            elif f.suffix == ".yml":
                errors.append(f"{rel}: use the .yaml extension")
            elif f.suffix != ".yaml":
                continue
            elif f.name == "_database.yaml":
                doc = _parse(f, rel, DatabaseAnnotation, errors)
                if doc is not None:
                    tree.databases[db] = (doc, rel)
            elif f.name.startswith("_"):
                errors.append(f"{rel}: unknown special file (only _database.yaml is allowed here)")
            else:
                doc = _parse(f, rel, TableAnnotation, errors)
                if doc is not None:
                    tree.tables[(db, f.stem)] = (doc, rel)
    return tree, errors
