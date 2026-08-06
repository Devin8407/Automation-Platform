# Workflow Definition Management

## Purpose

The `workflow_definitions` capability manages reusable workflow definitions. It validates definitions, constructs Domain objects, coordinates persistence, and initializes any mechanism-specific state required by their triggers.

A created Workflow Definition is the reusable structure from which future Workflow Executions are compiled.

## Responsibilities

The capability owns:

- Workflow definition creation and deletion
- Task and trigger definition validation
- Dependency graph validation
- Plugin configuration validation coordination
- Trigger initialization coordination
- Definition-creation transaction boundaries

Plugins remain responsible for plugin-specific configuration validation. Persistence remains responsible for storing and reconstructing definitions.

## Creation Input and Validation

Creation accepts Application-level input describing workflow metadata, task definitions, trigger definitions, and enabled state. The complete definition is validated before commit.

### Task Validation

A valid task graph satisfies all of the following:

- At least one task exists.
- Task keys are unique.
- Task plugin types are registered.
- Plugin configurations are valid.
- Retry counts are valid.
- Dependencies reference existing tasks.
- Tasks do not depend on themselves.
- Dependencies are not duplicated.
- The dependency graph contains no cycles.

The workflow therefore reaches Persistence as a valid directed acyclic graph.

### Trigger Validation

Trigger validation ensures that plugin types are registered and configurations are valid. Plugin-specific validation is delegated to:

```text
plugin.validate_configuration(configuration)
```

Workflow definition creation translates plugin validation failures into the appropriate Application error.

Validation answers **"Is this a valid workflow definition?"** It is separate from initializing runtime state required by a trigger mechanism.

### Trigger Resolution During Creation

Trigger plugins are resolved during validation. The resolved plugin stays associated with the `TriggerDefinition` created from that input so initialization does not immediately repeat the registry lookup.

```text
CreateTriggerDefinition
        |
        +-- resolve plugin
        +-- validate configuration
        |
        v
TriggerDefinition + resolved plugin
```

That pair is passed to trigger initialization.

## Definition Creation Transaction

After validation and Domain construction, creation owns this Unit of Work:

```text
BEGIN UoW
    |
    +-- save WorkflowDefinition
    |       +-- TaskDefinitions
    |       +-- TriggerDefinitions
    |
    +-- flush
    +-- initialize trigger runtime state
    +-- commit
```

### Why `flush()` Is Required

Some trigger mechanisms need persistence state that references a newly created Trigger Definition. Chronological triggers are the first example: their scheduling-state foreign key requires the Trigger Definition to already exist in PostgreSQL.

```text
persist definition
        |
        v
flush
        |
        v
initialize trigger state
        |
        v
commit
```

`flush()` sends pending changes to the database **without committing the transaction**. If initialization fails, the entire definition-creation transaction still rolls back.

## Invariant: Atomic Definition Initialization

> **A successfully persisted trigger definition also has any runtime state required by its trigger mechanism.**

For a chronological trigger:

```text
WorkflowDefinition
        +
TriggerDefinition
        +
ChronologicalTriggerState
        =
one transaction
```

The Scheduler therefore does not need to discover and repair newly created chronological definitions that were persisted without scheduling state.

## Trigger Initialization Boundary

Workflow definition management does not know how chronological scheduling works. It delegates mechanism-specific initialization to `TriggerInitializationService`, supplying:

- The resolved trigger implementation
- The corresponding Trigger Definition
- The existing Unit of Work

Initialization participates in the caller's transaction; it does not open or commit its own. See [Trigger Initialization](trigger-initialization.md).

## Ownership Boundaries

| Component | Owns |
| --- | --- |
| Workflow definition management | Definition validation, Domain construction, creation transaction, initialization coordination |
| Plugins | Plugin-specific configuration validation |
| Persistence | Definition storage, SQL, foreign-key enforcement, transaction participation |
| Trigger mechanism services | Mechanism-specific initialization behavior |

This keeps generic definition management from accumulating knowledge about every trigger mechanism.

## Testing Strategy

Important Application-level scenarios include:

- Invalid task and trigger definitions are rejected.
- Plugin configuration validation is invoked.
- Duplicate task keys, invalid dependencies, and dependency cycles are rejected.
- Trigger initialization receives the same Unit of Work as definition creation.
- Initialization failure prevents definition creation from committing.
- Successfully created chronological definitions receive required scheduling state.

Database-specific persistence behavior belongs to Persistence integration tests.
