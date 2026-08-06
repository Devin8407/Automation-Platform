# Trigger Initialization

## Purpose

Different trigger mechanisms may require different durable state when a Trigger Definition is created.

`TriggerInitializationService` is the Application-level dispatch point between generic workflow-definition creation and mechanism-specific initialization. It keeps Workflow Definition management unaware of the persistence requirements of individual trigger mechanisms.

```text
WorkflowDefinitionService
        |
        | resolved plugin + TriggerDefinition + UoW
        v
TriggerInitializationService
        |
        | mechanism dispatch
        v
mechanism-specific Application capability
```

The service answers:

> **Does this trigger mechanism require initialization, and if so, which Application capability performs it?**

## Inputs and Transaction Ownership

Initialization receives:

- The already-resolved trigger plugin class
- Its `TriggerDefinition`
- The caller's existing Unit of Work

It does **not** resolve the plugin again, revalidate configuration, open another Unit of Work, or commit the transaction. The caller retains ownership of the definition-creation transaction.

For a chronological trigger:

```text
BEGIN
    |
    +-- persist WorkflowDefinition
    +-- persist TriggerDefinition
    +-- flush
    |
    +-- TriggerInitializationService
    |       |
    |       v
    |   ChronologicalTriggerService.initialize()
    |       |
    |       +-- create chronological scheduling state
    |
    +-- COMMIT
```

If initialization fails, the complete definition creation rolls back. This prevents a successfully persisted definition from missing state required by its mechanism.

## Validation vs. Initialization

These are deliberately separate responsibilities:

- **Validation:** Is this trigger definition valid?
- **Initialization:** What durable state does this valid trigger mechanism require?

Plugin configuration validation occurs before persistence begins. Initialization occurs after the Trigger Definition has been staged and flushed. This separation also naturally supports mechanisms that require no durable initialization.

## Mechanism-Based Dispatch

Dispatch is based on trigger mechanism interfaces, not individual plugin names.

For example:

```text
IntervalTrigger
        |
        | subclass of
        v
ChronologicalTrigger
        |
        v
ChronologicalTriggerService.initialize()
```

Conceptually, the dispatcher maps:

```text
ChronologicalTrigger
        ->
ChronologicalTriggerService.initialize
```

It does **not** maintain entries such as:

```text
interval -> initialize
cron     -> initialize
daily    -> initialize
```

This is the key extensibility property. If a future `CronTrigger` implements `ChronologicalTrigger`, it automatically follows the existing chronological initialization path; no `CronTrigger`-specific dispatch entry is required.

### Extension Example

A new trigger plugin does not necessarily require a new initialization path.

For example, if `CronTrigger` implements the existing `ChronologicalTrigger` mechanism, initialization can recognize it through that mechanism and create the same kind of chronological scheduling state used by other chronological triggers.

The plugin remains responsible for its trigger-specific behavior, while the application layer remains responsible for mechanism-level initialization and transaction coordination.

A new initialization path is needed only when a trigger introduces a genuinely new mechanism with different durable state or initialization requirements.

## Why the Type Hierarchy Is the Source of Truth

Mechanism interfaces already encode the information required for dispatch:

```text
IntervalTrigger
    is a ChronologicalTrigger
```

Adding a separate field such as:

```text
mechanism = CHRONOLOGICAL
```

would duplicate information already represented by the type system. Interface relationships therefore remain the source of truth for mechanism-specific hosting behavior.

## Mechanisms Without Initialization

A valid trigger plugin that does not match a mechanism requiring initialization produces no operation.

There is intentionally no artificial interface such as `NoInitializationTrigger` and no enum value for "no initialization." Absence of required initialization is represented by the absence of a matching initialization capability.

## Architectural Boundary

`TriggerInitializationService` is intentionally small because it owns one architectural policy:

> **Generic definition creation delegates initialization according to supported trigger mechanism interfaces.**

It should not become a generic trigger orchestration framework. Runtime processing belongs to mechanism-specific capabilities such as `ChronologicalTriggerService`.

## Future Mechanisms

A future mechanism may introduce its own Application capability:

```text
WebhookTrigger
        |
        v
WebhookTriggerService
```

If webhook definitions require initialization, that mechanism can be added to initialization dispatch. If they do not, no initialization entry is necessary.

Different trigger mechanisms can therefore use different platform infrastructure without being forced behind an artificial generic trigger lifecycle.

## Testing Strategy

Important scenarios include:

- Chronological trigger implementations dispatch to chronological initialization.
- The existing Unit of Work is passed through unchanged.
- Configuration is not revalidated.
- The plugin is not resolved again.
- A supported trigger requiring no initialization produces no operation.
- New implementations of an existing mechanism use that mechanism's existing initialization path.

Mechanism-specific initialization behavior belongs to the corresponding capability tests.
