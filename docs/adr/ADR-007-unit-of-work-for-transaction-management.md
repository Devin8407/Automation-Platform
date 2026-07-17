# ADR-007: Unit of Work for Transaction Management

## Status

Accepted

## Context

Many business operations require coordinated updates across multiple repositories.

Examples include:

- Processing a task
- Starting a workflow
- Cancelling a workflow

A decision was required regarding how transactional consistency should be managed without exposing SQLAlchemy sessions to the Application Layer.

## Decision

The platform will use the Unit of Work pattern to define transactional boundaries.

Each business operation creates a new Unit of Work.

The Unit of Work owns a SQLAlchemy Session and constructs repositories that participate in the same transaction.

Application services depend only on a Unit of Work Factory and remain unaware of SQLAlchemy sessions.

## Alternatives Considered

### Repository-Owned Sessions

Allow each repository operation to create and manage its own database session.

**Pros**

- Very simple implementation
- Repositories remain independent

**Cons**

- Multiple repositories cannot participate in a single transaction
- Difficult to guarantee consistency
- Transaction boundaries become fragmented

### Application-Owned Sessions

Allow application services to create SQLAlchemy sessions and pass them to repositories.

**Pros**

- Supports shared transactions
- Straightforward implementation

**Cons**

- Leaks persistence concerns into the Application Layer
- Couples business logic to SQLAlchemy
- Weakens architectural separation

### Unit of Work (Selected)

Manage transactions through a dedicated Unit of Work abstraction.

**Pros**

- Centralized transaction management
- Shared transaction across repositories
- Keeps SQLAlchemy hidden from the Application Layer
- Clear business-operation boundaries

**Cons**

- Additional abstraction
- Slightly more initialization complexity

## Consequences

### Positive

- Business operations execute atomically
- Repository implementations remain simple
- Application services remain persistence independent
- Supports future expansion to additional repositories

### Negative

- Requires Unit of Work infrastructure
- Additional object creation per business operation

The Unit of Work pattern establishes clear transactional boundaries while preserving separation between application logic and persistence infrastructure.
