# Documentation

This directory contains the technical documentation for the Automation Platform.

Documentation is organized into three primary areas:

```text
docs/
├── architecture/    Current system design and technical behavior
├── adr/             Architectural decisions and their reasoning
└── planning         Project direction and implementation priorities
```

For a first introduction to the system, start with the [Architecture Overview](architecture/overview.md).

---

# Architecture

[Architecture Documentation](architecture/README.md)

Describes the system **as it currently exists**, including:

- Architectural responsibilities and boundaries.
- Domain and data models.
- Workflow execution.
- Application orchestration.
- Persistence and concurrency.
- Queue-based work distribution.
- Plugin extensibility.
- Runtime processes.
- Configuration, infrastructure, and observability.

The Architecture README provides the recommended reading order and navigation into detailed subsystem documentation.

---

# Architecture Decision Records

[Architecture Decision Records](adr/README.md)

ADRs preserve the reasoning behind significant architectural decisions, including:

- The context that motivated a decision.
- The selected approach.
- Alternatives considered.
- Tradeoffs and consequences.

Architecture documentation describes **what the system is now**.

ADRs explain **why significant architectural choices were made**.

---

# Project Planning

[Project Roadmap](roadmap.md)

The roadmap tracks completed engineering milestones, the current development stage, and longer-term direction.

Planning documentation may describe incomplete or future capabilities and should therefore not be treated as documentation of existing system behavior.

---

# Documentation Hierarchy

```text
docs/README.md
    │
    ├── architecture/
    │      │
    │      ├── README.md
    │      │      Navigation and recommended reading order
    │      │
    │      ├── overview.md
    │      │      Complete high-level architecture
    │      │
    │      ├── top-level architecture documents
    │      │
    │      └── subsystem folders
    │             └── README.md + detailed documents
    │
    ├── adr/
    │      └── README.md + individual ADRs
    │
    └── roadmap.md
```

Each level has a distinct responsibility:

- **Documentation README** — routes readers to the appropriate documentation area.
- **Architecture README** — indexes the architecture documentation and defines its reading order.
- **Architecture Overview** — explains how the complete system works.
- **Subsystem READMEs** — explain and navigate individual architectural subsystems.
- **Detailed architecture documents** — describe specific capabilities and guarantees.
- **ADRs** — preserve architectural decision history.
- **Planning documents** — describe completed milestones, active work, and future direction.

Detailed information should live in the document that owns that responsibility rather than being duplicated across documentation levels.
