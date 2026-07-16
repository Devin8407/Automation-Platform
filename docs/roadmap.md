# Project Roadmap

## Purpose

This document describes the long-term evolution of the Automation Platform.

Rather than serving as a strict implementation checklist, the roadmap outlines the major engineering milestones that gradually transform the project into a production-style backend platform.

The roadmap intentionally favors architectural quality over feature count.

---

# Guiding Principles

The project will evolve incrementally.

Each phase should:

- Introduce one or more significant engineering concepts.
- Preserve existing architectural boundaries.
- Avoid unnecessary complexity.
- Leave the system in a deployable, working state.

---

# Phase 1 — Foundation

Goal:

Establish the core architecture and development environment.

Major milestones:

- Repository setup
- Development tooling
- Documentation
- Architecture
- ADRs
- Domain model

Status:

✅ In Progress

---

# Phase 2 — Core Workflow Engine

Goal:

Build the minimum viable workflow platform.

Major milestones:

- Domain models
- SQLAlchemy models
- Repository layer
- Workflow creation
- Sequential workflow execution
- Manual trigger
- Task plugin system
- PostgreSQL-backed queue
- Worker process

Deliverable:

A manually started workflow can execute end-to-end.

---

# Phase 3 — API

Goal:

Expose the platform through a REST API.

Major milestones:

- FastAPI
- Request validation
- CRUD operations
- API documentation
- OpenAPI generation

Deliverable:

Workflows can be managed entirely through HTTP.

---

# Phase 4 — Scheduling

Goal:

Support automated workflow execution.

Major milestones:

- Scheduler runtime
- Cron trigger
- Trigger plugin architecture
- Trigger persistence

Deliverable:

Scheduled workflows execute automatically.

---

# Phase 5 — Production Improvements

Goal:

Improve robustness and maintainability.

Major milestones:

- Retry policies
- Heartbeats
- Structured logging
- Configuration management
- Health endpoints
- Docker Compose
- GitHub Actions

Deliverable:

Production-style deployment experience.

---

# Phase 6 — Advanced Workflow Engine

Potential future capabilities include:

- Parallel execution
- DAG workflows
- Workflow versioning
- Priority scheduling
- Distributed workers
- RabbitMQ queue
- Redis caching
- Metrics
- Observability

These features are intentionally deferred until they solve meaningful engineering problems.

---

# Long-Term Vision

The completed project should demonstrate:

- Production-quality backend architecture
- Clean software design
- Extensibility
- Asynchronous execution
- Testing
- Documentation
- Maintainability

The project is intended to serve as a portfolio centerpiece and a practical demonstration of backend engineering skills.
