"""Fixtures for task processing application service tests."""

from collections.abc import Callable

import pytest

from automation_platform.domain import TaskOutput, TaskResult
from automation_platform.persistence import StartTaskExecutionResult


@pytest.fixture
def parent_outputs() -> dict[str, TaskOutput]:
    """Return example parent task outputs."""

    return {
        "parent_a": TaskOutput(
            values={
                "value": 10,
            }
        ),
        "parent_b": TaskOutput(
            values={
                "value": 20,
            }
        ),
    }


@pytest.fixture
def start_task_result_factory(
    parent_outputs: dict[str, TaskOutput],
) -> Callable[..., StartTaskExecutionResult]:
    """Return a factory for task start results."""

    def factory(
        *,
        plugin_type: str = "test_task",
        configuration=None,
        inputs=None,
    ) -> StartTaskExecutionResult:
        return StartTaskExecutionResult(
            plugin_type=plugin_type,
            configuration=configuration or {"option": "value"},
            parent_outputs=inputs if inputs is not None else parent_outputs,
        )

    return factory


@pytest.fixture
def successful_task_result_factory() -> Callable[..., TaskResult]:
    """Return a factory for successful plugin task results."""

    def factory(
        *,
        output: TaskOutput | None = None,
        message: str | None = None,
    ) -> TaskResult:
        return TaskResult(
            succeeded=True,
            output=output or TaskOutput(values={"result": "success"}),
            message=message,
        )

    return factory


@pytest.fixture
def failed_task_result_factory() -> Callable[..., TaskResult]:
    """Return a factory for failed plugin task results."""

    def factory(
        *,
        output: TaskOutput | None = None,
        message: str | None = "Task failed.",
    ) -> TaskResult:
        return TaskResult(
            succeeded=False,
            output=output or TaskOutput(),
            message=message,
        )

    return factory
