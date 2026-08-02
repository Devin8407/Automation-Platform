import pytest

from automation_platform.domain import TaskContext, TaskOutput
from automation_platform.plugins.exceptions import InvalidPluginConfigurationError
from automation_platform.plugins.tasks.implementations.collect_inputs import (
    CollectInputsTask,
)


def test_validate_configuration_accepts_empty_configuration():
    CollectInputsTask.validate_configuration({})


def test_validate_configuration_rejects_fields():
    with pytest.raises(
        InvalidPluginConfigurationError,
        match="does not accept configuration fields",
    ):
        CollectInputsTask.validate_configuration(
            {"unexpected": "value"},
        )


def test_execute_collects_no_inputs():
    task = CollectInputsTask()

    context = TaskContext(
        configuration={},
        inputs={},
    )

    result = task.execute(context)

    assert result.succeeded is True
    assert result.output == TaskOutput(values={})
    assert result.message is None


def test_execute_collects_single_input():
    task = CollectInputsTask()

    context = TaskContext(
        configuration={},
        inputs={
            "producer": TaskOutput(
                values={"value": "hello"},
            ),
        },
    )

    result = task.execute(context)

    assert result.succeeded is True
    assert result.output == TaskOutput(
        values={
            "producer": {"value": "hello"},
        }
    )


def test_execute_collects_multiple_inputs_by_task_key():
    task = CollectInputsTask()

    context = TaskContext(
        configuration={},
        inputs={
            "left": TaskOutput(
                values={"value": "A"},
            ),
            "right": TaskOutput(
                values={"value": "B"},
            ),
        },
    )

    result = task.execute(context)

    assert result.succeeded is True
    assert result.output == TaskOutput(
        values={
            "left": {"value": "A"},
            "right": {"value": "B"},
        }
    )
