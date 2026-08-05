# Trigger Plugins

## Purpose

Trigger plugins define configurable behavior for workflow activation
mechanisms.

Triggers do not all share one natural runtime model. A chronological
trigger, webhook trigger, and future filesystem trigger can require
fundamentally different platform infrastructure.

For that reason, trigger extensibility is organized around **mechanism
interfaces** rather than a universal polling method such as
`is_ready()`.

------------------------------------------------------------------------

## Base Trigger Interface

Every trigger derives from the common `Trigger` interface:

``` text
Plugin
└── Trigger
```

`Trigger` currently adds no behavior beyond the shared plugin contract:

-   `plugin_type`
-   `validate_configuration(...)`

The base type identifies the plugin category. More specific interfaces
define mechanism behavior.

------------------------------------------------------------------------

## Trigger Mechanisms

A trigger mechanism is a family of trigger implementations that can be
hosted by the same Application/runtime infrastructure because they share
a behavioral contract.

The implemented chronological family is:

``` text
Trigger
└── ChronologicalTrigger
    ├── IntervalTrigger
    ├── CronTrigger          [future]
    ├── DailyTimeTrigger     [future]
    └── OneTimeTrigger       [future]
```

`ChronologicalTrigger` defines:

``` python
next_occurrence(
    configuration,
    after,
) -> datetime | None
```

Future mechanisms may introduce their own interfaces:

``` text
Trigger
├── ChronologicalTrigger
├── WebhookTrigger       [future]
└── FilesystemTrigger    [future]
```

There is deliberately no `TriggerMechanism` enum. The class hierarchy is
the source of truth. If `IntervalTrigger` inherits from
`ChronologicalTrigger`, it belongs to the chronological mechanism.

This lets Application dispatch use the mechanism interface itself rather
than duplicate the same information in metadata.

------------------------------------------------------------------------

## Persisted Trigger Definitions

The generic trigger definition remains small:

``` text
TriggerDefinition
├── plugin_type
├── configuration
└── enabled
```

For an interval trigger:

``` text
plugin_type = "interval"

configuration = {
    "interval_seconds": 60
}
```

The definition does not persist a separate mechanism or category.

Resolution works through the implementation type:

``` text
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

------------------------------------------------------------------------

## Configuration Validation

Concrete trigger plugins own validation of plugin-specific
configuration.

During workflow-definition creation, Application resolves the plugin and
invokes:

``` text
plugin.validate_configuration(configuration)
```

Application does not duplicate rules such as which fields an interval
trigger accepts or which interval values are valid.

Validation is separate from mechanism initialization. Configuration is
validated first; mechanism-specific Application infrastructure then
initializes any durable state required by that mechanism.

------------------------------------------------------------------------

## Chronological Triggers

Chronological triggers start workflows based on time.

The first implementation is `IntervalTrigger`.

A chronological plugin calculates its next occurrence relative to a
supplied datetime:

``` text
configuration + after
        │
        ▼
ChronologicalTrigger.next_occurrence(...)
        │
        ▼
datetime | None
```

`next_occurrence()` is intentionally constrained to be:

-   Fast.
-   Deterministic.
-   Local.
-   I/O-free.
-   Independent of Persistence, queues, and Application services.

This is important because scheduling may invoke it while PostgreSQL
holds a row lock on the trigger's durable state.

A chronological plugin does **not** query scheduling state, lock rows,
update `next_run_at`, create workflow executions, commit transactions,
enqueue tasks, or run the Scheduler loop.

------------------------------------------------------------------------

## IntervalTrigger

`IntervalTrigger` uses configuration conceptually like:

``` json
{
  "interval_seconds": 60
}
```

Its next occurrence is:

``` text
next occurrence = after + interval
```

For recurring schedules, Application passes the persisted scheduled
occurrence as `after`, not wall-clock `now`.

That preserves deterministic catch-up:

``` text
interval:        1 hour
next_run_at:     09:00
current time:    11:30

09:00 -> 10:00
10:00 -> 11:00
11:00 -> 12:00
```

The initial policy therefore processes missed occurrences rather than
skipping directly to the first future time.

------------------------------------------------------------------------

## Mechanism Initialization

Some mechanisms need durable runtime state beyond their reusable
`TriggerDefinition`.

Chronological triggers need a persisted `next_run_at`. The plugin does
not create this state itself.

During definition creation:

``` text
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

The initialization dispatcher operates on mechanism interfaces, not
concrete plugin names.

Conceptually:

``` text
ChronologicalTrigger
        │
        ▼
ChronologicalTriggerService.initialize
```

A future `CronTrigger(ChronologicalTrigger)` therefore uses the existing
chronological initialization path automatically.

A valid mechanism that requires no initialization simply has no
initialization action. There is no `NoInitializationTrigger`
abstraction.

Initialization and durable state are Application/Persistence concerns,
not Plugin Layer concerns.

------------------------------------------------------------------------

## Runtime Relationship

The Scheduler runtime does not directly orchestrate trigger plugins.

``` text
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

The Scheduler remains a thin driver of the Application capability.

Persistence owns durable chronological state and PostgreSQL locking.
Application owns the transaction and orchestration. The plugin owns only
trigger-specific validation and next-occurrence calculation.

------------------------------------------------------------------------

## Durable State Is Not Plugin State

Chronological scheduling persists state such as:

``` text
trigger_definition_id
next_run_at
```

That state belongs to Persistence and is orchestrated by Application.

It is not stored in a generic plugin runtime-state object and is not
controlled by the plugin implementation.

Different trigger mechanisms may eventually require fundamentally
different state. They should introduce mechanism-appropriate persistence
only when required rather than forcing all triggers into one generic
state schema.

Detailed transaction, `FOR UPDATE SKIP LOCKED`, and scheduling
concurrency behavior belongs in the Application/Persistence
chronological-trigger documentation rather than here.

------------------------------------------------------------------------

## Package Organization

The trigger package is currently well served by:

``` text
plugins/triggers/
├── interface.py
├── registry.py
├── chronological.py
└── implementations/
    └── interval.py
```

The base `Trigger` interface stays at the trigger package root because
it represents the entire trigger category.

`ChronologicalTrigger` can also remain directly under `triggers/`: it is
a small shared mechanism interface, and a deeper subpackage would add
structure without currently reducing complexity.

If a trigger mechanism later grows enough to own several support
modules, it can then become a mechanism-specific subpackage.

------------------------------------------------------------------------

## Testing

Shared trigger infrastructure tests should cover discovery,
registration, duplicate handling, lookup, and unknown plugin handling.

`IntervalTrigger` tests should cover:

-   Valid configuration.
-   Missing or malformed interval configuration.
-   Zero and negative intervals.
-   Correct next-occurrence calculation.
-   Relevant edge cases.

Application integration tests should separately verify:

-   Unknown trigger types are rejected during definition creation.
-   Configuration validation occurs during definition creation.
-   Chronological triggers receive chronological initialization.
-   Non-chronological mechanisms do not receive chronological state.
-   Due triggers resolve the correct plugin.
-   Scheduling failures roll back according to the Application
    transaction design.

`FOR UPDATE SKIP LOCKED` and multi-Scheduler concurrency are
Persistence/Application integration concerns, not plugin unit-test
concerns.

------------------------------------------------------------------------

## Adding Future Triggers

A new chronological plugin should normally require only another
implementation:

``` python
class CronTrigger(ChronologicalTrigger):
    ...
```

Existing chronological Application, Persistence, and Scheduler
infrastructure should host it without changes.

A fundamentally different mechanism such as webhooks may legitimately
require a new mechanism interface, Application capability, persistence
support if necessary, runtime/API entry point, and initialization
dispatch entry if initialization is needed.

That does not violate the plugin architecture. Extensibility applies
within a supported mechanism; the platform does not force unrelated
mechanisms through one runtime model.

The central rule is:

> **Trigger plugins define trigger-specific behavior. Mechanism-specific
> Application services provide the platform behavior required to host
> them.**
