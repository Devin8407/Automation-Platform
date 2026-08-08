"""Tests for FastAPI application dependencies."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from automation_platform.runtime.api.dependencies import (
    get_workflow_definition_service,
    get_workflow_execution_query_service,
    get_workflow_start_service,
)


def test_get_workflow_definition_service_returns_app_service():
    """The dependency should return the workflow definition service from app state."""

    service = MagicMock()
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                workflow_definition_service=service,
            )
        )
    )

    assert get_workflow_definition_service(request) is service


def test_get_workflow_start_service_returns_app_service():
    """The dependency should return the workflow start service from app state."""

    service = MagicMock()
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                workflow_start_service=service,
            )
        )
    )

    assert get_workflow_start_service(request) is service


def test_get_workflow_execution_query_service_returns_app_service():
    """The dependency should return the workflow execution query service from app state."""

    service = MagicMock()
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                workflow_execution_query_service=service,
            )
        )
    )

    assert get_workflow_execution_query_service(request) is service
