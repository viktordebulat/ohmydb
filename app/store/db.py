"""SQLAlchemy models. SQLite now, Postgres later — same code, different URL."""

from datetime import datetime
from pathlib import Path

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

# Migration scripts ship inside the app package (app/migrations/) rather
# than under the repo-root alembic/ convention, so they're resolvable both
# in a repo checkout and from a non-editable install (Docker: the wheel only
# packages app/, not the repo root — see Dockerfile.example). alembic.ini at
# the repo root exists purely for the dev CLI (`alembic revision
# --autogenerate`, `task db:revision`); this path is what actually runs at
# app startup.
_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


class Base(DeclarativeBase):
    pass


class EntityRow(Base):
    __tablename__ = "entities"
    __table_args__ = (UniqueConstraint("cluster", "database", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cluster: Mapped[str] = mapped_column(String(255))
    database: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(32))
    engine: Mapped[str] = mapped_column(String(255), default="")
    ddl: Mapped[str] = mapped_column(Text, default="")
    columns: Mapped[list] = mapped_column(JSON, default=list)
    attrs: Mapped[dict] = mapped_column(JSON, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime)
    # Transitive upstream/downstream entity ids, precomputed at sync time
    # (see store/repo.py: sync_cluster) so reads are a lookup, not a BFS.
    upstream: Mapped[list] = mapped_column(JSON, default=list)
    downstream: Mapped[list] = mapped_column(JSON, default=list)


class EdgeRow(Base):
    __tablename__ = "edges"

    id: Mapped[int] = mapped_column(primary_key=True)
    src_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    dst_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(32))


class LabelRow(Base):
    __tablename__ = "labels"
    # Identity-keyed on purpose (no FK to entities): labels must survive an
    # entity being dropped and recreated. Orphan labels are hidden, not deleted.
    __table_args__ = (UniqueConstraint("cluster", "database", "table_name", "key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cluster: Mapped[str] = mapped_column(String(255))
    database: Mapped[str] = mapped_column(String(255))
    table_name: Mapped[str] = mapped_column(String(255))
    key: Mapped[str] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(String(1024), default="")
    # "manual" (PUT /labels) or "auto" (config label_rules, rederived every
    # sync — see store/repo.py: sync_auto_labels). Existing rows predate this
    # column and were all manual, hence the server-side default.
    source: Mapped[str] = mapped_column(String(16), default="manual", server_default="manual")


def run_migrations(engine: Engine) -> None:
    """Bring the schema at `engine` up to head via Alembic
    (app/migrations/versions/). Runs on the engine's own connection —
    required for in-memory sqlite, where a second, separately-opened
    connection is a different empty database."""
    from alembic import command
    from alembic.config import Config

    cfg = Config()
    cfg.set_main_option("script_location", str(_MIGRATIONS_DIR))
    with engine.connect() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")


def make_session_factory(url: str) -> sessionmaker[Session]:
    engine = create_engine(url)
    run_migrations(engine)
    return sessionmaker(engine, expire_on_commit=False)
