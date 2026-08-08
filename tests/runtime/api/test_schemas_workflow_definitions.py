"""Tests for workflow definition HTTP schemas."""

from uuid import UUID

from automation_platform.runtime.api.schemas import (
    CreateWorkflowDefinitionRequest,
    CreateWorkflowDefinitionResponse,
    StartWorkflowResponse,
)


def test_create_workflow_definition_request_converts_to_application_model(
    create_task_definition_factory,
    create_trigger_definition_factory,
):
    """The HTTP request should convert nested definitions into application models."""

    request = CreateWorkflowDefinitionRequest(
        name="Example Workflow",
        description="Example description",
        tasks=[
            {
                "plugin_type": "http",
                "key": "fetch",
                "configuration": {"url": "https://example.com"},
                "dependencies": [],
                "max_tries": 3,
            },
            {
                "plugin_type": "transform",
                "key": "transform",
                "configuration": {"field": "name"},
                "dependencies": ["fetch"],
                "max_tries": 2,
            },
        ],
        triggers=[
            {
                "plugin_type": "interval",
                "configuration": {"interval_seconds": 60},
                "enabled": True,
            }
        ],
        enabled=False,
    )

    result = request.to_application_model()

    assert result.name == "Example Workflow"
    assert result.description == "Example description"
    assert result.enabled is False

    assert len(result.tasks) == 2
    assert result.tasks[0].plugin_type == "http"
    assert result.tasks[0].key == "fetch"
    assert result.tasks[0].configuration == {"url": "https://example.com"}
    assert result.tasks[0].dependencies == []
    assert result.tasks[0].max_tries == 3

    assert result.tasks[1].dependencies == ["fetch"]

    assert len(result.triggers) == 1
    assert result.triggers[0].plugin_type == "interval"
    assert result.triggers[0].configuration == {"interval_seconds": 60}
    assert result.triggers[0].enabled is True


def test_create_workflow_definition_request_uses_empty_configuration_and_lists_by_default():
    """Optional request collections should default to empty values."""

    request = CreateWorkflowDefinitionRequest(
        name="Example",
        description="Description",
        tasks=[],
        triggers=[],
        enabled=True,
    )

    result = request.to_application_model()

    assert result.tasks == []
    assert result.triggers == []


def test_create_workflow_definition_response_contains_id():
    """The create response should expose the workflow definition identifier."""

    workflow_definition_id = UUID("12345678-1234-5678-1234-567812345678")

    response = CreateWorkflowDefinitionResponse(
        workflow_definition_id=workflow_definition_id,
    )

    assert response.workflow_definition_id == workflow_definition_id


def test_start_workflow_response_contains_id():
    """The start response should expose the workflow execution identifier."""

    workflow_execution_id = UUID("12345678-1234-5678-1234-567812345678")

    response = StartWorkflowResponse(
        workflow_execution_id=workflow_execution_id,
    )

    assert response.workflow_execution_id == workflow_execution_id
