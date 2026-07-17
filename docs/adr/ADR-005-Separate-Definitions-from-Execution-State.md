# ADR-005: Separate Definitions from Execution State

## Status

Accepted

## Context

A workflow may execute many times throughout its lifetime.

The platform must preserve execution history while allowing workflow definitions to be reused without modification.

A decision was required regarding whether workflow execution state should be stored directly within workflow definitions or represented independently.

## Decision

Workflow definitions will remain immutable after creation.

Each workflow execution will create independent runtime state while referencing the original workflow definition.

Workflow definitions describe what should happen.

Workflow executions describe what is currently happening.

## Alternatives Considered

### Mutable Workflow Definitions

**Pros**

- Simpler conceptual model
- Fewer runtime objects

**Cons**

- Prevents concurrent executions
- Makes execution history difficult
- Couples runtime state to reusable definitions
- Complicates retries and workflow versioning

### Immutable Workflow Definitions (Selected)

**Pros**

- Supports multiple concurrent executions
- Preserves complete execution history
- Clean separation of definition and runtime state
- Enables future workflow versioning

**Cons**

- Additional runtime objects
- Slightly more complex persistence model

## Consequences

### Positive

- Workflow definitions remain reusable
- Runtime state is isolated to individual executions
- Future features such as retries, auditing, and versioning become easier
- Better separation of concerns

### Negative

- Additional database records are created for each execution
- Requires managing both definition and execution models

Separating workflow definitions from workflow executions establishes a clean execution model while supporting repeated execution and future extensibility.
