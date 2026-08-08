"""Fixtures for API tests."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from automation_platform.application import WorkflowExecutionQueryService
from automation_platform.runtime.api.app import create_app


@pytest.fixture
def mock_api_services():
    """Return mocked application services used by the API."""

    return {
        "workflow_definition_service": MagicMock(),
        "workflow_start_service": MagicMock(),
        "workflow_execution_query_service": MagicMock(),
    }


@pytest.fixture
def api_app(mock_api_services):
    """Create a FastAPI application with mocked application services."""

    return create_app(**mock_api_services)


@pytest.fixture
def api_client(api_app):
    """Return a test client for the API."""

    return TestClient(api_app)


@pytest.fixture
def api_integration_client(
    workflow_definition_service,
    workflow_start_service,
    uow_factory,
):
    """Return an API client backed by real application services and persistence."""

    workflow_execution_query_service = WorkflowExecutionQueryService(
        uow_factory=uow_factory,
    )

    app = create_app(
        workflow_definition_service=workflow_definition_service,
        workflow_start_service=workflow_start_service,
        workflow_execution_query_service=workflow_execution_query_service,
    )

    return TestClient(app)
