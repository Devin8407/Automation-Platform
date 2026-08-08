# Workflows

## Create Workflow Definition

```http
POST /workflow-definitions
```

Creates a reusable Workflow Definition.

The request contains:

```text
name
description
tasks
triggers
enabled
```

Tasks and triggers are represented by nested request objects.

Conceptually:

```json
{
  "name": "example-workflow",
  "description": "Example workflow",
  "tasks": [
    {
      "...": "task definition"
    }
  ],
  "triggers": [
    {
      "...": "trigger definition"
    }
  ],
  "enabled": true
}
```

The exact nested task and trigger schemas are available through the generated OpenAPI documentation at `/docs` or `/openapi.json`.

A successful request returns:

```text
201 Created
```

The created definition can subsequently be started through:

```text
POST /workflow-definitions/{workflow_definition_id}/start
```

### Validation Errors

The server validates the complete workflow definition before creating it.

Invalid definitions return:

```text
400 Bad Request
```

Examples include:

- invalid task dependencies,
- duplicate task keys,
- invalid plugin configurations,
- invalid trigger configurations,
- cyclic task dependencies.

The client should treat a `400` response as indicating that the submitted definition is not valid.

### Missing or Invalid References

A workflow definition referenced by an operation may not exist:

```text
404 Not Found
```

The client should not assume that a previously known identifier remains valid indefinitely.

## Start Workflow

```http
POST /workflow-definitions/{workflow_definition_id}/start
```

Starts a new Workflow Execution from an existing Workflow Definition.

The request does not require a request body.

Conceptually:

```text
Workflow Definition
        ↓
start
        ↓
Workflow Execution
```

A successful request returns:

```text
201 Created
```

The response contains the identifier of the newly created Workflow Execution.

The returned identifier can then be used with:

```text
GET /workflow-executions/{workflow_execution_id}
```

Starting a workflow is asynchronous. A successful response means that the Workflow Execution was created; it does not mean that every Task Execution has completed.

### Disabled Definitions

A Workflow Definition may exist while being disabled.

Attempting to start a disabled definition returns:

```text
409 Conflict
```

The definition should be enabled before attempting to start it again.

### Missing Definitions

If the requested Workflow Definition does not exist:

```text
404 Not Found
```

is returned.

## Retrieve Workflow Execution

```http
GET /workflow-executions/{workflow_execution_id}
```

Retrieves the durable state of a Workflow Execution.

A successful request returns:

```text
200 OK
```

The response contains the Workflow Execution and its Task Executions.

The current Workflow Execution representation contains:

```text
id
workflow_definition_id
status
task_executions
created_at
started_at
completed_at
```

Each Task Execution contains:

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

Conceptually:

```json
{
  "id": "...",
  "workflow_definition_id": "...",
  "status": "RUNNING",
  "task_executions": [
    {
      "id": "...",
      "task_definition_id": "...",
      "key": "example-task",
      "plugin_type": "example",
      "status": "COMPLETED",
      "output": {},
      "error_message": null,
      "started_at": "...",
      "completed_at": "..."
    }
  ],
  "created_at": "...",
  "started_at": "...",
  "completed_at": null
}
```

The exact serialized field types and enum values are defined by the generated OpenAPI schema.

### Execution Status

The `status` field represents the current Workflow Execution state.

Task Execution responses contain their corresponding task status.

Execution state is asynchronous, so clients that need to wait for completion should retrieve the execution after starting it rather than assuming that a `201 Created` response represents completed work.

### Task Output

Completed Task Executions may contain an `output` dictionary.

The output represents the values produced by the task and can vary according to the task's Plugin.

The API does not impose a universal schema on Plugin output.

### Missing Executions

If the requested Workflow Execution does not exist:

```text
404 Not Found
```

is returned.

## Typical Client Flow

A client creating and executing a workflow follows:

```text
1. POST /workflow-definitions
        ↓
   201 Created

2. POST /workflow-definitions/{id}/start
        ↓
   201 Created
        ↓
   execution ID

3. GET /workflow-executions/{execution_id}
        ↓
   200 OK
        ↓
   current execution state
```

The client can retrieve the execution whenever it needs updated state.

## Error Responses

The current application-level error mappings are:

| Situation                     |                      Status |
| ----------------------------- | --------------------------: |
| Invalid workflow definition   |           `400 Bad Request` |
| Workflow Definition not found |             `404 Not Found` |
| Workflow Execution not found  |             `404 Not Found` |
| Workflow Definition disabled  |              `409 Conflict` |
| Unmapped `ApplicationError`   | `500 Internal Server Error` |

Unexpected programming, infrastructure, or server failures are not expected to use these application-level error semantics.

## Generated Reference

The generated OpenAPI documentation is the authoritative reference for the exact HTTP schemas:

```text
/docs
/redoc
/openapi.json
```

This document describes the intended consumer workflow and the meaning of the API operations; it does not duplicate the complete generated schema.
