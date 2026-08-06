# ADR-020: Explicit Runtime Configuration and Composition Roots

## Status

Accepted

## Context

The Automation Platform has multiple independently executable Runtime processes, including:

- Worker
- Reconciler
- Scheduler
- API server

These processes require configuration and infrastructure such as:

- Database settings.
- Queue configuration.
- Runtime polling intervals.
- Lease and heartbeat timing.
- Logging configuration.

The architecture needs a consistent way to load configuration and construct each process's dependencies without introducing global state or coupling components to deployment concerns.

## Decision

Each executable Runtime will have a bootstrap module that acts as its **composition root**.

Configuration is loaded once at process startup from environment variables into an immutable `Settings` object.

Bootstrap then uses those settings to construct the dependencies required by that process:

```text
Environment Variables
        ↓
load_settings()
        ↓
Settings
        ↓
Runtime Bootstrap
        ↓
Infrastructure
        ↓
Application / Queue Dependencies
        ↓
Runtime
```

`Settings` is not exposed as globally accessible state.

Components do not independently:

- Read environment variables.
- Retrieve global Settings.
- Construct shared infrastructure.

Instead, required configuration and dependencies are supplied explicitly during construction.

Runtime classes likewise do not construct their own repositories, Queue implementations, Application services, or shared infrastructure. Their bootstrap modules own that responsibility.

Deployment mechanisms such as Docker or Docker Compose may supply environment variables and select which executable to launch, but they do not own application dependency composition.

## Alternatives Considered

### Global Settings Object

Expose process-wide Settings that components can access directly.

**Pros**

- Convenient.
- Requires little dependency plumbing.

**Cons**

- Introduces global state.
- Makes dependencies implicit.
- Makes isolated testing harder.
- Allows configuration concerns to spread throughout the codebase.

### Components Read Environment Variables

Allow individual components to load the values they require.

**Pros**

- Reduces bootstrap wiring.

**Cons**

- Couples components to the deployment environment.
- Duplicates parsing and validation.
- Distributes configuration responsibility.
- Makes testing more difficult.

### Runtime Classes Construct Their Dependencies

Allow Runtime classes to construct their own infrastructure and services.

**Pros**

- Simplifies process startup.
- Requires fewer constructor dependencies.

**Cons**

- Couples Runtime behavior to concrete infrastructure.
- Mixes process behavior with dependency construction.
- Obscures dependency graphs.
- Makes Runtime classes harder to test.
- Makes implementations harder to replace.

### Explicit Configuration and Composition Roots (Selected)

Load configuration once and explicitly construct each process's dependency graph at its Runtime boundary.

**Pros**

- Keeps dependencies explicit.
- Avoids global configuration state.
- Centralizes parsing and validation.
- Separates Runtime behavior from dependency construction.
- Allows each process to construct only what it requires.
- Improves testing and implementation replaceability.
- Works consistently across local and deployed environments.

**Cons**

- Requires explicit dependency wiring.
- Some construction logic may be repeated across Runtime bootstraps.
- Shared dependency changes may require updates to multiple bootstraps.

## Consequences

### Positive

- Configuration has one well-defined process entry point.
- Environment concerns remain at the outer Runtime boundary.
- Application, Domain, Plugins, and Persistence do not depend directly on environment variables.
- Runtime classes remain independently testable.
- Each executable process has an explicit dependency graph.
- Shared infrastructure can be constructed once per process and reused where appropriate.
- Future Runtimes can follow the same composition model without introducing global state.

### Negative

- Runtime bootstraps contain explicit construction code.
- Some dependency wiring may be duplicated.
- Changes to shared dependencies may affect multiple composition roots.

This duplication is intentionally preferred over global state or a premature dependency-injection framework.

Shared bootstrap helpers may be introduced later if repeated construction behavior becomes a meaningful and stable abstraction.
