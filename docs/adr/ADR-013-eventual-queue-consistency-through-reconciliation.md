# ADR-013: Eventual Queue Consistency Through Reconciliation

## Status

Accepted

---

## Context

Completing a task requires updating persistence and then updating the queue.

These operations belong to separate infrastructure components and therefore execute in separate transactions.

A process crash between persistence commit and queue update creates a narrow failure window in which newly runnable tasks are not immediately enqueued.

Several approaches were considered to eliminate this dual-write problem.

---

## Decision

The architecture accepts the remaining dual-write window and repairs it through periodic reconciliation.

A reconciliation scheduler periodically identifies tasks that are:

- Pending
- Have zero remaining dependencies
- Are not currently executing

Any missing runnable tasks are re-enqueued.

Normal execution does not depend upon reconciliation.

The reconciliation process exists solely to repair the persistence-to-queue failure window.

---

## Alternatives Considered

### Ready-To-Queue State

**Pros**

- Explicit durable handoff.
- Scheduler can enqueue Ready-To-Queue tasks.

**Cons**

- Duplicates queue state.
- Complicates task lifecycle.
- Does not eliminate dual-write.

---

### Transactional Outbox

**Pros**

- Eliminates dual-write problem.
- Production-standard pattern.
- Strong delivery guarantees.

**Cons**

- Additional subsystem.
- Dispatcher required.
- Increased implementation complexity.

---

### Periodic Reconciliation (Selected)

**Pros**

- Simple implementation.
- Small operational footprint.
- Queue abstraction remains unchanged.
- Easy future migration to an Outbox.

**Cons**

- Temporary delay before missing work is recovered.
- Eventual rather than immediate consistency.

---

## Consequences

### Positive

- Architecture remains simple.
- Dual-write failures are automatically repaired.
- Queue and persistence remain cleanly separated.
- Future Outbox implementation remains possible without changing higher layers.

### Negative

- Recovery is not instantaneous.
- Additional scheduler process is required.

The architecture intentionally favors simplicity during Phase 1 while ensuring correctness through deterministic reconciliation rather than stronger transactional guarantees.
