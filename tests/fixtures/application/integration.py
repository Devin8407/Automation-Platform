"""Fixtures for application integration tests."""

from datetime import datetime
from typing import Any

import pytest

from automation_platform.application import (
    ChronologicalTriggerService,
    TaskProcessingService,
    TriggerInitializationService,
    WorkflowDefinitionService,
    WorkflowStartService,
)
from automation_platform.domain import TaskContext, TaskOutput, TaskResult
from automation_platform.plugins import Task, TaskRegistry, TriggerRegistry
from automation_platform.plugins.triggers import ChronologicalTrigger
from automation_platform.plugins.triggers.implementations.interval import (
    IntervalTrigger,
)

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


class RecordingTask(IntegrationTask):
    """Task plugin that records how many times it executes."""

    plugin_type = "recording"

    executions = 0

    def execute(self, context: TaskContext) -> TaskResult:
        type(self).executions += 1

        return TaskResult(
            succeeded=True,
            output=TaskOutput(
                values={
                    "executed": True,
                }
            ),
        )


@pytest.fixture
def recording_task_type():
    """Return the recording task plugin type."""

    RecordingTask.executions = 0

    return RecordingTask


# ==================================================================================================
# Test Trigger Plugins
# ==================================================================================================


class OneShotTrigger(ChronologicalTrigger):
    """Chronological trigger with exactly one scheduled occurrence."""

    plugin_type = "one_shot"

    @classmethod
    def validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        """Accept a single ISO-formatted occurrence."""

        occurrence = configuration.get("occurrence")

        if not isinstance(occurrence, str):
            raise ValueError("occurrence must be an ISO-formatted datetime string.")

        if set(configuration) != {"occurrence"}:
            raise ValueError("One-shot trigger configuration must contain only occurrence.")

        datetime.fromisoformat(occurrence)

    @classmethod
    def next_occurrence(
        cls,
        configuration: dict[str, Any],
        after: datetime,
    ) -> datetime | None:
        """Return the configured occurrence once, then terminate."""

        occurrence = datetime.fromisoformat(configuration["occurrence"])

        if after == occurrence:
            return None

        return occurrence


class FailingInitializationTrigger(ChronologicalTrigger):
    """Chronological trigger that fails while calculating its first occurrence."""

    plugin_type = "failing_initialization"

    @classmethod
    def validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        """Accept an empty configuration."""

    @classmethod
    def next_occurrence(
        cls,
        configuration: dict[str, Any],
        after: datetime,
    ) -> datetime | None:
        """Raise to simulate trigger initialization failure."""

        raise RuntimeError("Trigger initialization failed.")


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
        self._register(RecordingTask)


class IntegrationTriggerRegistry(TriggerRegistry):
    """Trigger registry containing controlled integration-test plugins."""

    def __init__(self) -> None:
        """Register integration-test trigger plugins without discovery."""

        self._implementations = {}

        self._register(IntervalTrigger)
        self._register(OneShotTrigger)
        self._register(FailingInitializationTrigger)


# ==================================================================================================
# Registries
# ==================================================================================================


@pytest.fixture
def task_registry() -> TaskRegistry:
    """Return a task registry containing integration-test plugins."""

    FailOnceTask.attempts = 0
    RecordingTask.executions = 0

    return IntegrationTaskRegistry()


@pytest.fixture
def trigger_registry() -> TriggerRegistry:
    """Return a trigger registry containing integration-test plugins."""

    return IntegrationTriggerRegistry()


# ==================================================================================================
# Application Services
# ==================================================================================================


@pytest.fixture
def workflow_start_service(
    uow_factory,
    postgres_queue,
) -> WorkflowStartService:
    """Return a workflow start service backed by real persistence."""

    return WorkflowStartService(
        uow_factory=uow_factory,
        execution_queue=postgres_queue,
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


@pytest.fixture
def chronological_trigger_service(
    uow_factory,
    trigger_registry,
    workflow_start_service,
) -> ChronologicalTriggerService:
    """Return a chronological trigger service backed by real persistence."""

    return ChronologicalTriggerService(
        uow_factory=uow_factory,
        trigger_registry=trigger_registry,
        workflow_start_service=workflow_start_service,
    )


@pytest.fixture
def trigger_initialization_service(
    chronological_trigger_service,
) -> TriggerInitializationService:
    """Return a trigger initialization service."""

    return TriggerInitializationService(
        chronological_trigger_service=chronological_trigger_service,
    )


@pytest.fixture
def workflow_definition_service(
    uow_factory,
    task_registry,
    trigger_registry,
    trigger_initialization_service,
) -> WorkflowDefinitionService:
    """Return a workflow definition service backed by real persistence."""

    return WorkflowDefinitionService(
        uow_factory=uow_factory,
        task_registry=task_registry,
        trigger_registry=trigger_registry,
        trigger_initialization_service=trigger_initialization_service,
    )


@pytest.fixture
def chronological_trigger_service_factory(
    uow_factory,
    trigger_registry,
    workflow_start_service,
):
    """Return a factory for chronological trigger application services."""

    def factory() -> ChronologicalTriggerService:
        return ChronologicalTriggerService(
            uow_factory=uow_factory,
            trigger_registry=trigger_registry,
            workflow_start_service=workflow_start_service,
        )

    return factory
