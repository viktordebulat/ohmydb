"""Annotation repo format (v1): pydantic models + tree loader.

Layout (see docs/ANNOTATIONS.md):
    <root>/_global.yaml          optional: version, query_hints, ignore
    <root>/<db>/_database.yaml   optional: description, query_hints
    <root>/<db>/<table>.yaml     one per table/view/mat_view/dictionary

Field names follow Apache Ossie/OSI where they overlap, so an exporter stays
cheap later. Models forbid unknown keys: a typo'd key must fail, not be
silently dropped (same lesson as label_rules in docs/LEARNINGS.md).
"""

import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError
from ruamel.yaml.scalarstring import LiteralScalarString

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


def format_errors(e: ValidationError) -> list[str]:
    """`loc: msg` per error, loc dotted (`columns.ts.description`)."""
    return [f"{'.'.join(str(p) for p in err['loc']) or '(root)'}: {err['msg']}" for err in e.errors()]


def _parse(path: Path, rel: str, model: type[BaseModel], errors: list[str]) -> dict | None:
    try:
        return normalize(model.model_validate(_read(path)))
    except ValidationError as e:
        errors += [f"{rel}: {msg}" for msg in format_errors(e)]
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


# --- write side (M24): round-trip edits keep comments, order and quoting ---

def _rt_yaml() -> YAML:
    y = YAML(typ="rt", pure=True)
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)  # house style, see docs/ANNOTATIONS.md
    return y


def load_rt(text: str) -> CommentedMap:
    doc = _rt_yaml().load(text)
    if doc is None:
        return CommentedMap()
    if not isinstance(doc, CommentedMap):
        raise ValueError("expected a mapping at the top level")
    return doc


def dump_rt(doc: CommentedMap) -> str:
    buf = io.StringIO()
    _rt_yaml().dump(doc, buf)
    return buf.getvalue()


def _to_rt(value):
    """Plain JSON value -> ruamel nodes; multi-line strings become `|` blocks."""
    if isinstance(value, dict):
        return CommentedMap((k, _to_rt(v)) for k, v in value.items())
    if isinstance(value, list):
        return CommentedSeq(_to_rt(v) for v in value)
    if isinstance(value, str) and "\n" in value:
        return LiteralScalarString(value)
    return value


def merge_patch(target, patch):
    """RFC 7386 JSON merge patch applied in place to a ruamel round-trip map:
    nested dicts merge, anything else (lists included) replaces, null deletes.
    Untouched keys keep their comments and formatting."""
    if not isinstance(patch, dict):
        return _to_rt(patch)
    if not isinstance(target, dict):
        target = CommentedMap()
    for k, v in patch.items():
        if v is None:
            target.pop(k, None)
        else:
            target[k] = merge_patch(target.get(k), v)
    return target


def _key(name: str) -> str:
    # JSON strings are valid YAML double-quoted scalars.
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", name) else json.dumps(name)


def render_stub(database: str, name: str, columns: list[str]) -> str:
    """Empty table file for a drift MR. Empty values are dropped on load, so
    an unfilled stub reads as unannotated."""
    lines = [
        f"# {database}.{name}: stub added by ohmydb (schema drift). Fill in what you",
        "# know, leave the rest empty. Format: docs/ANNOTATIONS.md in the ohmydb repo.",
        'description: ""',
        'grain: ""',
    ]
    if columns:
        lines.append("columns:")
        lines += [f'  {_key(c)}: {{description: ""}}' for c in columns]
    return "\n".join(lines) + "\n"
