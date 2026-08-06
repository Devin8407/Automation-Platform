# Plugin Architecture

## Purpose

The Plugin Layer is the Automation Platform's extension boundary. It defines configurable task and trigger behavior without owning workflow orchestration, persistence, execution queues, or runtime process control.

It answers:

> **What implementation provides this configured behavior?**

Implementations are discovered at process startup and later resolved through typed registries. Persisted definitions store stable `plugin_type` identifiers rather than Python classes.

---

## Responsibilities and Boundaries

The Plugin Layer owns:

- Plugin interfaces and concrete implementation discovery.
- Registration and resolution by `plugin_type`.
- Duplicate identifier detection and unknown-plugin handling.
- Plugin-specific configuration validation.
- Task- and trigger-specific behavior contracts.

It does **not** own workflow orchestration, persistence, queue management, worker or Scheduler loops, HTTP routing, or workflow-execution creation.

Plugins remain independent of SQLAlchemy, repositories, Units of Work, execution queues, Application services, and runtimes.

---

## Core Design

All plugins derive from a small shared contract:

```text
Plugin
├── plugin_type
└── validate_configuration(...)
```

`plugin_type` is the stable identifier stored in workflow definitions. Concrete implementations own their configuration rules; Application services invoke validation when definitions are created or modified.

The platform currently has two plugin categories:

```text
Plugin
├── Task
└── Trigger
```

They share discovery, registration, identifiers, and validation, but intentionally have different behavior contracts:

- [Task plugins](tasks.md) implement executable workflow work.
- [Trigger plugins](triggers.md) define trigger-specific behavior hosted by mechanism-specific Application infrastructure.

---

## Discovery and Registries

Discovery imports implementation modules and finds concrete subclasses of the relevant plugin interface. It runs during process startup; normal execution uses registry lookup.

Shared registry infrastructure conceptually stores:

```python
dict[str, type[T]]
```

Current typed registries are `TaskRegistry` and `TriggerRegistry`.

```text
Persisted plugin_type
        │
        ▼
Plugin Registry
        │
        ▼
Implementation Class
```

This keeps persisted workflow configuration independent of Python implementation details.

---

## Package Organization

```text
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

Shared infrastructure remains at the plugin package root. Each category owns its interfaces, typed registry, and implementations.

Mechanism-specific trigger interfaces can live inside `triggers/` when they represent a shared contract for a family of plugins. Add deeper structure only when concrete complexity requires it.

---

## Platform Interaction

The normal dependency direction is:

```text
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

Runtime processes are thin drivers of Application capabilities. Application decides when plugin behavior is needed and coordinates platform state around it. Plugins do not depend upward on Application or Runtime.

---

## Testing

Registry and discovery tests should cover discovery, registration, duplicate detection, lookup, unknown-plugin handling, and supported plugin types.

Concrete plugin tests should cover configuration validation, plugin-specific behavior, and relevant edge cases. Application integration tests separately verify that the surrounding platform resolves and uses plugins correctly.

---

## Future Evolution

Possible additions include plugin versioning, capability metadata, richer configuration schemas, compatibility checks, deprecation support, or external plugin packaging. Introduce them only when concrete requirements justify them.

The central rule remains:

> **Plugins provide extensible behavior; the platform owns orchestration and execution state.**
