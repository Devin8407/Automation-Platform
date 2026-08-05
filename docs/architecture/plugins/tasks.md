# Task Plugins

## Purpose

Task plugins implement the work performed by workflow tasks.

The platform determines when a task executes, constructs its input
context, invokes the resolved plugin, and interprets the result. The
plugin performs only its configured task behavior.

------------------------------------------------------------------------

## Interface

A task plugin receives a `TaskContext` and returns a `TaskResult`.

``` text
TaskContext
    │
    ▼
Task Plugin
    │
    ▼
TaskResult
```

Task plugins also inherit the shared plugin contract: `plugin_type` and
`validate_configuration(...)`.

------------------------------------------------------------------------

## TaskContext

The Application Layer constructs `TaskContext` immediately before plugin
execution.

It contains:

-   Task configuration.
-   Outputs from completed parent tasks.

``` text
TaskContext
├── configuration
└── inputs
    └── parent task key -> TaskOutput
```

Parent outputs are keyed by logical task key rather than persistence
identifiers. Task implementations therefore do not need to understand
execution IDs or database structure.

`TaskContext` defines the information a task plugin is allowed to
consume from the workflow execution.

------------------------------------------------------------------------

## TaskResult

A task plugin returns:

``` text
TaskResult
├── succeeded: bool
├── output: TaskOutput
└── message: str | None
```

`TaskResult` deliberately does not return a workflow-engine
`TaskStatus`.

Statuses such as `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, and
`CANCELLED` describe platform execution state. The plugin reports the
outcome of its own work; Application and Persistence determine the
resulting state transition.

------------------------------------------------------------------------

## What Task Plugins Do Not Own

Task plugins do not:

-   Change persisted task execution state.
-   Complete workflow executions.
-   Update dependency counters.
-   Decide which child tasks become runnable.
-   Enqueue tasks.
-   Claim queue work.
-   Decide whether another retry is available.

Those decisions belong to the platform.

------------------------------------------------------------------------

## Failure Semantics

### Expected task failure

An ordinary unsuccessful outcome is returned explicitly:

``` text
TaskResult
    succeeded = false
    message = failure explanation
```

Application interprets the result and applies the platform's retry and
workflow-state rules.

### Unexpected exception

Unexpected exceptions are allowed to propagate. Examples include
programming errors or failures that prevent the plugin from producing a
meaningful `TaskResult`.

Application does not automatically convert arbitrary exceptions into
ordinary unsuccessful task results. This prevents infrastructure or
programming failures from silently consuming normal workflow retry
attempts.

Runtime recovery and queue lease behavior handle interrupted processing
according to the execution architecture.

------------------------------------------------------------------------

## Side Effects and Idempotency

Task plugins are not required to be pure. They may call external APIs,
write files, send messages, transform data, or invoke external services.

Recovery can cause a logical task to be physically executed again. Where
practical, externally visible operations should therefore be idempotent
or use idempotency support from the external system.

The plugin interface does not promise exactly-once physical execution.

------------------------------------------------------------------------

## Lifecycle

``` text
TaskProcessingService
        │
        ├── load execution context
        ├── resolve plugin_type
        ▼
TaskRegistry
        │
        ▼
Task Plugin
        │
        ├── execute TaskContext
        ▼
TaskResult
        │
        ▼
Application interprets result
```

The plugin does not persist or orchestrate its own execution state.

------------------------------------------------------------------------

## Testing

Concrete task plugin tests should cover:

-   Valid and invalid configuration.
-   Successful execution.
-   Expected unsuccessful results.
-   Plugin-specific edge cases.
-   Exceptional behavior where relevant.

Application integration tests should separately verify unknown-plugin
rejection, configuration validation during definition creation, correct
plugin resolution, `TaskContext` construction, `TaskResult`
interpretation, and propagation of unexpected exceptions.
