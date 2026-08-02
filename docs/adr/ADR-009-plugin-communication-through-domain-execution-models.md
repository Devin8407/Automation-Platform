# ADR-009: Plugin Communication Through Domain Execution Models

## Status

Accepted

## Context

Task plugins require configuration and data produced by previously completed tasks.

Plugins must also communicate execution outcomes back to the workflow engine.

A decision was required regarding whether plugins should directly interact with platform infrastructure and workflow state or communicate through an explicit execution contract.

Plugin-specific configuration may vary substantially between implementations, making it undesirable for the Application Layer to understand each plugin's configuration schema.

## Decision

Task plugins will receive execution information through a TaskContext domain object and communicate expected execution outcomes through a TaskResult domain object.

The Application Layer is responsible for:

- Constructing TaskContext.
- Resolving the configured plugin implementation.
- Invoking the plugin.
- Interpreting TaskResult.
- Requesting the appropriate persistence transition.

TaskContext contains the execution information intentionally exposed to the plugin, including:

- Plugin configuration.
- Outputs from dependency tasks keyed by stable task key.

TaskResult communicates the plugin's expected execution outcome and output.

Expected task-level failures are represented through TaskResult rather than workflow-engine status values.

Unexpected programming or infrastructure exceptions propagate as exceptions and are not automatically interpreted as configured task failures.

Plugin-specific configuration validation belongs to the plugin implementation because the plugin owns the meaning and schema of its configuration.

Plugins do not directly access:

- Workflow persistence.
- Execution queues.
- Workflow orchestration services.
- Mutable workflow execution state.

Plugins may perform the external side effects inherent to their configured behavior, but platform orchestration remains outside the plugin.

## Alternatives Considered

### Plugins Access Platform Infrastructure Directly

**Pros**

- Plugins can retrieve or mutate additional platform information as needed.
- Less context construction required by Application.

**Cons**

- Couples plugins to infrastructure.
- Blurs workflow orchestration boundaries.
- Makes plugins harder to test.
- Makes execution behavior dependent on platform internals.

### Application Understands Plugin Configuration Schemas

**Pros**

- Centralized validation.

**Cons**

- Couples Application to every concrete plugin type.
- Requires Application changes whenever plugin configuration evolves.
- Violates the plugin abstraction.

### Domain Execution Models (Selected)

Plugins receive explicit execution context and return explicit execution results.

**Pros**

- Plugins remain independent of workflow infrastructure.
- Execution contracts are explicit.
- Application retains orchestration responsibility.
- Plugins can be tested independently.
- Plugin configuration schemas remain plugin-owned.
- Execution context can evolve without exposing persistence internals.

**Cons**

- Requires additional domain execution models.
- Application must construct execution context.
- Context/result contracts must evolve carefully as plugin requirements grow.

## Consequences

### Positive

- Plugin execution has a narrow, explicit boundary.
- Workflow infrastructure remains outside plugin implementations.
- Application centrally interprets plugin outcomes.
- Plugin-specific validation remains colocated with plugin behavior.
- Expected failures and unexpected exceptions have distinct semantics.
- Future plugin implementations can evolve without teaching Application their internal configuration schemas.

### Negative

- Additional execution models are required.
- Application performs context construction before every plugin invocation.
- Plugins performing non-idempotent external side effects must account for the platform's at-least-once physical execution semantics.

Separating plugin behavior from platform orchestration preserves clean architectural boundaries while providing plugins with the information required to perform meaningful work.
