# Persistence

## Purpose

The Persistence Layer stores, reconstructs, and safely transitions
platform state while hiding database implementation details from the
rest of the system.

Application code does not perform SQL directly and remains unaware of
SQLAlchemy models, PostgreSQL-specific queries, sessions, connection
management, or locking syntax. Persistence exposes repositories and
transactional operations that work with Domain objects or narrowly
scoped persistence operation models rather than database rows.

> **Persistence answers: How is application state stored, retrieved, and
> transitioned safely?**

## Responsibilities

Persistence owns:

-   Workflow definition, workflow execution, and chronological scheduling persistence.
-   Reconstruction of Domain objects from stored data.
-   Targeted persistence operations required by Application use cases.
-   Concurrency-sensitive state transitions and database locking.
-   Execution dependency state.
-   Sessions and Unit of Work transaction infrastructure.
-   Mapping between Domain objects and SQLAlchemy models.
-   Isolation of SQLAlchemy and PostgreSQL from other layers.

Persistence does **not** own workflow orchestration, plugin execution,
trigger occurrence calculation, `TaskContext` construction, `TaskResult`
interpretation, queue claims/leases/heartbeats, Worker or Scheduler
lifecycle, polling, HTTP routing, or API schemas.

It provides the durable state and concurrency primitives those systems
require without implementing their business behavior.

## Design Principles

### Infrastructure Encapsulation

SQLAlchemy models, sessions, SQL expressions, and PostgreSQL-specific
behavior remain internal to Persistence. Application can, for example,
request the next due chronological trigger without knowing that
PostgreSQL uses `FOR UPDATE SKIP LOCKED` to select it safely.

### Domain Independence

Domain models remain independent of SQLAlchemy. Persistence translates
between Domain and database representations rather than attaching
persistence behavior to Domain objects.

Database tables do not need a one-to-one Domain representation.
Chronological scheduling state, for example, is durable infrastructure
state used by Persistence and Application and does not need to become
part of the core workflow Domain.

> **Database tables do not need to correspond one-to-one with Domain objects.**

Persistence may maintain durable state that exists solely to support infrastructure or Application operations. Such state should become part of the Domain only when it represents a genuine Domain concept, not merely because it is persisted.

### Aggregate and Targeted Persistence

Repositories own persistence for major aggregate roots:

-   A `WorkflowDefinition` contains Task Definitions and Trigger
    Definitions.
-   A `WorkflowExecution` contains Task Executions.

Repositories can persist or reconstruct complete aggregates when a use
case requires them. Runtime-heavy operations instead use narrowly scoped
methods that retrieve or modify only the necessary state.

This avoids unnecessarily performing:

``` text
load complete aggregate
    ↓
change one small piece of state
    ↓
save complete aggregate
```

when a targeted operation is safer and more efficient.

### Atomic State Transitions

Persistence implements concurrency-sensitive changes using database
operations and PostgreSQL concurrency primitives. Examples include
conditional task transitions, atomic dependency-counter updates,
workflow failure and cancellation, and row locking for due chronological
triggers.

Application coordinates **what** should happen. Persistence owns the SQL
and locking required to make the persisted transition safe.

### Transactional Composition

A business transition may require several repository operations.
Operations executed through the same Unit of Work share one database
transaction and become durable together when committed.

For example:

``` text
lock due trigger
    ↓
advance scheduling state
    ↓
create WorkflowExecution
    ↓
commit
```

Multiple repositories participate, but the persistence changes form one
atomic transaction.

## Architecture

``` mermaid
flowchart TD
    Application["Application Service"]
    UOW["Unit of Work"]
    Repository["Repository"]
    Mapper["Mapper"]
    Session["SQLAlchemy Session"]
    Engine["SQLAlchemy Engine"]
    DB[(PostgreSQL)]

    Application --> UOW
    UOW --> Repository
    Repository --> Mapper
    Repository --> Session
    Session --> Engine
    Engine --> DB
```

Application services define business-level transaction boundaries. A
Unit of Work provides repositories sharing one SQLAlchemy Session.
Repositories implement persistence operations within that transaction.

## Repository API

Current repositories are:

-   `WorkflowDefinitionRepository`
-   `WorkflowExecutionRepository`
-   `ChronologicalTriggerRepository`

Their APIs are designed around Application use cases rather than generic
table-level CRUD.

See:

- [Database and Unit of Work](database-and-uow.md)
- [Database Schema](database-schema.md)
- [Workflow Definitions](workflow-definitions.md)
- [Workflow Executions](workflow-executions.md)
- [Chronological Triggers](chronological-triggers.md)

## Persistence Operation Models

Targeted operations may accept or return persistence-specific
request/result dataclasses such as:

-   `StartTaskExecutionResult`
-   `CompleteTaskExecutionRequest`
-   `CompleteTaskExecutionResult`
-   `RetryTaskExecutionRequest`
-   `RetryTaskExecutionResult`
-   `DueChronologicalTrigger`

These are neither Domain objects nor SQLAlchemy models. They define
persistence operation boundaries and allow Persistence to return exactly
what an Application use case requires without exposing database rows or
reconstructing unnecessary aggregates.

## Object Mapping

Persistence distinguishes three kinds of representation:

**Domain objects** represent platform concepts independently of
persistence technology, including `WorkflowDefinition`,
`TaskDefinition`, `TriggerDefinition`, `WorkflowExecution`,
`TaskExecution`, and `TaskOutput`.

**SQLAlchemy models** represent tables, columns, foreign keys,
relationships, constraints, and PostgreSQL-specific storage types. They
remain internal to Persistence. Chronological scheduling state has a
SQLAlchemy model despite having no corresponding core Domain object.

**Mappers** translate between Domain objects and SQLAlchemy models.
Repositories coordinate persistence behavior; mappers perform
representation conversion and do not execute SQL. Mapped values include
workflow/task/trigger definitions, workflow/task executions, and JSONB
plugin configuration and task output.

Persistence stores plugin configuration but does not interpret it.
Chronological scheduling state needs no Domain mapper because its
repository works with the internal persistence model and exposes
targeted operation results.

## Queue and Runtime Boundaries

Persistence does not enqueue, claim, finish, or remove execution queue
entries. This keeps workflow persistence independent of a particular
queue implementation.

``` text
Persistence → durable state
Application → business consequences
Runtime / Queue → delivery and worker ownership
```

A future replacement of a PostgreSQL-backed queue with an external
broker should not require redesigning workflow execution or
chronological scheduling persistence.

Runtime processes that use Persistence generally:

1.  Load configuration.
2.  Create the SQLAlchemy Engine.
3.  Create the Session Factory.
4.  Create the Unit of Work Factory.
5.  Construct required Application services.
6.  Begin runtime-specific processing.

Repositories are created by each Unit of Work around its shared Session.
Worker, Reconciler, and Scheduler processes may each maintain their own
Engine and connection pool while using the same PostgreSQL database.

## Package Organization

``` text
persistence/
│
├── database/
│   ├── __init__.py
│   ├── sqlalchemy_uow.py
│   └── unit_of_work.py
│
├── workflow_definitions/
│   ├── __init__.py
│   ├── repository.py
│   ├── _mapper.py
│   └── _model.py
│
├── workflow_executions/
│   ├── __init__.py
│   ├── repository.py
│   ├── operations.py
│   ├── _mapper.py
│   └── _model.py
│
├── chronological_triggers/
│   ├── __init__.py
│   ├── repository.py
│   ├── operations.py
│   └── _model.py
│
└── __init__.py
```

Packages are organized around aggregates and durable persistence
concerns. A package does not imply that its state must be a core Domain
concept. Targeted request/result models may live separately from
repository implementations.

## Testing Strategy

Persistence is tested independently from Application orchestration.

Unit tests are appropriate for mapper conversions, small deterministic
repository helpers, and Unit of Work behavior.

Behavior dependent on SQL semantics must be tested against real
PostgreSQL, especially conditional transitions, dependency updates,
concurrent completion/failure, chronological row locking, and
`SKIP LOCKED` behavior. PostgreSQL concurrency guarantees should not be
inferred from mocks.

A smaller cross-layer suite should exercise Application services against
real Persistence to verify execution graph creation, task progression,
parent outputs, retries, terminal failure, chronological initialization,
atomic schedule advancement plus execution creation, and overdue
catch-up behavior.

Queue and runtime lifecycle integration remains separate from
Persistence testing.

## What Does Not Belong Here

Persistence should not contain:

- Application orchestration.
- `TaskContext` construction or `TaskResult` interpretation.
- Task or trigger plugin resolution and execution.
- Trigger occurrence calculation.
- Queue claims, leases, or heartbeats.
- Worker or Scheduler loops and polling.
- HTTP routing or API schemas.

Persistence exposes the durable state operations, transaction boundaries, and concurrency primitives these systems require without implementing their responsibilities.

## Future Evolution

Possible improvements include Alembic migrations, optimized targeted
reads, bulk operations, query profiling, additional indexes, read/write
separation, archival or partitioning of execution history, alternative
persistence implementations, and execution-attempt or fencing state if
stronger task concurrency guarantees become necessary.

Scheduling-specific infrastructure should likewise be introduced only
for concrete requirements. The current design intentionally does not
require Scheduler leases, heartbeat state, claim tokens, generic
trigger-state JSON, or distributed locks.

Future changes should remain internal to Persistence wherever possible,
and public persistence abstractions should evolve from concrete
Application requirements rather than prematurely exposing database
implementation details.
