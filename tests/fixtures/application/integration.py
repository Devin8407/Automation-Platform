"""Fixtures for application integration tests."""

from typing import Any

import pytest

from automation_platform.application.task_processing.services import (
    TaskProcessingService,
)
from automation_platform.application.workflow_definitions.services import (
    WorkflowDefinitionService,
)
from automation_platform.application.workflow_start.services import (
    WorkflowStartService,
)
from automation_platform.domain import TaskContext, TaskOutput, TaskResult
from automation_platform.plugins import Task, TaskRegistry, TriggerRegistry

# ==================================================================================================
# Test Task Plugin Base
# ==================================================================================================


class IntegrationTask(Task):
    """Base class for integration-test task plugins."""

    @classmethod
    def validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        """Accept any configuration for integration-test tasks."""


# ==================================================================================================
# Test Task Plugins
# ==================================================================================================


class SuccessfulTask(IntegrationTask):
    """Task plugin that always completes successfully."""

    plugin_type = "successful"

    def execute(self, context: TaskContext) -> TaskResult:
        return TaskResult(
            succeeded=True,
            output=TaskOutput(
                values={
                    "result": "success",
                }
            ),
        )


class InputTask(IntegrationTask):
    """Task plugin that returns its received parent inputs."""

    plugin_type = "input"

    def execute(self, context: TaskContext) -> TaskResult:
        return TaskResult(
            succeeded=True,
            output=TaskOutput(
                values={"inputs": {key: output.values for key, output in context.inputs.items()}}
            ),
        )


class FailingTask(IntegrationTask):
    """Task plugin that always reports failure."""

    plugin_type = "failing"

    def execute(self, context: TaskContext) -> TaskResult:
        return TaskResult(
            succeeded=False,
            output=TaskOutput(),
            message="Test task failure.",
        )


class FailOnceTask(IntegrationTask):
    """Task plugin that fails once and then succeeds."""

    plugin_type = "fail_once"

    attempts = 0

    def execute(self, context: TaskContext) -> TaskResult:
        type(self).attempts += 1

        if type(self).attempts == 1:
            return TaskResult(
                succeeded=False,
                output=TaskOutput(),
                message="First attempt failed.",
            )

        return TaskResult(
            succeeded=True,
            output=TaskOutput(
                values={
                    "result": "success",
                }
            ),
        )


# ==================================================================================================
# Test Registries
# ==================================================================================================


class IntegrationTaskRegistry(TaskRegistry):
    """Task registry containing controlled integration-test plugins."""

    def __init__(self) -> None:
        """Register integration-test task plugins without discovery."""

        self._implementations = {}

        self._register(SuccessfulTask)
        self._register(InputTask)
        self._register(FailingTask)
        self._register(FailOnceTask)


# ==================================================================================================
# Registries
# ==================================================================================================


@pytest.fixture
def task_registry() -> TaskRegistry:
    """Return a task registry containing integration-test plugins."""

    FailOnceTask.attempts = 0

    return IntegrationTaskRegistry()


@pytest.fixture
def trigger_registry() -> TriggerRegistry:
    """Return an empty trigger registry."""

    return TriggerRegistry()


# ==================================================================================================
# Application Services
# ==================================================================================================


@pytest.fixture
def workflow_definition_service(
    uow_factory,
    task_registry,
    trigger_registry,
) -> WorkflowDefinitionService:
    """Return a workflow definition service backed by real persistence."""

    return WorkflowDefinitionService(
        uow_factory=uow_factory,
        task_registry=task_registry,
        trigger_registry=trigger_registry,
    )


@pytest.fixture
def workflow_start_service(
    uow_factory,
    queue,
) -> WorkflowStartService:
    """Return a workflow start service backed by real persistence."""

    return WorkflowStartService(
        uow_factory=uow_factory,
        queue=queue,
    )


@pytest.fixture
def task_processing_service(
    uow_factory,
    task_registry,
) -> TaskProcessingService:
    """Return a task processing service backed by real persistence."""

    return TaskProcessingService(
        uow_factory=uow_factory,
        task_registry=task_registry,
    )
