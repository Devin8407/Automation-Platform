from sqlalchemy import Engine

from automation_platform.infrastructure.database import create_sqlalchemy_engine


def test_create_sqlalchemy_engine_returns_engine() -> None:
    engine = create_sqlalchemy_engine(
        "sqlite:///:memory:",
        echo_sql=False,
    )

    assert isinstance(engine, Engine)

    engine.dispose()


def test_engine_can_connect() -> None:
    engine = create_sqlalchemy_engine(
        "sqlite:///:memory:",
        echo_sql=False,
    )

    with engine.connect() as connection:
        assert connection is not None

    engine.dispose()
