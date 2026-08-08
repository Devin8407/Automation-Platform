"""Tests for HTTP exception handlers."""

import json
from unittest.mock import MagicMock

import pytest

from automation_platform.application import (
    ApplicationError,
    InvalidWorkflowDefinitionError,
    WorkflowDefinitionDisabledError,
    WorkflowDefinitionNotFoundError,
    WorkflowExecutionNotFoundError,
)
from automation_platform.runtime.api.exception_handlers import (
    handle_application_error,
    handle_invalid_workflow_definition,
    handle_workflow_definition_disabled,
    handle_workflow_definition_not_found,
    handle_workflow_execution_not_found,
)


@pytest.mark.parametrize(
    ("handler", "exception", "status_code", "error"),
    [
        (
            handle_invalid_workflow_definition,
            InvalidWorkflowDefinitionError("Invalid definition."),
            400,
            "invalid_workflow_definition",
        ),
        (
            handle_workflow_definition_not_found,
            WorkflowDefinitionNotFoundError("Definition does not exist."),
            404,
            "workflow_definition_not_found",
        ),
        (
            handle_workflow_definition_disabled,
            WorkflowDefinitionDisabledError("Definition is disabled."),
            409,
            "workflow_definition_disabled",
        ),
        (
            handle_workflow_execution_not_found,
            WorkflowExecutionNotFoundError("Execution does not exist."),
            404,
            "workflow_execution_not_found",
        ),
        (
            handle_application_error,
            ApplicationError("Application failure."),
            500,
            "application_error",
        ),
    ],
)
def test_application_error_handlers_return_expected_response(
    handler,
    exception,
    status_code,
    error,
):
    """Application errors should map to the expected HTTP response."""

    response = handler(MagicMock(), exception)

    assert response.status_code == status_code
    assert response.media_type == "application/json"
    assert json.loads(response.body) == {
        "error": error,
        "detail": str(exception),
    }
