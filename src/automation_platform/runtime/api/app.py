"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from ...application import (
    ApplicationError,
    InvalidWorkflowDefinitionError,
    WorkflowDefinitionDisabledError,
    WorkflowDefinitionNotFoundError,
    WorkflowDefinitionService,
    WorkflowExecutionNotFoundError,
    WorkflowExecutionQueryService,
    WorkflowStartService,
)
from .exception_handlers import (
    handle_application_error,
    handle_invalid_workflow_definition,
    handle_workflow_definition_disabled,
    handle_workflow_definition_not_found,
    handle_workflow_execution_not_found,
)
from .routers import router


def create_app(
    workflow_definition_service: WorkflowDefinitionService,
    workflow_start_service: WorkflowStartService,
    workflow_execution_query_service: WorkflowExecutionQueryService,
) -> FastAPI:
    """Create the FastAPI application."""

    app = FastAPI(
        title="Automation Platform API",
        version="0.1.0",
    )

    app.state.workflow_definition_service = workflow_definition_service
    app.state.workflow_start_service = workflow_start_service
    app.state.workflow_execution_query_service = workflow_execution_query_service

    app.include_router(router)

    app.add_exception_handler(
        InvalidWorkflowDefinitionError,
        handle_invalid_workflow_definition,
    )

    app.add_exception_handler(
        WorkflowDefinitionNotFoundError,
        handle_workflow_definition_not_found,
    )

    app.add_exception_handler(
        WorkflowDefinitionDisabledError,
        handle_workflow_definition_disabled,
    )

    app.add_exception_handler(
        WorkflowExecutionNotFoundError,
        handle_workflow_execution_not_found,
    )

    app.add_exception_handler(
        ApplicationError,
        handle_application_error,
    )

    return app
