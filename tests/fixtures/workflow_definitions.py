"""
Pytest fixtures for workflow definition domain objects.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID, uuid4

import pytest

from automation_platform.domain.workflow_definitions import (
    TaskDefinition,
    TriggerDefinition,
    WorkflowDefinition,
)


@pytest.fixture
def task_definition_factory() -> Callable[..., TaskDefinition]:
    """Create task definitions for tests."""

    def factory(
        *,
        id: UUID | None = None,
        key: str = "task",
        plugin_type: str = "test.task",
        configuration: dict | None = None,
        dependencies: list[UUID] | None = None,
        max_tries: int = 3,
    ) -> TaskDefinition:
        return TaskDefinition(
            id=id or uuid4(),
            key=key,
            plugin_type=plugin_type,
            configuration=configuration or {},
            dependencies=dependencies or [],
            max_tries=max_tries,
        )

    return factory


@pytest.fixture
def trigger_definition_factory() -> Callable[..., TriggerDefinition]:
    """Create trigger definitions for tests."""

    def factory(
        *,
        id: UUID | None = None,
        plugin_type: str = "test.trigger",
        configuration: dict | None = None,
        enabled: bool = True,
    ) -> TriggerDefinition:
        return TriggerDefinition(
            id=id or uuid4(),
            plugin_type=plugin_type,
            configuration=configuration or {},
            enabled=enabled,
        )

    return factory


@pytest.fixture
def workflow_definition_factory(
    task_definition_factory: Callable[..., TaskDefinition],
    trigger_definition_factory: Callable[..., TriggerDefinition],
) -> Callable[..., WorkflowDefinition]:
    """Create workflow definitions for tests."""

    def factory(
        *,
        id: UUID | None = None,
        name: str = "Test Workflow",
        description: str = "Test Description",
        enabled: bool = True,
        task_definitions: list[TaskDefinition] | None = None,
        trigger_definitions: list[TriggerDefinition] | None = None,
    ) -> WorkflowDefinition:
        return WorkflowDefinition(
            id=id or uuid4(),
            name=name,
            description=description,
            enabled=enabled,
            task_definitions=task_definitions or [task_definition_factory()],
            trigger_definitions=trigger_definitions or [trigger_definition_factory()],
        )

    return factory
