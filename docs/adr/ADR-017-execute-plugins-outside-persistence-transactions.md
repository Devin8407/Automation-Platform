# ADR-017: Execute Plugins Outside Persistence Transactions

## Status

Accepted

## Context

Task plugins may perform arbitrary and potentially long-running work, including external I/O.

Task processing requires durable persistence operations both before and after plugin execution:

- Establishing that the task is processable.
- Recording the resulting success or failure.

One option was to execute the plugin while holding the same persistence transaction open.

This would keep the processing sequence inside one transaction but could hold database connections and locks for the entire duration of arbitrary plugin execution.

## Decision

Task plugins will execute outside persistence transactions.

Task processing is divided into separate phases:

1. Open a persistence transaction.
2. Start or recover the TaskExecution and load the execution data required by the plugin.
3. Commit and close the persistence transaction.
4. Execute the plugin without an open persistence transaction.
5. Open a new persistence transaction.
6. Persist the successful or failed execution result using targeted state-transition operations.
7. Commit and close the transaction.

Application services own these transaction boundaries.

No SQLAlchemy Session or Unit of Work remains open for the duration of arbitrary plugin execution.

## Alternatives Considered

### Execute Plugin Inside Persistence Transaction

**Pros**

- Simpler sequential transaction model.
- All processing appears inside one transaction.

**Cons**

- Holds database connections during arbitrary work.
- May hold locks for long periods.
- Reduces database concurrency.
- External operations may take seconds, minutes, or fail unpredictably.
- Couples transaction lifetime to plugin implementation behavior.

### Execute Plugin Outside Persistence Transactions (Selected)

**Pros**

- Database transactions remain short.
- Connections are released during long-running work.
- Database locks are not held during external I/O.
- Plugin duration does not determine transaction duration.
- Supports concurrent workers more effectively.

**Cons**

- Task processing spans multiple transactions.
- Worker failure between phases must be recoverable.
- Another worker may recover the same logical task after lease expiration.

## Consequences

### Positive

- Persistence transactions remain bounded and predictable.
- Long-running plugins do not consume database resources unnecessarily.
- Worker concurrency is improved.
- Plugin execution remains independent of SQLAlchemy session lifetime.

### Negative

- Task execution cannot be treated as one database transaction.
- Crash and recovery behavior between phases must be explicitly supported.
- Exactly-once physical plugin execution is not guaranteed.

Plugin execution is intentionally treated as external work surrounded by short durable state transitions rather than as work performed inside a database transaction.
