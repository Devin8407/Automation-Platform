# Automation Platform

> A workflow execution engine built around asynchronous DAG execution, concurrent workers, durable state transitions, extensible plugins, scheduling, and failure recovery.

Automation Platform is a backend system for defining and asynchronously executing dependency-based workflows.

Rather than treating workflow execution as a simple background-job problem, the project focuses on the coordination challenges that appear in real execution systems: **concurrency, durable state, worker ownership, dependency scheduling, retries, process failure, duplicate work, and recovery across transactional boundaries**.

The result is a modular workflow engine with independently executable Worker, Scheduler, and Reconciler processes backed by PostgreSQL.

## Engineering Highlights

- **Asynchronous DAG execution** supporting fan-out, fan-in, parallel branches, dependency tracking, and task output propagation.
- **Concurrent Workers** using PostgreSQL `FOR UPDATE SKIP LOCKED` for non-blocking work claiming.
- **Lease-based work ownership** using unique claim tokens, renewable leases, heartbeats, expiration, and safe reclamation.
- **Concurrency-safe Persistence** using conditional SQL state transitions and atomic dependency progression rather than generic aggregate overwrites.
- **Failure recovery** through idempotent Queue operations and reconciliation of runnable work stranded between Persistence and Queue operations.
- **Durable scheduling** with concurrent Scheduler processes coordinating chronological triggers through transactional PostgreSQL row locking.
- **Extensible Plugins** for task and trigger behavior without coupling implementations to orchestration, Persistence, or Runtime processes.
- **Independent Runtime processes** with explicit configuration, composition roots, graceful shutdown, and shared infrastructure.
- **Layered automated testing** covering unit behavior, PostgreSQL semantics, concurrency, failure recovery, and end-to-end workflow execution.
- **Documented architectural reasoning** through focused technical documentation and 22 Architecture Decision Records.

---

## Architecture

The platform is a **modular monolith with independently executable Runtime processes**.

```text
                         ┌─────────────────┐
                         │   API / Client  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Application   │
                         └────────┬────────┘
                                  │
                ┌─────────────────┼─────────────────┐
                ▼                 ▼                 ▼
           Persistence         Plugins      Execution Queue
                │                                   │
                │                                   ▼
                │                                Workers
                │
                ├────────────► Scheduler
                │
                └────────────► Reconciler
                │
                ▼
            PostgreSQL
```

Responsibilities are deliberately separated:

| Component           | Responsibility                                        |
| ------------------- | ----------------------------------------------------- |
| **Domain**          | Core workflow and execution concepts                  |
| **Application**     | Use cases and workflow orchestration                  |
| **Persistence**     | Durable state and concurrency-safe transitions        |
| **Execution Queue** | Runnable-work delivery and temporary Worker ownership |
| **Plugins**         | Extensible task and trigger behavior                  |
| **Worker**          | Executes claimed Task Executions                      |
| **Scheduler**       | Processes durable chronological trigger occurrences   |
| **Reconciler**      | Repairs stranded runnable work                        |

The system remains one codebase while Runtime processes can execute independently.

[Read the Architecture Overview →](docs/architecture/overview.md)

---

## Workflow Execution

Workflows are directed acyclic graphs of dependent tasks:

```text
              A
              │
         ┌────┴────┐
         ▼         ▼
         B         C
         │         │
         └────┬────┘
              ▼
              D
```

Starting a workflow compiles its reusable definition into an independent `WorkflowExecution` containing runtime `TaskExecution` state.

```text
Workflow Definition
        │
        ▼
Compiled Workflow Execution
        │
        ▼
Runnable Tasks
        │
        ▼
Execution Queue
        │
        ▼
Concurrent Workers
        │
        ▼
Task Plugins
        │
        ▼
Atomic Persistence Transitions
        │
        ├────► Newly Runnable Tasks
        │
        └────► Workflow Completion
```

Independent branches can execute concurrently. Completed task outputs become available to downstream tasks, and atomic dependency updates determine when those tasks become runnable.

Definitions remain separate from execution state, allowing multiple executions of the same workflow to progress concurrently without sharing mutable runtime state.

---

## Concurrency and Failure Recovery

The platform assumes that **processes can crash and concurrent operations can race**.

Different coordination problems intentionally use different mechanisms:

| Problem                                      | Mechanism                       |
| -------------------------------------------- | ------------------------------- |
| Concurrent Queue claiming                    | `FOR UPDATE SKIP LOCKED`        |
| Worker crashes                               | Renewable leases and expiration |
| Stale Worker Queue mutations                 | Unique claim-token validation   |
| Concurrent dependency progression            | Atomic database updates         |
| Invalid or duplicate execution transitions   | Conditional SQL transitions     |
| Duplicate Queue publication                  | Idempotent enqueueing           |
| Persistence commits before Queue publication | Reconciliation                  |
| Concurrent scheduled occurrences             | Transactional row locking       |

One important example is the boundary between durable Persistence state and runnable-work delivery.

```text
Persistence COMMIT
        │
        X process crashes
        │
        ▼
Queue publication never occurs
```

The Reconciler periodically discovers Task Executions that Persistence says are runnable and idempotently republishes them to the Queue.

This allows Persistence and Queue transactions to remain independent while stranded work remains recoverable.

---

## Durable Scheduling

Workflows can also start automatically from chronological triggers.

Reusable trigger configuration is separated from durable scheduling progress:

```text
TriggerDefinition
    reusable configuration

ChronologicalTriggerState
    next scheduled occurrence
```

Multiple Scheduler processes can safely operate concurrently.

Each due occurrence is claimed using short-lived PostgreSQL row locking, and schedule advancement is committed atomically with creation of the corresponding Workflow Execution.

```text
lock due occurrence
        │
        ▼
calculate next occurrence
        │
        ▼
advance scheduling state
        +
create Workflow Execution
        │
        ▼
COMMIT
        │
        ▼
publish runnable tasks
```

Failures after Persistence commits are handled through the same reconciliation mechanism used by explicitly started workflows.

The first implemented chronological mechanism is an interval trigger, while the architecture supports additional chronological trigger plugins without changing Scheduler orchestration.

---

## Plugin Architecture

Task and trigger behavior is extensible through Plugins.

Task Plugins operate through a Domain-level contract:

```python
execute(context: TaskContext) -> TaskResult
```

Plugins remain independent of:

- Workflow orchestration.
- Persistence implementations.
- Execution Queue ownership.
- Runtime process lifecycle.

Application code resolves and invokes Plugins while retaining responsibility for execution semantics, retries, state transitions, and workflow progression.

Trigger mechanisms use specialized capability interfaces rather than being forced through one universal trigger abstraction.

---

## Testing

Concurrency and recovery guarantees are tested at the architectural boundaries that provide them.

The test suite includes:

**Unit tests** for Domain behavior, Application orchestration, Plugins, and Runtime loops.

**PostgreSQL integration tests** for:

- Conditional state transitions.
- Atomic dependency progression.
- Queue claiming and leases.
- Claim-token validation.
- `FOR UPDATE SKIP LOCKED`.
- Chronological row locking.
- Idempotent Queue operations.

**System tests** for:

- DAG fan-out and fan-in.
- Parallel task execution.
- Dependency output propagation.
- Retries and terminal failures.
- Multiple concurrent Workers.
- Stranded-work recovery.
- Multiple concurrent Schedulers.
- End-to-end scheduled workflow execution.

GitHub Actions runs automated tests and quality checks on repository changes.

---

## Technology

|                            |                                             |
| -------------------------- | ------------------------------------------- |
| **Language**               | Python                                      |
| **Database**               | PostgreSQL                                  |
| **ORM / Database Toolkit** | SQLAlchemy                                  |
| **Testing**                | pytest                                      |
| **Quality**                | Ruff                                        |
| **CI**                     | GitHub Actions                              |
| **Deployment**             | Docker *(planned multi-process deployment)- |
| **API**                    | FastAPI *(planned)-                         |

PostgreSQL is used intentionally for database-backed concurrency primitives such as conditional updates, row locking, and `SKIP LOCKED`.

---

## Project Status

The core workflow engine, concurrency model, recovery mechanisms, and durable scheduling system are implemented.

### Implemented

```text
✓ DAG workflow execution
✓ Compiled independent Workflow Executions
✓ Concurrent Worker processing
✓ PostgreSQL Execution Queue
✓ Lease-based Worker ownership and heartbeats
✓ Conditional execution state transitions
✓ Atomic dependency progression
✓ Task output propagation
✓ Retry and terminal failure handling
✓ Persistence → Queue reconciliation
✓ Extensible task and trigger Plugins
✓ Durable chronological trigger state
✓ Concurrent Scheduler processing
✓ Interval scheduling
✓ Explicit Runtime configuration and composition
✓ Graceful Runtime shutdown
✓ Unit, integration, concurrency, and system testing
✓ Continuous integration
✓ Architecture documentation and ADRs
```

### Next

```text
REST API
    ↓
Containerized multi-process deployment
    ↓
Production hardening
```

See the [Project Roadmap](docs/roadmap.md) for completed milestones and future direction.

---

## Documentation

The repository includes detailed documentation for both the current architecture and the reasoning behind significant design decisions.

| Documentation                                           | Purpose                                              |
| ------------------------------------------------------- | ---------------------------------------------------- |
| [Documentation Index](docs/README.md)                   | Entry point to project documentation                 |
| [Architecture](docs/architecture/README.md)             | Architecture index and recommended reading order     |
| [Architecture Overview](docs/architecture/overview.md)  | Complete high-level system design                    |
| [Execution Model](docs/architecture/execution-model.md) | Workflow compilation and DAG progression             |
| [Persistence](docs/architecture/persistence/README.md)  | Durable state and concurrency guarantees             |
| [Execution Queue](docs/architecture/execution-queue.md) | Work delivery, claims, leases, and Queue concurrency |
| [Plugins](docs/architecture/plugins/README.md)          | Task and trigger extension architecture              |
| [Runtime](docs/architecture/runtime/README.md)          | Worker, Scheduler, and Reconciler processes          |
| [Architecture Decision Records](docs/adr/README.md)     | Decisions, alternatives, and architectural tradeoffs |

Architecture documentation describes **how the system currently works**.

ADRs preserve **why significant architectural choices were made**.

---

## Design Philosophy

This project deliberately focuses on a smaller feature set with carefully designed internals rather than attempting to reproduce every feature of a commercial workflow platform.

The central engineering principle is:

> **Prefer explicit correctness, concurrency, recoverability, testing, and architectural reasoning over feature breadth built on weak foundations.**

The implementation is designed so that important guarantees can be explained, tested, and traced to the architectural decisions that created them.

---

## License

This project is licensed under the MIT License.
