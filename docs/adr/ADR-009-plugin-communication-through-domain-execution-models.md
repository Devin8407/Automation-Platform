# ADR-006: Plugin Communication Through Domain Execution Models

## Status

Accepted

## Context

Task plugins require configuration and data produced by previously completed tasks.

A decision was required regarding how plugins should receive execution information and communicate execution results.

One option was to allow plugins to directly access persistence, queue infrastructure, or application services.

Another option was to provide plugins with all required execution information through domain execution models and require plugins to return execution results to the Application Layer.

## Decision

Task plugins will receive all execution information through a TaskContext domain object.

Task plugins will communicate execution outcomes exclusively through a TaskResult domain object.

The Application Layer is responsible for constructing TaskContext, invoking plugins, interpreting TaskResult, and updating workflow execution state.

Plugins do not directly access persistence, queues, workflow execution state, or orchestration services.

## Alternatives Considered

### Plugins Access Infrastructure Directly

**Pros**

- Plugins can retrieve additional information as needed.
- Less orchestration required by the Application Layer.

**Cons**

- Couples plugins to infrastructure.
- Harder to test independently.
- Blurs architectural boundaries.
- Makes plugin implementations less reusable.

### Domain Execution Models (Selected)

**Pros**

- Plugins remain infrastructure-independent.
- Clear separation between execution behavior and orchestration.
- Improved testability.
- Consistent execution contract.
- Easier future extension of execution context.

**Cons**

- Application Layer performs additional orchestration.
- Execution models may evolve as new plugin requirements emerge.

## Consequences

### Positive

- Plugins become deterministic units of executable behavior.
- Infrastructure concerns remain outside plugin implementations.
- Workflow orchestration remains centralized.
- Future plugin categories can adopt the same execution model.

### Negative

- Additional domain objects are required.
- Application services construct execution context before plugin invocation.

Separating plugin execution from infrastructure preserves clean architectural boundaries while providing a consistent execution model for extensible workflow behavior.
