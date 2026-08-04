# Automation Platform

> A production-style workflow execution platform built around asynchronous DAG execution, concurrent workers, durable state transitions, extensible plugins, and failure recovery.

## Overview

Automation Platform is a backend system for defining and executing automated workflows.

Workflows are modeled as directed acyclic graphs (DAGs) of tasks. At runtime, workflow definitions are compiled into independent executions, runnable tasks are distributed through a PostgreSQL-backed execution queue, and background workers process independent tasks concurrently.

The project is designed around the kinds of problems that appear in production workflow and job-processing systems: concurrent execution, worker failures, durable state, dependency scheduling, retries, duplicate work, and consistency between independently updated components.

Rather than hiding these problems behind framework abstractions, the platform implements the underlying coordination mechanisms explicitly.

### Highlights

- **Asynchronous DAG execution** with fan-out, fan-in, dependency tracking, and task output propagation.
- **Concurrent background workers** using PostgreSQL `FOR UPDATE SKIP LOCKED` for non-blocking work claiming.
- **Renewable worker leases** with unique claim tokens, heartbeats, expiration, and safe reclamation of abandoned work.
- **Transition-oriented persistence** using conditional and atomic SQL operations instead of generic aggregate overwrites.
- **Concurrency-safe dependency progression** using atomic database updates so sibling tasks can complete simultaneously.
- **Failure recovery through reconciliation**, repairing runnable tasks stranded by failures between persistence and queue operations.
- **Idempotent queue operations** that allow normal execution and recovery processes to safely race.
- **Extensible plugin architecture** with generic discovery and registries for adding task and trigger implementations.
- **Layered automated testing** spanning unit tests, PostgreSQL integration tests, concurrency scenarios, and end-to-end workflow execution.
- **Documented architecture and tradeoffs** through focused technical documentation and Architecture Decision Records (ADRs).

---

## Architecture

The platform is structured as a **modular monolith with independently executable runtime processes**.

```text
                         ┌─────────────────┐
                         │   API / Client  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Application   │
                         │      Layer      │
                         └───────┬─────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              Persistence    Task Plugins   Execution
                  Layer                       Queue
                    │                           │
                    │                           ▼
                    │                        Workers
                    │
                    └──────────────┐
                                   │
                                   ▼
                              PostgreSQL


                 Recovery path:

                 Persistence ──► Reconciler
                                      │
                                      ▼
                               Execution Queue
```

Responsibilities are intentionally separated:

- **Domain** represents workflow definitions, executions, task context, and results.
- **Application** owns workflow orchestration and business capabilities.
- **Persistence** owns durable state and concurrency-safe state transitions.
- **Execution Queue** owns runnable-work delivery and temporary worker ownership.
- **Workers** coordinate Queue claims with Application task processing.
- **Reconciler** repairs work stranded by partial Persistence-to-Queue failures.
- **Plugins** provide extensible task and trigger behavior.
- **Runtime bootstraps** construct dependencies, configure processes, and manage lifecycle.

The system remains one codebase rather than being decomposed into microservices, while Worker, Reconciler, Scheduler, and API responsibilities can run as independent processes.

[Read the Architecture Overview →](docs/architecture/overview.md)

---

## Workflow Execution

A workflow is defined as a DAG of dependent tasks.

For example:

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

When the workflow starts:

1. The reusable definition is compiled into a new `WorkflowExecution` and its runtime `TaskExecution` objects.
2. Tasks with no unmet dependencies become runnable and enter the Execution Queue.
3. Workers claim runnable tasks and execute the corresponding task plugins.
4. Completed task outputs are persisted and made available to dependent tasks.
5. Child dependency counts are atomically updated.
6. Newly runnable tasks are queued.
7. Independent branches execute concurrently.
8. The workflow completes when all of its tasks have completed.

The reusable definition remains separate from execution state, allowing multiple instances of the same workflow to execute concurrently.

---

## Concurrency and Worker Coordination

The PostgreSQL-backed Execution Queue supports multiple concurrent workers.

Workers claim tasks using:

```sql
FOR UPDATE SKIP LOCKED
```

so workers can claim independent queue entries without blocking one another.

A claim establishes a **renewable lease** containing a unique claim token. While executing a task, the worker periodically sends heartbeats to maintain ownership.

```text
queued
   │
   ▼
claimed ──► heartbeat ──► heartbeat ──► ...
   │
   │ task completes
   ▼
finished

   or

heartbeat expires
   │
   ▼
reclaimable by another worker
```

Every ownership-sensitive queue operation validates the claim token. A stale worker therefore cannot finish or release work after another worker has taken ownership.

This allows worker processes to fail and work to be recovered without permanent task ownership.

---

## Durable State and Concurrency

Persistence is the authoritative source of workflow execution state.

Instead of loading a complete execution, modifying it in memory, and blindly saving the object graph, the platform uses **explicit state transitions**.

Examples include:

```text
start task
complete task
retry task
```

Transitions are implemented with conditional SQL operations that verify the expected current state.

Dependency progression is also performed atomically in PostgreSQL.

For a fan-in:

```text
B ──┐
    ├──► D
C ──┘
```

B and C can complete concurrently while each safely contributes to D's dependency count. The workflow does not require a global execution lock, allowing independent tasks to make progress simultaneously.

This persistence model is documented in more detail in the [Persistence Architecture](docs/architecture/persistence.md).

---

## Failure Recovery

Persistence and the Execution Queue intentionally have separate transactional boundaries.

That creates an important failure case:

```text
task completes
      │
      ▼
Persistence commits
      │
      X process crashes
      │
      ▼
Queue update never happens
```

The durable workflow state is correct, but newly runnable work could be missing from the Queue.

A dedicated **Reconciler** periodically searches Persistence for runnable tasks that are absent from normal execution progress and idempotently enqueues them.

Because enqueueing is itself idempotent, the Worker path and recovery path can safely race.

This provides eventual recovery without coupling the persistence transaction to the PostgreSQL Queue implementation or requiring a distributed transaction.

---

## Extensible Task and Trigger System

Task and trigger behavior is implemented through interface-based plugins.

The plugin infrastructure provides:

```text
Plugin Interface
       │
       ▼
Generic Discovery
       │
       ▼
Generic Registry
       │
       ▼
Concrete Implementations
```

Task plugins execute through a domain-level contract:

```python
execute(context: TaskContext) -> TaskResult
```

`TaskContext` provides configuration and dependency outputs. The returned result is interpreted and persisted by the Application Layer.

Plugins therefore remain independent of:

- Workflow orchestration
- Persistence implementations
- Execution Queue state
- Worker lifecycle

New task implementations can be added without modifying the workflow engine or Worker.

---

## Reliability Model

The platform is designed around the assumption that processes can fail and concurrent operations can race.

Several mechanisms work together to preserve correctness:

| Problem | Mechanism |
|---|---|
| Multiple workers claim work concurrently | `FOR UPDATE SKIP LOCKED` |
| Worker crashes during execution | Renewable leases and expiration |
| Stale worker attempts Queue mutation | Unique claim-token validation |
| Multiple parents complete concurrently | Atomic dependency updates |
| Duplicate scheduling attempts | Idempotent Queue insertion |
| Persistence commits but Queue update fails | Reconciliation |
| Duplicate/stale execution attempts | Conditional state transitions |
| Long-running task exceeds initial claim period | Worker heartbeats |

The architecture favors explicit invariants, idempotency, and recovery over assuming ideal execution conditions.

---

## Testing

The project uses multiple levels of automated testing.

**Unit tests** cover isolated Domain, Application, Plugin, Worker, and Reconciler behavior.

**PostgreSQL integration tests** exercise behavior that depends on real database semantics, including queue claiming, row locking, leases, state transitions, dependency updates, and concurrency.

**System tests** run real components together to verify properties such as:

- DAG fan-out and fan-in
- Task output propagation
- Retry and terminal failure behavior
- Concurrent Workers
- Workflow completion
- Recovery of stranded runnable work

Continuous integration runs the automated test and quality checks on repository changes.

---

## Technology

The platform is built primarily with:

- **Python**
- **PostgreSQL**
- **SQLAlchemy**
- **pytest**
- **Docker**
- **GitHub Actions**
- **Ruff**

The architecture is designed so infrastructure such as the Execution Queue can later be replaced without changing core workflow orchestration.

---

## Documentation

The repository contains detailed technical documentation explaining both the architecture and the reasoning behind it.

- [Documentation Index](docs/README.md)
- [Architecture Overview](docs/architecture/overview.md)
- [Execution Model](docs/architecture/execution-model.md)
- [Persistence Architecture](docs/architecture/persistence.md)
- [Execution Queue](docs/architecture/execution-queue.md)
- [Plugin Architecture](docs/architecture/plugins.md)
- [Architecture Decision Records](docs/adr/README.md)

ADRs document significant decisions together with the alternatives and tradeoffs considered, including:

- Modular monolith architecture
- Queue-driven execution
- Dependency-based DAG scheduling
- Compiled Workflow Executions
- Transition-oriented persistence
- Lease-based Queue ownership
- Eventual Queue consistency through reconciliation

---

## Project Status

The core workflow execution architecture is implemented.

### Implemented

- Workflow and Task domain models
- Workflow DAG definitions
- Compiled Workflow Executions
- Task dependency and output propagation
- Application orchestration services
- PostgreSQL persistence
- Transition-oriented execution repositories
- PostgreSQL Execution Queue
- Concurrent Queue claiming
- Renewable Worker leases and heartbeats
- Background Worker runtime
- Retry and workflow failure handling
- Reconciliation runtime
- Generic task and trigger plugin infrastructure
- Prototype task plugins
- Environment-based configuration
- Process-wide logging infrastructure
- Graceful runtime shutdown
- Unit, integration, concurrency, and system testing
- GitHub Actions CI
- Architecture documentation and ADRs
- Durable scheduled trigger processing
- Scheduler runtime

### In Progress / Planned

- REST API with FastAPI
- Containerized multi-process deployment
- Additional production task and trigger plugins

The project is under active development, with the execution engine and its core concurrency and recovery mechanisms forming the current foundation.

---

## Design Philosophy

The goal of this project is not to reproduce every feature of a commercial workflow platform.

Instead, it focuses on implementing a smaller system with carefully designed internals:

> **Prefer a limited feature set with strong correctness, concurrency, failure recovery, testing, and architectural reasoning over a large feature set built on weak foundations.**

Significant design choices are documented so that the reasoning and tradeoffs behind the implementation remain visible alongside the code.

---

## License

This project is licensed under the MIT License.
