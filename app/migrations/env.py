from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.store.db import Base  # noqa: E402

target_metadata = Base.metadata


def _resolve_url() -> str:
    """CLI usage (`alembic upgrade head`) resolves the URL the same way the
    app does — OHMYDB_CONFIG/config.yaml. Programmatic usage (app/store/db.py:
    run_migrations) skips this by attaching a live connection instead, see
    run_migrations_online below."""
    from app.cli import DEFAULT_CONFIG
    from app.config import load_config

    return load_config(DEFAULT_CONFIG).storage_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url") or _resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    A programmatic caller (app/store/db.py: run_migrations) attaches a live
    connection via config.attributes["connection"] — migrations then run on
    the exact same connection as the app engine, which matters for in-memory
    sqlite (a second connection to "sqlite://" is a different, empty database).
    Plain CLI usage (`alembic upgrade head`) has no such connection and
    builds its own engine from the resolved app config instead.
    """
    connectable = config.attributes.get("connection", None)

    if connectable is None:
        connectable = engine_from_config(
            {"sqlalchemy.url": _resolve_url()},
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    else:
        context.configure(connection=connectable, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
