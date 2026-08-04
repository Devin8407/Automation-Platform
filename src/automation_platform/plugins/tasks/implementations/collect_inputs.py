"""Task plugin that collects dependency outputs."""

from typing import Any, ClassVar

from ....domain import TaskContext, TaskOutput, TaskResult
from ...exceptions import InvalidPluginConfigurationError
from ..interface import Task


class CollectInputsTask(Task):
    """Collect dependency outputs keyed by dependency task key."""

    plugin_type: ClassVar[str] = "collect_inputs"

    @classmethod
    def validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        if configuration:
            raise InvalidPluginConfigurationError(
                f"CollectInputsTask does not accept configuration fields: {sorted(configuration)}."
            )

    def execute(self, context: TaskContext) -> TaskResult:
        values = {task_key: output.values for task_key, output in context.inputs.items()}

        return TaskResult(
            succeeded=True,
            output=TaskOutput(values=values),
        )
