# ADR-010: Compiled Workflow Executions

## Status

Accepted

---

## Context

Workers repeatedly perform runtime scheduling operations while processing workflow executions.

Initially, runtime scheduling information was intended to be reconstructed from the WorkflowDefinition whenever a task completed. This required traversing task definitions and dependency relationships to determine child tasks and runnable work.

As the execution model evolved, it became clear that this approach unnecessarily repeated work already known when the WorkflowExecution was created.

A decision was required regarding whether workers should dynamically reconstruct the execution graph or whether runtime scheduling information should be precomputed when a workflow execution begins.

---

## Decision

Workflow executions snapshot all runtime information required for execution, including:

- Task dependency counts
- Child task relationships
- Retry policy
- Runtime task state

Workers should never need to consult WorkflowDefinitions during normal execution.

WorkflowDefinitions remain immutable specifications.

WorkflowExecutions represent the compiled runtime projection of those specifications.

---

## Alternatives Considered

### Reconstruct Execution Graph During Processing

**Pros**

- No duplicated scheduling information.
- WorkflowExecution remains smaller.
- Execution graph always derived directly from the workflow definition.

**Cons**

- Repeated graph traversal during execution.
- More complex worker implementation.
- Additional repository queries may be required.
- Runtime repeatedly performs deterministic work.

---

### Compiled Workflow Execution (Selected)

**Pros**

- Worker execution becomes significantly simpler.
- Runtime scheduling requires only execution state.
- No repeated graph reconstruction.
- Execution becomes self-contained.
- Supports efficient parallel task scheduling.

**Cons**

- Some scheduling information is duplicated.
- Workflow execution creation performs additional work.

---

## Consequences

### Positive

- WorkflowExecution becomes the single runtime representation of workflow state.
- Workers operate entirely on execution data.
- Scheduling logic becomes straightforward and efficient.
- Persistence naturally stores the execution graph needed during runtime.
- Retry policy becomes independent of later WorkflowDefinition changes.
- Workers execute entirely from WorkflowExecution state.

### Negative

- Runtime scheduling metadata must remain consistent with the workflow definition when an execution is created.
- Workflow executions require slightly more storage.

The additional storage is considered an acceptable trade-off for a simpler and more efficient runtime execution model.
