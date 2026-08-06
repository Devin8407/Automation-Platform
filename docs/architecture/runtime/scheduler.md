# Scheduler Runtime

## Purpose

The Scheduler drives workflow activation for chronological triggers.

A chronological trigger starts workflows according to time-based occurrences, such as an interval schedule and potentially future cron or one-time schedules.

The Scheduler itself contains very little scheduling logic:

```text
Scheduler
    ↓
ChronologicalTriggerService.process_next_due()
```

Application, Plugins, and Persistence determine what constitutes an occurrence and how it is processed.

> **The Scheduler drives chronological processing; it does not implement chronological scheduling behavior.**

## Responsibilities

The Scheduler Runtime:

- Repeatedly requests due chronological work from Application.
- Immediately continues while due work is available.
- Waits when no occurrence is due.
- Handles process shutdown.
- Logs Runtime-level failures.
- Avoids tight retry loops after failed processing.

It does **not**:

- Query scheduling tables directly.
- Resolve Trigger Plugins.
- Calculate schedule occurrences.
- Advance chronological state.
- Manage database locks.
- Create Workflow Executions directly.
- Publish Task Executions directly to the Execution Queue.

Those responsibilities belong to Application, Plugins, Persistence, and the existing workflow-start path.

## Chronological Processing Boundary

The Scheduler invokes:

```python
ChronologicalTriggerService.process_next_due()
```

Each call processes at most one due chronological occurrence.

Conceptually:

```text
Scheduler
    ↓
ChronologicalTriggerService
    ↓
Persistence selects + locks due state
    ↓
Plugin calculates next occurrence
    ↓
Application advances/removes schedule state
    +
starts Workflow Execution
    ↓
COMMIT
```

The service returns:

```text
True
    one occurrence was processed

False
    no chronological occurrence is currently due
```

Detailed trigger initialization, Plugin contracts, scheduling-state persistence, and Workflow Execution creation are documented in their owning architectural subsystems.

## Scheduler Loop

The Runtime loop can therefore remain small:

```python
while running:
    processed = chronological_trigger_service.process_next_due()

    if not processed:
        wait(poll_interval)
```

When processing succeeds, the Scheduler immediately asks for another due occurrence.

It waits only when no work is due:

```text
process → True
process → True
process → True
nothing due → False
wait
```

The polling interval therefore controls **idle scheduling latency**, not maximum scheduling throughput.

## Concurrency

Multiple Scheduler processes may operate concurrently:

```text
Scheduler A ─┐
Scheduler B ─┼──> PostgreSQL chronological state
Scheduler C ─┘
```

Persistence selects due chronological state using:

```sql
FOR UPDATE SKIP LOCKED
```

A locked occurrence is skipped by other Scheduler transactions, allowing them to process different due occurrences instead.

Conceptually:

```text
Scheduler 1 → occurrence A

Scheduler 2 → A locked → occurrence B

Scheduler 3 → A/B locked → occurrence C
```

The PostgreSQL row lock acts as a short-lived claim on the selected occurrence.

Schedulers do not coordinate directly.

## Why Scheduler Ownership Uses Row Locks

Worker processing may execute arbitrary plugin code for a long time, so Workers require renewable Queue leases, claim tokens, and heartbeats.

Chronological processing is deliberately different.

A scheduling transaction performs bounded local work:

```text
lock due state
    ↓
calculate next occurrence
    ↓
advance/remove scheduling state
    ↓
create Workflow Execution
    ↓
commit
```

Chronological Trigger Plugin calculations are expected to be fast, deterministic, local, and free of I/O.

A database transaction can therefore safely own the occurrence for its short processing lifetime.

If the Scheduler dies:

```text
Scheduler crashes
    ↓
transaction terminates
    ↓
PostgreSQL rolls back
    ↓
row lock released
    ↓
occurrence remains due
```

The Scheduler therefore does not require:

```text
Scheduler IDs
claim tokens
heartbeats
lease expiration
leader election
distributed Scheduler locks
```

## Atomicity

Chronological schedule advancement and Workflow Execution creation occur in the same Persistence Unit of Work.

Conceptually:

```text
BEGIN
    ↓
lock due occurrence
    ↓
calculate next occurrence
    ↓
advance or remove scheduling state
    ↓
create Workflow Execution
    ↓
COMMIT
```

The database cannot commit only one side of that operation.

It cannot persist:

```text
schedule advanced
but
Workflow Execution missing
```

or:

```text
Workflow Execution created
but
schedule not advanced
```

If processing fails before commit, both changes roll back and the occurrence remains due.

This atomicity is provided by Application and Persistence; the Scheduler merely drives the operation.

## Failure Handling

### Processing Failure

If trigger calculation, Persistence, or workflow creation fails:

```text
process occurrence
    ↓
transaction fails
    ↓
ROLLBACK
    ↓
occurrence remains due
```

The Scheduler logs the failure.

It then waits before attempting more work so that a permanently failing occurrence cannot create an uncontrolled tight loop.

### Scheduler Crash

An open transaction is rolled back by PostgreSQL, releasing the selected row lock.

Another Scheduler can subsequently process the still-due occurrence.

### Successful Processing

Schedule advancement/removal and Workflow Execution creation become durable together.

The Scheduler can immediately request another occurrence.

## Catch-Up Behavior

Recurring chronological triggers advance relative to the **persisted scheduled occurrence**, not directly from the current wall-clock time.

For example:

```text
interval     = 1 hour
next_run_at  = 09:00
current time = 11:30
```

Processing advances:

```text
09:00 → 10:00
```

not directly to `12:00`.

Because `10:00` remains due, the Scheduler immediately processes another occurrence:

```text
09:00 → 10:00
10:00 → 11:00
11:00 → 12:00
```

Once the next occurrence is in the future, `process_next_due()` eventually returns `False` and the Scheduler waits.

This provides deterministic catch-up without silently skipping persisted occurrences.

The calculation itself belongs to the Chronological Trigger Plugin/Application path rather than the Scheduler Runtime.

## Finite Chronological Triggers

The chronological Plugin contract may return:

```python
next_occurrence(...) -> datetime | None
```

`None` means no future occurrence exists.

Application/Persistence then removes the chronological runtime scheduling state while preserving the reusable `TriggerDefinition`.

Conceptually:

```text
TriggerDefinition
    remains

ChronologicalTriggerState
    removed
```

The Scheduler requires no special behavior for finite schedules.

This allows future chronological plugins such as one-time schedules to use the same Runtime loop.

## Execution Queue Boundary

The Scheduler does not directly publish Task Executions.

Chronological processing reuses the existing workflow-start capability:

```text
Scheduler
    ↓
ChronologicalTriggerService
    ↓
WorkflowStartService
    ↓
Workflow Execution created
```

Runnable root tasks are propagated through the platform's normal Persistence → Queue boundary.

If Queue publication is interrupted after durable commit, the existing Reconciler repairs missing runnable work.

The Scheduler therefore does not introduce a second workflow-start or Queue-recovery path.

## Polling and Shutdown

The Scheduler waits according to:

```text
scheduler_poll_interval
```

only when no chronological work is currently due or after a failed processing attempt requiring delay.

It uses its shutdown Event for interruptible waiting rather than unconditional sleep.

The Scheduler exposes:

```text
stop()
```

and bootstrap maps:

```text
SIGINT
SIGTERM
```

to that operation.

## Bootstrap

Scheduler bootstrap constructs the dependencies required to host chronological processing:

```text
load Settings
    ↓
configure logging
    ↓
build Infrastructure
    ↓
build Persistence dependencies
    ↓
build Trigger Plugin registry
    ↓
build WorkflowStartService
    ↓
build ChronologicalTriggerService
    ↓
construct Scheduler
    ↓
register shutdown signals
    ↓
run
```

The process is exposed through:

```text
automation-scheduler
```

Deployment may run multiple Scheduler instances when additional chronological-processing concurrency is useful.

## Extensibility

The Scheduler depends on the chronological mechanism rather than individual chronological Plugin types.

For example:

```text
ChronologicalTrigger
├── IntervalTrigger
├── CronTrigger       [future]
├── DailyTimeTrigger  [future]
└── OneTimeTrigger    [future]
```

Adding another chronological Plugin should not require Scheduler changes.

A fundamentally different trigger mechanism, such as a webhook, may require different Runtime infrastructure because it does not share the chronological polling and locking model.

## Current Scope

The current Scheduler supports:

- Chronological trigger processing.
- Interval-based triggers.
- Durable next-occurrence state.
- Multiple concurrent Scheduler processes.
- Deterministic catch-up.
- Atomic schedule advancement and Workflow Execution creation.
- Graceful shutdown.
- Configurable idle polling.

Intentionally deferred capabilities include:

- Cron and one-time Trigger Plugins.
- Configurable missed-run policies.
- Batch scheduling.
- Scheduling priorities.
- Separate scheduling queues.
- Scheduler leases and heartbeats.
- Distributed Scheduler locks.
- Generic trigger runtime-state frameworks.

These should be introduced only when concrete requirements justify them.

## Guiding Principle

```text
Runtime
    drives chronological processing

Application
    orchestrates occurrence processing

Plugins
    calculate schedule-specific behavior

Persistence
    stores scheduling state and provides concurrency

Execution Queue
    delivers runnable Task Executions
```

> **The Scheduler should remain a thin process loop around the chronological Application capability.**
