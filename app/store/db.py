"""SQLAlchemy models. SQLite now, Postgres later — same code, different URL."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


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


def make_session_factory(url: str) -> sessionmaker[Session]:
    # No migration framework (no Alembic): create_all only creates missing
    # *tables*, it won't add columns to an existing one. Upgrade path for a
    # schema change like this is "drop and resync the catalog" (task clean +
    # resync) — see docs/LEARNINGS.md.
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)
