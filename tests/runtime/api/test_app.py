"""Tests for the FastAPI application factory."""

from automation_platform.application import WorkflowExecutionNotFoundError
from automation_platform.runtime.api.app import create_app


def test_create_app_stores_application_services(
    mock_api_services,
):
    """The application factory should expose services through app state."""

    app = create_app(**mock_api_services)

    assert (
        app.state.workflow_definition_service is (mock_api_services["workflow_definition_service"])
    )
    assert app.state.workflow_start_service is (mock_api_services["workflow_start_service"])
    assert (
        app.state.workflow_execution_query_service
        is (mock_api_services["workflow_execution_query_service"])
    )


def test_create_app_registers_workflow_routes(
    api_client,
):
    """The application should expose the workflow API routes."""

    response = api_client.post("/workflow-definitions/not-a-uuid/start")

    assert response.status_code == 422


def test_create_app_registers_application_error_handlers(
    api_client,
    mock_api_services,
):
    """The application should register application exception handlers."""

    mock_api_services[
        "workflow_execution_query_service"
    ].get.side_effect = WorkflowExecutionNotFoundError("Execution does not exist.")

    response = api_client.get("/workflow-executions/12345678-1234-5678-1234-567812345678")

    assert response.status_code == 404
    assert response.json() == {
        "error": "workflow_execution_not_found",
        "detail": "Execution does not exist.",
    }
