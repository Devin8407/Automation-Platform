# Chronological Trigger Persistence

## Purpose

`ChronologicalTriggerRepository` owns the durable scheduling state
required by chronological trigger mechanisms.

It stores **when a Trigger Definition should next be processed** and
provides the database locking needed for safe concurrent scheduling. It
does not calculate occurrences; chronological trigger plugins own that
behavior and Application coordinates it.

## Repository API

The API is intentionally narrow:

``` text
create(...)
delete(...)
get_next_due(...)
update_next_run(...)
```

Responsibilities are:

-   Creating scheduling state.
-   Deleting scheduling state.
-   Selecting and locking the earliest due trigger.
-   Updating its next scheduled occurrence.

## Definition vs. Scheduling State

Reusable trigger definition and runtime scheduling state are separate
concepts.

``` text
TriggerDefinition
├── id
├── plugin_type
├── configuration
└── enabled

ChronologicalTriggerState
├── trigger_definition_id
└── next_run_at
```

The `TriggerDefinition` describes **what the trigger is**.
`ChronologicalTriggerState.next_run_at` records **the next scheduled
occurrence that has not yet been processed**.

For example:

``` text
TriggerDefinition
    plugin_type = "interval"
    configuration =
        interval_seconds = 3600

ChronologicalTriggerState
    next_run_at = 10:00
```

After the 10:00 occurrence is processed successfully:

``` text
next_run_at = 11:00
```

The reusable Trigger Definition remains unchanged.

Chronological scheduling state has an internal SQLAlchemy model but no
corresponding core Domain object. This is intentional: durable
infrastructure state does not need a one-to-one Domain representation.

## State Lifecycle

Scheduling state is initialized when its Trigger Definition is created.

Because initialization participates in the same Unit of Work as workflow
definition creation:

``` text
WorkflowDefinition
TriggerDefinition
ChronologicalTriggerState
```

commit atomically.

A successfully persisted chronological trigger therefore has the durable
state required by the Scheduler.

If a chronological trigger has no future occurrence, its scheduling
state may later be deleted while its reusable Trigger Definition remains
persisted.

## Due-Trigger Selection

The Scheduler processes one due chronological occurrence at a time.

Persistence retrieves the earliest **enabled** chronological trigger
whose:

``` text
next_run_at <= now
```

Due state is ordered deterministically by scheduled occurrence, using
the Trigger Definition identifier as a stable secondary ordering.

The selected scheduling-state row is locked with PostgreSQL:

``` sql
FOR UPDATE SKIP LOCKED
```

The lock remains held for the surrounding transaction.

### Why `FOR UPDATE`

Without a row lock, two Schedulers could observe and process the same
due occurrence. `FOR UPDATE` gives the transaction exclusive access to
that scheduling-state row while the occurrence is processed.

### Why `SKIP LOCKED`

A Scheduler should not wait for another Scheduler's occurrence when
different due work is available.

``` text
Scheduler 1 -> locks A

Scheduler 2 -> skips locked A -> locks B

Scheduler 3 -> skips locked A and B -> locks C
```

This lets multiple Scheduler processes naturally distribute due work
without a global Scheduler lock.

## Lock Scope

The scheduling-state row remains locked while Application processes the
occurrence:

``` text
BEGIN
    │
    ├── select due state
    │       FOR UPDATE SKIP LOCKED
    │
    │       row locked
    │
    ├── calculate next occurrence
    │
    ├── update/delete scheduling state
    │
    ├── create WorkflowExecution
    │
    └── COMMIT

row lock released
```

Occurrence calculation therefore happens while the lock is held.
Chronological trigger plugins must calculate occurrences using fast,
deterministic, local, I/O-free behavior.

The lock is **not** held while arbitrary workflow tasks execute.

## Due Operation Model

A targeted result such as `DueChronologicalTrigger` can provide exactly
what Application needs:

``` text
trigger definition ID
workflow definition ID
plugin type
plugin configuration
scheduled occurrence
```

Application can process the occurrence without depending on the
chronological SQLAlchemy model or reconstructing an unnecessary
aggregate.

## Atomic Scheduling

Processing an occurrence changes two important pieces of persisted
state:

``` text
chronological scheduling state
    +
WorkflowExecution
```

Both use the same Unit of Work.

> **Schedule advancement and WorkflowExecution creation commit
> atomically.**

A committed transaction cannot leave either:

``` text
schedule advanced
but
WorkflowExecution missing
```

or:

``` text
WorkflowExecution created
but
schedule not advanced
```

## Failure Recovery

The shared transaction makes recovery straightforward.

**Trigger calculation fails**

``` text
lock occurrence
    ↓
calculation fails
    ↓
ROLLBACK
    ↓
lock released
    ↓
occurrence remains due
```

**WorkflowExecution creation fails**

``` text
lock occurrence
    ↓
advance schedule
    ↓
execution creation fails
    ↓
ROLLBACK
    ↓
schedule advancement undone
    ↓
occurrence remains due
```

**Scheduler crashes during the transaction**

``` text
open transaction
    ↓
Scheduler dies
    ↓
connection/transaction terminates
    ↓
PostgreSQL rolls back
    ↓
row lock released
    ↓
occurrence remains due
```

**Successful processing**

``` text
advance scheduling state
    +
create WorkflowExecution
    ↓
COMMIT
```

Both changes become durable together.

## Why Scheduling Does Not Use Leases

Execution queue leases are appropriate because Workers may execute
arbitrary tasks for significant periods.

Chronological scheduling performs only short transactional work:

``` text
lock row
calculate next occurrence
update scheduling state
create WorkflowExecution
commit
```

The PostgreSQL row lock acts as the temporary claim. If the Scheduler
disappears, PostgreSQL releases it by rolling back the transaction.

Chronological scheduling therefore does not require Scheduler claim
tokens, heartbeats, lease expiration, or durable Scheduler ownership.
Those remain execution-queue concepts.

## Concurrency Guarantees

Persistence guarantees that:

-   A due occurrence is locked before processing.
-   Concurrent Schedulers skip occurrences already being processed.
-   Different due occurrences can be processed concurrently.
-   Schedule advancement and WorkflowExecution creation participate in
    the same transaction.

The PostgreSQL transaction and row lock are sufficient because the
protected work is short-lived; this should not be forced into the
long-running task execution lease model.

## Queue Boundary

Chronological persistence does not enqueue workflow work directly.

The Scheduler persists the scheduling transition and resulting
`WorkflowExecution` through Persistence. Existing workflow-start
behavior remains responsible for queue interaction after the persistence
transaction commits.

This keeps chronological persistence independent of queue
implementation.

## Testing

PostgreSQL integration tests should cover:

-   Creating scheduling state.
-   Retrieving a due trigger.
-   Ignoring future triggers.
-   Deterministically selecting the earliest due trigger.
-   Updating the next occurrence.
-   Deleting scheduling state.
-   Locking selected state.
-   Skipping locked state from a concurrent transaction.
-   Allowing concurrent transactions to claim different due triggers.

Row-lock behavior must be tested against PostgreSQL rather than inferred
from mocks.

Cross-layer tests should additionally verify that chronological
definitions initialize durable scheduling state, processing advances the
schedule and creates a `WorkflowExecution` atomically, and overdue
recurring triggers advance according to the platform's catch-up
semantics.

## Evolution

Scheduling-specific features should be added only when concrete
requirements justify them.

The current design intentionally does not require Scheduler leases,
heartbeat state, claim tokens, generic trigger-state JSON, or
distributed locks.
