"""FastAPI dependencies for accessing application services."""

from __future__ import annotations

from fastapi import Request

from ...application import (
    WorkflowDefinitionService,
    WorkflowExecutionQueryService,
    WorkflowStartService,
)


def get_workflow_definition_service(request: Request) -> WorkflowDefinitionService:
    """Return the workflow definition application service."""

    return request.app.state.workflow_definition_service


def get_workflow_start_service(request: Request) -> WorkflowStartService:
    """Return the workflow start application service."""

    return request.app.state.workflow_start_service


def get_workflow_execution_query_service(request: Request) -> WorkflowExecutionQueryService:
    """Return the workflow execution query application service."""

    return request.app.state.workflow_execution_query_service
