# ADR-002: Queue-Driven Execution

## Status

Accepted

## Context

The Automation Platform executes workflows consisting of one or more tasks.

A decision was required regarding how runnable task executions should be delivered to execution processes.

The simplest approach would be for the Application Layer to execute tasks synchronously when a workflow is started. While straightforward, this would tightly couple workflow orchestration to physical execution, block callers while work executes, and prevent independent worker processes from processing tasks concurrently.

The project is intended to support asynchronous execution, multiple workers, failure recovery, and replaceable queue infrastructure.

## Decision

Runnable task executions will be delivered through an Execution Queue and processed asynchronously by Worker runtimes.

The Execution Queue is an architectural abstraction responsible for work delivery and temporary worker ownership.

The initial implementation uses PostgreSQL, while callers depend only on the queue interface so that a different implementation such as RabbitMQ may be introduced later.

Runtime processes own queue-specific lifecycle concerns, including:

- Claiming runnable work.
- Maintaining worker leases.
- Heartbeating claims.
- Releasing retryable work.
- Finishing claims.

The Application Layer does not own queue claims or lease state.

Instead, Application services perform complete business use cases and return the resulting business disposition to the runtime.

For task processing, this includes:

- Whether the currently claimed task should be retried.
- Which child task executions became newly runnable.

The Worker uses this result to perform the appropriate queue operation.

Workflow startup may enqueue initial runnable tasks as part of its orchestration, but queue delivery and claim lifecycle remain infrastructure/runtime concerns.

## Alternatives Considered

### Synchronous Execution

The Application Layer directly executes tasks as workflows progress.

**Pros**

- Simple implementation.
- Minimal infrastructure.
- Straightforward execution flow.

**Cons**

- Couples workflow orchestration to physical execution.
- Blocks callers until work completes.
- Prevents independent worker scaling.
- Makes worker recovery difficult.
- Limits future extensibility.

### Queue-Driven Execution (Selected)

Runnable work is delivered through an Execution Queue and processed by independent Worker runtimes.

**Pros**

- Enables asynchronous execution.
- Separates workflow orchestration from work delivery.
- Supports multiple concurrent workers.
- Supports worker failure recovery.
- Allows queue implementations to evolve independently.
- Keeps queue lease mechanics outside business orchestration.

**Cons**

- Introduces additional infrastructure.
- Requires worker coordination.
- Introduces eventual-consistency and recovery concerns between durable workflow state and queue state.

## Consequences

### Positive

- API and trigger runtimes do not execute arbitrary workflow tasks directly.
- Workers remain independent of workflow business rules.
- Application services remain independent of queue lease semantics.
- Multiple workers can process independent task executions concurrently.
- Queue infrastructure can evolve without changing workflow orchestration.

### Negative

- The system contains more moving parts than synchronous execution.
- Queue delivery and durable workflow state must be coordinated across separate boundaries.
- Worker recovery and duplicate physical execution must be considered explicitly.

Queue-driven execution establishes a clean separation between durable workflow orchestration and asynchronous work delivery while allowing runtime and queue infrastructure to evolve independently.
