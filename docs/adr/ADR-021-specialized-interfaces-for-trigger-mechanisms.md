# ADR-021: Specialized Interfaces for Trigger Mechanisms

## Status

Accepted

## Context

Trigger plugins determine when workflow executions should begin, but different trigger mechanisms may require fundamentally different hosting behavior.

For example:

```text
Chronological trigger
    → Scheduler polling
    → durable scheduling state
    → next-occurrence calculation

Webhook trigger
    → HTTP/event reception

Filesystem trigger
    → filesystem/event monitoring
```

A universal operation such as:

```python
is_ready(configuration) -> bool
```

would make these mechanisms appear interchangeable while hiding their different infrastructure requirements.

The architecture therefore needs a way to represent shared capabilities without forcing unrelated trigger mechanisms through one generic execution contract.

## Decision

Trigger mechanisms will be represented through **specialized interfaces**.

The base:

```text
Trigger
```

identifies the trigger plugin category but does not define a universal readiness or execution operation.

Mechanisms with shared platform requirements define specialized interfaces.

The first is:

```text
ChronologicalTrigger
```

with:

```python
next_occurrence(
    configuration: dict[str, Any],
    after: datetime,
) -> datetime | None
```

Concrete chronological plugins implement that capability:

```text
Trigger
└── ChronologicalTrigger
    ├── IntervalTrigger
    ├── CronTrigger          [future]
    └── OneTimeTrigger       [future]
```

`next_occurrence()` is a pure calculation and must remain:

- Deterministic.
- Fast.
- Local.
- I/O-free.
- Independent of Persistence.
- Independent of the Execution Queue.
- Independent of Application services.

A returned datetime represents the next occurrence. `None` indicates that no future occurrence exists.

Platform responsibilities remain separated:

```text
Plugin
    implementation-specific behavior

Mechanism-specific Application capability
    hosts that behavior

Persistence
    durable state and concurrency

Runtime
    drives the capability
```

Mechanism membership is represented by interface inheritance.

No parallel trigger-mechanism enum, category field, or persisted mechanism value is introduced.

## Alternatives Considered

### Universal Trigger Readiness Interface

Require every trigger to implement a common operation such as `is_ready()`.

**Pros**

- Simple abstraction.
- Makes all triggers appear interchangeable.

**Cons**

- Hides fundamentally different hosting requirements.
- Provides insufficient contracts for mechanism-specific infrastructure.
- Encourages infrastructure behavior to leak into plugins or generic orchestration.
- Artificially treats chronological, webhook, and event-driven triggers as equivalent.

### Trigger Mechanism Enum

Classify plugins using values such as:

```text
CHRONOLOGICAL
WEBHOOK
FILESYSTEM
```

**Pros**

- Explicit classification.
- Straightforward dispatch.

**Cons**

- Duplicates information already represented by interfaces.
- Creates two sources of truth.
- Provides classification without a behavioral contract.
- Requires central enum changes for new mechanisms.

### Specialized Mechanism Interfaces (Selected)

Represent each meaningful mechanism through an interface defining the behavior required by its hosting infrastructure.

**Pros**

- Makes mechanism capabilities explicit.
- Avoids artificial universal behavior.
- Avoids duplicated mechanism metadata.
- Allows implementations of the same mechanism to reuse infrastructure.
- Keeps plugins independent of Application and Persistence.
- Supports type-level reasoning about plugin capabilities.

**Cons**

- Introduces additional interfaces.
- Fundamentally new mechanisms may require new infrastructure.
- Trigger implementations are not universally interchangeable.

## Consequences

### Positive

- Chronological plugins remain simple calculation components.
- Scheduler infrastructure does not depend on concrete chronological implementations.
- New chronological plugins can reuse existing chronological infrastructure.
- Trigger implementations remain infrastructure-independent.
- Future mechanisms can expose contracts appropriate to their actual behavior.
- Mechanism classification cannot drift from interface implementation.

### Negative

- Trigger architecture uses a capability hierarchy rather than one uniform interface.
- Application infrastructure must understand the mechanism interfaces it supports.
- Fundamentally new mechanisms may require dedicated Application, Persistence, or Runtime support.

Trigger extensibility therefore applies both to **new implementations of existing mechanisms** and, when necessary, to **new mechanisms with their own architectural requirements**.
