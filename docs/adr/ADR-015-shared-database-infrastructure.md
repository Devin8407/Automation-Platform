# ADR-015: Shared Database Infrastructure

## Status

Accepted

---

## Context

Both the Persistence Layer and the PostgreSQL Queue implementation require access to the same database infrastructure.

Originally, SQLAlchemy infrastructure was owned by the Persistence Layer.

As the Queue evolved into an independent infrastructure component, it became clear that Queue should not depend upon Persistence simply to obtain database connectivity.

A decision was required regarding ownership of shared SQLAlchemy infrastructure.

---

## Decision

Database infrastructure will be owned by a dedicated Infrastructure package.

Infrastructure is responsible for constructing and exposing:

- SQLAlchemy Engine
- SessionFactory
- Declarative Base

Persistence and Queue depend upon Infrastructure.

Neither depends upon the other.

Infrastructure contains no business logic.

---

## Alternatives Considered

### Persistence Owns SQLAlchemy Infrastructure

**Pros**

- Fewer packages.
- Simpler initial implementation.

**Cons**

- Queue depends on Persistence.
- Blurs architectural boundaries.
- Makes independent infrastructure evolution more difficult.

---

### Shared Infrastructure Package (Selected)

**Pros**

- Clear ownership.
- Removes coupling between Queue and Persistence.
- Supports multiple infrastructure consumers.
- Simplifies future infrastructure additions.

**Cons**

- Introduces another package.
- Slightly increases project structure.

---

## Consequences

### Positive

- Infrastructure concerns are centralized.
- Queue and Persistence remain independent.
- SQLAlchemy configuration has a single owner.
- Future infrastructure components can reuse the same facilities.

### Negative

- Additional architectural layer to maintain.

Centralizing database infrastructure preserves clean dependency direction while allowing multiple infrastructure components to share common SQLAlchemy configuration without introducing coupling.
