# Worker Runtime

## Overview

The Worker runtime executes runnable task executions from the Execution Queue.

A Worker continuously claims task executions, processes them through the Application Layer, maintains ownership of long-running claims through heartbeats, and disposes of each claim according to the processing result.

Workers are intentionally stateless with respect to workflow execution. Durable execution state is owned by Persistence, while runnable work ownership is managed by the Execution Queue.

Multiple Worker processes may run concurrently.

---

## Responsibilities

The Worker is responsible for:

- polling the Execution Queue for runnable task executions
- claiming one task execution at a time
- maintaining the queue claim while task processing is in progress
- delegating task execution to `TaskProcessingService`
- releasing claims when tasks should be retried
- finishing claims when processing is complete
- enqueueing newly runnable task executions through the queue's finish operation
- gracefully responding to runtime shutdown requests

The Worker is not responsible for:

- determining task business behavior
- directly executing task plugins
- managing workflow or task execution state
- determining dependency readiness
- implementing retry policy
- directly reading or writing Persistence
- repairing missing queue entries

These responsibilities belong to the Application, Domain, Persistence, Plugin, Queue, and Reconciliation layers.

---

## Execution Lifecycle

The Worker continuously performs the following loop:

1. Request a claim from the Execution Queue.
2. If no work is available, wait for the configured polling interval.
3. Start heartbeat management for the acquired claim.
4. Pass the claimed task execution identifier to `TaskProcessingService`.
5. Stop heartbeat management when processing returns.
6. Verify that the claim can still be trusted.
7. Dispose of the claim according to the processing result.
8. Repeat until shutdown is requested.

Conceptually:

```text
claim()
   │
   ├── no claim
   │      │
   │      ▼
   │    wait
   │      │
   │      └───────────────┐
   │                      │
   ▼                      │
start heartbeat           │
   │                      │
   ▼                      │
process task              │
   │                      │
   ▼                      │
stop heartbeat            │
   │                      │
   ▼                      │
claim still trusted?      │
   │                      │
   ├── no → abandon       │
   │                      │
   └── yes                │
         │                │
         ├── retry        │
         │     ↓          │
         │   release()    │
         │                │
         └── complete     │
               ↓          │
             finish()     │
               │          │
               └──────────┘
```

---

## Claim and Lease Management

Queue claims are leases rather than permanent ownership.

A claim contains:

- the claimed task execution identifier
- a unique claim token identifying the current lease

While processing a task, the Worker periodically calls:

```text
ExecutionQueue.heartbeat(claim)
```

to renew the lease.

The heartbeat runs independently from task processing because plugin execution may take longer than the queue lease timeout.

### Heartbeat Thread

Each active claim receives a temporary heartbeat thread.

The heartbeat thread:

- waits for the configured heartbeat interval
- renews the current claim
- repeats while processing continues
- exits immediately when processing finishes
- marks the claim as untrusted if ownership is lost or heartbeat status cannot be determined

The heartbeat thread does not:

- process tasks
- mutate workflow state
- release claims
- finish claims
- make retry decisions

Claim disposition remains owned by the Worker's main execution thread.

---

## Untrusted Claims

A Worker must not perform queue disposition using a claim it can no longer trust.

A claim becomes untrusted when:

- `heartbeat()` reports that the lease is no longer owned
- `heartbeat()` raises an exception and ownership can no longer be confirmed

A heartbeat exception does not necessarily prove that ownership was lost. It means the Worker can no longer safely assume ownership.

When a claim becomes untrusted, the Worker does not call:

```text
release()
```

or:

```text
finish()
```

for that claim.

The durable Application-layer state may already have changed. The Reconciler is responsible for repairing runnable work that was not subsequently reflected in the Execution Queue.

---

## Processing Results

The Worker delegates task processing to:

```text
TaskProcessingService
```

The returned processing result tells the Worker how the queue claim should be handled.

### Retry

If:

```text
should_retry = true
```

the Worker calls:

```text
ExecutionQueue.release(claim)
```

The existing queue entry remains present and becomes immediately claimable again.

### Completion

If:

```text
should_retry = false
```

the Worker calls:

```text
ExecutionQueue.finish(
    claim,
    enqueue_task_ids,
)
```

This operation:

1. verifies ownership through the claim token
2. removes the completed task from the queue
3. idempotently enqueues newly runnable task executions

These operations occur atomically within the Queue Layer.

---

## Persistence and Queue Consistency

Task processing and queue disposition cannot share a single transaction because they belong to separate architectural operations.

A failure may therefore occur between:

```text
Application state committed
        │
        X
queue.finish() not executed
```

For example, Task A may successfully complete and make Task B durably runnable, but the Worker may terminate before Task B is inserted into the Execution Queue.

The Worker does not attempt to solve this consistency gap itself.

The Reconciler periodically repairs this condition by ensuring all durably runnable task executions are present in the queue.

---

## Polling

When no runnable task is available, the Worker waits for:

```text
worker_poll_interval
```

before polling again.

The Worker uses its stop event as an interruptible wait rather than performing an unconditional sleep.

This allows shutdown requests to wake an idle Worker immediately instead of waiting for the entire polling interval to expire.

---

## Graceful Shutdown

The Worker exposes:

```text
stop()
```

which sets the Worker's shutdown event.

Runtime bootstrap maps operating-system shutdown signals to this method:

```text
SIGINT ──┐
         ├──> Worker.stop()
SIGTERM ─┘
```

This supports:

- local `Ctrl+C` shutdown
- container shutdown
- process-manager shutdown

Shutdown does not forcibly terminate currently executing plugin code. The Worker reaches a safe processing boundary before its main loop exits.

---

## Configuration

The Worker uses the following runtime configuration:

| Setting | Purpose |
|---|---|
| `worker_poll_interval` | Delay between queue polls when no work is available |
| `worker_heartbeat_interval` | Frequency at which active claims are renewed |
| `queue_lease_timeout` | Maximum time a claim may remain without a valid heartbeat |

The heartbeat interval must remain comfortably below the queue lease timeout.

Current configuration validation requires:

```text
queue_lease_timeout >= 3 × worker_heartbeat_interval
```

This provides tolerance for scheduling delays before a lease becomes eligible for reclamation.

---

## Runtime Bootstrap

Worker bootstrap constructs the runtime dependencies at the process boundary.

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
build persistence dependencies
      │
      ▼
build task plugin registry
      │
      ▼
build TaskProcessingService
      │
      ▼
build ExecutionQueue
      │
      ▼
construct Worker
      │
      ▼
register shutdown signals
      │
      ▼
Worker.run()
```

The Worker runtime is exposed as a Python console entry point:

```text
automation-worker
```

Deployment infrastructure can start any number of independent Worker processes using this entry point.

---

## Concurrency Model

Each Worker process:

- has a unique worker identifier
- claims one task execution at a time
- executes one task at a time
- uses a temporary heartbeat thread while that task executes

Horizontal concurrency is achieved by running multiple Worker processes.

Queue-level row locking and claim tokens coordinate ownership between Workers.

Workers do not coordinate directly with one another.

---

## Failure Recovery

### Worker Dies Before Task Processing

The claim eventually expires and another Worker may reclaim the task.

### Worker Dies During Task Processing

The claim eventually expires.

Durable task state determines what happens when processing is attempted again.

### Heartbeat Reports Lost Ownership

The Worker marks the claim as untrusted and performs no queue disposition.

### Heartbeat Cannot Determine Ownership

The Worker conservatively treats the claim as untrusted.

### Application Processing Requests Retry

The Worker releases the claim so the task can be claimed again.

### Application Processing Commits but Queue Disposition Fails

The Reconciler eventually restores any durably runnable tasks missing from the queue.

---

## Testing

Worker behavior is tested at multiple levels.

### Unit Tests

Unit tests cover:

- polling behavior
- claim processing
- retry release
- successful finish
- heartbeat lifecycle
- lost claims
- heartbeat exceptions
- processing exceptions
- graceful shutdown
- signal handling

Queue and Application dependencies are mocked at this level.

### Integration and System Tests

PostgreSQL-backed tests verify:

- successful DAG execution
- fan-out and fan-in execution
- retries
- retry exhaustion
- workflow failure
- cancellation of unfinished tasks
- harmless handling of stale queue entries
- concurrent Worker participation
- interaction with reconciliation

These tests exercise real Persistence, Queue, Application, Worker, and Plugin components.
