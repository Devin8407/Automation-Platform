# ADR-023: HTTP API as an Application Boundary

## Status

Accepted

## Context

The Automation Platform needs an external interface through which clients can create Workflow Definitions, start Workflow Executions, and inspect execution state.

The existing architecture already separates Runtime processes from Application business orchestration:

```text
Runtime
    ↓
Application
    ↓
Domain / Persistence / Plugins / Execution Queue
```

Introducing an HTTP API could preserve this boundary or allow HTTP-specific code to become another layer of business orchestration.

The API also needs to operate as an independently executable process and support multiple concurrent API processes without relying on shared process memory.

The existing Application services already provide the required business capabilities:

```text
WorkflowDefinitionService
WorkflowStartService
WorkflowExecutionQueryService
```

The API therefore needs to determine how those capabilities are exposed without duplicating their behavior.

## Decision

The HTTP API is implemented as a **thin Runtime boundary over the Application Layer**.

```text
HTTP Client
    ↓
API Runtime
    ↓
Application capability
    ↓
Domain / Persistence / Plugins / Execution Queue
```

The API owns:

- HTTP transport.
- Request and response representations.
- HTTP routing.
- HTTP ↔ Application/Domain conversion.
- Translation of Application failures into HTTP semantics.
- API process composition and lifecycle.

Application remains responsible for business orchestration.

Routers do not access repositories, create Unit of Works, resolve Plugins, manipulate workflow state, or implement scheduling and execution behavior.

HTTP/Pydantic schemas remain separate from Application and Domain models.

Application services are constructed by the API composition root. FastAPI dependencies provide request-time access to those already-constructed services rather than constructing them.

The API is independently executable and may run multiple processes concurrently. Authoritative state therefore remains in the existing durable mechanisms rather than API process memory.

Manual workflow start uses the existing `WorkflowStartService` capability rather than introducing an API-specific trigger mechanism.

## Alternatives Considered

### API as a Business Logic Layer

The API could directly coordinate repositories, Plugins, and workflow state transitions.

```text
HTTP
    ↓
API business logic
    ↓
Persistence / Plugins / Queue
```

Rejected because this would duplicate Application orchestration and create a second owner for workflow behavior.

### API-Specific Business Capabilities

Each endpoint could implement its own workflow behavior rather than invoking existing Application capabilities.

Rejected because the same business operation could then behave differently depending on whether it was initiated through the API, Scheduler, or another Runtime.

## Consequences

### Positive

- HTTP remains a transport concern rather than becoming a business layer.
- Existing Application capabilities can be reused by external clients.
- Application remains independent of FastAPI and HTTP.
- API processes can operate concurrently without shared in-memory coordination.
- HTTP representations can evolve independently from Domain models.
- API failures can be translated into HTTP semantics without changing Application exceptions.
- Future API endpoints can be added by exposing existing or newly defined Application capabilities.

### Negative

- Some request handling requires explicit conversion between HTTP and Application/Domain models.
- Simple HTTP operations cannot bypass Application merely because a repository operation exists.
- New business behavior requires an Application capability before it can be exposed through HTTP.

## Consequences for Future Development

New API endpoints should represent meaningful client capabilities rather than mirror internal repositories or Application implementation details.

If an endpoint requires business behavior that does not already exist, that behavior should first be introduced in the Application Layer.

The API should remain:

```text
HTTP
    ↓
Application capability
```

rather than becoming another location in which workflow business logic is implemented.
