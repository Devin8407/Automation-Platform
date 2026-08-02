# ADR-018: Trigger-Specific Runtime Mechanisms

## Status

Accepted

## Context

Workflow definitions may contain multiple trigger types, including:

- Manual triggers.
- Chronological/scheduled triggers.
- Webhook triggers.
- Future event-driven triggers.

An initial design considered a universal trigger-evaluation runtime that would periodically evaluate every trigger through a common readiness operation.

However, trigger activation mechanisms are fundamentally different.

A scheduled trigger naturally depends on time.

A webhook trigger reacts to an incoming HTTP event.

A manual trigger reacts directly to an explicit request.

Future event triggers may consume messages or external events.

Forcing all trigger categories through one polling/evaluation mechanism would introduce an artificial abstraction.

## Decision

Trigger types may use trigger-specific runtime mechanisms.

Examples include:

- Chronological triggers → Scheduler runtime.
- Webhook triggers → HTTP/Webhook runtime.
- Manual triggers → API runtime.
- Event triggers → Event-specific consumer/runtime.

Trigger detection is therefore heterogeneous.

Once a runtime determines that a workflow should begin, workflow starting is homogeneous and is delegated to the shared WorkflowStartService.

Generic TriggerDefinition objects remain persisted and contain common declarative information such as:

- Plugin type.
- Configuration.
- Enabled state.

Trigger-specific durable state may be modeled separately when required rather than adding type-specific fields to every TriggerDefinition.

Trigger plugin interfaces are not required to expose one universal polling-oriented `is_ready()` contract if that contract does not fit their activation mechanism.

## Alternatives Considered

### Universal Trigger Evaluator

Every trigger is periodically evaluated through a common readiness interface.

**Pros**

- One runtime mechanism.
- Uniform conceptual model.

**Cons**

- Poor fit for webhook and manual triggers.
- Encourages polling for inherently event-driven mechanisms.
- Forces unrelated trigger state into a common model.
- Creates artificial abstractions.

### Trigger-Specific Runtime Mechanisms (Selected)

Each trigger category uses an appropriate activation mechanism while sharing common workflow-start orchestration.

**Pros**

- Runtime behavior matches trigger semantics.
- Event-driven triggers remain event-driven.
- Scheduled triggers can use scheduler-specific state.
- Generic workflow-start logic remains reusable.
- Avoids forcing trigger-specific state into generic definitions.

**Cons**

- Multiple runtime mechanisms may exist.
- Trigger categories may require category-specific infrastructure.

## Consequences

### Positive

- Trigger detection mechanisms remain natural to their event source.
- Workflow starting has one shared implementation.
- Generic TriggerDefinition remains useful without dictating runtime behavior.
- Future trigger types can introduce appropriate runtime mechanisms.

### Negative

- There is no single universal trigger execution loop.
- Trigger-specific state and infrastructure may need separate implementations.

The architecture therefore treats trigger detection as heterogeneous while treating workflow starting as a common business capability.
