# Scheduler

## Overview

The Scheduler is the runtime responsible for starting workflows in response to **chronological triggers**.

A chronological trigger represents a trigger whose workflow activation is determined by time. Examples include interval-based schedules and, potentially in the future, cron expressions or one-time schedules.

The Scheduler itself contains very little scheduling logic. It repeatedly asks the Application Layer to process the next due chronological trigger.

```text
Scheduler Runtime
       │
       │ process_next_due()
       ▼
ChronologicalTriggerService
       │
       ├── find and lock next due trigger
       ├── calculate its next occurrence
       ├── advance its scheduling state
       └── start its workflow
```

This keeps the runtime focused on process lifecycle while scheduling behavior remains in the Application, Plugin, and Persistence layers.

---

## Responsibilities

Scheduling behavior is divided across four parts of the platform.

### Scheduler Runtime

The Scheduler runtime is responsible for:

- running the scheduler process
- repeatedly requesting chronological work from the Application Layer
- waiting when no work is available
- handling graceful shutdown
- logging runtime failures

It does not understand trigger definitions, plugins, database locking, or workflow execution creation.

### Application Layer

`ChronologicalTriggerService` coordinates chronological scheduling.

It is responsible for:

- initializing durable state for chronological triggers
- retrieving the next due occurrence through Persistence
- resolving the appropriate trigger plugin
- asking the plugin to calculate its next occurrence
- advancing or removing scheduling state
- starting the associated workflow
- coordinating these changes within one transaction

Trigger initialization during workflow definition creation is dispatched according to the trigger's mechanism interface.

### Trigger Plugins

Chronological trigger plugins define schedule-specific behavior.

For example, `IntervalTrigger` knows how to calculate:

```text
scheduled occurrence + interval → next occurrence
```

Plugins do not access Persistence, the execution queue, or Application services.

### Persistence Layer

Persistence owns durable chronological state and database concurrency.

It is responsible for:

- storing the next scheduled occurrence
- selecting the earliest due trigger
- locking due state
- skipping state already being processed by another Scheduler
- advancing scheduling state
- deleting exhausted scheduling state

---

# Chronological Trigger Model

Chronological triggers are represented through the trigger plugin type hierarchy.

```text
Trigger
   │
   └── ChronologicalTrigger
           │
           └── IntervalTrigger
```

`ChronologicalTrigger` defines the behavior shared by trigger plugins that can use the Scheduler infrastructure.

Conceptually:

```python
next_occurrence(
    configuration,
    after,
) -> datetime | None
```

A plugin returns the first occurrence after the supplied scheduled time.

Returning `None` means that the trigger has no future occurrence.

The Scheduler does not need to know whether it is processing an interval, cron expression, one-time schedule, or another chronological implementation. All such plugins share the same chronological contract.

---

# Trigger Definitions and Scheduling State

A trigger's reusable definition and its runtime scheduling state are stored separately.

A trigger definition contains information such as:

```text
TriggerDefinition
├── id
├── plugin_type
├── configuration
└── enabled
```

For an interval trigger:

```text
plugin_type = "interval"

configuration =
{
    "interval_seconds": 60
}
```

The definition describes **what the trigger is**.

Chronological scheduling state separately records **where that trigger currently is in its schedule**:

```text
ChronologicalTriggerState
├── trigger_definition_id
└── next_run_at
```

For example:

```text
TriggerDefinition
    plugin_type = "interval"
    interval_seconds = 3600

ChronologicalTriggerState
    next_run_at = 10:00
```

The trigger definition remains reusable configuration. `next_run_at` changes as occurrences are processed.

---

# Initialization

Chronological scheduling state is created when its workflow definition is created.

The definition creation flow is:

```text
WorkflowDefinitionService
        │
        ├── validate trigger configuration
        │
        ├── resolve trigger plugin
        │
        ├── save workflow definition
        │
        ├── save trigger definitions
        │
        ├── flush definitions
        │
        ▼
TriggerInitializationService
        │
        │ identifies ChronologicalTrigger
        ▼
ChronologicalTriggerService.initialize()
        │
        ├── calculate first occurrence
        └── create chronological state
        │
        ▼
      COMMIT
```

Initialization uses the same Unit of Work as workflow definition creation.

The flush makes the persisted trigger definitions available for the chronological state's foreign key without committing the transaction.

A flush is not a commit. If initialization fails afterward, the entire transaction is still rolled back.

This establishes the invariant:

> A successfully created chronological trigger definition has the durable scheduling state required to run it.

No Scheduler reconciliation process is required to discover and initialize missing state.

---

# Processing a Due Trigger

The Scheduler repeatedly invokes:

```python
ChronologicalTriggerService.process_next_due()
```

Each call processes at most one chronological occurrence.

Conceptually:

```text
BEGIN TRANSACTION
        │
        ▼
find earliest due trigger
        │
        │ FOR UPDATE SKIP LOCKED
        ▼
lock chronological state
        │
        ▼
resolve trigger plugin
        │
        ▼
calculate next occurrence
        │
        ├── future occurrence exists
        │       ↓
        │   update next_run_at
        │
        └── no future occurrence
                ↓
            delete runtime state
        │
        ▼
start workflow execution
        │
        ▼
COMMIT
        │
        ▼
release row lock
```

`process_next_due()` returns:

```text
True  → one occurrence was processed
False → no occurrence is currently due
```

---

# Scheduler Loop

Because one Application call processes one occurrence, the Scheduler runtime can remain very small.

Conceptually:

```python
while running:
    processed = chronological_trigger_service.process_next_due()

    if not processed:
        wait(poll_interval)
```

When an occurrence is processed successfully, the Scheduler immediately checks for more work.

It only waits when no trigger is currently due.

This allows a Scheduler to naturally drain overdue work:

```text
process occurrence → True
process occurrence → True
process occurrence → True
nothing due       → False
wait
```

The polling interval therefore controls idle scheduling latency rather than limiting scheduling throughput.

---

# Concurrency

The platform supports multiple Scheduler processes.

For example:

```text
Scheduler A ─┐
Scheduler B ─┼──> PostgreSQL
Scheduler C ─┘
```

Chronological trigger state is selected using:

```sql
FOR UPDATE SKIP LOCKED
```

Suppose three triggers are due:

```text
A
B
C
```

Concurrent Scheduler transactions can behave like:

```text
Scheduler 1 → locks A

Scheduler 2 → A is locked
              skips A
              locks B

Scheduler 3 → A and B are locked
              skips both
              locks C
```

Schedulers therefore distribute available work without requiring a global Scheduler lock.

---

# Why Row Locks Are Used

A normal query such as:

```text
SELECT earliest due trigger
LIMIT 1
```

could allow several Scheduler processes to select the same occurrence before any of them updates it.

Locking the selected chronological state prevents another Scheduler from processing that occurrence concurrently.

`SKIP LOCKED` also prevents other Scheduler processes from unnecessarily waiting for that row. They can immediately look for another due occurrence.

The row lock therefore acts as the Scheduler's temporary claim on an occurrence.

---

# Why the Scheduler Does Not Use Leases

Task workers use durable claims, heartbeats, and lease expiration because arbitrary task execution may take a long time.

Chronological scheduling is different.

Processing an occurrence consists only of:

```text
lock state
calculate next occurrence
update state
create WorkflowExecution
commit
```

The trigger calculation is deliberately required to be fast, deterministic, local, and free of I/O.

The database transaction is therefore short-lived.

If a Scheduler process crashes while holding the row:

```text
Scheduler crashes
      ↓
transaction terminates
      ↓
PostgreSQL rolls back
      ↓
row lock is released
      ↓
another Scheduler can process it
```

There is no need for:

- Scheduler IDs
- claim tokens
- heartbeats
- lease expiration
- distributed Scheduler locks

---

# Atomicity

Schedule advancement and workflow execution creation occur in the same Persistence Unit of Work.

This is one of the central guarantees of the Scheduler design.

```text
BEGIN
   │
   ├── lock due occurrence
   ├── calculate next occurrence
   ├── advance scheduling state
   └── create WorkflowExecution
   │
COMMIT
```

Therefore the database cannot commit:

```text
schedule advanced
but
WorkflowExecution missing
```

or:

```text
WorkflowExecution created
but
schedule not advanced
```

If either operation fails, both are rolled back.

---

# Failure Behavior

The transaction design provides straightforward recovery from Scheduler failures.

### Trigger calculation fails

```text
lock occurrence
      ↓
next_occurrence() fails
      ↓
ROLLBACK
      ↓
occurrence remains due
```

The Scheduler runtime logs the failure and waits before trying again, preventing a permanently failing occurrence from causing a tight retry loop.

### Workflow start fails

```text
lock occurrence
      ↓
advance schedule
      ↓
workflow start fails
      ↓
ROLLBACK
      ↓
schedule advancement is undone
```

The occurrence remains available for another attempt.

### Scheduler crashes

```text
open transaction
      ↓
Scheduler crashes
      ↓
transaction rolls back
      ↓
lock released
      ↓
occurrence remains due
```

### Successful processing

```text
advance schedule
      +
create WorkflowExecution
      ↓
COMMIT
```

Both changes become durable together.

---

# Execution Queue Boundary

Creating a `WorkflowExecution` and enqueueing its initially runnable tasks are separate concerns.

The execution queue deliberately exists outside the Persistence Unit of Work so that the queue implementation remains replaceable.

The Scheduler therefore does not directly interact with the queue.

Instead, it reuses the existing workflow-start capability:

```text
ChronologicalTriggerService
        ↓
WorkflowStartService
        ↓
persist WorkflowExecution
        ↓
commit scheduling transaction
        ↓
enqueue initial runnable tasks
```

The existing persistence-to-queue reliability strategy remains responsible for repairing missing queue entries.

The Scheduler does not bypass or duplicate that architecture.

---

# Catch-Up Behavior

Recurring triggers advance relative to their **persisted scheduled occurrence**, not the current wall-clock time.

Suppose:

```text
interval    = 1 hour
next_run_at = 09:00
current time = 11:30
```

Processing the trigger calculates:

```text
09:00 → 10:00
```

It does not skip directly to 12:00.

Because 10:00 is still due, the Scheduler immediately processes another occurrence:

```text
09:00 → 10:00
10:00 → 11:00
11:00 → 12:00
```

Once `next_run_at` becomes 12:00, the trigger is no longer due and normal scheduling continues.

This provides deterministic catch-up behavior and ensures persisted occurrences are not silently skipped.

---

# Finite Chronological Triggers

The chronological interface allows:

```python
next_occurrence(...) -> datetime | None
```

`None` indicates that no occurrence exists after the one currently being processed.

When this happens, the Scheduler deletes only the trigger's **chronological runtime state**.

```text
TriggerDefinition
    remains persisted

ChronologicalTriggerState
    deleted
```

The trigger definition describes the workflow configuration and should not disappear simply because its schedule has completed.

Deleting the workflow definition remains responsible for deleting its trigger definitions and any associated runtime state.

This behavior allows future finite plugins such as a `OneTimeTrigger` without requiring Scheduler changes.

---

# Extending Chronological Scheduling

New chronological trigger plugins use the existing Scheduler infrastructure by implementing `ChronologicalTrigger`.

For example:

```text
ChronologicalTrigger
├── IntervalTrigger
├── CronTrigger
├── DailyTimeTrigger
└── OneTimeTrigger
```

Adding one of these should require implementing its plugin behavior, not modifying:

- Scheduler runtime
- chronological Application orchestration
- chronological Persistence
- workflow-start behavior

The class hierarchy identifies the trigger mechanism, so no separate trigger-mechanism enum or persisted mechanism field is required.

A fundamentally different mechanism, such as a webhook, may require its own Application/runtime infrastructure because it does not share the chronological scheduling contract.

---

# Architectural Boundaries

The Scheduler feature intentionally maintains the following boundaries:

```text
Runtime
    drives the scheduling loop

Application
    orchestrates chronological activation

Plugins
    implement schedule-specific behavior

Persistence
    stores state and provides concurrency

Execution Queue
    handles runnable task delivery
```

In particular:

> The Scheduler runtime does not perform scheduling business logic.

and:

> Trigger plugins do not perform infrastructure operations.

and:

> Persistence provides locking but does not decide what an occurrence means or when a workflow should start.

These boundaries allow each part of the system to evolve independently while keeping the scheduling path straightforward.

---

# Current Scope

The initial Scheduler supports:

- chronological trigger infrastructure
- interval-based triggers
- durable next-occurrence state
- multiple concurrent Scheduler processes
- deterministic catch-up
- atomic schedule advancement and workflow creation
- graceful Scheduler shutdown
- configurable idle polling

The following features are intentionally deferred until they are needed:

- cron triggers
- one-time triggers
- configurable missed-run policies
- batch scheduling
- Scheduler leases or heartbeats
- scheduling priorities
- separate scheduling queues
- distributed locks
- generic trigger runtime-state frameworks

The current design focuses on providing one complete, reliable chronological scheduling path while leaving room for additional chronological plugins to use the same infrastructure.
