# ADR-008: Dependency-Based Workflow Scheduling

## Status

Accepted

## Context

The Automation Platform executes workflows composed of multiple tasks.

A decision was required regarding how the Workflow Engine should determine which tasks become runnable during execution.

A simple approach would be to execute tasks sequentially by maintaining a current task index or program counter.

While straightforward, this approach only supports linear workflows and requires special-case logic to introduce parallel execution.

The platform is intended to support both sequential and parallel workflows using a single execution model while keeping workers independent of workflow structure.

## Decision

Workflow scheduling will be based on task dependencies rather than execution order.

Each Task Definition specifies the tasks upon which it depends.

When a workflow execution is created, each Task Execution records the number of remaining unresolved dependencies.

When a task completes, the Workflow Engine decrements the remaining dependency count of each dependent task.

If a task's remaining dependency count reaches zero, the Workflow Engine enqueues that task for execution.

Workers remain unaware of workflow topology and simply execute the task assigned to them.

## Alternatives Considered

### Sequential Program Counter

Maintain the index of the next task to execute.

**Pros**

- Very simple implementation
- Easy to understand
- Well suited for strictly linear workflows

**Cons**

- Does not naturally support parallel execution
- Requires additional logic for branching and synchronization
- Couples workflow structure to execution logic

### Dependency-Based Scheduling (Selected)

Determine runnable tasks using dependency counts.

**Pros**

- Supports both sequential and parallel workflows
- Sequential workflows become a special case
- Workers remain independent of workflow structure
- Scales naturally to arbitrary directed acyclic graphs (DAGs)
- Eliminates separate scheduling logic for parallel execution

**Cons**

- More complex workflow initialization
- Additional runtime state must be maintained
- Requires dependency bookkeeping throughout execution

## Consequences

### Positive

- Provides a single execution model for all supported workflows
- Enables parallel execution without architectural changes
- Simplifies worker responsibilities
- Keeps workflow orchestration centralized within the Workflow Engine
- Future workflow complexity is accommodated without redesigning the scheduler

### Negative

- Workflow executions require additional runtime metadata
- Dependency state must be updated atomically during task completion
- Cyclic workflow definitions must be rejected during validation

Dependency-based scheduling establishes a general execution model in which tasks become runnable as soon as all required dependencies have completed, allowing sequential and parallel workflows to be handled uniformly.
