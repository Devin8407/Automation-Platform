from ..config import Settings
from .database import create_session_factory, create_sqlalchemy_engine
from .infrastructure import Infrastructure

# ==================================================================================================
# Public API
# ==================================================================================================


def build_infrastructure(settings: Settings) -> Infrastructure:
    engine = create_sqlalchemy_engine(settings.database_url, settings.echo_sql)

    session_factory = create_session_factory(engine)

    return Infrastructure(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
    )
