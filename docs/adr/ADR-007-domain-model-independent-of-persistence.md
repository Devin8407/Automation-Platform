# ADR-006: Domain Model Independent of Persistence

## Status

Accepted

## Context

The Automation Platform requires persistent storage while maintaining a clean separation between business logic and infrastructure.

A decision was required regarding whether domain objects should also serve as SQLAlchemy models or whether persistence concerns should be isolated from the Domain Layer.

## Decision

The platform will maintain separate domain objects and persistence models.

Domain objects represent business concepts used throughout the Application Layer.

Persistence models represent the relational schema used by SQLAlchemy and PostgreSQL.

Repositories are responsible for translating between the two representations through dedicated mappers.

## Alternatives Considered

### Shared Domain and Persistence Models

Use the same classes for both business logic and SQLAlchemy persistence.

**Pros**

- Less code
- Simpler initial implementation
- Common for CRUD-oriented applications

**Cons**

- Couples business logic to SQLAlchemy
- Makes infrastructure concerns visible throughout the system
- Harder to evolve persistence independently
- Reduces separation of concerns

### Separate Domain and Persistence Models (Selected)

Maintain distinct domain objects and persistence models.

**Pros**

- Clear separation between business logic and persistence
- Domain remains independent of SQLAlchemy
- Easier testing of business logic
- Persistence implementation can evolve independently

**Cons**

- Requires object mapping
- Additional implementation effort

## Consequences

### Positive

- Domain remains infrastructure independent
- SQLAlchemy is isolated to the Persistence Layer
- Repository responsibilities are clearly defined
- Supports future persistence changes

### Negative

- Additional mapping code
- Slightly increased complexity

Separating the domain model from persistence models reinforces architectural boundaries while keeping infrastructure concerns isolated from business logic.
