"""Workflow HTTP routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from ....application import (
    WorkflowDefinitionService,
    WorkflowExecutionQueryService,
    WorkflowStartService,
)
from ..dependencies import (
    get_workflow_definition_service,
    get_workflow_execution_query_service,
    get_workflow_start_service,
)
from ..schemas import (
    CreateWorkflowDefinitionRequest,
    CreateWorkflowDefinitionResponse,
    GetWorkflowExecutionResponse,
    StartWorkflowResponse,
)

router = APIRouter()


@router.post(
    "/workflow-definitions",
    response_model=CreateWorkflowDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workflow_definition(
    request: CreateWorkflowDefinitionRequest,
    service: WorkflowDefinitionService = Depends(get_workflow_definition_service),
) -> CreateWorkflowDefinitionResponse:
    """Create a workflow definition."""

    workflow_definition_id = service.create(request.to_application_model())

    return CreateWorkflowDefinitionResponse(
        workflow_definition_id=workflow_definition_id,
    )


@router.post(
    "/workflow-definitions/{workflow_definition_id}/start",
    response_model=StartWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_workflow(
    workflow_definition_id: UUID,
    service: WorkflowStartService = Depends(get_workflow_start_service),
) -> StartWorkflowResponse:
    """Start a workflow execution."""

    workflow_execution_id = service.start(workflow_definition_id)

    return StartWorkflowResponse(
        workflow_execution_id=workflow_execution_id,
    )


@router.get(
    "/workflow-executions/{workflow_execution_id}",
    response_model=GetWorkflowExecutionResponse,
    status_code=status.HTTP_200_OK,
)
def get_workflow_execution(
    workflow_execution_id: UUID,
    service: WorkflowExecutionQueryService = Depends(get_workflow_execution_query_service),
) -> GetWorkflowExecutionResponse:
    """Get a workflow execution."""

    workflow_execution = service.get(workflow_execution_id)

    return GetWorkflowExecutionResponse.from_domain(
        workflow_execution,
    )
