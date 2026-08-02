# ADR-004: Runtime Processes and Application Services

## Status

Accepted

## Context

The Automation Platform contains multiple runtime mechanisms, including:

- API processes.
- Worker processes.
- Scheduler processes.
- Webhook handlers.
- Future event consumers.

A decision was required regarding where process-control responsibilities end and business orchestration begins.

Allowing each runtime to implement workflow behavior independently would duplicate business logic and couple orchestration to particular delivery mechanisms.

At the same time, moving process-specific concerns such as queue polling, heartbeats, HTTP transport, or trigger event reception into Application services would couple business capabilities to runtime infrastructure.

## Decision

Runtime processes will remain thin control mechanisms responsible for determining when Application capabilities should be invoked.

Runtime responsibilities include:

- Process loops.
- Polling and sleeping.
- Queue claims.
- Queue heartbeats.
- Lease handling.
- Queue finish/release operations.
- HTTP transport.
- Trigger-specific event reception.
- Process startup and shutdown.

The Application Layer owns complete business use cases and workflow orchestration.

Application responsibilities include:

- Workflow definition management.
- Workflow execution creation.
- Task processing orchestration.
- TaskContext construction.
- Plugin resolution.
- TaskResult interpretation.
- Persistence transaction boundaries.
- Determining resulting business actions.

Runtime processes invoke Application services rather than implementing workflow state transitions or business rules themselves.

The guiding distinction is:

> Runtime determines when a capability should be invoked.

> Application determines what business operation should happen.

Runtime processes may use infrastructure directly when that infrastructure represents runtime control rather than business state, such as Worker interaction with the Execution Queue.

## Alternatives Considered

### Runtime-Specific Business Logic

Each runtime implements the orchestration required for its use case.

**Pros**

- Minimal initial abstraction.
- Direct implementation.

**Cons**

- Duplicates business logic.
- Couples business behavior to transport/process mechanisms.
- Produces inconsistent behavior across runtimes.
- Makes independent testing difficult.

### Application Owns All Runtime Infrastructure

Application services also manage worker loops, queue claims, HTTP behavior, and trigger polling.

**Pros**

- Centralizes more behavior.

**Cons**

- Couples business logic to runtime infrastructure.
- Makes Application services long-running and stateful.
- Reduces queue and transport independence.
- Blurs the boundary between invocation and business behavior.

### Thin Runtimes with Shared Application Services (Selected)

Runtime processes own control flow and invocation mechanisms while Application services own complete business operations.

**Pros**

- Centralizes business behavior.
- Keeps runtimes focused.
- Preserves queue and transport independence.
- Makes Application services independently testable.
- Allows different runtimes to reuse the same capabilities.

**Cons**

- Requires carefully defining the runtime/Application boundary.
- Some runtime processes still require meaningful infrastructure coordination.

## Consequences

### Positive

- Workflow business logic has one implementation.
- Runtimes remain focused on process and delivery concerns.
- Worker queue mechanics remain outside Application.
- New entry points can reuse existing Application capabilities.
- Application services can be tested without running complete runtime processes.

### Negative

- Runtime processes are thin but not logic-free.
- Developers must distinguish runtime coordination from business orchestration.

This separation allows runtime mechanisms to vary independently while preserving a single implementation of each business capability.
