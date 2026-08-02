import pytest

from automation_platform.domain import TaskContext, TaskOutput
from automation_platform.plugins.exceptions import InvalidPluginConfigurationError
from automation_platform.plugins.tasks.implementations.produce_value import (
    ProduceValueTask,
)


def test_validate_configuration_accepts_value():
    ProduceValueTask.validate_configuration(
        {"value": "hello"},
    )


def test_validate_configuration_accepts_none_value():
    ProduceValueTask.validate_configuration(
        {"value": None},
    )


def test_validate_configuration_rejects_missing_value():
    with pytest.raises(
        InvalidPluginConfigurationError,
        match="requires 'value'",
    ):
        ProduceValueTask.validate_configuration({})


def test_validate_configuration_rejects_unexpected_fields():
    with pytest.raises(
        InvalidPluginConfigurationError,
        match="unexpected fields",
    ):
        ProduceValueTask.validate_configuration(
            {
                "value": "hello",
                "other": 123,
            }
        )


def test_execute_returns_configured_value():
    task = ProduceValueTask()

    context = TaskContext(
        configuration={"value": "hello"},
        inputs={},
    )

    result = task.execute(context)

    assert result.succeeded is True
    assert result.output == TaskOutput(
        values={"value": "hello"},
    )
    assert result.message is None


def test_execute_preserves_complex_value():
    task = ProduceValueTask()

    value = {
        "name": "test",
        "items": [1, 2, 3],
        "enabled": True,
    }

    context = TaskContext(
        configuration={"value": value},
        inputs={},
    )

    result = task.execute(context)

    assert result.succeeded is True
    assert result.output == TaskOutput(
        values={"value": value},
    )
