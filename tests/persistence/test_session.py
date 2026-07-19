from sqlalchemy.orm import Session, sessionmaker

from automation_platform.persistence.database import create_session_factory


def test_create_session_factory_returns_sessionmaker(engine) -> None:
    session_factory = create_session_factory(engine)

    assert isinstance(session_factory, sessionmaker)


def test_session_factory_creates_session(session_factory) -> None:
    session = session_factory()

    assert isinstance(session, Session)

    session.close()
