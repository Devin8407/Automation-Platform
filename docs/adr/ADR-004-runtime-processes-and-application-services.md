# ADR-004: Runtime Processes and Application Services

## Status

Accepted

## Context

The Automation Platform is composed of multiple runtime processes, including an API server, background workers, and a scheduler.

A decision was required regarding where business logic should reside.

One option was to allow each runtime process to implement its own orchestration logic.

Another option was to centralize workflow orchestration within a shared application layer that all runtime processes invoke.

## Decision

Runtime processes will remain thin and will contain only process-specific responsibilities such as receiving HTTP requests, polling queues, or evaluating trigger conditions.

Business logic and workflow orchestration will reside exclusively within the Application Layer.

Each runtime process invokes shared application services rather than implementing orchestration independently.

This establishes a clear separation between runtime concerns and business capabilities.

## Alternatives Considered

### Runtime-Specific Business Logic

**Pros**

- Simple to begin implementing
- Minimal initial abstraction

**Cons**

- Business logic becomes duplicated
- Difficult to maintain consistent behavior
- Harder to test independently
- Adding new runtime processes requires duplicating orchestration

### Shared Application Layer (Selected)

**Pros**

- Single implementation of workflow orchestration
- Consistent behavior across all runtime processes
- Improved testability
- Easier future expansion to additional runtimes
- Clear separation of responsibilities

**Cons**

- Additional architectural abstraction
- Requires careful definition of application boundaries

## Consequences

### Positive

- Runtime processes remain simple and focused
- Business logic is reusable across API, workers, schedulers, and future runtimes
- Improves maintainability and testing
- Reinforces dependency inversion

### Negative

- Requires additional coordination when defining application services
- Introduces another architectural layer to understand

Separating runtime processes from application services produces a more maintainable architecture while allowing new entry points to reuse existing business capabilities.
