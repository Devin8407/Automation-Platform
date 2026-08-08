# Workflow Execution Query

## Purpose

The `workflow_execution_query` capability retrieves persisted Workflow Executions for callers that need to inspect execution state.

It provides an Application boundary between callers and Persistence without introducing query-specific business logic or transport concerns.

```text
Caller
    ↓
WorkflowExecutionQueryService
    ↓
Unit of Work
    ↓
WorkflowExecutionRepository
    ↓
WorkflowExecution
```

The capability is intentionally small because retrieving an execution does not require additional orchestration.

## Responsibilities

The capability owns:

- Workflow Execution retrieval
- Not-found error translation
- Unit-of-Work ownership for standalone queries

Persistence remains responsible for loading the execution and managing database access.

The API remains responsible for converting the resulting Domain object into its HTTP representation.

## Retrieval

`get()` accepts a Workflow Execution identifier and creates its own Unit of Work:

```text
get(workflow_execution_id)
        |
        +-- create UoW
        +-- load WorkflowExecution
        +-- raise if missing
        |
        v
WorkflowExecution
```

The repository is accessed through the Unit of Work:

```text
uow.workflow_executions.load(workflow_execution_id)
```

If the execution exists, the existing `WorkflowExecution` Domain object is returned.

The service does not construct a separate Application DTO because the query currently requires no additional transformation or business representation.

## Missing Executions

A missing Workflow Execution is translated into:

```text
WorkflowExecutionNotFoundError
```

The Application capability therefore distinguishes:

```text
execution exists
    ↓
return WorkflowExecution

execution does not exist
    ↓
WorkflowExecutionNotFoundError
```

The service does not translate this error into an HTTP response. The API performs that translation at its own boundary:

```text
WorkflowExecutionNotFoundError
        ↓
404 Not Found
```

This keeps the Application Layer independent of HTTP.

## Persistence Boundary

The service depends on the Unit-of-Work abstraction rather than directly accessing Persistence infrastructure.

It does not:

- perform SQL,
- access database sessions directly,
- construct repository implementations,
- manage database infrastructure.

The resulting boundary remains:

```text
Application
    ↓
Unit of Work
    ↓
WorkflowExecutionRepository
```

rather than allowing callers such as the API to bypass Application and access Persistence directly.

## Domain Boundary

The service returns the existing `WorkflowExecution` Domain object.

It does not:

- serialize the execution,
- define HTTP response fields,
- depend on FastAPI or Pydantic,
- expose Persistence models.

The API performs the transport conversion separately:

```text
WorkflowExecution
    ↓
GetWorkflowExecutionResponse.from_domain(...)
    ↓
HTTP response
```

This keeps Domain and Application models independent of the API representation.

## Testing Strategy

Important Application-level scenarios include:

- An existing Workflow Execution is returned.
- The Workflow Execution is loaded through the Unit of Work.
- A missing Workflow Execution raises `WorkflowExecutionNotFoundError`.
- The service does not perform HTTP or transport-specific conversion.
- The service does not access Persistence infrastructure directly.

Repository and database behavior remain the responsibility of Persistence tests.

HTTP error conversion remains the responsibility of API tests.
