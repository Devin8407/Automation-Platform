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

Current background runtimes are:

```text
Runtime
├── Worker
├── Reconciler
└── Scheduler
```

A future API Runtime can provide the external HTTP entry point.

Each process solves a different operational problem:

| Runtime        | Responsibility                               | Primary Dependency                        |
| -------------- | -------------------------------------------- | ----------------------------------------- |
| **Worker**     | Execute runnable Task Executions.            | `TaskProcessingService` + Execution Queue |
| **Reconciler** | Repair runnable work missing from the Queue. | Unit of Work + Execution Queue            |
| **Scheduler**  | Process due chronological occurrences.       | `ChronologicalTriggerService`             |

Conceptually:

```text
Scheduler
    starts workflows when chronological occurrences are due

Worker
    executes runnable tasks

Reconciler
    repairs runnable tasks missing from the Queue
```

See:

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
- Choose concurrency mechanisms according to the work being performed.
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
Worker
    ↓
TaskProcessingService
```

and:

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

It directly coordinates two existing abstractions because reconciliation currently contains very little Application policy.

If meaningful reconciliation policy develops, it can be extracted into an Application service.

## Concurrency and Recovery

Each Runtime uses a concurrency model appropriate to its work.

### Worker

Workers execute potentially long-running arbitrary plugin code.

Ownership therefore uses:

```text
claim token
+
renewable lease
+
heartbeat
```

Multiple Workers coordinate through the Execution Queue without communicating directly.

### Scheduler

Chronological processing is deliberately short-lived and transactional.

Multiple Schedulers coordinate through PostgreSQL:

```sql
FOR UPDATE SKIP LOCKED
```

No Scheduler leases, claim tokens, or heartbeats are required.

### Reconciler

Reconciliation is repeatable repair work.

A single Reconciler is sufficient for the current system, and repeated publication is safe because Queue enqueueing is idempotent.

Additional scaling mechanisms are deferred until required.

These different strategies are intentional. Runtime concurrency is not forced through one generic mechanism.

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
register shutdown signals
    ↓
run
```

Each bootstrap constructs only the dependency graph required by its process.

Conceptually:

```text
Worker
    → ExecutionQueue
    → TaskProcessingService

Reconciler
    → UnitOfWorkFactory
    → ExecutionQueue

Scheduler
    → ChronologicalTriggerService
```

Runtime classes receive already-constructed dependencies, keeping dependency composition separate from runtime behavior.

## Process Entry Points

Current Runtime processes are exposed through Python console entry points:

```text
automation-worker
automation-reconciler
automation-scheduler
```

Deployment infrastructure determines how many instances of each process run.

For example:

```text
PostgreSQL

Worker 1
Worker 2
Worker 3

Reconciler

Scheduler 1
Scheduler 2
```

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

into that runtime operation.

Polling Runtimes use their shutdown Event for interruptible waits:

```python
stop_event.wait(interval)
```

rather than unconditional sleeps.

This allows idle processes to respond immediately to shutdown without coupling Runtime classes to operating-system signal handling.

## Failure Handling

Failure policy remains Runtime-specific.

| Runtime        | Failure Strategy                                                                             |
| -------------- | -------------------------------------------------------------------------------------------- |
| **Worker**     | Protect claim ownership; abandon Queue disposition if the claim becomes untrusted.           |
| **Reconciler** | Log failed repair cycles and retry after the configured interval.                            |
| **Scheduler**  | Roll back failed occurrence transactions and avoid tight retries of repeatedly failing work. |

Runtime failure handling determines how the process continues.

Application, Persistence, and Queue guarantees continue to determine system correctness.

## No Shared Base Runtime

Worker, Reconciler, and Scheduler share some superficial lifecycle concepts:

```text
run()
stop()
shutdown Event
polling
logging
signal registration
```

They intentionally do not inherit from a generic `BaseRuntime`.

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

Settings are loaded during bootstrap and required values are passed explicitly to Runtime construction.

Logging is likewise configured once during bootstrap.

Runtime modules then use ordinary module-level loggers for meaningful events such as startup, shutdown, failed cycles, claim ownership problems, and unexpected processing failures.

Neither Configuration nor Observability becomes part of Runtime correctness.

## Package Organization

Runtime code is organized by independently executable process:

```text
runtime/
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

The documentation mirrors that organization:

```text
docs/architecture/runtime/
├── overview.md
├── worker.md
├── reconciler.md
└── scheduler.md
```

## Testing Strategy

Runtime behavior is tested at several levels.

**Unit tests** verify Runtime loops, polling, shutdown, failure handling, dependency interactions, and Runtime-specific concurrency behavior using mocked architectural dependencies.

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

The Runtime testing goal is to verify process behavior and architectural guarantees rather than duplicate lower-level subsystem tests.

## Guiding Principle

> **Runtime processes decide when and how to drive platform capabilities. The capabilities themselves remain owned by Application, Persistence, Plugins, Domain, and the Execution Queue.**
