from automation_platform.persistence.database.sqlalchemy_uow import (
    SQLAlchemyUnitOfWork,
    SQLAlchemyUnitOfWorkFactory,
)


def test_factory_creates_unit_of_work(uow_factory: SQLAlchemyUnitOfWorkFactory) -> None:
    uow = uow_factory()

    assert isinstance(uow, SQLAlchemyUnitOfWork)


def test_uow_constructs_repositories(uow) -> None:
    assert uow.chronological_triggers is not None
    assert uow.workflow_definitions is not None
    assert uow.workflow_executions is not None


def test_uow_context_manager(uow_factory: SQLAlchemyUnitOfWorkFactory) -> None:
    with uow_factory() as uow:
        assert isinstance(uow, SQLAlchemyUnitOfWork)


def test_commit_does_not_raise(uow) -> None:
    uow.commit()


def test_rollback_does_not_raise(uow) -> None:
    uow.rollback()
