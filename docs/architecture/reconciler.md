# Reconciler Runtime

## Overview

The Reconciler runtime repairs inconsistencies between durable task execution state and the Execution Queue.

The normal execution path attempts to enqueue newly runnable task executions immediately. However, Persistence state and Queue state are updated through separate operations. A process failure between those operations can leave a task durably runnable but absent from the queue.

The Reconciler provides eventual recovery from this failure window.

---

## Responsibilities

The Reconciler is responsible for:

- periodically discovering durably runnable task executions
- ensuring those task executions are present in the Execution Queue
- retrying reconciliation after transient failures
- gracefully responding to runtime shutdown requests

The Reconciler is not responsible for:

- executing tasks
- determining dependency readiness
- changing task execution state
- changing workflow execution state
- implementing workflow retry behavior
- determining whether a task is already present in the queue
- scheduling workflows according to chronological triggers

---

## Runnable Task Definition

For reconciliation purposes, a task execution is runnable when:

```text
status = PENDING
AND
unmet_dependency_count = 0
```

Persistence exposes a repository query that returns the identifiers of task executions satisfying these conditions.

The Reconciler treats Persistence as the durable source of truth for whether work should be runnable.

---

## Reconciliation Lifecycle

The Reconciler continuously performs:

1. Open a Unit of Work.
2. Query Persistence for runnable task execution identifiers.
3. Close the Unit of Work.
4. Pass those identifiers to the Execution Queue.
5. Wait for the configured reconciliation interval.
6. Repeat until shutdown is requested.

Conceptually:

```text
Persistence
     │
     ▼
find_runnable_ids()
     │
     ▼
[runnable task IDs]
     │
     ▼
Reconciler
     │
     ▼
ExecutionQueue.enqueue()
     │
     ▼
wait
     │
     └──────────────> repeat
```

The Persistence operation is read-only.

Queue mutation is owned by the Queue Layer.

---

## Why Reconciliation Is Necessary

Normal task completion follows this sequence:

```text
Task A executes
      │
      ▼
Application transaction
      │
      ├── A → COMPLETED
      └── B becomes runnable
      │
      ▼
transaction commits
      │
      ▼
Worker calls queue.finish(A, [B])
      │
      ▼
B enters Execution Queue
```

There is an unavoidable failure window:

```text
Application transaction commits
      │
      ▼
B is durably runnable
      │
      X process terminates
      │
      ▼
queue.finish() never executes
```

The resulting state is:

```text
Persistence:
    B = PENDING
    unmet_dependency_count = 0

Execution Queue:
    B is absent
```

Without a repair mechanism, B could remain stranded indefinitely.

The Reconciler eventually discovers B and calls:

```text
ExecutionQueue.enqueue([B])
```

restoring the expected queue state.

---

## Idempotency

The Reconciler does not query the Execution Queue to determine which runnable tasks are missing.

Instead, it sends all currently runnable task execution identifiers to:

```text
ExecutionQueue.enqueue()
```

Queue enqueueing is idempotent.

If a task execution is already queued, enqueueing it again has no effect.

Therefore reconciliation can safely perform:

```text
find all durably runnable tasks
              │
              ▼
enqueue all of them
```

without calculating a difference between Persistence and Queue state.

This keeps the Reconciler independent of Queue implementation details.

---

## Architectural Boundary

The Reconciler accesses durable task state through the Unit of Work and Task Execution Repository.

It does not use SQLAlchemy directly.

Conceptually:

```text
Reconciler
    │
    ├── UnitOfWork
    │      │
    │      └── TaskExecutionRepository
    │
    └── ExecutionQueue
```

A separate Application service is not currently used because reconciliation policy is intentionally minimal.

The runtime directly coordinates two existing abstractions:

```text
Persistence says:
"These task executions are runnable."

Queue says:
"I will ensure these task executions are queued."
```

If reconciliation later develops substantial application policy, that policy can be extracted into an Application service.

---

## Reconciliation Cycle Failures

A failed reconciliation cycle does not terminate the runtime.

For example:

```text
reconcile
    │
    ▼
Persistence unavailable
    │
    ▼
exception logged
    │
    ▼
wait interval
    │
    ▼
try again
```

Individual reconciliation operations allow exceptions to propagate to the runtime loop.

The runtime loop owns the policy of logging the failure and continuing with a later cycle.

This makes reconciliation tolerant of temporary database or queue failures.

---

## Polling Interval

Reconciliation runs according to:

```text
reconciliation_interval
```

The interval controls the maximum normal delay before stranded runnable work is rediscovered.

The Reconciler uses its stop event for the interval wait rather than an unconditional sleep.

This makes an idle Reconciler immediately responsive to shutdown requests.

---

## Graceful Shutdown

The Reconciler exposes:

```text
stop()
```

which sets its shutdown event.

Runtime bootstrap maps operating-system signals to this method:

```text
SIGINT ──┐
         ├──> Reconciler.stop()
SIGTERM ─┘
```

This supports graceful local, container, and process-manager shutdown.

---

## Runtime Bootstrap

Reconciler bootstrap constructs its dependencies at process startup.

Conceptually:

```text
load settings
      │
      ▼
configure logging
      │
      ▼
build infrastructure
      │
      ├── database engine
      └── session factory
      │
      ▼
build Unit of Work factory
      │
      ▼
build ExecutionQueue
      │
      ▼
construct Reconciler
      │
      ▼
register shutdown signals
      │
      ▼
Reconciler.run()
```

The Reconciler runtime is exposed as a Python console entry point:

```text
automation-reconciler
```

---

## Relationship to Worker

Worker and Reconciler have different responsibilities.

### Worker

The Worker handles the normal execution path:

```text
Queue
  ↓
claim
  ↓
process task
  ↓
release / finish
```

### Reconciler

The Reconciler handles recovery:

```text
Persistence
  ↓
find runnable work
  ↓
ensure queued
```

The Worker attempts immediate propagation of newly runnable work.

The Reconciler provides eventual repair when immediate propagation fails.

Together they provide:

```text
fast normal path
      +
eventual consistency repair
```

---

## Relationship to Scheduler

The Reconciler and chronological Scheduler solve different problems.

The Reconciler answers:

> Which existing task executions are already runnable but may be missing from the Execution Queue?

The Scheduler answers:

> Which scheduled workflow definitions are due to create new workflow executions?

Therefore:

```text
Scheduler
    ↓
creates workflow executions

Reconciler
    ↓
repairs runnable task queueing

Worker
    ↓
executes runnable tasks
```

These are separate runtime responsibilities.

---

## Scaling

A single Reconciler process is sufficient for the current prototype.

The current repository query returns all runnable task execution identifiers in one reconciliation cycle.

Potential future scaling improvements include:

- batching runnable-task discovery
- pagination
- multiple reconciliation processes
- reconciliation metrics
- adaptive reconciliation intervals

These are intentionally deferred until system scale creates a concrete requirement.

---

## Testing

Reconciler behavior is tested at multiple levels.

### Unit Tests

Unit tests cover:

- discovering and enqueueing runnable tasks
- no-op behavior when no tasks are runnable
- repeated reconciliation
- recovery after reconciliation-cycle exceptions
- graceful shutdown
- signal handling

Persistence and Queue dependencies are mocked at this level.

### Persistence Integration Tests

The Task Execution Repository verifies that runnable-task discovery correctly identifies:

```text
PENDING
+
unmet_dependency_count = 0
```

task executions using real PostgreSQL.

### System Tests

System testing verifies the complete recovery path:

```text
workflow starts
      │
      ▼
root task becomes durably runnable
      │
      X initial queue propagation omitted
      │
      ▼
Worker finds no work
      │
      ▼
Reconciler discovers root
      │
      ▼
root enters queue
      │
      ▼
Worker executes root
      │
      ▼
workflow completes
```

This proves the primary reliability property provided by reconciliation:

> Durably runnable work that is missing from the Execution Queue is eventually recovered.
