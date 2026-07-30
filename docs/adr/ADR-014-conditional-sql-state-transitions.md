# ADR-011: Conditional SQL State Transitions

## Status

Accepted

---

## Context

Workflow executions are processed concurrently by multiple workers.

A traditional read-modify-write approach loads execution state into memory, modifies domain objects, and later persists those changes.

Under concurrent execution this approach introduces stale reads, lost updates, and duplicate state transitions unless additional locking or optimistic concurrency mechanisms are introduced.

A decision was required regarding where concurrency validation should occur.

---

## Decision

Workflow execution state transitions will be implemented using conditional SQL updates.

Each repository transition performs its concurrency validation within the database.

Typical transitions include conditions such as:

- Pending → Running
- Running → Completed
- Running → Pending
- Running → Failed

Transitions only succeed when the current persisted state matches the expected lifecycle state.

Repository methods return whether the transition succeeded rather than relying on application-level locking or optimistic version checks.

---

## Alternatives Considered

### Read-Modify-Write

**Pros**

- Natural object-oriented workflow.
- Familiar repository implementation.

**Cons**

- Lost update races.
- Requires additional concurrency mechanisms.
- Stale workers may overwrite newer state.
- Difficult to reason about correctness.

---

### Optimistic Version Numbers

**Pros**

- Detects conflicting updates.
- Widely understood.

**Cons**

- Additional version management.
- Independent task completions unnecessarily conflict.
- Does not simplify workflow transition logic.

---

### Conditional SQL Transitions (Selected)

**Pros**

- Concurrency validation occurs atomically.
- No stale object overwrites.
- No additional locking mechanism required.
- Maps naturally to workflow lifecycle transitions.

**Cons**

- Repository implementation becomes more SQL-oriented.
- Transition methods require carefully designed update statements.

---

## Consequences

### Positive

- Concurrency correctness is enforced by the database.
- Application services remain free of concurrency logic.
- Repository transitions become naturally idempotent.
- Independent tasks execute concurrently without workflow-level locking.

### Negative

- Repository implementation relies more heavily on SQL capabilities such as conditional updates and RETURNING clauses.
- Transition logic is less generic than CRUD repositories.

The architecture intentionally delegates concurrency control to atomic conditional SQL transitions rather than application-level synchronization.
