from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from .base import Base, _scan_models

fileConfig(context.config.config_file_name)


def run_migrations():
    path = context.config.get_section_option("app:main", "tetkit.db_models_path")
    _scan_models(path)
    _run_migrations_online(context, Base.metadata)


def _run_migrations_online(context, metadata):
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    url = context.config.get_section_option("app:main", "sqlalchemy.url")
    engine = create_engine(url, poolclass=pool.NullPool)

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=metadata,
        )

        with context.begin_transaction():
            context.run_migrations()
