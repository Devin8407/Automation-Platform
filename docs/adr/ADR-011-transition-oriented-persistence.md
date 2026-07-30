# ADR-008: Transition-Oriented Persistence

## Status

Accepted

---

## Context

Workflow executions evolve through well-defined lifecycle transitions rather than arbitrary modifications to an object graph.

The original persistence design loaded a WorkflowExecution aggregate, allowed arbitrary modifications, and persisted the resulting object graph using a generic save operation.

This approach couples persistence to object synchronization and makes it difficult to enforce execution invariants during concurrent task execution.

A decision was required regarding whether repositories should expose generic CRUD operations or explicit workflow state transitions.

---

## Decision

Workflow execution repositories expose explicit lifecycle transitions.

Current transitions include:

- create()
- load()
- start_task()
- complete_task()
- retry_task()

Future transitions may include:

- cancel_workflow_execution()

Each transition owns:

- persistence correctness
- concurrency validation
- atomic SQL state changes

Application services orchestrate transitions but never perform state modifications directly.

---

## Alternatives Considered

### Generic Aggregate Save

**Pros**

- Simple repository interface.
- Familiar CRUD semantics.
- Minimal repository methods.

**Cons**

- Difficult to enforce workflow invariants.
- Encourages blind object synchronization.
- Poor concurrency characteristics.
- Business transitions become implicit.

---

### Transition-Oriented Persistence (Selected)

**Pros**

- Explicit workflow lifecycle.
- Concurrency rules localized within persistence.
- Easier to reason about correctness.
- Repository methods correspond to business transitions.

**Cons**

- More repository methods.
- Additional implementation complexity.

---

## Consequences

### Positive

- Persistence becomes responsible for enforcing execution invariants.
- Business transitions become explicit.
- Runtime concurrency becomes easier to reason about.
- Generic aggregate synchronization is eliminated.
- Repository methods correspond directly to workflow lifecycle transitions.
- Concurrency correctness becomes localized within persistence.
- Application services remain free of SQL-level concurrency concerns.

### Negative

- Repository interfaces grow as workflow lifecycle expands.
- New transitions require dedicated repository methods.

Workflow executions are treated as state machines rather than mutable object graphs, resulting in stronger concurrency guarantees and clearer persistence semantics.
