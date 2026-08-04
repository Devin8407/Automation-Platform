"""Task plugin that always reports an expected failure."""

from typing import Any, ClassVar

from ....domain import TaskContext, TaskOutput, TaskResult
from ...exceptions import InvalidPluginConfigurationError
from ..interface import Task


class FailTask(Task):
    """Report a configured expected task failure."""

    plugin_type: ClassVar[str] = "fail"

    @classmethod
    def validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        unexpected_keys = configuration.keys() - {"message"}

        if unexpected_keys:
            raise InvalidPluginConfigurationError(
                f"FailTask configuration contains unexpected fields: {sorted(unexpected_keys)}."
            )

        if "message" in configuration and not isinstance(
            configuration["message"],
            str,
        ):
            raise InvalidPluginConfigurationError(
                "FailTask configuration field 'message' must be a string."
            )

    def execute(self, context: TaskContext) -> TaskResult:
        message = context.configuration.get(
            "message",
            "Task configured to fail.",
        )

        return TaskResult(
            succeeded=False,
            output=TaskOutput(),
            message=message,
        )
