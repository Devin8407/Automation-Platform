"""API runtime bootstrap."""

from __future__ import annotations

import logging

import uvicorn

from ...application import (
    ChronologicalTriggerService,
    TriggerInitializationService,
    WorkflowDefinitionService,
    WorkflowExecutionQueryService,
    WorkflowStartService,
)
from ...config import load_settings
from ...execution_queue import build_execution_queue
from ...infrastructure import build_infrastructure
from ...observability import configure_logging
from ...persistence import build_unit_of_work_factory
from ...plugins import (
    TaskRegistry,
    TriggerRegistry,
)
from .app import create_app

logger = logging.getLogger(__name__)

# ==================================================================================================
# Public API
# ==================================================================================================


def run_api() -> None:
    """Construct and run the API runtime."""

    settings = load_settings()
    configure_logging(settings.log_level)

    infrastructure = build_infrastructure(settings)

    unit_of_work_factory = build_unit_of_work_factory(infrastructure)

    execution_queue = build_execution_queue(infrastructure)

    task_registry = TaskRegistry()
    trigger_registry = TriggerRegistry()

    workflow_start_service = WorkflowStartService(
        uow_factory=unit_of_work_factory,
        execution_queue=execution_queue,
    )

    chronological_trigger_service = ChronologicalTriggerService(
        uow_factory=unit_of_work_factory,
        trigger_registry=trigger_registry,
        workflow_start_service=workflow_start_service,
    )

    trigger_initialization_service = TriggerInitializationService(
        chronological_trigger_service=chronological_trigger_service,
    )

    workflow_definition_service = WorkflowDefinitionService(
        uow_factory=unit_of_work_factory,
        task_registry=task_registry,
        trigger_registry=trigger_registry,
        trigger_initialization_service=trigger_initialization_service,
    )

    workflow_execution_query_service = WorkflowExecutionQueryService(
        uow_factory=unit_of_work_factory,
    )

    app = create_app(
        workflow_definition_service=workflow_definition_service,
        workflow_start_service=workflow_start_service,
        workflow_execution_query_service=workflow_execution_query_service,
    )

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
    )
