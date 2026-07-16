# ADR-002: Queue-Driven Execution

## Status

Accepted

## Context

The Automation Platform executes workflows consisting of one or more tasks. A decision was needed regarding how task execution should be coordinated.

The simplest approach would be for the application layer to execute tasks synchronously when a workflow is started. While straightforward, this tightly couples workflow orchestration with task execution, prevents asynchronous processing, and limits future scalability.

The project is intended to demonstrate production-style backend architecture, including background workers and asynchronous execution.

## Decision

The application layer will orchestrate workflow execution by placing runnable task executions onto an execution queue rather than executing them directly.

Background workers will invoke shared application services to process claimed task executions and persist execution state.

The execution queue is treated as an architectural abstraction. The initial implementation will use PostgreSQL as the queue backend, allowing the implementation to evolve in the future without changing orchestration logic.

## Alternatives Considered

### Synchronous Execution

The application layer executes each task directly.

**Pros**

* Very simple implementation
* Minimal infrastructure
* Easier to understand initially

**Cons**

* Couples orchestration and execution
* API requests remain blocked until completion
* Difficult to scale independently
* Makes background processing difficult
* Limits future extensibility

### Queue-Driven Execution (Selected)

Runnable work is enqueued by application layer for background workers to claim.

**Pros**

* Enables multiple runtime processes to share a common orchestration model.
* Separates orchestration from execution
* Enables asynchronous processing
* Supports independent worker processes
* Better represents production workflow systems
* Allows future replacement of the queue implementation

**Cons**

* Additional architectural complexity
* Requires worker coordination
* Introduces queue management responsibilities

## Consequences

### Positive

* Clear separation of responsibilities
* API requests can return immediately
* Workers remain independent of workflow logic
* Future support for multiple workers becomes straightforward
* Queue implementation can evolve without affecting orchestration

### Negative

* More moving parts than synchronous execution
* Additional execution state must be tracked
* Queue failures and worker recovery must be handled

This decision establishes a clean architectural boundary between workflow orchestration and task execution that supports future scalability while remaining appropriate for a modular monolith.
