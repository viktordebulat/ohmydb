"""ClickHouse introspector. All ClickHouse-specific knowledge lives here."""

import re

import clickhouse_connect

from app.core.models import Column, Edge, EdgeKind, Entity, EntityKind

SYSTEM_DBS = ("system", "information_schema", "INFORMATION_SCHEMA")

_KIND_BY_ENGINE = {
    "MaterializedView": EntityKind.MAT_VIEW,
    "View": EntityKind.VIEW,
    "Dictionary": EntityKind.DICTIONARY,
}


def _extract_to_target(ddl: str, default_db: str) -> tuple[str, str] | None:
    """Target of `CREATE MATERIALIZED VIEW ... TO [db.]table AS SELECT ...`."""
    head = re.split(r"\bAS\s+SELECT\b", ddl, maxsplit=1, flags=re.IGNORECASE)[0]
    m = re.search(r"\bTO\s+(?:`?(\w+)`?\.)?`?(\w+)`?", head)
    if not m:
        return None
    return (m.group(1) or default_db, m.group(2))


def _extract_sources(ddl: str) -> list[tuple[str, str]]:
    """Qualified `FROM/JOIN db.table` references in a view's SELECT body."""
    return re.findall(r"\b(?:FROM|JOIN)\s+`?(\w+)`?\.`?(\w+)`?", ddl, flags=re.IGNORECASE)


def _parse_dict_source(ddl: str, default_db: str) -> tuple[str, str] | None:
    """ClickHouse-backed source from dictionary DDL:
    SOURCE(CLICKHOUSE(DB 'app' TABLE 'users')). system.dictionaries.source is
    empty until the dictionary is first loaded, so DDL is the reliable place."""
    m = re.search(r"SOURCE\(CLICKHOUSE\(([^)]*)\)", ddl, flags=re.IGNORECASE)
    if not m:
        return None
    body = m.group(1)
    table = re.search(r"\bTABLE\s+'([^']+)'", body, flags=re.IGNORECASE)
    if not table:
        return None
    db = re.search(r"\b(?:DB|DATABASE)\s+'([^']+)'", body, flags=re.IGNORECASE)
    return (db.group(1) if db else default_db, table.group(1))


class ClickHouseIntrospector:
    def __init__(self, cluster: str, host: str, port: int = 8123,
                 username: str = "default", password: str = "",
                 databases: list[str] | None = None,
                 extra: dict | None = None):
        self.cluster = cluster
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.databases = databases or []
        self.extra = extra or {}

    def _client(self):
        return clickhouse_connect.get_client(
            host=self.host, port=self.port,
            username=self.username, password=self.password,
            **self.extra,
        )

    def introspect(self) -> tuple[list[Entity], list[Edge]]:
        client = self._client()
        db_filter = "AND database IN %(dbs)s" if self.databases else ""
        params = {"dbs": self.databases} if self.databases else {}

        columns: dict[tuple[str, str], list[Column]] = {}
        for db, table, name, typ, comment in client.query(
            f"""SELECT database, table, name, type, comment FROM system.columns
                WHERE database NOT IN {SYSTEM_DBS} {db_filter}
                ORDER BY database, table, position""",
            parameters=params,
        ).result_rows:
            columns.setdefault((db, table), []).append(Column(name, typ, comment))

        entities: list[Entity] = []
        edge_set: set[tuple] = set()

        def add_edge(src: tuple[str, str], dst: tuple[str, str], kind: EdgeKind):
            edge_set.add(((self.cluster, *src), (self.cluster, *dst), kind))

        for db, name, engine, ddl, dep_dbs, dep_tables in client.query(
            f"""SELECT database, name, engine, create_table_query,
                       dependencies_database, dependencies_table
                FROM system.tables
                WHERE database NOT IN {SYSTEM_DBS} AND NOT startsWith(name, '.inner') {db_filter}""",
            parameters=params,
        ).result_rows:
            kind = _KIND_BY_ENGINE.get(engine, EntityKind.TABLE)
            attrs = {}
            if kind == EntityKind.MAT_VIEW:
                head = re.split(r"\bAS\s+SELECT\b", ddl, maxsplit=1, flags=re.IGNORECASE)[0]
                if re.search(r"\bREFRESH\b", head):
                    attrs["refreshable"] = True
                target = _extract_to_target(ddl, db)
                if target:
                    add_edge((db, name), target, EdgeKind.WRITES_TO)
            if kind == EntityKind.DICTIONARY:
                src = _parse_dict_source(ddl, db)
                if src:
                    add_edge((db, name), src, EdgeKind.DICT_SOURCE)
            if kind in (EntityKind.MAT_VIEW, EntityKind.VIEW):
                # Regex fallback: dependencies arrays don't cover plain views
                # and refreshable MVs (no insert trigger).
                for src_db, src_table in _extract_sources(ddl):
                    add_edge((db, name), (src_db, src_table), EdgeKind.READS_FROM)
            # Reverse deps: this table's dependents are views reading from it.
            for dep_db, dep_table in zip(dep_dbs, dep_tables):
                add_edge((dep_db, dep_table), (db, name), EdgeKind.READS_FROM)
            entities.append(Entity(
                cluster=self.cluster, database=db, name=name, kind=kind,
                engine=engine, ddl=ddl, columns=columns.get((db, name), []),
                attrs=attrs,
            ))

        edges = [Edge(src=s, dst=d, kind=k) for s, d, k in sorted(edge_set)]
        return entities, edges
