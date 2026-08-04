# ADR-XXX: Explicit Runtime Configuration and Composition Roots

## Status

Accepted

## Context

The Automation Platform consists of multiple independently executable runtime processes, including:

- Workers
- Reconciler
- Scheduler
- API server

These processes require shared configuration and infrastructure, including:

- Database connection settings
- Queue configuration
- Runtime polling intervals
- Lease and heartbeat timing
- Logging configuration

A decision is required regarding:

1. How runtime configuration is made available throughout the system.
2. Where runtime dependencies are constructed and wired together.

Configuration could be exposed through globally accessible settings or singleton objects. This would allow components to retrieve configuration directly when needed, but it would introduce implicit dependencies and global state.

Alternatively, individual components could read environment variables directly or construct their own infrastructure. This would distribute configuration and dependency-construction responsibilities throughout the codebase and couple application components to deployment concerns.

Instead, configuration will be loaded once at each process boundary and passed explicitly through a runtime composition root responsible for constructing that process's dependency graph.

## Decision

Each independently executable runtime process will have a bootstrap module that acts as its composition root.

Runtime configuration will be loaded from environment variables into an immutable `Settings` object at process startup.

The bootstrap module will use these settings to construct shared infrastructure and application dependencies and explicitly provide those dependencies to the runtime.

Conceptually:

```text
Environment Variables
        ↓
load_settings()
        ↓
Settings
        ↓
Runtime Bootstrap
        ↓
Shared Infrastructure
        ↓
Application / Queue Dependencies
        ↓
Runtime
```

`Settings` will not be exposed as globally accessible state.

Components will not independently load environment variables or retrieve configuration through a global settings object. Instead, configuration values will be supplied explicitly to the components that require them during dependency construction.

Runtime classes will likewise not construct their own infrastructure. Construction and wiring of dependencies belong to their respective bootstrap composition roots.

Deployment mechanisms such as Docker and Docker Compose may provide environment variables and select which runtime executable to launch, but they will not own application dependency composition.

## Alternatives Considered

### Global Settings Object

Expose a process-wide `Settings` singleton that components can access when needed.

**Pros**

- Convenient access to configuration.
- Minimal dependency plumbing.
- Simple for small applications.

**Cons**

- Introduces global state.
- Makes dependencies implicit.
- Makes components harder to test in isolation.
- Allows configuration concerns to spread throughout the architecture.
- Makes it less clear which components actually require configuration.

### Components Load Environment Variables Directly

Allow individual components to retrieve the environment variables they require.

**Pros**

- Components can obtain configuration independently.
- Less bootstrap wiring is required.

**Cons**

- Couples application components to the deployment environment.
- Duplicates configuration parsing and validation.
- Makes testing more difficult.
- Distributes configuration responsibility throughout the codebase.
- Prevents configuration from being validated centrally.

### Runtime Classes Construct Their Dependencies

Allow each runtime class to construct its repositories, queue, application services, and infrastructure internally.

**Pros**

- Simple runtime startup.
- Fewer dependencies exposed through constructors.

**Cons**

- Couples runtime behavior to concrete infrastructure.
- Makes runtime classes difficult to unit test.
- Mixes process behavior with dependency construction.
- Obscures the dependency graph.
- Makes replacing implementations more difficult.

### Explicit Runtime Configuration and Composition Roots (Selected)

Load configuration once and construct the dependency graph at each runtime's process boundary.

**Pros**

- Keeps dependencies explicit.
- Avoids global configuration state.
- Centralizes configuration parsing and validation.
- Keeps runtime behavior separate from dependency construction.
- Improves unit testing.
- Allows each runtime process to construct only the dependencies it requires.
- Makes infrastructure implementations easier to replace.
- Provides a clear process-level dependency graph.
- Works naturally with local development, containers, and production deployment.

**Cons**

- Requires explicit dependency wiring.
- Bootstrap modules contain some repetitive construction logic.
- Adding dependencies may require updating multiple runtime composition roots.

## Consequences

### Positive

- Configuration has a single, well-defined entry point at process startup.
- Environment-specific concerns remain at the outer runtime boundary.
- Application, Domain, Plugin, and Persistence components do not depend directly on environment variables.
- Components expose their configuration requirements through explicit dependencies.
- Runtime classes remain independently testable.
- Each executable process has a clear composition root.
- Shared infrastructure can be constructed once per process and reused where appropriate.
- Deployment configuration remains separate from Python application composition.
- Future runtimes can follow the same startup architecture without introducing global state.

### Negative

- Runtime bootstraps require explicit dependency construction.
- Some dependency-construction code may be repeated between runtime processes.
- Changes to shared dependencies may require updates to multiple bootstrap modules.

This duplication is intentionally preferred over introducing global state or prematurely creating a generalized dependency-injection framework.

Shared bootstrap helpers may be extracted later if repeated construction logic develops into a meaningful and stable abstraction.
