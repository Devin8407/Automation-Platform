# ADR-022: Transactional Chronological Trigger Processing

## Status

Accepted

## Context

Chronological triggers require the platform to identify due occurrences and start the corresponding workflows safely when:

- Multiple Scheduler processes run concurrently.
- Multiple triggers are due simultaneously.
- A Scheduler crashes during processing.
- Trigger calculation fails.
- Workflow Execution creation fails.
- Queue publication fails after Persistence commits.

Processing an occurrence requires two related durable changes:

```text
advance or remove scheduling state
        +
create WorkflowExecution
```

These changes must not commit independently.

Advancing the schedule without creating the execution would lose an occurrence.

Creating the execution without advancing the schedule could process the same occurrence again.

A concurrency and transaction model is therefore required for chronological processing.

## Decision

Chronological scheduling state is persisted separately from reusable `TriggerDefinition` data.

Conceptually:

```text
chronological_trigger_state
───────────────────────────
trigger_definition_id
next_run_at
```

This is mechanism-specific operational state rather than a core Domain object.

Each processing transaction handles at most one due occurrence.

Persistence claims that occurrence using PostgreSQL:

```sql
FOR UPDATE SKIP LOCKED
```

with due occurrences ordered deterministically.

The selected row lock acts as temporary ownership for the duration of the transaction:

```text
Scheduler A
    → locks occurrence A

Scheduler B
    → skips A
    → processes occurrence B
```

No Scheduler lease, heartbeat, claim token, leader election, or global Scheduler lock is maintained.

Processing occurs in one Unit of Work:

```text
BEGIN
    ↓
lock one due occurrence
    ↓
resolve chronological plugin
    ↓
calculate next occurrence
    ↓
advance or remove scheduling state
    ↓
create WorkflowExecution + TaskExecutions
    ↓
COMMIT
```

`ChronologicalTrigger.next_occurrence()` executes while the row remains locked.

This is acceptable because the chronological plugin contract requires that calculation to remain fast, deterministic, local, and I/O-free.

If processing fails before commit, the transaction rolls back, the row lock is released, and the occurrence remains due.

For recurring triggers, the next occurrence is calculated relative to the persisted:

```text
next_run_at
```

rather than directly from the current wall-clock time.

This preserves deterministic scheduling and allows missed occurrences to be processed through subsequent Scheduler iterations instead of silently skipped.

The Execution Queue does **not** participate in this transaction.

After Persistence commits, initially runnable Task Executions are published through the existing workflow-start path:

```text
schedule transition
        +
WorkflowExecution creation
        ↓
Persistence COMMIT
        ↓
Execution Queue publication
```

If Queue publication fails after commit, existing reconciliation detects durably runnable Task Executions and idempotently restores them to the Queue.

## Alternatives Considered

### Scheduler Leader Election

Allow only one Scheduler to process chronological work.

**Pros**

- Simple concurrency model.

**Cons**

- Requires leader-election and recovery infrastructure.
- Prevents natural horizontal Scheduler concurrency.
- Is unnecessary when PostgreSQL can safely claim independent rows.

### Renewable Scheduler Leases

Use claim tokens, timestamps, and heartbeats similarly to Worker Queue ownership.

**Pros**

- Explicit durable ownership.
- Appropriate for long-running work.

**Cons**

- Requires lease, heartbeat, expiration, and reclamation behavior.
- Chronological processing is intentionally short and transactional.
- Duplicates ownership already provided by database row locks.

### Unlocked Optimistic Processing

Read due state without locking and detect conflicts during update.

**Pros**

- Avoids holding a row lock during calculation.

**Cons**

- Allows multiple Schedulers to perform duplicate speculative work.
- Requires additional conflict handling.
- Makes occurrence processing harder to reason about.
- Provides little benefit while trigger calculation remains fast and local.

### Separate Schedule and Execution Transactions

Advance scheduling state and create the Workflow Execution independently.

**Pros**

- Smaller individual transactions.

**Cons**

- Allows one durable transition to commit without the other.
- Introduces avoidable consistency and recovery problems.

### Distributed Persistence/Queue Transaction

Make Queue publication atomic with schedule advancement and Workflow Execution creation.

**Pros**

- Eliminates the post-commit Queue publication window.

**Cons**

- Couples transaction semantics to the Queue implementation.
- Makes alternative Queue technologies harder to introduce.
- Adds distributed transaction complexity.
- Solves a failure window already recoverable through reconciliation.

### Transactional Row Locking With Post-Commit Queue Publication (Selected)

Use short-lived PostgreSQL row locks to claim occurrences, atomically persist schedule progression and Workflow Execution creation, then publish runnable work after commit.

**Pros**

- Supports concurrent Scheduler processes.
- Prevents concurrent committed processing of the same occurrence.
- Automatically releases ownership on rollback or process failure.
- Prevents partial schedule/execution commits.
- Requires no Scheduler-specific lease system.
- Preserves Execution Queue independence.
- Reuses reconciliation for post-commit Queue failures.

**Cons**

- Holds the scheduling row lock while occurrence calculation and execution creation occur.
- Requires chronological plugin calculation to remain bounded and I/O-free.
- Queue publication remains eventually consistent with Persistence.
- Catch-up of many missed occurrences may require repeated transactions.

## Consequences

### Positive

- Multiple Schedulers can safely process independent due occurrences.
- Schedule progression and Workflow Execution creation are atomic.
- Scheduler crashes before commit naturally leave the occurrence available for retry.
- No leader-election or Scheduler lease infrastructure is required.
- Chronological plugins remain independent of Persistence concurrency mechanics.
- The Execution Queue remains a separate, replaceable subsystem.
- Existing reconciliation handles the remaining Persistence-to-Queue failure window.
- Persisted-time advancement provides deterministic catch-up behavior.

### Negative

- The current implementation depends on PostgreSQL transactional row-locking semantics.
- A row lock is retained while the occurrence is calculated and its Workflow Execution is created.
- Queue publication is not atomic with Persistence.
- Large scheduling backlogs require repeated occurrence-processing transactions.

The selected design uses **database transactions for short-lived chronological ownership** while preserving the platform's existing separation between durable execution state and runnable-work delivery.
