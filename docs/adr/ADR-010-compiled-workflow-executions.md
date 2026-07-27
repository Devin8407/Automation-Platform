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

Workflow executions will contain a compiled representation of the execution graph.

When a WorkflowExecution is created, the Application Layer computes runtime scheduling information for every TaskExecution, including:

- Remaining dependency count
- Child task identifiers
- Initial execution state

This information becomes part of the persisted WorkflowExecution.

Workers perform scheduling decisions exclusively using execution state rather than traversing the WorkflowDefinition.

WorkflowDefinition remains the authoritative description of the workflow structure.

WorkflowExecution stores a runtime projection optimized for execution.

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

### Negative

- Runtime scheduling metadata must remain consistent with the workflow definition when an execution is created.
- Workflow executions require slightly more storage.

The additional storage is considered an acceptable trade-off for a simpler and more efficient runtime execution model.
