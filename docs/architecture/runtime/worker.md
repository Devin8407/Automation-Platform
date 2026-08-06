# Worker Runtime

## Purpose

The Worker executes runnable Task Executions delivered by the Execution Queue.

It coordinates temporary Queue ownership with Application task processing:

```text
Execution Queue
      ↓
    Worker
      ↓
TaskProcessingService
```

The Worker does not own workflow execution state or task business behavior.

> **The Worker owns the runtime lifecycle around a Queue claim; Application and Persistence own what processing that task means.**

## Responsibilities

The Worker:

- Polls the Execution Queue.
- Claims one runnable Task Execution at a time.
- Maintains active claims through heartbeats.
- Delegates processing to `TaskProcessingService`.
- Releases claims when another attempt is required.
- Finishes claims when processing is complete.
- Publishes newly runnable work through Queue `finish`.
- Responds gracefully to shutdown.

It does **not**:

- Execute Task Plugins directly.
- Determine dependency readiness.
- Implement retry policy.
- Mutate Workflow or Task Execution state directly.
- Access Persistence directly.
- Repair missing Queue entries.

Those responsibilities belong to Application, Persistence, Plugins, Queue, and Reconciliation.

## Execution Lifecycle

The Worker continuously performs:

```text
claim
  │
  ├── no work
  │      ↓
  │     wait
  │
  └── claim acquired
         ↓
   start heartbeat
         ↓
   process task
         ↓
   stop heartbeat
         ↓
   claim trusted?
      ┌──┴──┐
     no    yes
      │      │
 abandon    ├── retry → release
            │
            └── complete → finish
```

More precisely:

1. Request a claim from the Execution Queue.
2. Wait when no work is available.
3. Start heartbeat management for an acquired claim.
4. Pass its Task Execution identifier to `TaskProcessingService`.
5. Stop heartbeat management when processing returns.
6. Verify that the claim remains trusted.
7. Release or finish the claim according to the processing result.
8. Repeat until shutdown.

## Claim Ownership

Queue claims are temporary leases.

A claim identifies:

```text
task_execution_id
+
claim_token
```

The Task Execution identifier identifies the work.

The claim token identifies the current lease incarnation.

While processing, the Worker periodically calls:

```text
ExecutionQueue.heartbeat(claim)
```

because arbitrary plugin execution may outlive the Queue lease timeout.

### Heartbeat Thread

Each active claim receives a temporary heartbeat thread.

The thread:

- Waits for the configured heartbeat interval.
- Renews the claim.
- Continues while task processing remains active.
- Exits when processing finishes.
- Marks the claim untrusted if ownership is lost or can no longer be confirmed.

It does **not**:

- Process tasks.
- Mutate workflow state.
- Release or finish claims.
- Make retry decisions.

Queue disposition remains the responsibility of the Worker's main thread.

## Claim Trust

The Worker performs Queue disposition only while ownership can still be trusted.

A claim becomes untrusted when:

- `heartbeat()` reports that the current lease is no longer owned, or
- `heartbeat()` fails and current ownership cannot be confirmed.

A heartbeat exception does not necessarily prove that ownership was lost.

It means ownership is uncertain.

The Worker therefore conservatively avoids:

```text
release(claim)
finish(claim, ...)
```

once a claim becomes untrusted.

This prevents an old Worker from modifying Queue state that may already belong to a newer claim.

Durable execution state remains protected separately by Application and Persistence.

## Application Processing

The Worker delegates the claimed Task Execution to:

```text
TaskProcessingService
```

Application determines the durable processing outcome.

The Worker only translates that outcome into Queue behavior.

### Retry

When another attempt is required:

```text
Application commits retry state
        ↓
Worker
        ↓
ExecutionQueue.release(claim)
```

The existing Queue entry remains present and becomes claimable again.

### Completion

When no retry is required:

```text
Application commits durable transition
        ↓
Worker
        ↓
ExecutionQueue.finish(
    claim,
    enqueue_task_ids,
)
```

`finish` atomically:

1. Validates the current claim token.
2. Removes the claimed Queue entry.
3. Idempotently publishes supplied runnable Task Execution identifiers.

The Worker does not independently determine which child tasks are runnable.

## Persistence → Queue Boundary

Durable processing and Queue disposition use separate transactions:

```text
TaskProcessingService
        ↓
Persistence COMMIT
        ↓
Worker Queue disposition
```

A process can fail between those operations.

For example:

```text
Task A completes
    ↓
Task B becomes durably runnable
    ↓
COMMIT
    ↓
Worker crashes
    ↓
queue.finish() never occurs
```

The Worker does not attempt to synchronize the two systems through a distributed transaction.

The Reconciler eventually republishes durably runnable work missing from the Queue.

## Polling and Shutdown

When no work is available, the Worker waits for:

```text
worker_poll_interval
```

using its shutdown Event:

```python
stop_event.wait(worker_poll_interval)
```

rather than an unconditional sleep.

The Worker exposes:

```text
stop()
```

and bootstrap maps:

```text
SIGINT
SIGTERM
```

to that operation.

Shutdown does not forcibly terminate currently executing plugin code. The Worker reaches a safe processing boundary before leaving its main loop.

## Configuration

Worker behavior uses:

| Setting                     | Purpose                                                        |
| --------------------------- | -------------------------------------------------------------- |
| `worker_poll_interval`      | Delay between empty Queue polls.                               |
| `worker_heartbeat_interval` | Frequency of lease renewal.                                    |
| `queue_lease_timeout`       | Maximum duration without a valid heartbeat before reclamation. |

Current configuration validation requires:

```text
queue_lease_timeout
    >=
3 × worker_heartbeat_interval
```

This provides tolerance for scheduling delays before another Worker may reclaim the lease.

## Concurrency

Each Worker process:

- Has a unique Worker identifier.
- Claims one Task Execution at a time.
- Executes one task at a time.
- Uses one temporary heartbeat thread while that task executes.

Horizontal concurrency comes from running multiple Worker processes:

```text
Worker A ─┐
Worker B ─┼──> Execution Queue
Worker C ─┘
```

Workers do not communicate directly.

The Queue coordinates temporary ownership through leases and claim tokens, while Persistence independently protects durable state transitions.

## Failure Recovery

| Failure                                         | Behavior                                                  |
| ----------------------------------------------- | --------------------------------------------------------- |
| Worker dies before or during processing         | Lease eventually expires and work may be reclaimed.       |
| Heartbeat reports lost ownership                | Claim becomes untrusted; no Queue disposition occurs.     |
| Heartbeat cannot confirm ownership              | Claim is conservatively treated as untrusted.             |
| Application requests retry                      | Worker releases the current claim.                        |
| Persistence commits but Queue disposition fails | Reconciliation eventually restores missing runnable work. |

This deliberately combines two safety boundaries:

```text
Execution Queue
    protects temporary delivery ownership

Persistence
    protects durable execution state
```

## Bootstrap

Worker bootstrap constructs its process dependencies:

```text
load Settings
    ↓
configure logging
    ↓
build Infrastructure
    ↓
build Persistence dependencies
    ↓
build Task Plugin registry
    ↓
build TaskProcessingService
    ↓
build ExecutionQueue
    ↓
construct Worker
    ↓
register shutdown signals
    ↓
run
```

The process is exposed through:

```text
automation-worker
```

Deployment may run any required number of independent Workers.

## Testing

Unit tests cover:

- Polling.
- Claim processing.
- Retry release.
- Successful finish.
- Heartbeat lifecycle.
- Lost and uncertain claims.
- Processing failures.
- Graceful shutdown and signal handling.

Integration and system tests cover:

- DAG execution.
- Fan-out and fan-in.
- Retries and retry exhaustion.
- Workflow failure and cancellation.
- Stale Queue entries.
- Concurrent Worker participation.
- Reconciliation recovery.

Detailed Queue lease semantics and durable task-transition behavior are documented by the Execution Queue and Persistence architecture respectively.
