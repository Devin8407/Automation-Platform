"""Tests for workflow HTTP routes."""

from datetime import datetime
from uuid import UUID

from automation_platform.application import (
    CreateWorkflowDefinition,
    WorkflowExecutionNotFoundError,
)
from automation_platform.domain import WorkflowStatus


def test_create_workflow_definition_returns_created_response(
    api_client,
    mock_api_services,
):
    """Creating a workflow should return its new identifier."""

    workflow_definition_id = UUID("12345678-1234-5678-1234-567812345678")
    mock_api_services["workflow_definition_service"].create.return_value = workflow_definition_id

    response = api_client.post(
        "/workflow-definitions",
        json={
            "name": "Example Workflow",
            "description": "Example description",
            "tasks": [
                {
                    "plugin_type": "successful",
                    "key": "task",
                    "configuration": {"value": 42},
                    "dependencies": [],
                    "max_tries": 2,
                }
            ],
            "triggers": [],
            "enabled": True,
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "workflow_definition_id": str(workflow_definition_id),
    }

    mock_api_services["workflow_definition_service"].create.assert_called_once()

    request = mock_api_services["workflow_definition_service"].create.call_args.args[0]

    assert isinstance(request, CreateWorkflowDefinition)
    assert request.name == "Example Workflow"
    assert request.tasks[0].plugin_type == "successful"
    assert request.tasks[0].configuration == {"value": 42}


def test_create_workflow_definition_rejects_invalid_request(
    api_client,
    mock_api_services,
):
    """Invalid request data should be rejected before calling the service."""

    response = api_client.post(
        "/workflow-definitions",
        json={
            "name": "Example Workflow",
            "description": "Example description",
            "tasks": [
                {
                    "plugin_type": "successful",
                    "key": "task",
                    "configuration": {},
                    "dependencies": [],
                }
            ],
            "triggers": [],
            "enabled": True,
        },
    )

    assert response.status_code == 422
    mock_api_services["workflow_definition_service"].create.assert_not_called()


def test_start_workflow_returns_created_response(
    api_client,
    mock_api_services,
):
    """Starting a workflow should return the new execution identifier."""

    workflow_definition_id = UUID("12345678-1234-5678-1234-567812345678")
    workflow_execution_id = UUID("87654321-4321-8765-4321-876543218765")

    mock_api_services["workflow_start_service"].start.return_value = workflow_execution_id

    response = api_client.post(f"/workflow-definitions/{workflow_definition_id}/start")

    assert response.status_code == 201
    assert response.json() == {
        "workflow_execution_id": str(workflow_execution_id),
    }

    mock_api_services["workflow_start_service"].start.assert_called_once_with(
        workflow_definition_id,
    )


def test_start_workflow_rejects_invalid_definition_id(
    api_client,
    mock_api_services,
):
    """An invalid workflow definition identifier should be rejected."""

    response = api_client.post("/workflow-definitions/not-a-uuid/start")

    assert response.status_code == 422
    mock_api_services["workflow_start_service"].start.assert_not_called()


def test_get_workflow_execution_returns_response(
    api_client,
    mock_api_services,
    workflow_execution_factory,
):
    """Getting a workflow execution should return its HTTP representation."""

    workflow_execution = workflow_execution_factory(
        status=WorkflowStatus.RUNNING,
    )
    mock_api_services["workflow_execution_query_service"].get.return_value = workflow_execution

    response = api_client.get(f"/workflow-executions/{workflow_execution.id}")

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == str(workflow_execution.id)
    assert response_data["workflow_definition_id"] == str(workflow_execution.workflow_definition_id)
    assert response_data["status"] == "RUNNING"

    assert (
        datetime.fromisoformat(response_data["created_at"].replace("Z", "+00:00"))
        == workflow_execution.created_at
    )

    assert response_data["started_at"] is None
    assert response_data["completed_at"] is None

    assert response_data["task_executions"] == [
        {
            "id": str(task.id),
            "task_definition_id": str(task.task_definition_id),
            "key": task.key,
            "plugin_type": task.plugin_type,
            "status": task.status.name,
            "output": None,
            "error_message": task.error_message,
            "started_at": None,
            "completed_at": None,
        }
        for task in workflow_execution.task_executions
    ]

    mock_api_services["workflow_execution_query_service"].get.assert_called_once_with(
        workflow_execution.id,
    )


def test_get_workflow_execution_maps_not_found_error(
    api_client,
    mock_api_services,
):
    """A missing execution should be returned as an HTTP 404."""

    workflow_execution_id = UUID("12345678-1234-5678-1234-567812345678")

    mock_api_services[
        "workflow_execution_query_service"
    ].get.side_effect = WorkflowExecutionNotFoundError(
        f"Workflow execution {workflow_execution_id} does not exist."
    )

    response = api_client.get(f"/workflow-executions/{workflow_execution_id}")

    assert response.status_code == 404
    assert response.json() == {
        "error": "workflow_execution_not_found",
        "detail": f"Workflow execution {workflow_execution_id} does not exist.",
    }


def test_get_workflow_execution_rejects_invalid_id(
    api_client,
    mock_api_services,
):
    """An invalid workflow execution identifier should be rejected."""

    response = api_client.get("/workflow-executions/not-a-uuid")

    assert response.status_code == 422
    mock_api_services["workflow_execution_query_service"].get.assert_not_called()
