"""Task plugin that produces a configured value."""

from typing import Any, ClassVar

from ....domain import TaskContext, TaskOutput, TaskResult
from ...exceptions import InvalidPluginConfigurationError
from ..interface import Task


class ProduceValueTask(Task):
    """Produce a configured value as task output."""

    plugin_type: ClassVar[str] = "produce_value"

    @classmethod
    def validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        if "value" not in configuration:
            raise InvalidPluginConfigurationError(
                "ProduceValueTask configuration requires 'value'."
            )

        unexpected_keys = configuration.keys() - {"value"}

        if unexpected_keys:
            raise InvalidPluginConfigurationError(
                f"ProduceValueTask configuration contains unexpected fields: "
                f"{sorted(unexpected_keys)}."
            )

    def execute(self, context: TaskContext) -> TaskResult:
        value = context.configuration.get("value")

        return TaskResult(
            succeeded=True,
            output=TaskOutput(
                values={"value": value},
            ),
        )
