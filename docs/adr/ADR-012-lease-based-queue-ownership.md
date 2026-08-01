# ADR-009: Lease-Based Queue Ownership

## Status

Accepted

---

## Context

Workers execute tasks that may take an arbitrary amount of time.

The queue must recover abandoned work after worker crashes while preventing multiple workers from simultaneously owning the same task.

A permanent ownership model cannot safely distinguish between an active worker and a crashed worker.

A decision was required regarding how queue ownership should be represented.

---

## Decision

## Decision

Queue ownership is represented using renewable leases.

Claiming work assigns:

- Worker identifier
- Claim token
- Claim timestamp
- Heartbeat timestamp

The claim token uniquely identifies the current lease owner and is regenerated whenever a task is claimed or reclaimed.

Workers periodically renew their lease by updating the heartbeat timestamp.

If a lease expires, another worker may safely reclaim the task by obtaining a new lease and claim token.

Every queue operation that modifies queue state—including heartbeat, release, and finish—validates both the task execution identifier and the current claim token before performing any changes.

Queue operations whose claim validation fails become no-ops, preventing stale workers from modifying queue state after ownership has transferred.

Queue ownership is intentionally temporary rather than permanent, allowing abandoned work to be recovered automatically while guaranteeing that at most one worker holds the active lease for a runnable task.

---

## Alternatives Considered

### Permanent Claims

**Pros**

- Simple implementation.
- Minimal metadata.

**Cons**

- Crashed workers permanently block work.
- Manual intervention required.

---

### Lease-Based Ownership (Selected)

**Pros**

- Automatic recovery after crashes.
- Safe lease stealing.
- Prevents stale workers from modifying queue state.
- Works for both PostgreSQL and RabbitMQ implementations.

**Cons**

- Requires heartbeat mechanism.
- Additional queue metadata.
- Requires claim validation.

---

## Consequences

### Positive

- Queue ownership becomes fault tolerant.
- Workers safely detect lost ownership.
- Stale workers cannot complete queue operations.
- Queue abstraction remains independent of persistence.

### Negative

- Heartbeat traffic is required.
- Lease timeout must be configured appropriately.

Representing ownership as renewable leases allows abandoned work to be recovered automatically while maintaining a single active owner for every runnable task.
