# Task Plugins

## Purpose

Task plugins implement the work performed by workflow tasks.

The platform decides when a task executes, constructs its input context, invokes the resolved plugin, and interprets the result. The plugin performs only its configured task behavior.

---

## Contract

Task plugins inherit the shared `plugin_type` and `validate_configuration(...)` contract, then receive a `TaskContext` and return a `TaskResult`:

```text
TaskContext
    │
    ▼
Task Plugin
    │
    ▼
TaskResult
```

### `TaskContext`

Application constructs `TaskContext` immediately before execution:

```text
TaskContext
├── configuration
└── inputs
    └── parent task key -> TaskOutput
```

It contains the task configuration and outputs from completed parent tasks. Parent outputs are keyed by logical task key rather than persistence identifiers, so plugins do not need to understand execution IDs or database structure.

`TaskContext` defines the information a plugin is allowed to consume from the workflow execution.

### `TaskResult`

A task plugin returns:

```text
TaskResult
├── succeeded: bool
├── output: TaskOutput
└── message: str | None
```

`TaskResult` deliberately does not expose workflow-engine `TaskStatus` values such as `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, or `CANCELLED`. The plugin reports the outcome of its work; Application and Persistence determine the resulting execution-state transition.

---

## Platform-Owned Behavior

Task plugins do not:

- Change persisted task execution state or complete workflow executions.
- Update dependency counters or decide which child tasks become runnable.
- Enqueue tasks or claim queue work.
- Decide whether another retry is available.

Those decisions belong to the platform.

A task plugin therefore describes **what work to perform and its outcome**, not how that outcome advances the workflow. Retry eligibility, dependency progression, execution status, workflow completion, and subsequent task scheduling remain platform decisions.

---

## Failure Semantics

### Expected failure

An ordinary unsuccessful outcome is explicit:

```text
TaskResult
    succeeded = false
    message = failure explanation
```

Application interprets the result and applies platform retry and workflow-state rules.

### Unexpected exception

Unexpected exceptions propagate. Examples include programming errors or failures that prevent the plugin from producing a meaningful `TaskResult`.

Application does not automatically convert arbitrary exceptions into ordinary unsuccessful results; otherwise infrastructure or programming failures could silently consume normal workflow retry attempts. Runtime recovery and queue lease behavior handle interrupted processing according to the execution architecture.

---

## Side Effects and Idempotency

Task plugins need not be pure. They may call external APIs, write files, send messages, transform data, or invoke external services.

Recovery can cause a logical task to execute physically more than once. Where practical, externally visible operations should therefore be idempotent or use idempotency support from the external system.

The plugin interface does **not** promise exactly-once physical execution.

---

## Lifecycle

```text
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

---

## Testing

Concrete task plugin tests should cover valid and invalid configuration, successful execution, expected unsuccessful results, plugin-specific edge cases, and exceptional behavior where relevant.

Application integration tests should separately verify unknown-plugin rejection, validation during definition creation, correct plugin resolution, `TaskContext` construction, `TaskResult` interpretation, and propagation of unexpected exceptions.
