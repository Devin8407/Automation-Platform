"""Integration tests for the workflow HTTP API."""

from uuid import UUID, uuid4

# ==================================================================================================
# Workflow Execution API
# ==================================================================================================


def test_create_start_and_get_workflow_execution(
    api_integration_client,
):
    """The API should create, start, and retrieve a persisted workflow execution."""

    create_response = api_integration_client.post(
        "/workflow-definitions",
        json={
            "name": "API Integration Workflow",
            "description": "Workflow created through the HTTP API.",
            "tasks": [
                {
                    "plugin_type": "successful",
                    "key": "root",
                    "configuration": {},
                    "dependencies": [],
                    "max_tries": 1,
                },
                {
                    "plugin_type": "successful",
                    "key": "child",
                    "configuration": {},
                    "dependencies": ["root"],
                    "max_tries": 1,
                },
            ],
            "triggers": [],
            "enabled": True,
        },
    )

    assert create_response.status_code == 201

    workflow_definition_id = UUID(
        create_response.json()["workflow_definition_id"],
    )

    start_response = api_integration_client.post(
        f"/workflow-definitions/{workflow_definition_id}/start",
    )

    assert start_response.status_code == 201

    workflow_execution_id = UUID(
        start_response.json()["workflow_execution_id"],
    )

    get_response = api_integration_client.get(
        f"/workflow-executions/{workflow_execution_id}",
    )

    assert get_response.status_code == 200

    execution = get_response.json()

    assert execution["id"] == str(workflow_execution_id)
    assert execution["workflow_definition_id"] == str(workflow_definition_id)
    assert execution["status"] == "RUNNING"

    assert len(execution["task_executions"]) == 2

    tasks_by_key = {task["key"]: task for task in execution["task_executions"]}

    assert tasks_by_key["root"]["plugin_type"] == "successful"
    assert tasks_by_key["root"]["status"] == "PENDING"

    assert tasks_by_key["child"]["plugin_type"] == "successful"
    assert tasks_by_key["child"]["status"] == "PENDING"


def test_get_workflow_execution_returns_not_found_for_missing_execution(
    api_integration_client,
):
    """The API should return 404 when the requested execution does not exist."""

    workflow_execution_id = uuid4()

    response = api_integration_client.get(
        f"/workflow-executions/{workflow_execution_id}",
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": "workflow_execution_not_found",
        "detail": (f"Workflow execution {workflow_execution_id} does not exist."),
    }


# ==================================================================================================
# Workflow Definition API
# ==================================================================================================


def test_create_workflow_definition_persists_through_api(
    api_integration_client,
    uow_factory,
):
    """Creating a workflow through the API should persist its definition."""

    response = api_integration_client.post(
        "/workflow-definitions",
        json={
            "name": "Persisted API Workflow",
            "description": "Verify API persistence.",
            "tasks": [
                {
                    "plugin_type": "successful",
                    "key": "task",
                    "configuration": {"value": 42},
                    "dependencies": [],
                    "max_tries": 2,
                }
            ],
            "triggers": [],
            "enabled": True,
        },
    )

    assert response.status_code == 201

    workflow_definition_id = UUID(
        response.json()["workflow_definition_id"],
    )

    with uow_factory() as uow:
        workflow_definition = uow.workflow_definitions.load(
            workflow_definition_id,
        )

    assert workflow_definition is not None
    assert workflow_definition.id == workflow_definition_id
    assert workflow_definition.name == "Persisted API Workflow"
    assert workflow_definition.description == "Verify API persistence."
    assert workflow_definition.enabled is True

    assert len(workflow_definition.task_definitions) == 1

    task = workflow_definition.task_definitions[0]

    assert task.key == "task"
    assert task.plugin_type == "successful"
    assert task.configuration == {"value": 42}
    assert task.max_tries == 2


def test_create_workflow_definition_returns_bad_request_for_invalid_definition(
    api_integration_client,
):
    """An invalid workflow definition should return a 400 response."""

    response = api_integration_client.post(
        "/workflow-definitions",
        json={
            "name": "Invalid API Workflow",
            "description": "This definition should fail application validation.",
            "tasks": [
                {
                    "plugin_type": "successful",
                    "key": "task",
                    "configuration": {},
                    "dependencies": ["does-not-exist"],
                    "max_tries": 1,
                }
            ],
            "triggers": [],
            "enabled": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_workflow_definition"
    assert response.json()["detail"]


def test_start_workflow_returns_not_found_for_missing_definition(
    api_integration_client,
):
    """Starting a nonexistent workflow definition should return 404."""

    workflow_definition_id = uuid4()

    response = api_integration_client.post(
        f"/workflow-definitions/{workflow_definition_id}/start",
    )

    assert response.status_code == 404
    assert response.json()["error"] == "workflow_definition_not_found"
    assert response.json()["detail"]


def test_start_disabled_workflow_returns_conflict(
    api_integration_client,
):
    """Starting a disabled workflow definition should return 409."""

    create_response = api_integration_client.post(
        "/workflow-definitions",
        json={
            "name": "Disabled API Workflow",
            "description": "This workflow cannot be started.",
            "tasks": [
                {
                    "plugin_type": "successful",
                    "key": "task",
                    "configuration": {},
                    "dependencies": [],
                    "max_tries": 1,
                }
            ],
            "triggers": [],
            "enabled": False,
        },
    )

    assert create_response.status_code == 201

    workflow_definition_id = UUID(
        create_response.json()["workflow_definition_id"],
    )

    response = api_integration_client.post(
        f"/workflow-definitions/{workflow_definition_id}/start",
    )

    assert response.status_code == 409
    assert response.json()["error"] == "workflow_definition_disabled"
    assert response.json()["detail"]
