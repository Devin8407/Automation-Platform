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

Queue ownership will be represented using renewable leases.

Claiming work assigns:

- worker identifier
- claim token
- claim timestamp
- heartbeat timestamp

Workers periodically renew their lease using heartbeats.

If a lease expires, another worker may safely reclaim the task.

Every queue operation that modifies ownership validates the current claim token before performing any changes.

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
