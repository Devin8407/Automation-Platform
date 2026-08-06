# Architecture Documentation

This directory contains the technical architecture documentation for the Automation Platform.

The documentation describes the architecture **as it currently exists**, including:

- Core concepts and execution semantics.
- Architectural responsibilities and boundaries.
- Application orchestration.
- Persistence and concurrency guarantees.
- Work distribution and recovery.
- Plugin extensibility.
- Runtime processes.
- Supporting configuration, infrastructure, and observability.

Significant architectural decisions and their historical reasoning are documented separately through Architecture Decision Records (ADRs).

## Start Here

Start with the [Architecture Overview](overview.md).

It provides the high-level system model, major architectural boundaries, concurrency and recovery approach, and links to the detailed documentation.

For a complete understanding of the architecture, use the following reading order:

1. [Architecture Overview](overview.md)
2. [Project Structure](project-structure.md)
3. [Domain](domain.md)
4. [Data Model](data-model.md)
5. [Execution Model](execution-model.md)
6. [Application](application/README.md)
7. [Plugins](plugins/README.md)
8. [Persistence](persistence/README.md)
9. [Execution Queue](execution-queue.md)
10. [Runtime](runtime/README.md)
11. [Configuration](configuration.md)
12. [Infrastructure](infrastructure.md)
13. [Observability](observability.md)
14. [Architecture Decision Records](../adr/README.md)

The first five documents establish the core system model. Subsystem README documents then provide their own local reading order for deeper material.

## Documentation Map

```text
architecture/
│
├── README.md
├── overview.md
├── project-structure.md
├── domain.md
├── data-model.md
├── execution-model.md
├── execution-queue.md
├── configuration.md
├── infrastructure.md
├── observability.md
│
├── application/
│   ├── README.md
│   └── ...
│
├── persistence/
│   ├── README.md
│   └── ...
│
├── plugins/
│   ├── README.md
│   └── ...
│
└── runtime/
    ├── README.md
    ├── worker.md
    ├── reconciler.md
    └── scheduler.md
```

## Document Responsibilities

| Document                                  | Purpose                                                                                        |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------- |
| [Architecture Overview](overview.md)      | High-level architecture, responsibilities, major guarantees, and system interactions.          |
| [Project Structure](project-structure.md) | Maps architectural responsibilities to packages and dependency boundaries.                     |
| [Domain](domain.md)                       | Defines the core business concepts and their responsibilities.                                 |
| [Data Model](data-model.md)               | Describes the conceptual relationships between definitions, executions, and operational state. |
| [Execution Model](execution-model.md)     | Explains workflow compilation, DAG progression, retries, failures, and completion.             |
| [Application](application/README.md)      | Describes platform use cases and orchestration.                                                |
| [Plugins](plugins/README.md)              | Describes extensible task and trigger behavior.                                                |
| [Persistence](persistence/README.md)      | Describes durable state, repositories, transactions, and concurrency guarantees.               |
| [Execution Queue](execution-queue.md)     | Describes runnable-work delivery, claims, leases, and Queue concurrency.                       |
| [Runtime](runtime/README.md)              | Describes the Worker, Reconciler, Scheduler, and common Runtime boundaries.                    |
| [Configuration](configuration.md)         | Describes typed startup configuration and its environment boundary.                            |
| [Infrastructure](infrastructure.md)       | Describes shared technical resource construction.                                              |
| [Observability](observability.md)         | Describes operational visibility and application logging.                                      |

## Documentation Principles

Architecture documentation follows a few conventions:

- **Top-level documents** describe system-wide concepts or relatively small architectural concerns.
- **Subsystem folders** contain a `README.md` plus detailed documents when a subsystem has several independently useful concerns.
- **Subsystem READMEs** provide local navigation rather than requiring the top-level README to list every detailed document.
- **Architecture documents** describe the current system.
- **ADRs** explain why significant architectural decisions were made.
- Detailed implementation behavior should live in the document that owns that responsibility rather than being repeated across multiple documents.

When documentation overlaps, the document for the owning architectural responsibility is authoritative.
