# ADR-016: Use-Case-Oriented Application Services

## Status

Accepted

## Context

The Application Layer coordinates business operations that frequently span multiple domain objects and persistence operations.

One possible organization was to mirror domain and persistence entities with services such as:

- WorkflowDefinitionService
- WorkflowExecutionService
- TaskExecutionService

Another option was to expose one global Application facade.

However, a single business operation such as processing a task may start or resume execution, load dependency outputs, resolve a plugin, execute it, persist the outcome, update dependencies, and determine subsequent work.

Splitting that operation across entity-oriented services would fragment one cohesive business capability.

## Decision

The Application Layer will be organized around complete business use cases rather than CRUD-style entity services.

Examples include:

- Workflow definition management.
- Workflow start.
- Task processing.

Each use-case service owns the orchestration necessary to complete that capability even when the operation spans multiple domain concepts or repository operations.

There will be no global Application facade.

Runtime processes receive only the Application service objects corresponding to capabilities they require.

## Alternatives Considered

### Entity-Oriented Application Services

**Pros**

- Mirrors Domain and Persistence structure.
- Familiar organization.

**Cons**

- Splits cohesive business operations across services.
- Encourages service-to-service coordination.
- Makes orchestration harder to locate.

### Global Application Facade

**Pros**

- Single entry point.
- Simple dependency wiring initially.

**Cons**

- Accumulates unrelated capabilities.
- Gives runtimes access to operations they do not require.
- Increases coupling as the platform grows.

### Use-Case-Oriented Services (Selected)

**Pros**

- Keeps complete business operations cohesive.
- Makes orchestration easy to locate.
- Minimizes inter-service dependencies.
- Gives runtimes narrow capability-specific dependencies.
- Scales naturally as new business capabilities are introduced.

**Cons**

- Package organization does not exactly mirror Domain or Persistence.
- Some use cases legitimately touch several aggregates.

## Consequences

### Positive

- Application structure reflects platform capabilities.
- Business operations remain cohesive.
- Runtime dependencies remain narrow.
- Application services can evolve independently.

### Negative

- Developers must identify business capability boundaries rather than mechanically creating services for every entity.

The Application Layer is therefore modeled around what the platform can do rather than around the objects it stores.
