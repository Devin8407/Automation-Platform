# Project Roadmap

## Purpose

This roadmap describes the evolution of the Automation Platform from its architectural foundation into a production-style workflow execution system.

The roadmap is organized around major engineering milestones rather than individual features. Each phase introduces a meaningful system capability while preserving the architectural boundaries established by earlier work.

The project prioritizes correctness, reliability, maintainability, and architectural depth over feature count.

---

# Guiding Principles

Development follows several principles:

- Build complete vertical capabilities rather than isolated features.
- Preserve clear boundaries between Domain, Application, Persistence, Queue, Plugins, and Runtime processes.
- Introduce infrastructure only when it solves a concrete problem.
- Design explicitly for concurrency and process failure.
- Prefer idempotency and recoverability over assumptions of perfect execution.
- Validate important behavior with real PostgreSQL integration and system tests.
- Document significant architectural decisions and their tradeoffs.
- Keep the system operational at the end of each major milestone.

---

# Phase 1 — Architecture and Domain Foundation

**Goal:** Establish the architectural boundaries and core execution model before building infrastructure around them.

### Milestones

- [x] Repository and Python project structure
- [x] Development tooling
- [x] Modular monolith architecture
- [x] Domain model
- [x] Workflow and Task definitions
- [x] Workflow and Task executions
- [x] Separation of reusable definitions from runtime state
- [x] Dependency-based DAG model
- [x] Application Layer boundaries
- [x] Runtime/Application responsibility separation
- [x] Architecture documentation
- [x] Architecture Decision Records

**Deliverable:** A documented domain and architecture capable of supporting asynchronous workflow execution without coupling business logic to infrastructure.

**Status:** ✅ Complete

---

# Phase 2 — Extensible Workflow Definitions

**Goal:** Make workflows extensible without coupling the workflow engine to individual task or trigger implementations.

### Milestones

- [x] Common plugin interface
- [x] Generic plugin discovery
- [x] Generic typed plugin registry
- [x] Task plugin extension point
- [x] Trigger plugin extension point
- [x] Plugin configuration validation
- [x] Domain-level `TaskContext`
- [x] Domain-level `TaskResult`
- [x] Dependency output propagation
- [x] Prototype task implementations
- [x] Plugin unit testing infrastructure

**Deliverable:** New task and trigger implementations can be introduced through stable extension points without modifying workflow orchestration.

**Status:** ✅ Complete

---

# Phase 3 — Durable Workflow Execution

**Goal:** Build the durable execution model and persistence infrastructure required to run workflows safely.

### Milestones

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

**Deliverable:** Workflow execution state can be created, reconstructed, and advanced durably through explicit concurrency-safe transitions.

**Status:** ✅ Complete

---

# Phase 4 — Concurrent Queue-Driven Execution

**Goal:** Distribute runnable tasks safely across independent background workers.

### Milestones

- [x] Execution Queue abstraction
- [x] PostgreSQL-backed queue
- [x] Idempotent task enqueueing
- [x] FIFO task claiming
- [x] `FOR UPDATE SKIP LOCKED` concurrency
- [x] Lease-based task ownership
- [x] Unique claim tokens
- [x] Lease expiration and reclamation
- [x] Worker heartbeats
- [x] Safe Queue release
- [x] Atomic Queue finish and child enqueueing
- [x] Multiple-worker concurrency support
- [x] Queue integration and concurrency tests

**Deliverable:** Multiple workers can safely claim and process independent tasks concurrently while abandoned work remains recoverable.

**Status:** ✅ Complete

---

# Phase 5 — Workflow Engine and Worker Runtime

**Goal:** Connect the Domain, Application, Persistence, Plugins, and Queue into a complete asynchronous execution system.

### Milestones

- [x] Workflow start orchestration
- [x] Workflow Definition compilation
- [x] Root task scheduling
- [x] Task Processing Application service
- [x] Task plugin execution
- [x] Task output propagation
- [x] Fan-out execution
- [x] Fan-in execution
- [x] Parallel sibling execution
- [x] Retry handling
- [x] Terminal workflow failure
- [x] Worker polling runtime
- [x] Per-claim heartbeat lifecycle
- [x] Untrusted-claim handling
- [x] Graceful Worker shutdown
- [x] Worker bootstrap/composition root
- [x] Worker executable entry point
- [x] Worker unit tests
- [x] End-to-end PostgreSQL workflow tests
- [x] Multiple-Worker system tests

**Deliverable:** DAG workflows execute asynchronously end-to-end through concurrent background Workers.

**Status:** ✅ Complete

---

# Phase 6 — Reliability and Runtime Infrastructure

**Goal:** Make workflow execution resilient to process failures and establish shared production-style runtime infrastructure.

### Milestones

- [x] Persistence/Queue failure-window analysis
- [x] Reconciliation strategy
- [x] Runnable-task recovery query
- [x] Reconciler runtime
- [x] Idempotent recovery of stranded work
- [x] Reconciler failure recovery loop
- [x] Reconciler graceful shutdown
- [x] Reconciler bootstrap and executable entry point
- [x] Stranded-work system tests
- [x] Environment-based configuration
- [x] Explicit Settings dependency
- [x] Configuration validation
- [x] Process-wide logging infrastructure
- [x] OS signal handling
- [x] Shared database infrastructure
- [x] GitHub Actions CI
- [x] Ruff linting and formatting
- [x] Runtime architecture documentation

**Deliverable:** The execution engine can recover runnable work stranded by partial failures and operate through independently configured long-running processes.

**Status:** ✅ Complete

---

# Phase 7 — Durable Scheduling

**Goal:** Allow workflows to begin automatically from durable trigger state.

### Milestones

- [ ] Chronological trigger abstraction
- [ ] Initial interval/scheduled trigger implementation
- [ ] Durable chronological trigger state
- [ ] Chronological trigger persistence
- [ ] Trigger initialization during Workflow Definition creation
- [ ] Concurrency-safe due-trigger claiming
- [ ] Atomic schedule advancement and Workflow Execution creation
- [ ] Scheduler Application services
- [ ] Scheduler runtime
- [ ] Scheduler configuration and bootstrap
- [ ] Multiple-Scheduler concurrency tests
- [ ] End-to-end scheduled workflow tests

**Deliverable:** Time-based workflows execute automatically while multiple Scheduler processes can safely evaluate due triggers without creating duplicate executions.

**Status:** 🚧 In Progress

---

# Phase 8 — REST API

**Goal:** Expose workflow management and execution capabilities through an external HTTP interface.

### Milestones

- [ ] FastAPI application
- [ ] API runtime/bootstrap
- [ ] Workflow Definition endpoints
- [ ] Workflow execution endpoints
- [ ] Execution status/history endpoints
- [ ] Request and response validation
- [ ] Application-layer error translation
- [ ] OpenAPI documentation
- [ ] API integration tests
- [ ] Health/readiness endpoints

**Deliverable:** Workflows can be defined, started, inspected, and managed through a documented REST API.

**Status:** ⏳ Planned

---

# Phase 9 — Containerized Deployment

**Goal:** Package the independently executable runtime processes into a reproducible local deployment.

### Milestones

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

**Deliverable:** The complete platform can be started reproducibly as a multi-process system using Docker Compose.

**Status:** ⏳ Planned

---

# Phase 10 — Production Hardening

**Goal:** Add operational capabilities justified by the completed prototype and real runtime behavior.

Potential improvements include:

- Structured logging
- Metrics and tracing
- Improved health and readiness reporting
- Queue depth and execution metrics
- Scheduler observability
- Database migrations
- Workflow versioning
- Execution retention policies
- More sophisticated retry policies
- Priority scheduling
- Rate limiting
- Secrets management

These features will be introduced selectively rather than treated as requirements for the initial platform.

**Status:** 🔮 Future

---

# Phase 11 — Distributed Infrastructure Evolution

**Goal:** Explore infrastructure changes only where the existing abstractions provide a meaningful reason to do so.

Potential capabilities include:

- RabbitMQ-backed Execution Queue
- Distributed Worker deployment
- Redis-backed coordination or caching
- Transactional Outbox for stronger Persistence-to-Queue delivery guarantees
- Horizontal Scheduler scaling
- Larger-scale reconciliation
- Queue prioritization
- Dead-letter handling

The existing architecture intentionally leaves room for these changes without requiring them for the current system.

**Status:** 🔮 Future

---

# Current Architecture Milestone

The platform has progressed beyond a basic workflow-engine prototype.

The implemented execution path currently supports:

```text
Workflow Definition
        │
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


Recovery:

Durably Runnable Task
        │
        X Missing Queue Propagation
        │
        ▼
    Reconciler
        │
        ▼
Idempotent Re-enqueue
```

The current development focus is adding **durable chronological scheduling** on top of this execution foundation.

---

# Long-Term Vision

The completed platform should demonstrate the engineering foundations of a production workflow system:

- Asynchronous DAG execution
- Concurrent background processing
- Durable workflow state
- Concurrency-safe database transitions
- Failure detection and recovery
- Extensible task and trigger implementations
- Independent long-running runtime processes
- Automated scheduling
- REST-based management
- Reproducible containerized deployment
- Layered automated testing
- CI/CD
- Operational observability
- Architecture documentation and explicit design reasoning

The project is intended to remain deliberately smaller than a commercial workflow platform while implementing its chosen capabilities with strong correctness guarantees and clearly defensible engineering tradeoffs.
