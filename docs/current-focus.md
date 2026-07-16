# Current Focus

## Purpose

This document tracks the project's current implementation focus.

It serves as a lightweight engineering notebook that helps maintain momentum between development sessions.

When returning to the project after time away, this document should answer:

> What should I work on next?

---

# Current Milestone

**Phase 2 — Core Workflow Engine**

Current objective:

Build the core domain model and persistence layer that will support workflow execution.

---

# Current Priorities

## 1. Domain Model

Design the core business models.

- Workflow Definition
- Workflow Execution
- Task Definition
- Task Execution
- Trigger Definition

Goals:

- Separate immutable definitions from runtime state.
- Keep models independent from persistence.
- Finalize relationships before implementation.

---

## 2. Persistence Layer

Design SQLAlchemy models and repositories.

Focus on:

- Entity relationships
- Repository interfaces
- Database initialization
- Persistence boundaries

---

## 3. Application Layer

Begin implementing application capabilities.

Initial services include:

- WorkflowStarter
- TaskProcessor

Keep orchestration independent from runtime processes.

---

# Deferred Until Later

Do not implement yet:

- FastAPI
- Scheduler
- Docker
- GitHub Actions
- RabbitMQ
- DAG execution
- Parallel workflows
- Retry policies
- Metrics
- Observability

The goal is to build a solid sequential execution model before introducing additional complexity.

---

# Current Architectural Priorities

When making implementation decisions:

- Preserve module boundaries.
- Favor composition over inheritance.
- Keep runtime processes thin.
- Keep orchestration inside the application layer.
- Separate definitions from execution state.
- Prefer interfaces over conditionals.
- Introduce complexity only when it solves a real problem.

---

# Definition of Done

The current milestone is complete when:

- Domain models are implemented.
- Persistence layer is functional.
- A manually started workflow executes sequentially.
- Background worker processes queued work.
- Unit tests cover the core execution flow.
