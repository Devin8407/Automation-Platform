# Architecture Documentation

## Purpose

This directory documents the architecture of the Automation Platform.

The goal is not simply to describe the implementation, but to explain:

- The major components of the system.
- The responsibilities and boundaries between those components.
- How workflows are represented and executed.
- How concurrency, failures, and recovery are handled.
- How the system can be extended without modifying core orchestration.

These documents describe the architecture **as it currently exists** and serve as the primary source of truth for the system's technical design.

The reasoning behind significant architectural choices is documented separately through Architecture Decision Records (ADRs).

---

# Recommended Reading Order

For someone new to the project, the recommended reading order is:

1. [Architecture Overview](overview.md)
2. [Domain Models](domain.md)
3. [Data Model](data-model.md)
4. [Execution Model](execution-model.md)
5. [Application Layer](application.md)
6. [Persistence Layer](persistence.md)
7. [Database Schema](database-schema.md)
8. [Execution Queue](execution-queue.md)
9. [Plugin Architecture](plugins.md)
10. [Worker Runtime](worker.md)
11. [Reconciler Runtime](reconciler.md)
12. [Infrastructure](infrastructure.md)
13. [Project Structure](project-structure.md)

The Architecture Overview is designed to stand on its own. The remaining documents provide progressively deeper explanations of individual parts of the system.

---

# Core Architecture

## Architecture Overview

[Architecture Overview](overview.md)

Provides a high-level explanation of the complete system and its major architectural boundaries.

Answers:

- What is the Automation Platform?
- What architectural style does it use?
- What are the major components?
- How do those components interact?
- How are concurrency and failure recovery approached?

This is the best starting point for understanding the project.

---

## Domain Models

[Domain Models](domain.md)

Describes the core business concepts represented by the Domain Layer.

Includes concepts such as:

- Workflow Definitions
- Task Definitions
- Trigger Definitions
- Workflow Executions
- Task Executions
- Task Contexts and Results

Answers:

- What concepts make up the platform?
- What belongs in the Domain Layer?
- How are reusable definitions separated from runtime state?

---

## Data Model

[Data Model](data-model.md)

Describes the relationships between the platform's major data concepts.

Answers:

- How are workflows, tasks, triggers, and executions related?
- Which objects represent reusable definitions?
- Which objects represent runtime state?
- How does execution data relate back to its definition?

---

## Execution Model

[Execution Model](execution-model.md)

Describes how a Workflow Definition becomes a running Workflow Execution and progresses through its task graph.

Covers concepts including:

- Compiled Workflow Executions
- Dependency-based scheduling
- DAG execution
- Runnable tasks
- Task output propagation
- Retries and failures
- Workflow completion

Answers:

- How does a workflow execute?
- How do tasks become runnable?
- How can independent tasks execute concurrently?
- How does completed work cause the workflow to progress?

---

# Application and Persistence

## Application Layer

[Application Layer](application.md)

Describes the business capabilities of the platform and the boundary between runtime processes and supporting infrastructure.

Answers:

- Where does orchestration live?
- What capabilities does the platform expose?
- How are Task Contexts constructed?
- How are plugins invoked?
- How do runtime processes interact with business logic?
- What belongs inside the Application Layer?

---

## Persistence Layer

[Persistence Layer](persistence.md)

Describes durable state management and the transition-oriented repository architecture.

Covers concepts including:

- Unit of Work
- Aggregate reconstruction
- Explicit execution transitions
- Atomic state updates
- Dependency progression
- Concurrency correctness

Answers:

- How is execution state persisted?
- Why are repositories transition-oriented rather than generic CRUD repositories?
- Where are concurrency invariants enforced?
- How can multiple tasks in the same workflow complete concurrently?

---

## Database Schema

[Database Schema](database-schema.md)

Documents the PostgreSQL representation of durable platform state.

Answers:

- How are domain concepts represented relationally?
- What tables and relationships exist?
- Which execution information is normalized or denormalized?
- Which indexes support runtime operations?

---

# Execution Infrastructure

## Execution Queue

[Execution Queue](execution-queue.md)

Describes how runnable work is distributed among Workers.

Covers:

- PostgreSQL-backed queueing
- Idempotent enqueueing
- Queue claims
- Renewable leases
- Claim tokens
- Heartbeats
- Lease expiration and reclamation
- Concurrent claiming with `FOR UPDATE SKIP LOCKED`

Answers:

- What does the Queue own?
- How do Workers safely claim work?
- How are stale Workers prevented from modifying Queue state?
- How can multiple Workers consume work concurrently?

---

## Plugin Architecture

[Plugin Architecture](plugins.md)

Describes the extension system used for task and trigger behavior.

Covers:

- Plugin interfaces
- Generic discovery
- Generic registries
- Typed registry wrappers
- Configuration validation
- Task execution contracts
- Trigger extension points

Answers:

- How are new task and trigger types added?
- How are implementations discovered and resolved?
- How are plugins kept independent from infrastructure and orchestration?

---

# Runtime Processes

Runtime processes are independently executable entry points into the same modular application.

They coordinate existing architectural boundaries rather than implementing core business rules themselves.

## Worker Runtime

[Worker Runtime](worker.md)

Describes the process responsible for consuming runnable work.

Covers:

- Polling and claiming
- Application task processing
- Heartbeat lifecycle
- Claim trust
- Retry and completion disposition
- Graceful shutdown
- Runtime bootstrap

Answers:

- What does a Worker do after claiming a task?
- How is a lease maintained during long-running work?
- What happens when ownership can no longer be trusted?
- Where is the boundary between Worker behavior and application logic?

---

## Reconciler Runtime

[Reconciler Runtime](reconciler.md)

Describes the recovery process responsible for repairing runnable tasks that are missing from the Execution Queue.

Covers:

- The Persistence-to-Queue failure window
- Runnable-task discovery
- Idempotent re-enqueueing
- Periodic recovery
- Failure handling
- Graceful shutdown

Answers:

- Why is reconciliation necessary?
- What happens if Persistence commits but Queue propagation fails?
- How does the system eventually recover stranded work?

---

# Supporting Architecture

## Infrastructure

[Infrastructure](infrastructure.md)

Describes shared technical infrastructure used across architectural modules.

Includes resources such as:

- SQLAlchemy Engine
- Session Factory
- Runtime Settings
- Shared infrastructure construction

Answers:

- Which technical resources are shared?
- Who constructs them?
- How are they supplied to Persistence, Queue, and runtime processes?

---

## Project Structure

[Project Structure](project-structure.md)

Maps architectural responsibilities to the physical Python package structure.

Answers:

- Where should new code live?
- What does each package own?
- Which dependencies between packages are allowed?
- How does the repository structure reflect the architecture?

---

# Relationship Between the Documents

The architecture documentation is intentionally layered.

```text
Architecture Overview
        │
        ▼
Domain + Data Model
        │
        ▼
Execution Model
        │
        ▼
Application
        │
        ├──────────────┐
        ▼              ▼
   Persistence    Execution Queue
        │              │
        └──────┬───────┘
               ▼
        Runtime Processes

Supporting all layers:
Plugins + Infrastructure + Project Structure
