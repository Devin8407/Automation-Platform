# Workflow Execution Persistence

## Purpose

`WorkflowExecutionRepository` persists workflow execution aggregates and
provides targeted state transitions used during task processing.

It supports complete aggregate persistence when needed, but frequent
runtime operations deliberately avoid reconstructing the full execution
graph when only a small subset of state is required.

## Responsibilities

The repository supports:

-   Loading and saving workflow executions.
-   Starting or resuming task executions.
-   Completing task executions.
-   Recording failed attempts and retries.
-   Updating dependency state.
-   Identifying newly runnable children.
-   Completing workflows.
-   Failing workflows.
-   Cancelling remaining work after workflow failure.

## Aggregate and Targeted Operations

Complete aggregate operations are appropriate when Application needs a
full `WorkflowExecution` and its Task Executions.

Runtime processing instead uses targeted operations such as:

``` text
start_task(...)
complete_task(...)
retry_task(...)
```

These operations expose only the persistence behavior required by the
Application use case.

Targeted methods may use persistence operation models such as:

-   `StartTaskExecutionResult`
-   `CompleteTaskExecutionRequest`
-   `CompleteTaskExecutionResult`
-   `RetryTaskExecutionRequest`
-   `RetryTaskExecutionResult`

These types are neither Domain objects nor SQLAlchemy rows.

## Task Start

Task start is intentionally idempotent for an already-running logical
task.

``` text
PENDING
    -> RUNNING
    -> set started_at
    -> processable

RUNNING
    -> remain RUNNING
    -> preserve started_at
    -> processable

COMPLETED / FAILED / CANCELLED / missing
    -> not processable
```

This supports recovery after queue lease expiration or redelivery.

`started_at` records when the **logical task execution first began**,
not the beginning of every physical Worker attempt.

For a processable task, `start_task()` returns the persisted data needed
to execute its plugin:

-   Plugin type.
-   Configuration.
-   Parent task outputs keyed by parent task key.

Parent outputs are loaded from the task executions referenced by the
task's persisted parent execution identifiers.

Persistence does not construct `TaskContext`; Application constructs it
from the returned execution data.

## Successful Completion

Only a task that remains `RUNNING` may transition successfully to
`COMPLETED`.

``` text
RUNNING
   |
   v
COMPLETED
   |
   +--> persist output
   |
   +--> set completed_at
   |
   +--> decrement child dependency counts
   |
   +--> identify newly runnable children
   |
   +--> complete workflow if appropriate
```

If a concurrent operation has already moved the task to a terminal
state, a stale completion must not overwrite it.

## Dependency Progression

Each Task Execution stores its remaining dependency count. When a parent
completes successfully, Persistence atomically updates its children.

A child becomes runnable when its remaining dependency count reaches
zero.

``` text
   A
  / \
 B   C
  \ /
   D
```

Completing `B` alone does not make `D` runnable. Only after both `B` and
`C` complete does `D` reach zero remaining dependencies.

Persistence returns the identifiers that became runnable; Application
decides the resulting business action, including queue publication.

Persistence determines which Task Executions became runnable as a result of the atomic dependency update and returns their identifiers to Application.

It does not decide how runnable tasks are delivered or processed. Application interprets the persistence result and coordinates the appropriate queue behavior.

## Retry Semantics

A failed plugin result does not necessarily mean the logical task has
failed.

When another try remains:

``` text
RUNNING -> RUNNING
remaining tries -> decremented
```

The task remains unresolved and may be processed again.

`PENDING` is not used for retries. Status semantics are:

``` text
PENDING
    = logical task has never begun

RUNNING
    = logical task has begun and remains unresolved

COMPLETED
    = logical task succeeded

FAILED
    = logical task exhausted its allowed tries

CANCELLED
    = logical task was terminated because its workflow could not continue
```

Only a task that remains `RUNNING` may record a failed attempt.

## Terminal Failure

When a task exhausts its available tries:

1.  The failing task transitions to `FAILED`.
2.  The workflow transitions `RUNNING -> FAILED`.
3.  Remaining `PENDING` and `RUNNING` tasks transition to `CANCELLED`.

The failing task remains `FAILED` because cancellation targets only
nonterminal tasks.

Workflow failure and sibling cancellation occur in the same database
transaction. Cancelled tasks receive their terminal completion timestamp
when cancellation occurs.

> **After a failed workflow transaction commits, it has no remaining
> `PENDING` or `RUNNING` Task Executions.**

## Concurrency Guarantees

Persistence guarantees that:

-   Only processable tasks may be started or resumed.
-   Only `RUNNING` tasks may complete.
-   Only `RUNNING` tasks may record failed attempts.
-   Dependency counters are updated atomically.
-   Terminal task states cannot be overwritten by stale results.
-   Workflow failure atomically cancels remaining nonterminal tasks.

Queue lease expiration may cause another Worker to receive a task whose
logical execution is already `RUNNING`. Persistence deliberately allows
it to be processed again and preserves the original `started_at`.

Whichever valid persistence transition reaches a terminal state first
prevents later stale transitions from overwriting that state.

These guarantees protect persisted state; queue claims, worker
ownership, heartbeats, lease expiration, and claim recovery remain queue
responsibilities.

## Mapping

The execution mapper translates persisted representations for:

-   `WorkflowExecution`
-   `TaskExecution`
-   `TaskOutput`
-   JSONB task output

Targeted runtime operations need not reconstruct these complete Domain
aggregates when a narrow result model is sufficient.

## Testing

PostgreSQL integration tests should cover:

-   Workflow execution persistence and reconstruction.
-   Task start and preservation of initial `started_at`.
-   Successful completion.
-   Retryable and terminal failure.
-   Sibling cancellation.
-   Dependency counter updates.
-   Workflow completion.
-   Conditional state transitions.
-   Concurrent completion attempts.
-   Concurrent failure attempts.

Cross-layer tests should additionally verify that workflow start
produces a valid persisted graph, parent outputs reach dependent
plugins, task chains progress, retries work across
Application/Persistence boundaries, and terminal failure produces the
expected persisted workflow state.
