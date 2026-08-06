# Workflow Definition Persistence

## Purpose

`WorkflowDefinitionRepository` persists and reconstructs the complete
reusable workflow definition aggregate.

A workflow definition contains its Task Definitions and Trigger
Definitions, including task dependency relationships.

## Responsibilities

The repository supports:

-   Loading workflow definitions.
-   Saving workflow definitions.
-   Deleting workflow definitions.
-   Synchronizing task definitions.
-   Synchronizing trigger definitions.
-   Persisting task dependency relationships.

Its API represents aggregate persistence rather than generic CRUD over
individual tables.

## Aggregate Synchronization

Saving a workflow definition synchronizes its persisted child entities
with the supplied aggregate state.

Conceptually:

``` text
WorkflowDefinition
├── TaskDefinition
├── TaskDefinition
└── TriggerDefinition
```

is treated as one reusable definition aggregate when a complete save or
load is required.

The repository and its mapper translate between Domain objects and
internal SQLAlchemy models. SQLAlchemy relationships, JSONB
configuration storage, foreign keys, and other database details remain
inside Persistence.

Plugin configuration is persisted but not interpreted by Persistence.

## Trigger Initialization and Flush

Some trigger mechanisms require durable state beyond the reusable
Trigger Definition. Chronological triggers are the current example.

Chronological scheduling state references a persisted
`TriggerDefinition`, so creation may require:

``` text
save WorkflowDefinition
    ↓
save TriggerDefinitions
    ↓
flush
    ↓
initialize chronological scheduling state
    ↓
commit
```

`flush()` makes the staged definition rows available to later SQL in the
same transaction without committing them.

Workflow Definition, Trigger Definition, and chronological scheduling
state therefore remain atomic: if initialization fails after the flush,
the transaction rolls back all of them.

> **A successfully persisted chronological Trigger Definition has the
> durable scheduling state required to execute it.**

Trigger initialization itself is coordinated by Application. The
workflow definition repository persists the aggregate;
mechanism-specific persistence remains owned by the relevant persistence
package.

## Mapping

The workflow definition mapper handles representations such as:

-   `WorkflowDefinition`
-   `TaskDefinition`
-   `TriggerDefinition`
-   Task dependency relationships
-   JSONB task configuration
-   JSONB trigger configuration

Mappers perform representation conversion and do not execute SQL.

## Testing

PostgreSQL integration tests should verify:

-   Workflow definition persistence and reconstruction.
-   Task and trigger synchronization.
-   Dependency persistence.
-   Deletion behavior.
-   Atomic creation when trigger initialization also writes durable
    state.

Mapper conversions can be tested independently where useful.
