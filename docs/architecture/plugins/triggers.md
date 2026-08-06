# Trigger Plugins

## Purpose

Trigger plugins define configurable behavior for workflow activation mechanisms.

Triggers do not share one natural runtime model: chronological, webhook, and filesystem triggers may require fundamentally different infrastructure. Trigger extensibility is therefore organized around **mechanism interfaces**, not a universal polling method such as `is_ready()`.

---

## Base Interface and Mechanisms

Every trigger derives from `Trigger`, which currently adds no behavior beyond the shared plugin contract:

- `plugin_type`
- `validate_configuration(...)`

The base type identifies the plugin category. Mechanism interfaces define shared behavior for trigger families that can be hosted by the same Application/runtime infrastructure.

The implemented chronological family is:

```text
Trigger
└── ChronologicalTrigger
    ├── IntervalTrigger
    ├── CronTrigger          [future]
    ├── DailyTimeTrigger     [future]
    └── OneTimeTrigger       [future]
```

`ChronologicalTrigger` defines:

```python
next_occurrence(
    configuration,
    after,
) -> datetime | None
```

Other mechanisms may introduce their own interfaces:

```text
Trigger
├── ChronologicalTrigger
├── WebhookTrigger       [future]
└── FilesystemTrigger    [future]
```

There is deliberately no `TriggerMechanism` enum. The class hierarchy is the source of truth: if `IntervalTrigger` inherits from `ChronologicalTrigger`, it belongs to that mechanism. Application can therefore dispatch on the mechanism interface without duplicating the same information in metadata.

---

## Persisted Definitions and Resolution

A generic trigger definition remains small:

```text
TriggerDefinition
├── plugin_type
├── configuration
└── enabled
```

For example:

```text
plugin_type = "interval"
configuration = {"interval_seconds": 60}
```

No separate mechanism or category is persisted. Resolution uses the implementation type:

```text
"interval"
    │
    ▼
TriggerRegistry
    │
    ▼
IntervalTrigger
    │
    └── inherits ChronologicalTrigger
```

---

## Configuration Validation

Concrete plugins own plugin-specific validation. During workflow-definition creation, Application resolves the plugin and invokes:

```text
plugin.validate_configuration(configuration)
```

Application does not duplicate rules such as accepted interval fields or valid interval values.

Validation and mechanism initialization are separate: configuration is validated first, then mechanism-specific Application infrastructure initializes any required durable state.

---

## Chronological Trigger Contract

Chronological triggers start workflows based on time. A plugin calculates its next occurrence relative to a supplied datetime:

```text
configuration + after
        │
        ▼
ChronologicalTrigger.next_occurrence(...)
        │
        ▼
datetime | None
```

`next_occurrence()` must remain:

- Fast.
- Deterministic.
- Local.
- I/O-free.
- Independent of Persistence, queues, and Application services.

Scheduling may invoke it while PostgreSQL holds a row lock on durable trigger state.

A chronological plugin does **not** query scheduling state, lock rows, update `next_run_at`, create workflow executions, commit transactions, enqueue tasks, or run the Scheduler loop.

### `IntervalTrigger`

`IntervalTrigger` uses configuration such as:

```json
{
  "interval_seconds": 60
}
```

Its calculation is:

```text
next occurrence = after + interval
```

For recurring schedules, Application passes the persisted scheduled occurrence as `after`, not wall-clock `now`. This preserves deterministic catch-up:

```text
interval:        1 hour
next_run_at:     09:00
current time:    11:30

09:00 -> 10:00
10:00 -> 11:00
11:00 -> 12:00
```

The initial policy therefore processes missed occurrences rather than skipping directly to the first future time.

---

## Mechanism Initialization

Some mechanisms require durable runtime state beyond their reusable `TriggerDefinition`. Chronological triggers, for example, need persisted `next_run_at`; the plugin does not create this state.

During definition creation:

```text
WorkflowDefinitionService
        │
        ├── resolve plugin
        ├── validate configuration
        ▼
TriggerInitializationService
        │
        │ recognizes ChronologicalTrigger
        ▼
ChronologicalTriggerService.initialize(...)
        │
        ▼
Persistence
```

Initialization dispatch operates on mechanism interfaces, not concrete plugin names. A future `CronTrigger(ChronologicalTrigger)` therefore uses the existing chronological initialization path automatically.

A valid mechanism requiring no initialization simply has no initialization action; there is no `NoInitializationTrigger` abstraction. Initialization and durable state are Application/Persistence concerns, not Plugin Layer concerns.

---

## Runtime Relationship

The Scheduler runtime is a thin driver and does not directly orchestrate trigger plugins:

```text
Scheduler Runtime
        │
        │ process_next_due()
        ▼
ChronologicalTriggerService
        │
        ├── Persistence claims due state
        ├── TriggerRegistry resolves plugin
        ├── plugin.next_occurrence(...)
        ├── Persistence advances schedule
        └── WorkflowStartService creates execution
```

Ownership remains explicit:

- **Persistence:** durable chronological state and PostgreSQL locking.
- **Application:** transactions and orchestration.
- **Plugin:** trigger-specific validation and next-occurrence calculation.

Detailed transaction, `FOR UPDATE SKIP LOCKED`, and scheduling-concurrency behavior belongs in the Application/Persistence chronological-trigger documentation.

---

## Durable State Is Not Plugin State

Chronological scheduling persists state such as:

```text
trigger_definition_id
next_run_at
```

This state belongs to Persistence and is orchestrated by Application. It is not stored in a generic plugin runtime-state object or controlled by the plugin implementation.

Future trigger mechanisms may require fundamentally different state. Add mechanism-appropriate persistence when required rather than forcing every trigger into one generic state schema.

---

## Package Organization

```text
plugins/triggers/
├── interface.py
├── registry.py
├── chronological.py
└── implementations/
    └── interval.py
```

`Trigger` stays at the package root because it represents the whole category. `ChronologicalTrigger` can also remain directly under `triggers/` while it is a small shared mechanism interface. If a mechanism later grows enough to own several support modules, it can become a mechanism-specific subpackage.

---

## Extending Triggers

A new chronological plugin should normally require only another implementation:

```python
class CronTrigger(ChronologicalTrigger):
    ...
```

Existing chronological Application, Persistence, initialization, and Scheduler infrastructure should host it without changes.

A fundamentally different mechanism such as webhooks may legitimately require a new mechanism interface, Application capability, persistence support where needed, runtime/API entry point, and initialization dispatch entry when initialization is required.

This does not violate the architecture: extensibility applies within a supported mechanism; unrelated mechanisms are not forced through one runtime model.

---

## Testing

Shared trigger infrastructure tests should cover discovery, registration, duplicate handling, lookup, and unknown-plugin handling.

`IntervalTrigger` tests should cover valid configuration, missing or malformed interval configuration, zero and negative intervals, correct next-occurrence calculation, and relevant edge cases.

Application integration tests should separately verify:

- Unknown trigger types are rejected during definition creation.
- Configuration validation occurs during definition creation.
- Chronological triggers receive chronological initialization.
- Non-chronological mechanisms do not receive chronological state.
- Due triggers resolve the correct plugin.
- Scheduling failures roll back according to the Application transaction design.

`FOR UPDATE SKIP LOCKED` and multi-Scheduler concurrency are Persistence/Application integration concerns, not plugin unit-test concerns.

The central rule is:

> **Trigger plugins define trigger-specific behavior. Mechanism-specific Application services provide the platform behavior required to host them.**
