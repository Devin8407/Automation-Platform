# Chronological Trigger Capability

## Purpose

The `chronological_triggers` capability hosts time-based trigger plugins. Plugins define schedule-specific behavior; Application coordinates that behavior with durable scheduling state and workflow creation.

Its public operations are:

```text
initialize()
process_next_due()
```

The Scheduler Runtime consumes `process_next_due()` without understanding scheduling persistence, plugin resolution, workflow creation, or database concurrency.

## Architectural Role

```text
Scheduler Runtime
        |
        v
ChronologicalTriggerService
        |
        +-- Unit of Work
        +-- Chronological Persistence
        +-- TriggerRegistry
        +-- ChronologicalTrigger plugin
        |
        v
WorkflowStartService
```

The service defines how chronological plugins participate in the platform. The plugin remains responsible for defining the schedule itself.

## Chronological Plugin Contract

Chronological plugins implement:

```text
next_occurrence(configuration, after)
        ->
datetime | None
```

A `datetime` means another occurrence exists; `None` means the schedule has no future occurrence.

The calculation must be:

- Fast
- Deterministic
- Local
- I/O-free

It must not perform database, queue, network, or filesystem operations. This restriction makes it safe to calculate while durable scheduling state is locked.

### Extending Chronological Triggers

Adding another chronological trigger type should not require changes to scheduling infrastructure.

A plugin that implements `ChronologicalTrigger` participates in the existing chronological mechanism:

* Trigger initialization creates the required scheduling state.
* Persistence stores that state alongside the Trigger Definition.
* The scheduler discovers due occurrences through the same persistence boundary.
* Runtime processing resolves the plugin and calls its `next_occurrence()` implementation.
* Existing transaction, locking, catch-up, and queue-publication semantics continue to apply.

For example, a new chronological plugin such as `CronTrigger` should require plugin-specific validation and occurrence calculation, but not a separate scheduler or processing path.

This extensibility applies **within the chronological trigger mechanism**. A fundamentally different trigger mechanism—such as webhooks, message subscriptions, or external events—may require different infrastructure and should not be forced through the chronological scheduling model.

## Initialization

Initialization occurs during Workflow Definition creation. The service receives the resolved `ChronologicalTrigger`, its `TriggerDefinition`, and the caller's Unit of Work.

```text
TriggerDefinition.configuration
        |
        v
ChronologicalTrigger.next_occurrence()
        |
        v
first next_run_at
        |
        v
ChronologicalTriggerRepository.create()
```

The first occurrence is calculated relative to the current UTC time. If the plugin returns `None`, no chronological scheduling state is created; otherwise the calculated occurrence is persisted.

The service does **not** commit. Initialization participates in the Workflow Definition creation transaction.

> **A successfully created chronological Trigger Definition has the durable scheduling state required to execute it.**

If initialization fails, the complete definition-creation transaction rolls back. See [Workflow Definition Management](workflow-definitions.md) and [Trigger Initialization](trigger-initialization.md).

## Processing Due Occurrences

`process_next_due()` is the runtime-facing scheduling operation. Each invocation processes at most one due occurrence and returns:

```text
True   one occurrence was processed
False  no chronological occurrence is currently due
```

Conceptually:

```text
BEGIN UoW
    |
    +-- get earliest due chronological trigger
    |       +-- Persistence locks scheduling row
    |
    +-- resolve trigger plugin
    +-- calculate next occurrence
    +-- update or delete scheduling state
    |
    +-- WorkflowStartService.start_and_commit()
            +-- create WorkflowExecution
            +-- create TaskExecutions
            +-- COMMIT
            +-- enqueue root tasks
```

Processing one occurrence per call keeps transactions short and allows multiple Scheduler processes to divide available work naturally.

### Resolving and Advancing the Trigger

Persistence returns the information needed to process the due occurrence:

```text
trigger definition ID
workflow definition ID
plugin type
configuration
scheduled occurrence
```

Application resolves the implementation through `TriggerRegistry`. It is expected to satisfy `ChronologicalTrigger` because chronological state is created only for plugins belonging to that mechanism.

The service calls:

```text
next_occurrence(
    configuration,
    persisted_next_run_at,
)
```

The persisted scheduled occurrence—not current wall-clock time—is deliberately used as `after`.

If another `datetime` is returned, scheduling state advances to it. If `None` is returned, chronological scheduling state is deleted while the reusable `TriggerDefinition` remains persisted. This allows finite schedules, such as a future one-time trigger, to finish without deleting their reusable definition.

## Catch-Up Behavior

Recurring schedules advance relative to the persisted occurrence, so missed runs are processed deterministically rather than silently skipped.

For example:

```text
interval:      1 hour
next_run_at:   09:00
current time:  11:30
```

Processing advances as follows:

```text
09:00 -> 10:00
10:00 -> 11:00
11:00 -> 12:00
```

At `12:00` the schedule is finally ahead of current time. Subsequent Scheduler iterations perform the catch-up because each invocation processes only one occurrence.

Alternative missed-run policies can be introduced later if a concrete requirement justifies them.

## Scheduling Concurrency

Multiple Scheduler processes are supported. Persistence selects due scheduling state using PostgreSQL:

```sql
FOR UPDATE SKIP LOCKED
```

Application neither implements this SQL nor manipulates row locks directly.

```text
Scheduler A
    |
    +-- process_next_due()
            +-- locks Trigger A

Scheduler B
    |
    +-- process_next_due()
            +-- skips A
            +-- locks Trigger B
```

Persistence therefore distributes due occurrences between concurrent Scheduler transactions without Application-level locking.

### Why Scheduling Uses Transaction Locks, Not Leases

Task execution uses renewable queue leases because plugins may run for significant periods and Workers may fail during that work. Chronological processing is short:

```text
lock occurrence
        |
calculate next occurrence
        |
advance/delete state
        |
create WorkflowExecution
        |
commit
```

The PostgreSQL transaction lock acts as the temporary scheduling claim. If the Scheduler dies, PostgreSQL rolls back the transaction, releases the row lock, and leaves the occurrence due.

No Scheduler claim token, heartbeat, renewable lease, leader election, or global mutex is required.

## Atomic Scheduling Guarantee

The scheduling row remains locked while Application resolves the plugin, calculates the next occurrence, advances/removes scheduling state, creates the Workflow Execution, and commits.

> **Schedule advancement and WorkflowExecution creation are committed atomically for a chronological occurrence.**

The transaction cannot commit either of these partial states:

```text
schedule advanced
but
WorkflowExecution missing
```

```text
WorkflowExecution created
but
schedule not advanced
```

Combined with `FOR UPDATE SKIP LOCKED`, this provides the intended concurrency property:

> **For a persisted chronological occurrence, at most one committed WorkflowExecution is created through concurrent Scheduler processing, and the schedule transition commits atomically with that execution creation.**

`WorkflowStartService.start_and_commit()` performs the terminal commit on the shared Unit of Work. See [Workflow Start](workflow-start.md#start_and_commitworkflow_definition_id-uow) for workflow-start and queue-publication semantics.

Queue publication remains outside this persistence atomicity boundary by design.

## Failure Behavior

All pre-commit failures preserve the due occurrence through transaction rollback:

| Failure | Result |
| --- | --- |
| `next_occurrence()` raises | Transaction rolls back; occurrence remains due. |
| Workflow creation fails after schedule advancement | Transaction rolls back; schedule advancement is undone. |
| Scheduler crashes before commit | PostgreSQL rolls back, releases the lock, and the occurrence remains due. |

These semantics follow from the database transaction and require no separate scheduling-ownership recovery protocol.

## Queue Boundary

Schedule advancement and Workflow Execution creation commit together; initial task publication happens afterward:

```text
schedule advancement
        +
WorkflowExecution creation
        |
        v
COMMIT
        |
        v
enqueue root tasks
```

The queue intentionally does not participate in the Persistence Unit of Work. A crash after commit but before enqueue can temporarily strand runnable work. The existing Reconciler repairs that state through idempotent queue publication.

Chronological scheduling does not bypass the queue abstraction merely because the current queue implementation also uses PostgreSQL.

## Scheduler Interaction

The Scheduler runtime remains deliberately small:

```text
while running:
    processed = chronological_trigger_service.process_next_due()

    if processed:
        immediately check again
    else:
        wait poll_interval
```

It drains currently due work without sleeping between successful occurrences and waits only when none is due.

The Scheduler does not know about `TriggerDefinition`, `ChronologicalTriggerState`, `TriggerRegistry`, `UnitOfWork`, repositories, `WorkflowExecution`, or PostgreSQL row locks. Those concerns stay behind Application and Persistence boundaries.

## Key Invariants

- `next_occurrence()` is fast, deterministic, local, and I/O-free.
- Initialization uses the caller's Unit of Work and does not commit.
- A finite schedule removes chronological state without deleting its Trigger Definition.
- Schedule advancement is relative to the persisted occurrence, providing deterministic catch-up.
- One invocation processes at most one due occurrence.
- Concurrent Scheduler processes divide work through persistence row locking.
- Schedule transition and Workflow Execution creation commit atomically.
- Queue publication occurs after commit and is recoverable through reconciliation.

## Deliberately Deferred Complexity

The chronological trigger design intentionally avoids infrastructure that is not currently required.

Examples include:

* Scheduler leases
* Leader election
* Distributed locking outside the database transaction model
* Batch scheduling
* Separate scheduling services
* Configurable missed-run policies
* More elaborate catch-up strategies

These are not assumed requirements of the current architecture.

They should be introduced only when concrete operational requirements justify the additional complexity. Until then, database transaction locks, deterministic occurrence calculation, and the existing catch-up behavior define the scheduling model.

## Testing Strategy

Important Application-level scenarios include:

- Initialization creates scheduling state for a returned first occurrence and creates none when the plugin returns `None`.
- Initialization uses the caller's Unit of Work and does not commit it.
- Due processing resolves the correct plugin and passes the persisted occurrence to `next_occurrence()`.
- A returned occurrence advances state; `None` removes scheduling state but preserves the Trigger Definition.
- Catch-up advances one persisted occurrence at a time.
- `process_next_due()` returns `False` when nothing is due and processes at most one occurrence per call.
- Trigger calculation and workflow-creation failures roll back scheduling changes.
- Workflow creation uses the same Unit of Work so schedule advancement and execution creation commit together.
- Queue publication occurs only after commit and can be recovered by reconciliation.

Persistence integration tests own PostgreSQL locking behavior, including `FOR UPDATE SKIP LOCKED`, and concurrent transaction correctness. Scheduler tests own polling and drain-loop behavior.
