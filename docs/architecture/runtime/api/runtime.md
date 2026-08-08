# API Runtime

## Purpose

The API Runtime provides the independently executable HTTP process through which external clients invoke Application capabilities.

It is intentionally thin:

```text
HTTP Client
    ↓
API Runtime
    ↓
Application
    ↓
Domain / Persistence / Execution Queue / Plugins
```

The API owns process composition and HTTP server lifecycle. Application owns the business operation.

The API:

- Constructs the dependency graph required by its HTTP capabilities.
- Creates the FastAPI application.
- Provides Application services to request handlers.
- Starts Uvicorn.
- Exposes the API as an independently executable process.

It does **not**:

- Access repositories directly.
- Create Unit of Works inside routers.
- Resolve or execute Plugins.
- Process chronological triggers.
- Advance scheduling state.
- Claim Queue work.
- Execute Task Plugins.
- Reconcile stranded runnable work.
- Implement workflow state transitions.

## Process Model

The API is designed to run as one or more processes.

Each process has its own:

```text
FastAPI application
Application service instances
Infrastructure objects
database connection pool
Uvicorn server
```

Authoritative state remains shared through PostgreSQL and the Execution Queue:

```text
API 1 ──┐
API 2 ──┼── PostgreSQL
API 3 ──┘
              +
        Execution Queue
```

Multiple API processes can therefore serve requests concurrently.

Correctness must not depend on shared process memory. Shared correctness remains in the same durable mechanisms used by the rest of the platform.

## Bootstrap

`runtime/api/bootstrap.py` is the API Runtime composition root.

The startup sequence is:

```text
load Settings
    ↓
configure logging
    ↓
build Infrastructure
    ↓
build UnitOfWorkFactory
    ↓
build ExecutionQueue
    ↓
construct registries
    ↓
construct Application services
    ↓
create FastAPI application
    ↓
start Uvicorn
```

Application services are constructed explicitly during bootstrap rather than by individual routers.

The API requires the Application capabilities used by its HTTP operations:

```text
TaskRegistry
TriggerRegistry

WorkflowStartService
WorkflowDefinitionService
TriggerInitializationService
ChronologicalTriggerService

WorkflowExecutionQueryService
```

The trigger services are required because Workflow Definition creation can initialize chronological trigger state.

The API does not process chronological occurrences. `ChronologicalTriggerService.process_next_due()` remains Scheduler responsibility.

## Server Lifecycle

Uvicorn owns the HTTP server lifecycle.

The API therefore does not implement its own request-processing loop:

```text
bootstrap
    ↓
FastAPI
    ↓
Uvicorn
    ↓
HTTP requests
```

Unlike Worker, Scheduler, and Reconciler, the API does not own an application-defined processing loop and therefore does not reproduce their explicit polling and shutdown behavior.

The current server configuration is:

```python
uvicorn.run(
    app,
    host="0.0.0.0",
    port=8000,
)
```

Docker and process placement remain deployment concerns rather than API implementation concerns.

## Configuration

The API follows the same startup configuration model as the other Runtimes:

```text
Environment
    ↓
load_settings()
    ↓
Infrastructure
    ↓
Application services
    ↓
FastAPI
```

Application services do not read environment variables themselves.

API host and port are currently supplied during API bootstrap rather than being part of the central `Settings` object.

Each API process may have its own database engine, connection pool, session factory, Unit-of-Work factory, and Application service instances while sharing authoritative PostgreSQL state with other API processes.

## Process Entry Point

The API is exposed through:

```text
automation-api
```

which maps to:

```text
runtime.api.bootstrap:run_api
```

Deployment determines how many API processes are active.

For example:

```text
API 1
API 2
API 3
```

may operate concurrently against the same platform infrastructure.

## Package Organization

```text
runtime/
└── api/
    ├── __init__.py
    ├── bootstrap.py
    ├── app.py
    ├── dependencies.py
    ├── exception_handler.py
    │
    ├── routers/
    │   ├── __init__.py
    │   └── workflows.py
    │
    └── schemas/
        ├── __init__.py
        ├── workflow_definitions.py
        └── workflow_executions.py
```

The package separates process composition, FastAPI configuration, request-time dependency access, HTTP routing, and HTTP representations.

## Testing Strategy

API Runtime tests verify process-specific behavior such as:

- Bootstrap dependency construction.
- FastAPI application construction.
- API process composition.
- Multi-process assumptions.

HTTP behavior is tested separately at the HTTP boundary.

The API Runtime does not duplicate Application, Persistence, Queue, Plugin, or Scheduler guarantees.
