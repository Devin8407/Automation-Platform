"""HTTP exception handlers for application errors."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from ...application import (
    ApplicationError,
    InvalidWorkflowDefinitionError,
    WorkflowDefinitionDisabledError,
    WorkflowDefinitionNotFoundError,
    WorkflowExecutionNotFoundError,
)


def handle_invalid_workflow_definition(
    request: Request,
    exc: InvalidWorkflowDefinitionError,
) -> JSONResponse:
    """Handle invalid workflow definition errors."""

    return JSONResponse(
        status_code=400,
        content={
            "error": "invalid_workflow_definition",
            "detail": str(exc),
        },
    )


def handle_workflow_definition_not_found(
    request: Request,
    exc: WorkflowDefinitionNotFoundError,
) -> JSONResponse:
    """Handle missing workflow definitions."""

    return JSONResponse(
        status_code=404,
        content={
            "error": "workflow_definition_not_found",
            "detail": str(exc),
        },
    )


def handle_workflow_definition_disabled(
    request: Request,
    exc: WorkflowDefinitionDisabledError,
) -> JSONResponse:
    """Handle disabled workflow definitions."""

    return JSONResponse(
        status_code=409,
        content={
            "error": "workflow_definition_disabled",
            "detail": str(exc),
        },
    )


def handle_workflow_execution_not_found(
    request: Request,
    exc: WorkflowExecutionNotFoundError,
) -> JSONResponse:
    """Handle missing workflow executions."""

    return JSONResponse(
        status_code=404,
        content={
            "error": "workflow_execution_not_found",
            "detail": str(exc),
        },
    )


def handle_application_error(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    """Handle otherwise-unmapped application errors."""

    return JSONResponse(
        status_code=500,
        content={
            "error": "application_error",
            "detail": str(exc),
        },
    )
