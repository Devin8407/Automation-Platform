# ADR-003: Interface-Based Plugin Extension Points

## Status

Accepted

## Context

The Automation Platform must support multiple task and trigger types while keeping Application services and Runtime processes independent of concrete implementations.

A decision was required regarding how implementations should be defined, discovered, and resolved without continually modifying orchestration code.

Possible approaches included explicit conditional dispatch, manually registered implementations, and interface-based plugins with automatic discovery.

## Decision

The platform will provide interface-based extension points for task and trigger plugins.

Each plugin category defines a common interface that concrete implementations must satisfy.

Plugin implementations expose stable plugin type identifiers that are persisted in workflow definitions and used to resolve the corresponding implementation at runtime.

Shared plugin infrastructure provides:

- Implementation discovery.
- Registration.
- Duplicate plugin type validation.
- Lookup by stable plugin type.

Concrete implementations are discovered from their designated implementation packages and registered when the relevant registry is initialized.

Application services depend on plugin interfaces and registries rather than concrete implementations.

This discovery mechanism is intended for application-owned plugin implementations available at process startup.

The platform does not currently support dynamically installing, unloading, or hot-loading third-party plugins while a process is running.

## Alternatives Considered

### Conditional Logic

Use conditional statements to select behavior based on plugin type.

**Pros**

- Simple initially.
- Requires little infrastructure.

**Cons**

- Dispatch logic grows with every implementation.
- Requires modifying orchestration code when implementations are added.
- Couples Application services to concrete plugin types.
- Encourages large dispatch methods.

### Manual Registration

Explicitly import and register every implementation.

**Pros**

- Simple and explicit.
- Easy to reason about.

**Cons**

- Requires maintaining centralized registration lists.
- New implementations require changes outside their implementation package.
- Creates unnecessary registration boilerplate.

### Interface-Based Discovery and Registration (Selected)

Discover implementations conforming to shared interfaces and register them by stable plugin type.

**Pros**

- Keeps orchestration independent of implementations.
- New implementations require minimal infrastructure changes.
- Provides centralized validation and lookup.
- Supports strongly typed extension contracts.
- Avoids manually maintained registration lists.

**Cons**

- Requires discovery and registry infrastructure.
- Discovery conventions must remain stable.
- Startup failures may occur for invalid or duplicate plugin registrations.

### Fully Dynamic Third-Party Plugin Framework

Support arbitrary external plugins being installed or loaded while the platform is running.

**Pros**

- Maximum extensibility.
- Supports external plugin ecosystems.

**Cons**

- Significantly greater lifecycle, security, packaging, and compatibility complexity.
- Not required by the current platform scope.

## Consequences

### Positive

- Application services remain unaware of concrete plugin implementations.
- Plugin implementations can be added without modifying orchestration logic.
- Persisted plugin identifiers remain stable independently of Python class names.
- Discovery and registration behavior is reusable across plugin categories.
- Plugin contracts remain explicit and testable.

### Negative

- Plugin discovery and registry infrastructure must be maintained.
- Invalid or duplicate plugin identifiers must be detected during initialization.
- Runtime installation or hot-loading of third-party plugins is not supported.

The selected approach provides automatic discovery and strongly typed extension points without introducing the complexity of a fully dynamic third-party plugin ecosystem.
