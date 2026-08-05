# Plugin Architecture

## Purpose

The Plugin Layer is the Automation Platform's extension boundary.

Plugins define configurable task and trigger behavior without owning
workflow orchestration, persistence, execution queues, or runtime
process control.

The Plugin Layer answers:

> **What implementation provides this configured behavior?**

The platform discovers implementations at process startup and resolves
them later through typed registries. Persisted definitions store stable
plugin identifiers rather than Python classes.

------------------------------------------------------------------------

## Responsibilities

The Plugin Layer is responsible for:

-   Defining plugin interfaces.
-   Discovering concrete implementations.
-   Registering implementations by `plugin_type`.
-   Detecting duplicate plugin identifiers.
-   Resolving implementations from persisted plugin types.
-   Validating plugin-specific configuration.
-   Defining task-specific and trigger-specific behavior contracts.

It is not responsible for workflow orchestration, persistence, queue
management, worker or Scheduler loops, HTTP routing, or creating
workflow executions.

------------------------------------------------------------------------

## Core Design

All plugins derive from a small shared base interface:

``` text
Plugin
├── plugin_type
└── validate_configuration(...)
```

`plugin_type` is the stable identifier stored in workflow definitions.
Concrete implementations own their configuration rules; Application
services invoke validation when definitions are created or modified.

Plugins remain independent of SQLAlchemy, repositories, Units of Work,
execution queues, Application services, and runtimes.

------------------------------------------------------------------------

## Discovery and Registries

Discovery dynamically imports implementation modules and finds concrete
subclasses of the relevant plugin interface. It occurs during process
startup; normal execution uses registry lookup.

Shared registry infrastructure conceptually stores:

``` python
dict[str, type[T]]
```

The current typed registries are:

``` text
TaskRegistry
TriggerRegistry
```

At runtime:

``` text
Persisted plugin_type
        │
        ▼
Plugin Registry
        │
        ▼
Implementation Class
```

This keeps persisted workflow configuration independent of Python
implementation details.

------------------------------------------------------------------------

## Plugin Categories

The platform currently has two plugin categories:

``` text
Plugin
├── Task
└── Trigger
```

They share discovery, registration, plugin identifiers, and
configuration validation, but intentionally have different behavioral
contracts.

-   [Task plugins](plugins/tasks.md) implement executable workflow work.
-   [Trigger plugins](plugins/triggers.md) define trigger-specific
    behavior used by mechanism-specific Application infrastructure.

------------------------------------------------------------------------

## Package Organization

``` text
plugins/
├── _plugin.py
├── _discovery.py
├── _registry.py
│
├── tasks/
│   ├── interface.py
│   ├── registry.py
│   └── implementations/
│
└── triggers/
    ├── interface.py
    ├── registry.py
    ├── chronological.py
    └── implementations/
```

Shared infrastructure remains at the plugin package root. Each plugin
category owns its interfaces, typed registry, and implementations.

Mechanism-specific trigger interfaces can live inside `triggers/` when
they represent a shared contract for a family of trigger plugins.
Additional structure should be introduced only when concrete complexity
requires it.

------------------------------------------------------------------------

## Interaction With the Platform

The normal dependency direction is:

``` text
Runtime
   │
   ▼
Application
   │
   ├────────► Plugin Registry ───────► Plugin
   │
   ▼
Domain / Persistence / Queue
```

Runtime processes are thin drivers of Application capabilities.
Application decides when plugin behavior is needed and coordinates
platform state around it. Plugins do not depend back upward on
Application or Runtime.

------------------------------------------------------------------------

## Testing Strategy

Registry and discovery tests should cover discovery, registration,
duplicate detection, lookup, unknown plugin handling, and supported
plugin types.

Concrete plugin tests should cover configuration validation,
plugin-specific behavior, and relevant edge cases.

Application integration tests separately verify that the surrounding
platform resolves and uses plugins correctly.

------------------------------------------------------------------------

## Future Evolution

Possible future additions include plugin versioning, capability
metadata, richer configuration schemas, compatibility checks,
deprecation support, or external plugin packaging. These should be
introduced only when concrete requirements justify them.

The central rule remains:

> **Plugins provide extensible behavior; the platform owns orchestration
> and execution state.**
