# Project Roadmap

## Purpose

This roadmap tracks the Automation Platform's evolution from its architectural foundation toward a production-style workflow execution system.

Development is organized around **engineering milestones rather than feature count**. Each phase introduces a meaningful capability while preserving the architectural boundaries established by earlier work.

The project prioritizes correctness, reliability, maintainability, recoverability, and architectural depth.

---

# Guiding Principles

Development follows several principles:

- Build complete vertical capabilities rather than isolated features.
- Preserve clear architectural responsibility boundaries.
- Introduce infrastructure only when justified by concrete requirements.
- Design explicitly for concurrency and process failure.
- Prefer idempotency and recoverability over assumptions of perfect execution.
- Validate database-dependent guarantees with real PostgreSQL tests.
- Record significant architectural decisions and tradeoffs through ADRs.
- Keep the system operational at the end of each major milestone.

---

# Phase 1 — Architecture and Domain Foundation

**Goal:** Establish the architectural boundaries and core execution model.

### Completed

- [x] Repository and Python project structure
- [x] Development tooling
- [x] Modular monolith architecture
- [x] Domain model
- [x] Workflow and Task Definitions
- [x] Workflow and Task Executions
- [x] Separation of reusable definitions from execution state
- [x] Dependency-based DAG model
- [x] Application Layer boundaries
- [x] Runtime/Application responsibility separation
- [x] Architecture documentation
- [x] Architecture Decision Records

**Outcome:** A documented architecture and domain model capable of supporting asynchronous workflow execution without coupling business logic to infrastructure.

**Status:** ✅ Complete

---

# Phase 2 — Extensible Workflow Definitions

**Goal:** Allow workflow behavior to evolve without coupling orchestration to individual task or trigger implementations.

### Completed

- [x] Common Plugin foundation
- [x] Generic Plugin discovery
- [x] Generic typed Plugin registry
- [x] Task Plugin extension point
- [x] Trigger Plugin extension point
- [x] Plugin configuration validation
- [x] Domain-level `TaskContext`
- [x] Domain-level `TaskResult`
- [x] Dependency output propagation
- [x] Prototype task implementations
- [x] Plugin unit testing infrastructure

**Outcome:** New task and trigger implementations can be introduced through stable extension points without modifying core workflow orchestration.

**Status:** ✅ Complete

---

# Phase 3 — Durable Workflow Execution

**Goal:** Persist and progress workflow executions safely.

### Completed

- [x] PostgreSQL integration
- [x] SQLAlchemy persistence models
- [x] Unit of Work abstraction
- [x] Workflow Definition persistence
- [x] Workflow Execution persistence
- [x] Compiled Workflow Executions
- [x] Runtime Task Execution graph
- [x] Transition-oriented repositories
- [x] Conditional task state transitions
- [x] Atomic dependency updates
- [x] Workflow completion detection
- [x] Retry state transitions
- [x] Workflow failure and cancellation behavior
- [x] PostgreSQL integration tests

**Outcome:** Workflow state can be created, reconstructed, and advanced through explicit concurrency-safe durable transitions.

**Status:** ✅ Complete

---

# Phase 4 — Concurrent Queue-Driven Execution

**Goal:** Distribute runnable tasks safely across concurrent Workers.

### Completed

- [x] Execution Queue abstraction
- [x] PostgreSQL-backed Queue
- [x] Idempotent task enqueueing
- [x] FIFO task claiming
- [x] `FOR UPDATE SKIP LOCKED` concurrency
- [x] Lease-based task ownership
- [x] Unique claim tokens
- [x] Lease expiration and reclamation
- [x] Worker heartbeats
- [x] Safe Queue release
- [x] Atomic Queue finish and child enqueueing
- [x] Multiple-Worker concurrency support
- [x] Queue integration and concurrency tests

**Outcome:** Multiple Workers can safely process independent tasks concurrently while abandoned Queue work remains recoverable.

**Status:** ✅ Complete

---

# Phase 5 — Workflow Engine and Worker Runtime

**Goal:** Connect Domain, Application, Persistence, Plugins, and Queue into a complete asynchronous execution path.

### Completed

- [x] Workflow start orchestration
- [x] Workflow Definition compilation
- [x] Root task scheduling
- [x] Task Processing Application service
- [x] Task Plugin execution
- [x] Task output propagation
- [x] Fan-out execution
- [x] Fan-in execution
- [x] Parallel sibling execution
- [x] Retry handling
- [x] Terminal workflow failure
- [x] Worker polling Runtime
- [x] Per-claim heartbeat lifecycle
- [x] Untrusted-claim handling
- [x] Graceful Worker shutdown
- [x] Worker composition root and executable entry point
- [x] Worker unit tests
- [x] End-to-end PostgreSQL workflow tests
- [x] Multiple-Worker system tests

**Outcome:** DAG workflows execute asynchronously end-to-end through concurrent background Workers.

**Status:** ✅ Complete

---

# Phase 6 — Reliability and Runtime Infrastructure

**Goal:** Recover from partial failures and establish shared production-style Runtime infrastructure.

### Completed

- [x] Persistence → Queue failure-window analysis
- [x] Reconciliation strategy
- [x] Runnable-task recovery query
- [x] Reconciler Runtime
- [x] Idempotent recovery of stranded work
- [x] Reconciler failure recovery loop
- [x] Reconciler graceful shutdown
- [x] Reconciler composition root and executable entry point
- [x] Stranded-work system tests
- [x] Environment-based configuration
- [x] Explicit immutable Settings
- [x] Configuration validation
- [x] Process-wide logging
- [x] OS signal handling
- [x] Shared database infrastructure
- [x] GitHub Actions CI
- [x] Ruff linting and formatting
- [x] Runtime architecture documentation

**Outcome:** The execution engine can recover runnable work stranded by partial failures and operate through independently configured long-running processes.

**Status:** ✅ Complete

---

# Phase 7 — Durable Scheduling

**Goal:** Start workflows automatically from durable chronological trigger state.

### Completed

- [x] Specialized chronological trigger abstraction
- [x] Interval trigger implementation
- [x] Durable chronological trigger state
- [x] Chronological trigger persistence
- [x] Trigger-state initialization during Workflow Definition creation
- [x] Concurrency-safe due-occurrence claiming
- [x] Atomic schedule advancement and Workflow Execution creation
- [x] Chronological trigger Application service
- [x] Scheduler Runtime
- [x] Scheduler configuration and composition root
- [x] Multiple-Scheduler concurrency tests
- [x] End-to-end scheduled workflow tests

**Outcome:** Chronological workflows execute automatically while multiple Scheduler processes safely coordinate due occurrences without duplicate committed executions.

**Status:** ✅ Complete

---

# Phase 8 — REST API

**Goal:** Expose workflow management and execution capabilities through an external HTTP interface.

### Planned

- [ ] FastAPI application
- [ ] API Runtime and composition root
- [ ] Workflow Definition endpoints
- [ ] Workflow Execution endpoints
- [ ] Execution status and history endpoints
- [ ] Request and response validation
- [ ] Application-layer error translation
- [ ] OpenAPI documentation
- [ ] API integration tests
- [ ] Health and readiness endpoints

**Outcome:** Workflows can be defined, started, inspected, and managed through a documented REST API.

**Status:** ⏳ Planned

---

# Phase 9 — Containerized Deployment

**Goal:** Package the independently executable Runtime processes into a reproducible local deployment.

### Planned

- [ ] Application Docker image
- [ ] Docker Compose environment
- [ ] PostgreSQL service
- [ ] API service
- [ ] Worker service
- [ ] Scheduler service
- [ ] Reconciler service
- [ ] Environment configuration
- [ ] Service health checks
- [ ] Graceful container shutdown
- [ ] End-to-end containerized validation

**Outcome:** The complete platform can be started reproducibly as a multi-process system using Docker Compose.

**Status:** ⏳ Planned

---

# Phase 10 — Production Hardening

**Goal:** Add operational capabilities justified by completed system behavior and real runtime requirements.

Potential improvements include:

- Structured logging.
- Metrics and distributed tracing.
- Improved health and readiness reporting.
- Queue depth and execution metrics.
- Scheduler observability.
- Database migrations.
- Workflow versioning.
- Execution retention policies.
- More sophisticated retry policies.
- Priority scheduling.
- Rate limiting.
- Secrets management.

These capabilities will be introduced selectively rather than treated as requirements for the initial platform.

**Status:** 🔮 Future

---

# Phase 11 — Distributed Infrastructure Evolution

**Goal:** Introduce distributed infrastructure only where concrete requirements justify replacing or extending existing abstractions.

Potential capabilities include:

- RabbitMQ-backed Execution Queue.
- Distributed Worker deployment.
- Redis-backed coordination or caching.
- Transactional Outbox for stronger Persistence → Queue delivery guarantees.
- Larger-scale Scheduler deployment.
- Larger-scale reconciliation.
- Queue prioritization.
- Dead-letter handling.

The existing architecture intentionally leaves room for these changes without requiring them for the current system.

**Status:** 🔮 Future

---

# Current State

With durable scheduling complete, the platform supports:

```text
Workflow Definition
        │
        ├──── explicit start
        │
        └──── chronological trigger
                    │
                    ▼
             Scheduler Runtime
                    │
        ┌───────────┘
        ▼
Compiled Workflow Execution
        │
        ▼
Runnable Task Executions
        │
        ▼
PostgreSQL Execution Queue
        │
        ▼
Concurrent Workers
        │
        ▼
Task Plugins
        │
        ▼
Atomic Persistence Transitions
        │
        ├────► Newly Runnable Tasks
        │
        └────► Workflow Completion
```

Runnable work lost during Persistence → Queue propagation is recovered through the Reconciler.

The next major milestone is the **REST API**, which will expose the existing Application capabilities through an external HTTP interface.

---

# Long-Term Direction

The project aims to demonstrate the engineering foundations of a production workflow system while remaining deliberately smaller than a commercial workflow platform.

The target capabilities include:

- Asynchronous DAG execution.
- Concurrent background processing.
- Durable workflow state.
- Concurrency-safe state transitions.
- Failure detection and recovery.
- Extensible task and trigger implementations.
- Independent Runtime processes.
- Automated scheduling.
- REST-based management.
- Reproducible containerized deployment.
- Layered automated testing.
- CI/CD.
- Operational observability.
- Explicit architecture documentation and decision records.

Future capabilities should continue to be introduced only when they provide concrete value while preserving clearly defensible architectural boundaries and correctness guarantees.
