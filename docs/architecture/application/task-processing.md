# Task Processing

## Purpose

The `task_processing` capability owns logical processing of a Task Execution after a Worker has obtained it from the Execution Queue.

The Worker owns queue delivery and claim lifecycle. `TaskProcessingService` owns the business operation performed against the claimed Task Execution. This keeps workflow and task state-transition logic out of the Worker runtime.

## High-Level Flow

```text
Worker
    |
    +-- claim queue item
    |
    v
TaskProcessingService.process(task_execution_id)
    |
    +-- start/resume task in Persistence
    +-- resolve task plugin
    +-- construct TaskContext
    +-- execute plugin
    +-- persist success or failure
    |
    v
Processing result
    |
    v
Worker
    |
    +-- finish/release queue claim
```

The Worker translates the Application result into queue disposition. Application does not manipulate queue leases.

## Transaction Boundaries

Task plugins may perform arbitrary or long-running work, including HTTP requests, file processing, external API calls, and data transformations. Plugin execution therefore occurs **outside** persistence transactions.

```text
Persistence transaction
        |
        +-- establish/resume execution state
        +-- load execution context
        |
        v
COMMIT / transaction ends
        |
        v
execute plugin
        |
        v
new Persistence transaction
        |
        +-- complete or record failure
```

This avoids holding database resources and locks while arbitrary plugin behavior runs.

## Starting or Resuming a Task

Persistence determines whether the task may be processed.

A logical task may be processable when it is `PENDING` or `RUNNING`:

- `PENDING` begins execution.
- `RUNNING` may be resumed after a previous Worker's queue lease expired or that Worker disappeared before completing the logical task.
- Terminal tasks are not executed again.

Allowing `RUNNING` tasks to resume supports queue redelivery and Worker recovery.

## Task Context and Plugin Execution

Before invoking the plugin, Application constructs a `TaskContext` containing the execution information the plugin needs, such as:

- Task configuration
- Inputs from completed dependencies
- Execution-specific metadata

The plugin does **not** receive repositories, SQLAlchemy sessions, a Unit of Work, queue implementations, or workflow orchestration services. This keeps plugins independently testable and infrastructure-independent.

Application resolves the implementation through `TaskRegistry`:

```text
TaskExecution.plugin_type
        |
        v
TaskRegistry
        |
        v
Task implementation
        |
        v
execute(TaskContext)
        |
        v
TaskResult
```

The plugin owns task-specific behavior. Application interprets the result within the workflow execution model.

## Processing Outcomes

### Successful Completion

Persistence atomically transitions the Task Execution:

```text
RUNNING
    |
    v
COMPLETED
```

Completion may decrement the unmet dependency counts of child tasks. Children whose count reaches zero become runnable. Persistence returns those Task Execution identifiers to Application, and the processing outcome makes them available to the Worker path for queue publication. If that was the final task of the workflow execution the workflow is also marked as complete and given completion time.

### Retryable Failure

If attempts remain, the failed attempt is recorded and remaining tries are decremented, but the logical task stays `RUNNING`:

```text
RUNNING
    |
    +-- record failed attempt
    +-- decrement remaining tries
    |
    v
RUNNING
```

The Worker can release its queue claim so the same queued Task Execution can be attempted again.

The task does **not** return to `PENDING`; `RUNNING` means the logical task has begun but has not reached a terminal outcome.

### Terminal Failure

If no attempts remain, the Task Execution becomes `FAILED`, the Workflow Execution fails, and Persistence cancels remaining nonterminal tasks:

```text
TaskExecution RUNNING
        |
        v
      FAILED
        |
        v
WorkflowExecution FAILED
        |
        v
remaining nonterminal tasks CANCELLED
```

Application coordinates this business outcome. Persistence owns the atomic SQL transitions that make it concurrency-safe.

## Queue and Persistence Are Separate Concurrency Domains

`TaskProcessingService` does not know whether the Worker still owns its queue claim. Queue ownership is represented by the Execution Queue's lease and claim-token mechanism.

| Component | Owns |
| --- | --- |
| Worker | `claim`, `heartbeat`, `release`, `finish` |
| TaskProcessingService | Logical task-processing orchestration |
| Task plugin | Task-specific behavior |
| Persistence | Durable state transitions and concurrency correctness |
| Execution Queue | Claims, leases, heartbeats, and redelivery |

Persistence protects durable Task Execution state through conditional transitions; the Queue protects delivery ownership through renewable leases and claim tokens.

## Stale Queue Entries

Persistence state is authoritative for whether a Task Execution may logically execute. A stale queue entry may refer to a task that is already terminal or was cancelled because another task failed the workflow.

```text
Worker
    |
    v
TaskProcessingService
    |
    v
Persistence rejects processing
```

The plugin is not executed. Loose coupling between queue and persistence therefore remains safe: stale delivery is harmless.

## Key Invariants

- Plugin execution occurs outside persistence transactions.
- `RUNNING` tasks may resume after queue redelivery; terminal tasks do not execute again.
- Retryable failure leaves the logical task `RUNNING`, not `PENDING`.
- Terminal task failure fails the workflow and cancels remaining nonterminal tasks.
- Persistence state, not queue presence, is authoritative for logical executability.
- Queue claim ownership remains a Worker/Execution Queue concern.

## Testing Strategy

Important Application-level scenarios include:

- Pending tasks can begin processing.
- Running tasks can resume after redelivery.
- Terminal tasks are not processed again.
- The correct plugin is resolved and `TaskContext` contains required dependency inputs.
- Successful completion advances dependencies and returns newly runnable children.
- Retryable failures decrement remaining attempts while the task remains logically running.
- Terminal failures fail the task and workflow and cancel remaining tasks.
- Stale cancelled queue entries do not execute plugins.

Persistence integration tests own low-level transition concurrency. Worker tests own queue claim lifecycle and translation of processing results into `release()` or `finish()`.
