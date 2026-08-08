# API HTTP Boundary

## Purpose

The HTTP layer translates between HTTP representations and Application capabilities.

```text
HTTP Request
    ↓
Request Schema
    ↓
Application Service
    ↓
Domain Result
    ↓
Response Schema
    ↓
HTTP Response
```

The HTTP layer owns routing, transport models, dependency access, and HTTP error translation.

It does not implement workflow business logic.

## FastAPI Application

`runtime/api/app.py` creates the FastAPI application and registers the API routers and exception handlers.

The Application Layer does not depend on FastAPI.

## Routers

The initial API uses:

```text
runtime/api/routers/workflows.py
```

The router contains the workflow-related endpoints:

```text
POST /workflow-definitions
POST /workflow-definitions/{workflow_definition_id}/start
GET  /workflow-executions/{workflow_execution_id}
```

Routers remain transport adapters:

```text
HTTP request
    ↓
request validation
    ↓
Application service
    ↓
HTTP response
```

They do not access repositories or create Unit of Works.

The three initial operations remain in one workflow router because they form a small, coherent API surface.

## FastAPI Dependencies

FastAPI `Depends()` provides request-time access to Application services.

Services are constructed during bootstrap:

```text
bootstrap
    ↓
Application service
    ↓
app.state
    ↓
FastAPI dependency
    ↓
router
```

The dependency functions therefore connect FastAPI's request handling to the composition root. They do not construct services or perform business orchestration.

## HTTP Schemas

HTTP/Pydantic models remain separate from Application and Domain models.

Request conversion follows:

```text
JSON
    ↓
Pydantic request schema
    ↓
Application input
    ↓
Application service
```

Response conversion follows:

```text
Domain object
    ↓
HTTP response schema
    ↓
JSON
```

For Workflow Definition creation:

```text
CreateWorkflowDefinitionRequest
    ↓
to_application_model()
    ↓
CreateWorkflowDefinition
    ↓
WorkflowDefinitionService
```

The API therefore does not pass Pydantic models into the Application Layer.

## HTTP Capabilities

### Create Workflow Definition

```text
POST /workflow-definitions
```

maps to:

```text
WorkflowDefinitionService.create(...)
```

and returns:

```text
201 Created
```

Application remains responsible for definition validation, Plugin validation, dependency validation, trigger initialization, and persistence.

### Start Workflow

```text
POST /workflow-definitions/{workflow_definition_id}/start
```

maps to:

```text
WorkflowStartService.start(workflow_definition_id)
```

and returns:

```text
201 Created
```

Manual workflow start is an Application operation rather than a Trigger mechanism.

The API does not calculate trigger occurrences, advance chronological state, or invoke the Scheduler.

### Retrieve Workflow Execution

```text
GET /workflow-executions/{workflow_execution_id}
```

maps to:

```text
WorkflowExecutionQueryService.get(...)
```

and returns:

```text
200 OK
```

The query capability allows clients to inspect durable execution state after starting an asynchronous workflow.

## Workflow Execution Responses

The initial response models are:

```text
TaskExecutionResponse
GetWorkflowExecutionResponse
```

Task execution responses expose:

```text
id
task_definition_id
key
plugin_type
status
output
error_message
started_at
completed_at
```

Workflow execution responses expose:

```text
id
workflow_definition_id
status
task_executions
created_at
started_at
completed_at
```

Internal execution-engine details such as:

```text
configuration
parent_task_ids
child_task_ids
remaining_dependencies
remaining_tries
```

are not exposed unless a future API requirement makes them part of the public contract.

Domain enums are converted explicitly into HTTP strings, and Domain task output is converted into the API's output representation.

## Workflow Execution Query

The API does not access Persistence directly.

Execution retrieval uses:

```text
WorkflowExecutionQueryService
```

which provides the Application boundary:

```text
API
    ↓
WorkflowExecutionQueryService
    ↓
Unit of Work
    ↓
WorkflowExecutionRepository
    ↓
WorkflowExecution
```

If the execution does not exist, Application raises:

```text
WorkflowExecutionNotFoundError
```

The API translates that Application failure into HTTP semantics.

## Exception Handling

Application exceptions remain Application concepts.

The API translates known failures into HTTP responses:

| Application exception             |               HTTP response |
| --------------------------------- | --------------------------: |
| `InvalidWorkflowDefinitionError`  |           `400 Bad Request` |
| `WorkflowDefinitionNotFoundError` |             `404 Not Found` |
| `WorkflowDefinitionDisabledError` |              `409 Conflict` |
| `WorkflowExecutionNotFoundError`  |             `404 Not Found` |
| Unmapped `ApplicationError`       | `500 Internal Server Error` |

A disabled Workflow Definition uses `409 Conflict` because the resource exists but its current state conflicts with the requested operation.

Known failures follow:

```text
Application exception
    ↓
API exception handler
    ↓
HTTP response
```

Unexpected exceptions remain server errors and are handled by the normal FastAPI/Uvicorn error path.

## Generated API Documentation

FastAPI generates OpenAPI documentation from the routes and Pydantic schemas.

The generated references are available at:

```text
/docs
/redoc
/openapi.json
```

These serve a different purpose from repository architecture documentation:

```text
docs/api/
    how consumers use the API

docs/architecture/runtime/api/
    how the API Runtime is designed
```

## Testing Strategy

HTTP unit tests verify:

- Request-to-Application conversion.
- Domain-to-response conversion.
- Router/Application interaction.
- HTTP exception mapping.

Integration tests exercise the actual FastAPI request path:

```text
HTTP request
    ↓
FastAPI
    ↓
Router
    ↓
Application
    ↓
Persistence
```

Important cases include:

```text
workflow definition creation
manual workflow start
workflow execution retrieval
missing resources
disabled definitions
invalid definitions
```

API integration tests do not duplicate DAG execution, Task Plugin execution, retry semantics, chronological occurrence calculation, Scheduler concurrency, or Queue lease behavior.
