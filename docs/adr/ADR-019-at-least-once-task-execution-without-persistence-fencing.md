# ADR-019: At-Least-Once Task Execution Without Persistence Fencing

## Status

Accepted

## Context

The Execution Queue uses renewable leases to coordinate Worker ownership.

A worker may lose its lease while executing a task. After lease expiration, another worker may reclaim the same queue entry and begin processing the same logical TaskExecution.

Queue ownership and persisted workflow state are intentionally separate.

Persistence does not know:

- Which worker currently owns a queue claim.
- Whether a queue lease remains valid.
- Which claim token identifies the current lease.

Therefore two workers may, in a narrow recovery window, physically execute the same logical task concurrently.

Conditional persistence transitions prevent terminal task state from being overwritten after one valid terminal transition succeeds, but they do not provide strict fencing between physical execution attempts.

A stronger design would require sharing an execution generation or fencing token between queue ownership and persisted task state.

## Decision

The platform will currently provide at-least-once physical task execution semantics and will not introduce queue-lease fencing into Persistence.

Queue lease ownership remains exclusively a Queue concern.

Persisted workflow state remains exclusively a Persistence concern.

Persistence uses conditional state transitions to ensure that stale workers cannot overwrite already-terminal task state.

Workers should stop processing when they discover that their queue lease has been lost, but lease checks are not treated as a strict correctness fence because ownership may change immediately after a check.

Task plugins that perform externally visible side effects should therefore be designed to tolerate duplicate physical execution where practical.

Strict fencing tokens or execution-attempt generations are deferred until stronger execution guarantees are required.

## Alternatives Considered

### Persist Queue Claim Tokens with TaskExecution

**Pros**

- Persistence could reject commits from workers that no longer own the lease.
- Provides stronger attempt ownership semantics.

**Cons**

- Couples Persistence to Queue ownership.
- Duplicates ephemeral queue state in durable workflow state.
- Introduces synchronization between two independently transactional systems.
- Complicates future queue replacement.

### Execution Generation / Fencing Tokens

**Pros**

- Provides strict ordering between execution attempts.
- Allows stale attempts to be rejected durably.
- Stronger protection for concurrent recovery races.

**Cons**

- Adds meaningful execution-state complexity.
- Requires coordination between queue delivery and Persistence.
- Not currently justified by platform requirements.

### Separate Queue Ownership and Persistence State (Selected)

**Pros**

- Preserves clean subsystem boundaries.
- Queue implementation remains replaceable.
- Persistence remains independent of delivery mechanics.
- Current conditional transitions prevent stale terminal overwrites.
- Simpler implementation.

**Cons**

- Duplicate physical plugin execution is possible.
- Exactly-once external side effects are not guaranteed.
- A narrow race remains regarding which valid terminal result wins.
- Plugins may require idempotency for safe external side effects.

## Consequences

### Positive

- Queue and Persistence remain independently evolvable.
- RabbitMQ or another broker can replace PostgreSQL queueing without adding queue-specific state to TaskExecution.
- Concurrency complexity remains appropriate for the current project scope.
- Stronger fencing can be introduced later without pretending the current system provides exactly-once execution.

### Negative

- Lease expiration may cause multiple workers to execute the same logical task.
- Conditional persistence transitions protect durable terminal state but cannot undo duplicate external side effects.
- Strict execution-attempt ownership is not guaranteed.

The platform explicitly chooses clean queue/persistence separation and at-least-once physical execution semantics over introducing persistence-level fencing at the current stage.
