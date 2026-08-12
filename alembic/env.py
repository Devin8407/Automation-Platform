from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from automation_platform.config import load_settings
from automation_platform.infrastructure import Base
from automation_platform.persistence import (
    ChronologicalTriggerStateModel,  # noqa: F401, F403
    TaskDefinitionDependencyModel,  # noqa: F401, F403
    TaskDefinitionModel,  # noqa: F401, F403
    TaskExecutionModel,  # noqa: F401, F403
    TriggerDefinitionModel,  # noqa: F401, F403
    WorkflowDefinitionModel,  # noqa: F401, F403
    WorkflowExecutionModel,  # noqa: F401, F403
)

# Alembic Config object.
config = context.config

# Configure Alembic's logging from alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Importing the ORM models above registers them with Base.metadata.
target_metadata = Base.metadata

# Load the application's database configuration.
settings = load_settings()

# Use the application's configured database URL instead of
# storing credentials in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""

    url = settings.database_url

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""

    configuration = config.get_section(
        config.config_ini_section,
        {},
    )

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
