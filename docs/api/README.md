# API

## Purpose

The Automation Platform API provides an HTTP interface for creating workflow definitions, starting workflows, and retrieving workflow execution state.

The API currently exposes:

```text
POST /workflow-definitions
POST /workflow-definitions/{workflow_definition_id}/start
GET  /workflow-executions/{workflow_execution_id}
```

Consumer-facing documentation is organized around these workflow operations.

## Getting Started

When running the API locally with its default server configuration, it is available at:

```text
http://localhost:8000
```

FastAPI also provides generated interactive documentation:

```text
http://localhost:8000/docs
```

and:

```text
http://localhost:8000/redoc
http://localhost:8000/openapi.json
```

The generated OpenAPI documentation contains the exact current request and response schemas.

## Workflow Lifecycle

The typical client interaction is:

```text
Create Workflow Definition
        ↓
Start Workflow
        ↓
Receive Workflow Execution ID
        ↓
Retrieve Workflow Execution
        ↓
Inspect execution state
```

Workflow definitions are reusable. Starting a definition creates a separate Workflow Execution, so the same definition can be started multiple times.

## Endpoints

| Method | Path                                                   | Purpose                                                |
| ------ | ------------------------------------------------------ | ------------------------------------------------------ |
| `POST` | `/workflow-definitions`                                | Create a reusable Workflow Definition.                 |
| `POST` | `/workflow-definitions/{workflow_definition_id}/start` | Start an execution of an existing Workflow Definition. |
| `GET`  | `/workflow-executions/{workflow_execution_id}`         | Retrieve the current state of a Workflow Execution.    |

See [Workflows](workflows.md) for request, response, and error details.

## HTTP Status Codes

Current successful responses are:

```text
POST /workflow-definitions
    → 201 Created

POST /workflow-definitions/{id}/start
    → 201 Created

GET /workflow-executions/{id}
    → 200 OK
```

Known application failures are represented as HTTP errors:

```text
400
    invalid workflow definition

404
    requested workflow definition or execution does not exist

409
    workflow definition exists but is disabled

500
    unmapped ApplicationError
```

Unexpected server or infrastructure failures are not represented as ordinary application errors.

## API Scope

The current API intentionally provides only the operations required to create definitions, start executions, and inspect execution state.

It does not currently expose workflow update or deletion operations, execution cancellation, trigger-management endpoints, pagination, or filtering.
