"""Tests for API runtime bootstrap."""

from unittest.mock import MagicMock

import automation_platform.runtime.api.bootstrap as bootstrap


def test_run_api_wires_services_and_runs_server(monkeypatch):
    """API bootstrap should wire application services into the FastAPI app."""

    settings = MagicMock()
    infrastructure = MagicMock()
    uow_factory = MagicMock()
    execution_queue = MagicMock()
    app = MagicMock()

    workflow_start_service = MagicMock()
    chronological_trigger_service = MagicMock()
    trigger_initialization_service = MagicMock()
    workflow_definition_service = MagicMock()
    workflow_execution_query_service = MagicMock()

    monkeypatch.setattr(bootstrap, "load_settings", lambda: settings)
    monkeypatch.setattr(bootstrap, "configure_logging", MagicMock())
    monkeypatch.setattr(bootstrap, "build_infrastructure", lambda _: infrastructure)
    monkeypatch.setattr(
        bootstrap,
        "build_unit_of_work_factory",
        lambda _: uow_factory,
    )
    monkeypatch.setattr(
        bootstrap,
        "build_execution_queue",
        lambda _: execution_queue,
    )
    monkeypatch.setattr(
        bootstrap,
        "WorkflowStartService",
        MagicMock(return_value=workflow_start_service),
    )
    monkeypatch.setattr(
        bootstrap,
        "ChronologicalTriggerService",
        MagicMock(return_value=chronological_trigger_service),
    )
    monkeypatch.setattr(
        bootstrap,
        "TriggerInitializationService",
        MagicMock(return_value=trigger_initialization_service),
    )
    monkeypatch.setattr(
        bootstrap,
        "WorkflowDefinitionService",
        MagicMock(return_value=workflow_definition_service),
    )
    monkeypatch.setattr(
        bootstrap,
        "WorkflowExecutionQueryService",
        MagicMock(return_value=workflow_execution_query_service),
    )
    monkeypatch.setattr(
        bootstrap,
        "create_app",
        MagicMock(return_value=app),
    )
    monkeypatch.setattr(bootstrap.uvicorn, "run", MagicMock())

    bootstrap.run_api()

    bootstrap.configure_logging.assert_called_once_with(settings.log_level)

    bootstrap.WorkflowStartService.assert_called_once_with(
        uow_factory=uow_factory,
        execution_queue=execution_queue,
    )
    bootstrap.ChronologicalTriggerService.assert_called_once_with(
        uow_factory=uow_factory,
        trigger_registry=bootstrap.ChronologicalTriggerService.call_args.kwargs["trigger_registry"],
        workflow_start_service=workflow_start_service,
    )
    bootstrap.TriggerInitializationService.assert_called_once_with(
        chronological_trigger_service=chronological_trigger_service,
    )
    bootstrap.WorkflowDefinitionService.assert_called_once_with(
        uow_factory=uow_factory,
        task_registry=bootstrap.WorkflowDefinitionService.call_args.kwargs["task_registry"],
        trigger_registry=bootstrap.WorkflowDefinitionService.call_args.kwargs["trigger_registry"],
        trigger_initialization_service=trigger_initialization_service,
    )
    bootstrap.WorkflowExecutionQueryService.assert_called_once_with(
        uow_factory=uow_factory,
    )

    bootstrap.create_app.assert_called_once_with(
        workflow_definition_service=workflow_definition_service,
        workflow_start_service=workflow_start_service,
        workflow_execution_query_service=workflow_execution_query_service,
    )

    bootstrap.uvicorn.run.assert_called_once_with(
        app,
        host="0.0.0.0",
        port=8000,
    )
