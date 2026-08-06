# Database and Unit of Work

## Purpose

The database package owns SQLAlchemy transaction infrastructure. It
gives Application services an explicit Unit of Work without exposing the
underlying Session.

## Unit of Work

A Unit of Work defines a database transaction boundary. Repositories
participating in the same Unit of Work share one SQLAlchemy Session.

``` text
with uow_factory() as uow:
    persistence operation
    persistence operation
    persistence operation

    uow.commit()
```

All operations performed through that Unit of Work participate in the
same transaction. If an exception occurs before commit, the transaction
is rolled back. The session is closed when the Unit of Work exits.

## Transaction Ownership

The top-level Application operation owns the Unit of Work for a business
transaction. Nested Application operations may participate in the
caller's Unit of Work when several operations must commit atomically.

For example:

``` text
ChronologicalTriggerService.process_next_due()
        │
        │ owns UoW
        │
        ├── ChronologicalTriggerRepository
        │       updates scheduling state
        │
        └── WorkflowStartService
                creates WorkflowExecution
                using same UoW
```

Persistence does not decide which business operations belong in one
transaction. Application makes that decision and composes repository
operations through the shared Unit of Work.

## Explicit Flushing

The Unit of Work exposes `flush()` when later operations in the same
transaction depend on rows already staged for persistence.

Workflow definition creation is one example because chronological
scheduling state references a persisted `TriggerDefinition` through a
foreign key:

``` text
save WorkflowDefinition
    ↓
save TriggerDefinitions
    ↓
flush
    ↓
create ChronologicalTriggerState
    ↓
commit
```

Flushing sends pending SQL to PostgreSQL without committing. The
transaction remains atomic.

If trigger initialization fails after the flush:

``` text
definitions flushed
    ↓
initialization fails
    ↓
ROLLBACK
    ↓
definitions and scheduling state are not persisted
```

Application uses the Unit of Work's public `flush()` operation rather
than accessing the SQLAlchemy Session directly.

## Database Lifecycle

Each independently running process creates its own SQLAlchemy Engine
during startup. The Engine maintains a reusable connection pool for that
process.

Application operations create Units of Work as needed. A Unit of Work
uses a Session, which obtains a connection from the Engine pool when
database work occurs. When the transaction finishes and the Session
closes, the connection returns to the pool.

Long-running Workers, Reconcilers, and Schedulers should not retain
database transactions or connections unnecessarily between operations.

## Transactional Locking

Repository operations may execute multiple SQL statements inside one
transaction. PostgreSQL locks acquired by those statements remain held
until the transaction completes; they are not released between
repository calls or statements.

For example, terminal workflow failure can perform:

``` text
UPDATE workflow -> FAILED
UPDATE remaining tasks -> CANCELLED
COMMIT
```

Chronological scheduling uses the same transactional principle
explicitly with:

``` sql
FOR UPDATE SKIP LOCKED
```

In both cases, database locking remains internal to Persistence while
Application composes the larger business operation.

## Concurrency Boundary

Persistence owns concurrency for **persisted state**, not runtime
process coordination.

For long-running task execution, queue ownership concepts such as claim
tokens, worker identifiers, heartbeats, lease expiration, and claim
recovery belong to the execution queue.

For short chronological scheduling work, the PostgreSQL transaction and
row lock are sufficient.

``` text
Long-running task execution
    ↓
durable queue lease

Short scheduling transaction
    ↓
PostgreSQL row lock
```

These systems intentionally use different concurrency models.
