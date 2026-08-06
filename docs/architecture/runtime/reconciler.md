# Reconciler Runtime

## Purpose

The Reconciler repairs runnable Task Executions that are present in durable Persistence state but missing from the Execution Queue.

This condition can occur because Persistence and Queue updates intentionally use separate transactions.

> **The Reconciler provides eventual repair across the Persistence → Queue consistency boundary.**

## Responsibilities

The Reconciler:

- Periodically discovers durably runnable Task Executions.
- Idempotently publishes those identifiers to the Execution Queue.
- Retries after transient reconciliation failures.
- Responds gracefully to shutdown.

It does **not**:

- Execute tasks.
- Determine dependency readiness.
- Modify Task or Workflow Execution state.
- Implement retry behavior.
- Inspect Queue state to determine which entries are missing.
- Process chronological scheduling.

## Durable Runnable State

For reconciliation purposes, a Task Execution is runnable when:

```text
status = PENDING
AND
remaining_dependencies = 0
```

Persistence exposes a repository query returning Task Execution identifiers satisfying these conditions.

Persistence is the source of truth for whether work is durably runnable.

## Why Reconciliation Exists

Normal task completion attempts immediate Queue propagation:

```text
Task A completes
    ↓
Persistence transaction
    ├── A = COMPLETED
    └── B becomes runnable
    ↓
COMMIT
    ↓
queue.finish(A, [B])
```

A process may fail after the durable commit but before Queue publication:

```text
Persistence:
    B = PENDING
    remaining_dependencies = 0

Execution Queue:
    B missing
```

Without repair, `B` could remain stranded indefinitely.

The Reconciler restores the normal delivery state:

```text
Persistence
    ↓
find runnable Task Execution IDs
    ↓
Reconciler
    ↓
ExecutionQueue.enqueue(...)
```

## Reconciliation Cycle

Each cycle performs:

1. Open a Unit of Work.
2. Query runnable Task Execution identifiers.
3. Close the Unit of Work.
4. Pass the identifiers to `ExecutionQueue.enqueue`.
5. Wait for the configured interval.
6. Repeat.

The Persistence operation is read-only.

Queue mutation remains owned by the Execution Queue.

## Idempotent Repair

The Reconciler does not calculate the difference between Persistence and Queue state.

Instead:

```text
find all durably runnable tasks
        ↓
enqueue all of them
```

Queue enqueueing is idempotent.

Therefore:

```text
already queued
    → unchanged

missing
    → restored
```

This keeps the Reconciler simple and independent of Queue implementation details.

It does not need a Queue query such as:

```text
which runnable IDs are currently missing?
```

## Architectural Boundary

The Reconciler directly coordinates:

```text
Reconciler
    ├── UnitOfWork
    │      └── TaskExecutionRepository
    │
    └── ExecutionQueue
```

There is currently no Reconciliation Application service because the operation contains little Application policy:

```text
Persistence:
    "These Task Executions are runnable."

Queue:
    "Ensure these identifiers are queued."
```

If reconciliation later develops meaningful policy, that policy can be moved into an Application service.

An extra service is not introduced merely for structural symmetry with Worker or Scheduler.

## Failure Handling

A failed reconciliation cycle does not terminate the process.

Conceptually:

```text
reconcile
    ↓
Persistence or Queue failure
    ↓
log exception
    ↓
wait
    ↓
try again
```

Individual operations may allow exceptions to propagate to the Runtime loop.

The Reconciler owns the process-level policy of logging the failure and continuing with a later cycle.

This makes reconciliation tolerant of temporary database or Queue failures.

## Polling and Shutdown

Reconciliation runs according to:

```text
reconciliation_interval
```

The interval determines the normal maximum delay before stranded runnable work is rediscovered.

The Reconciler waits using its shutdown Event:

```python
stop_event.wait(reconciliation_interval)
```

rather than unconditional sleep.

It exposes:

```text
stop()
```

and bootstrap maps:

```text
SIGINT
SIGTERM
```

to that operation.

## Relationship to Other Runtimes

The three background Runtimes solve different lifecycle problems:

```text
Scheduler
    creates Workflow Executions when chronological occurrences are due

Worker
    executes runnable Task Executions

Reconciler
    repairs runnable Task Executions missing from the Queue
```

Worker provides the fast normal propagation path.

Reconciler provides eventual repair if that propagation is interrupted.

Together:

```text
immediate Queue publication
        +
eventual reconciliation
```

avoid requiring a distributed transaction between Persistence and the Execution Queue.

## Scaling

A single Reconciler is sufficient for the current system.

The current Persistence query returns all runnable Task Execution identifiers in one cycle.

Potential future scaling improvements include:

- Batched discovery.
- Pagination.
- Multiple Reconciler processes.
- Reconciliation metrics.
- Adaptive intervals.

These are intentionally deferred until concrete scale requirements exist.

## Bootstrap

Reconciler bootstrap constructs:

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
construct Reconciler
    ↓
register shutdown signals
    ↓
run
```

The process is exposed through:

```text
automation-reconciler
```

## Testing

Unit tests cover:

- Discovery and enqueueing of runnable tasks.
- No-op cycles.
- Repeated reconciliation.
- Recovery after cycle failures.
- Graceful shutdown and signal handling.

Persistence integration tests verify that runnable discovery identifies:

```text
PENDING
+
remaining_dependencies = 0
```

Task Executions correctly.

System tests verify the complete repair path:

```text
Task Execution becomes durably runnable
    ↓
initial Queue propagation is absent
    ↓
Reconciler discovers it
    ↓
Queue entry is restored
    ↓
Worker executes it
```

The central guarantee is:

> **Durably runnable Task Executions missing from the Execution Queue are eventually republished.**
