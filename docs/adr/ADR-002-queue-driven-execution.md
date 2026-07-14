# ADR-002: Queue-Driven Execution

## Status

Accepted

## Context

The Automation Platform executes workflows consisting of one or more tasks. A decision was needed regarding how task execution should be coordinated.

The simplest approach would be for the Workflow Engine to execute tasks immediately after a workflow is started. While straightforward, this tightly couples workflow orchestration with task execution, prevents asynchronous processing, and limits future scalability.

The project is intended to demonstrate production-style backend architecture, including background workers and asynchronous execution.

## Decision

The Workflow Engine will orchestrate workflow execution by placing runnable tasks onto an execution queue rather than executing them directly.

Background workers will independently claim queued work, execute task implementations, and report execution results back to the Workflow Engine.

The execution queue is treated as an architectural abstraction. The initial implementation will use PostgreSQL as the queue backend, allowing the implementation to evolve in the future without changing orchestration logic.

## Alternatives Considered

### Synchronous Execution

The Workflow Engine executes each task directly.

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

The Workflow Engine enqueues runnable work for background workers.

**Pros**

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
