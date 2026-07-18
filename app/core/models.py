"""Database-agnostic core model: entities and typed dependency edges."""

from dataclasses import dataclass, field
from enum import StrEnum

# (cluster, database, name) — stable identity of an entity across syncs.
Identity = tuple[str, str, str]


class EntityKind(StrEnum):
    TABLE = "table"
    VIEW = "view"
    MAT_VIEW = "mat_view"
    DICTIONARY = "dictionary"
    # Referenced by an edge but not found during introspection (e.g. dropped
    # table still referenced, or table outside the introspected databases).
    EXTERNAL = "external"


class EdgeKind(StrEnum):
    READS_FROM = "reads_from"
    WRITES_TO = "writes_to"
    DICT_SOURCE = "dict_source"


@dataclass
class Column:
    name: str
    type: str
    comment: str = ""


@dataclass
class Entity:
    cluster: str
    database: str
    name: str
    kind: EntityKind
    engine: str = ""
    ddl: str = ""
    columns: list[Column] = field(default_factory=list)
    attrs: dict = field(default_factory=dict)

    @property
    def identity(self) -> Identity:
        return (self.cluster, self.database, self.name)


@dataclass
class Edge:
    src: Identity
    dst: Identity
    kind: EdgeKind
