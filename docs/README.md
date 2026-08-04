# Documentation

This directory contains the technical documentation for the Automation Platform.

Documentation is organized by purpose, from high-level system architecture to subsystem design, runtime behavior, architectural decisions, and project planning.

For a first introduction to the system, start with the [Architecture Overview](architecture/overview.md).

---

# Architecture

Documentation describing the overall structure, execution model, and major layers of the platform.

- [Architecture README](architecture/README.md)
- [Architecture Overview](architecture/overview.md)
- [Execution Model](architecture/execution-model.md)
- [Application Layer](architecture/application.md)
- [Domain Architecture](architecture/domain.md)
- [Persistence Architecture](architecture/persistence.md)
- [Database Schema](architecture/database-schema.md)
- [Data Model](architecture/data-model.md)
- [Project Structure](architecture/project-structure.md)

These documents explain how the major components of the platform interact and where responsibilities are placed.

---

# Subsystems

Documentation for major infrastructure and extension subsystems.

## Execution Queue

Describes runnable-work distribution, lease-based worker ownership, heartbeats, concurrency, and queue recovery behavior.

- [Execution Queue](architecture/execution-queue.md)

## Plugin System

Describes plugin discovery, registration, interfaces, and the extension model used by tasks and triggers.

- [Plugin Architecture](architecture/plugins.md)

---

# Runtime Processes

Documentation for independently executable processes and their operational responsibilities.

- [Worker](architecture/worker.md)
- [Reconciler](architecture/reconciler.md)
- [Scheduler](architecture/scheduler.md)

Runtime documentation focuses on process lifecycle and coordination rather than duplicating business logic owned by the Application Layer.

---

# Architecture Decision Records

Significant architectural decisions are documented as Architecture Decision Records (ADRs).

- [ADR Index](adr/README.md)

ADRs capture:

- The problem or architectural question.
- The chosen approach.
- Alternatives considered.
- Tradeoffs and consequences.

They provide the reasoning behind decisions that may not be apparent from the final implementation alone.

---

# Project Planning

Documents describing project direction and current implementation priorities.

- [Project Roadmap](roadmap.md)
- [Current Focus](current-focus.md)

Planning documents describe intended work and should not be treated as documentation of already implemented behavior.

---

# Documentation Levels

The documentation is intentionally organized at different levels of detail.

```text
README
   │
   ▼
Architecture Overview
   │
   ├── Architecture and subsystem documentation
   │
   ├── Runtime documentation
   │
   └── Data and execution models
   │
   ▼
Architecture Decision Records
