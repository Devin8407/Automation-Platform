# Runtime Architecture

## Purpose

The Runtime Layer contains the independently executable processes that drive the Automation Platform.

Runtime processes react to available work or external events and invoke the appropriate platform capabilities. They intentionally contain little business logic.

Responsibilities remain separated:

```text
Runtime
    drives platform capabilities

Application
    owns orchestration

Persistence
    owns durable state

Plugins
    own extensible behavior

Execution Queue
    owns runnable-work delivery
```

> **Runtime processes drive platform capabilities; they do not reimplement those capabilities.**

## Runtime Model

The platform is a modular monolith with multiple independently executable processes sharing the same codebase and architectural components.

Current Runtime processes are:

```text
Runtime
├── API
├── Worker
├── Reconciler
└── Scheduler
```

Each process solves a different operational problem:

| Runtime        | Responsibility                                | Primary Dependency                        |
| -------------- | --------------------------------------------- | ----------------------------------------- |
| **API**        | Expose Application capabilities through HTTP. | Application services                      |
| **Worker**     | Execute runnable Task Executions.             | `TaskProcessingService` + Execution Queue |
| **Reconciler** | Repair runnable work missing from the Queue.  | Unit of Work + Execution Queue            |
| **Scheduler**  | Process due chronological occurrences.        | `ChronologicalTriggerService`             |

Conceptually:

```text
API
    exposes Application capabilities through HTTP

Scheduler
    starts workflows when chronological occurrences are due

Worker
    executes runnable tasks

Reconciler
    repairs runnable tasks missing from the Queue
```

See:

- [API Runtime](api/README.md)
- [Worker Runtime](worker.md)
- [Reconciler Runtime](reconciler.md)
- [Scheduler Runtime](scheduler.md)

## Design Principles

Runtime processes follow several common principles:

- Keep runtime-specific logic small.
- Delegate business orchestration to Application.
- Construct dependencies explicitly during bootstrap.
- Support graceful shutdown.
- Use interruptible waits for polling.
- Recover from transient cycle failures where appropriate.
- Choose concurrency mechanisms according to the actual work.
- Avoid shared Runtime abstractions until meaningful common behavior emerges.

The Runtime Layer is a **process boundary**, not a second business-logic layer.

## Runtime Boundaries

Most Runtime interactions follow:

```text
Runtime
    ↓
Application Service
    ↓
Domain / Persistence / Plugins / Queue
```

For example:

```text
API
    ↓
Application Service
```

```text
Worker
    ↓
TaskProcessingService
```

```text
Scheduler
    ↓
ChronologicalTriggerService
```

The Reconciler is intentionally simpler:

```text
Reconciler
    ├── UnitOfWork
    └── ExecutionQueue
```

It directly coordinates two existing abstractions because reconciliation currently contains little Application policy.

If meaningful reconciliation policy develops, it can be extracted into an Application service.

## Concurrency Model

Concurrency is intentionally Runtime-specific.

### API

API processes may run concurrently. They share authoritative state through PostgreSQL and the Execution Queue rather than through process memory.

```text
API 1 ──┐
API 2 ──┼── PostgreSQL
API 3 ──┘
              +
        Execution Queue
```

No API-specific inter-process coordination mechanism is required.

### Worker

Workers execute potentially long-running arbitrary Plugin code. Queue ownership therefore uses:

```text
claim token
+
renewable lease
+
heartbeat
```

Multiple Workers coordinate through the Execution Queue without direct communication.

### Scheduler

Chronological processing is deliberately short-lived and transactional. Multiple Schedulers coordinate through PostgreSQL:

```sql
FOR UPDATE SKIP LOCKED
```

No Scheduler leases, claim tokens, heartbeats, leader election, or distributed Scheduler locks are required.

### Reconciler

Reconciliation is repeatable repair work. One Reconciler is sufficient for the current system because Queue enqueueing is idempotent.

Additional scaling mechanisms are deferred until required.

These strategies are intentionally different. Runtime concurrency is not forced through one generic mechanism.

## Bootstrap

Each Runtime has its own bootstrap module, which acts as that process's composition root.

The general startup sequence is:

```text
load Settings
    ↓
configure logging
    ↓
build Infrastructure
    ↓
construct required subsystem dependencies
    ↓
construct Application services
    ↓
construct Runtime
    ↓
register shutdown signals where required
    ↓
run
```

Each bootstrap constructs only the dependency graph required by its process.

Conceptually:

```text
API
    → Application services
    → FastAPI application

Worker
    → ExecutionQueue
    → TaskProcessingService

Reconciler
    → UnitOfWorkFactory
    → ExecutionQueue

Scheduler
    → ChronologicalTriggerService
```

Runtime classes receive already-constructed dependencies, keeping dependency composition separate from Runtime behavior.

## Process Entry Points

Current Runtime processes are exposed through Python console entry points:

```text
automation-api
automation-worker
automation-reconciler
automation-scheduler
```

Deployment infrastructure determines how many instances of each process run.

Process count and placement are deployment concerns rather than Application concerns.

## Graceful Shutdown

Long-running Runtimes expose:

```text
stop()
```

Bootstrap translates operating-system signals such as:

```text
SIGINT
SIGTERM
```

into that Runtime operation.

Polling Runtimes use their shutdown Event for interruptible waits:

```python
stop_event.wait(interval)
```

rather than unconditional sleeps.

The API is different because Uvicorn owns the HTTP server lifecycle rather than an application-defined processing loop.

## Failure Handling

Failure policy remains Runtime-specific.

| Runtime        | Failure Strategy                                                                                    |
| -------------- | --------------------------------------------------------------------------------------------------- |
| **API**        | Translate known Application failures into HTTP responses. Unexpected failures remain server errors. |
| **Worker**     | Protect claim ownership; abandon Queue disposition if the claim becomes untrusted.                  |
| **Reconciler** | Log failed repair cycles and retry after the configured interval.                                   |
| **Scheduler**  | Roll back failed occurrence transactions and avoid tight retries of repeatedly failing work.        |

Runtime failure handling determines how the process continues.

Application, Persistence, and Queue guarantees continue to determine system correctness.

## No Shared Base Runtime

Worker, Reconciler, Scheduler, and API share some superficial lifecycle concepts, but they intentionally do not inherit from a generic `BaseRuntime`.

Their work acquisition, failure semantics, concurrency requirements, dependencies, and lifecycle details are substantially different.

Small duplicated lifecycle patterns are preferable to an artificial shared abstraction.

A common Runtime abstraction should be introduced only if stable, meaningful common behavior emerges.

## Configuration and Observability

Runtime configuration comes from the shared immutable `Settings` object.

Examples include:

```text
worker_poll_interval
worker_heartbeat_interval
queue_lease_timeout
reconciliation_interval
scheduler_poll_interval
```

API server configuration is currently supplied during API bootstrap rather than being part of the central `Settings` object.

Settings are loaded during bootstrap and required values are passed explicitly to Runtime construction.

Logging is likewise configured once during bootstrap.

Runtime modules then use ordinary module-level loggers for meaningful operational events.

## Package Organization

Runtime code is organized by independently executable process:

```text
runtime/
├── api/
│   ├── bootstrap.py
│   ├── app.py
│   ├── dependencies.py
│   ├── exception_handler.py
│   ├── routers/
│   └── schemas/
│
├── worker/
│   ├── worker.py
│   └── bootstrap.py
│
├── reconciler/
│   ├── reconciler.py
│   └── bootstrap.py
│
└── scheduler/
    ├── scheduler.py
    └── bootstrap.py
```

The API has its own documentation folder because its HTTP boundary contains several independently useful concerns:

```text
docs/architecture/runtime/
├── README.md
├── worker.md
├── reconciler.md
├── scheduler.md
└── api/
    ├── README.md
    ├── runtime.md
    └── http.md
```

## Testing Strategy

Runtime behavior is tested at several levels.

**Unit tests** verify Runtime loops, polling, shutdown, failure handling, and dependency interactions using mocked architectural dependencies.

**Integration tests** verify PostgreSQL-backed Persistence and Queue behavior where mocks are insufficient.

**System tests** verify important cross-layer guarantees such as:

```text
workflow DAG execution
retry processing
terminal failure propagation
multiple Worker participation
reconciliation of stranded work
concurrent Scheduler processing
```

API HTTP behavior is tested at the API boundary rather than duplicated in lower-level subsystem tests.
