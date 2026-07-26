"""
Tests for workflow definition mapping.
"""

from uuid import uuid4

from automation_platform.domain.workflow_definitions import (
    TaskDefinition,
    TriggerDefinition,
    WorkflowDefinition,
)
from automation_platform.persistence.workflow_definitions._mapper import (
    WorkflowDefinitionMapper,
)
from automation_platform.persistence.workflow_definitions._model import (
    TaskDefinitionDependencyModel,
    TaskDefinitionModel,
    TriggerDefinitionModel,
    WorkflowDefinitionModel,
)


def test_workflow_to_model() -> None:
    workflow = WorkflowDefinition(
        id=uuid4(),
        name="Workflow",
        description="Description",
        enabled=True,
        task_definitions=[],
        trigger_definitions=[],
    )

    model = WorkflowDefinitionMapper.workflow_to_model(workflow)

    assert isinstance(model, WorkflowDefinitionModel)
    assert model.id == workflow.id
    assert model.name == workflow.name
    assert model.description == workflow.description
    assert model.enabled is workflow.enabled


def test_workflow_to_domain() -> None:
    model = WorkflowDefinitionModel(
        id=uuid4(),
        name="Workflow",
        description="Description",
        enabled=True,
    )

    tasks = []
    triggers = []

    workflow = WorkflowDefinitionMapper.workflow_to_domain(
        model,
        tasks,
        triggers,
    )

    assert workflow.id == model.id
    assert workflow.name == model.name
    assert workflow.description == model.description
    assert workflow.enabled == model.enabled
    assert workflow.task_definitions == tasks
    assert workflow.trigger_definitions == triggers


def test_task_to_model() -> None:
    workflow_id = uuid4()

    task = TaskDefinition(
        id=uuid4(),
        key="task",
        plugin_type="python",
        configuration={"value": 1},
        dependencies=[uuid4(), uuid4()],
        max_retries=3,
    )

    model = WorkflowDefinitionMapper.task_to_model(
        workflow_id,
        task,
    )

    assert isinstance(model, TaskDefinitionModel)
    assert model.id == task.id
    assert model.workflow_definition_id == workflow_id
    assert model.key == task.key
    assert model.plugin_type == task.plugin_type
    assert model.configuration == task.configuration
    assert model.max_retries == task.max_retries


def test_task_to_domain() -> None:
    dependency_ids = [uuid4(), uuid4()]

    model = TaskDefinitionModel(
        id=uuid4(),
        workflow_definition_id=uuid4(),
        key="task",
        plugin_type="python",
        configuration={"value": 1},
        max_retries=5,
    )

    task = WorkflowDefinitionMapper.task_to_domain(
        model,
        dependency_ids,
    )

    assert task.id == model.id
    assert task.key == model.key
    assert task.plugin_type == model.plugin_type
    assert task.configuration == model.configuration
    assert task.dependencies == dependency_ids
    assert task.max_retries == model.max_retries


def test_trigger_to_model() -> None:
    workflow_id = uuid4()

    trigger = TriggerDefinition(
        id=uuid4(),
        plugin_type="cron",
        configuration={"cron": "* * * * *"},
        enabled=True,
    )

    model = WorkflowDefinitionMapper.trigger_to_model(
        workflow_id,
        trigger,
    )

    assert isinstance(model, TriggerDefinitionModel)
    assert model.id == trigger.id
    assert model.workflow_definition_id == workflow_id
    assert model.plugin_type == trigger.plugin_type
    assert model.configuration == trigger.configuration
    assert model.enabled == trigger.enabled


def test_trigger_to_domain() -> None:
    model = TriggerDefinitionModel(
        id=uuid4(),
        workflow_definition_id=uuid4(),
        plugin_type="cron",
        configuration={"cron": "* * * * *"},
        enabled=True,
    )

    trigger = WorkflowDefinitionMapper.trigger_to_domain(model)

    assert trigger.id == model.id
    assert trigger.plugin_type == model.plugin_type
    assert trigger.configuration == model.configuration
    assert trigger.enabled == model.enabled


def test_dependency_to_model() -> None:
    task_id = uuid4()
    dependency_id = uuid4()

    model = WorkflowDefinitionMapper.dependency_to_model(
        task_id,
        dependency_id,
    )

    assert isinstance(model, TaskDefinitionDependencyModel)
    assert model.task_definition_id == task_id
    assert model.depends_on_task_definition_id == dependency_id


def test_dependencies_to_models() -> None:
    dependency_ids = [uuid4(), uuid4(), uuid4()]

    task = TaskDefinition(
        id=uuid4(),
        key="task",
        plugin_type="python",
        configuration={},
        dependencies=dependency_ids,
        max_retries=1,
    )

    models = WorkflowDefinitionMapper.dependencies_to_models(task)

    assert len(models) == len(dependency_ids)

    for model, dependency_id in zip(models, dependency_ids, strict=True):
        assert model.task_definition_id == task.id
        assert model.depends_on_task_definition_id == dependency_id
