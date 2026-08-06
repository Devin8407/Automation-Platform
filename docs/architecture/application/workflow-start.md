# Workflow Start

## Purpose

The `workflow_start` capability defines what it means to start a workflow. Callers request that a reusable Workflow Definition begin execution without needing to understand execution compilation, persistence, or initial queue publication.

The capability is shared by direct/manual starts and automatic trigger mechanisms.

## Responsibilities

Starting a workflow means:

1. Load the Workflow Definition.
2. Verify that it exists and is enabled.
3. Create a Workflow Execution.
4. Create a Task Execution for each Task Definition.
5. Translate definition dependencies into execution dependencies.
6. Initialize dependency counts and retry state.
7. Identify root tasks.
8. Persist the execution.
9. Commit the persistence transaction.
10. Enqueue root tasks.

Other capabilities should reuse this behavior rather than construct Workflow Execution state themselves.

## Compiling an Execution

Each Workflow Execution receives its own runtime task graph:

```text
WorkflowDefinition
        |
        | compile
        v
WorkflowExecution
        |
        +-- TaskExecution A
        +-- TaskExecution B
        +-- TaskExecution C
```

Runtime dependency information and retry state are initialized from the reusable definition. The resulting execution progresses independently without mutating its Workflow Definition.

Tasks with no unmet dependencies are root tasks and are initially runnable. Workflow start identifies them while constructing the graph and publishes their identifiers after the execution commits.

## Public Operations

### `start(workflow_definition_id)`

Use `start()` when the caller does not already have persistence changes that must commit atomically with workflow creation.

```text
start()
    |
    +-- create UoW
    +-- load and validate definition
    +-- create execution state
    +-- persist
    +-- commit
    +-- enqueue root tasks
```

`start()` owns its Unit of Work. A direct API/manual start can use it without introducing a separate manual-trigger scheduling mechanism.

### `start_and_commit(workflow_definition_id, uow)`

Use `start_and_commit()` when workflow creation must complete an existing Application transaction. Chronological scheduling is the first example.

```text
existing UoW
    |
    +-- load Workflow Definition
    +-- validate start
    +-- create WorkflowExecution
    +-- create TaskExecutions
    +-- persist execution
    +-- COMMIT supplied UoW
    +-- enqueue root tasks
```

For chronological scheduling, that commit contains both schedule advancement and Workflow Execution creation.

`start_and_commit()` is intentionally a **terminal operation** on the supplied Unit of Work. The caller must not perform additional persistence operations through that Unit of Work afterward. This makes transaction ownership explicit instead of hiding different behavior behind an optional Unit of Work parameter.

## Queue Publication Boundary

Initial runnable work is published only after persistence commits:

```text
persist execution
        |
        v
COMMIT
        |
        +-- persistence durable
        +-- database locks released
        |
        v
enqueue root tasks
```

This prevents Workers from receiving Task Execution identifiers before their execution state is durable.

Persistence and the Execution Queue are separate transactional systems, so a process may fail here:

```text
database commit
        |
        X process failure
        |
queue enqueue
```

That can temporarily leave runnable persisted work absent from the queue. The platform accepts this failure window rather than coupling the queue to the persistence transaction. The Reconciler repairs it using idempotent queue enqueue, preserving compatibility with future non-PostgreSQL queue implementations.

## Why Workflow Start Owns Publication

Returning root Task Execution IDs and requiring every caller to enqueue them would force the API, Scheduler, and future trigger runtimes to understand workflow-start internals.

Instead, callers request **start workflow**, and `WorkflowStartService` owns both creation of the execution and publication of its initial runnable work.

Trigger mechanisms likewise do not create Workflow Executions directly:

```text
ChronologicalTriggerService
        |
        | determines that workflow should start
        v
WorkflowStartService
        |
        +-- compile execution
        +-- persist
        +-- commit
        +-- publish roots
```

Centralizing compilation prevents different start mechanisms from producing subtly different runtime state.

## Key Invariants

- A Workflow Execution has its own runtime task graph and does not mutate its reusable definition.
- Root tasks are published only after execution state is durable.
- `start()` owns and commits its Unit of Work.
- `start_and_commit()` commits the supplied Unit of Work and is terminal for that UoW.
- Queue publication is outside persistence atomicity and is recoverable through reconciliation.

## Testing Strategy

Important scenarios include:

- A valid definition produces a complete execution graph.
- Missing or disabled definitions cannot be started.
- Root tasks, dependencies, and retry state are compiled correctly.
- `start()` owns and commits its transaction.
- `start_and_commit()` participates in and commits the supplied transaction.
- Root tasks are published only after persistence commits.
- Queue publication failure does not roll back already committed persistence state.

Cross-layer tests should verify that reconciliation recovers persisted runnable work if initial queue publication is interrupted.
