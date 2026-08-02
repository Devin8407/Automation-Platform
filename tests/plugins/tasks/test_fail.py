import pytest

from automation_platform.domain import TaskContext, TaskOutput
from automation_platform.plugins.exceptions import InvalidPluginConfigurationError
from automation_platform.plugins.tasks.implementations.fail import FailTask


def test_validate_configuration_accepts_empty_configuration():
    FailTask.validate_configuration({})


def test_validate_configuration_accepts_message():
    FailTask.validate_configuration(
        {"message": "Expected failure"},
    )


def test_validate_configuration_rejects_non_string_message():
    with pytest.raises(
        InvalidPluginConfigurationError,
        match="'message' must be a string",
    ):
        FailTask.validate_configuration(
            {"message": 123},
        )


def test_validate_configuration_rejects_unexpected_fields():
    with pytest.raises(
        InvalidPluginConfigurationError,
        match="unexpected fields",
    ):
        FailTask.validate_configuration(
            {"other": "value"},
        )


def test_execute_returns_failure():
    task = FailTask()

    context = TaskContext(
        configuration={},
        inputs={},
    )

    result = task.execute(context)

    assert result.succeeded is False
    assert result.output == TaskOutput()
    assert result.message == "Task configured to fail."


def test_execute_returns_configured_failure_message():
    task = FailTask()

    context = TaskContext(
        configuration={"message": "Something went wrong"},
        inputs={},
    )

    result = task.execute(context)

    assert result.succeeded is False
    assert result.output == TaskOutput()
    assert result.message == "Something went wrong"
