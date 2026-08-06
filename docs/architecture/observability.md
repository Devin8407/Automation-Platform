# Observability Architecture

## Purpose

Observability provides process-wide visibility into the behavior of the Automation Platform.

The current implementation establishes structured application logging as the platform's first observability capability.

Observability is intentionally separate from Infrastructure and business logic so operational visibility can evolve without becoming part of workflow correctness.

Future capabilities may include metrics and distributed tracing.

> **Observability should make system behavior understandable without becoming part of the behavior required for system correctness.**

## Responsibilities

Observability currently owns:

- Process-wide logging configuration.
- Consistent log formatting.
- Configured logging levels.
- Standard module-level logging.
- Exception and traceback reporting.
- Operational events emitted by Runtime and application components.

It does **not** own:

- Workflow orchestration.
- Runtime lifecycle or failure policy.
- Persistence.
- Queue behavior.
- Business state.
- Configuration loading.
- Dependency construction.

Those responsibilities remain with their respective architectural components.

## Design Principles

- Configure logging once at process startup.
- Use module-level loggers throughout the codebase.
- Keep logging configuration outside business components.
- Log meaningful operational events rather than every method call.
- Preserve exception information and tracebacks.
- Avoid coupling modules to log transport or storage.
- Keep observability outside correctness and synchronization mechanisms.
- Allow metrics and tracing to be introduced without reorganizing unrelated architecture.

## Architecture

```
Environment
    ↓
Configuration
    ↓
Settings.log_level
    ↓
Runtime Bootstrap
    ↓
configure_logging()
    ↓
Python Logging Hierarchy
    │
    ├── Worker
    ├── Scheduler
    ├── Reconciler
    ├── Application
    ├── Persistence
    ├── Queue
    └── other modules
```

Bootstrap configures logging before normal process behavior begins.

Individual modules then emit operational events through Python's standard logging hierarchy.

## Logging Configuration

Logging is configured once during process startup.

Conceptually:

```
def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=log_level.upper(),
        format=...,
    )
```

The exact format may evolve, but configuration remains centralized.

Runtime, Application, Persistence, and Queue modules do not independently call:

```
logging.basicConfig(...)
```

This prevents different components from competing over process-wide logging behavior.

## Module Loggers

Modules that emit operational information obtain their logger through:

```
logger = logging.getLogger(__name__)
```

Examples include:

```
automation_platform.runtime.worker.worker
automation_platform.runtime.scheduler.scheduler
automation_platform.runtime.reconciler.reconciler
```

Module names naturally identify the source of each event.

Components do not need access to Settings merely to obtain a logger.

## Bootstrap Integration

Observability is configured near the beginning of every executable process:

```
load Settings
    ↓
configure logging
    ↓
build Infrastructure
    ↓
construct dependencies
    ↓
construct Runtime
    ↓
run
```

Configuring logging before dependency construction ensures startup and initialization events use the same process-wide logging behavior as normal Runtime execution.

## Relationship to Configuration

Configuration and Observability have distinct responsibilities:

```
Environment
    ↓
Configuration
    ↓
Settings.log_level
    ↓
Observability
    ↓
logging behavior
```

Configuration owns the configured value.

Observability owns the operational behavior associated with that value.

For example:

```
Configuration
    parses LOG_LEVEL
        ↓
    Settings.log_level

Observability
    consumes Settings.log_level
        ↓
    configures Python logging
```

Observability does not load environment variables itself.

## Relationship to Infrastructure

Observability is intentionally separate from Infrastructure.

Infrastructure owns shared technical resources such as:

```
SQLAlchemy Engine
SessionFactory
Declarative Base
```

Observability owns operational visibility.

Although both are cross-cutting technical concerns, combining them would turn Infrastructure into a generic container for unrelated non-business functionality.

They therefore evolve independently.

## Logging Philosophy

Logging should describe **meaningful operational events**, not every function invocation.

Useful events include:

```
Runtime
├── started
└── stopping

Worker
├── task claimed
├── claim became untrusted
├── heartbeat failed
└── processing failed unexpectedly

Scheduler
├── occurrence processed
└── scheduling cycle failed

Reconciler
├── reconciliation failed
└── runnable work restored

Workflow
├── execution started
├── completed
└── failed
```

Routine internal operations should generally remain quiet unless a concrete diagnostic requirement exists.

For example, logging every repository method invocation usually adds noise without improving operational understanding.

Likewise, normal polling cycles that find no work should not produce repetitive logs by default.

## Runtime Logging

Long-running Runtime processes are important observability boundaries because they represent independently executable behavior.

### Worker

Useful Worker events include:

- Startup and shutdown.
- Task claims.
- Unexpected processing failures.
- Heartbeat failures.
- Claims becoming untrusted.

### Scheduler

Useful Scheduler events include:

- Startup and shutdown.
- Scheduling failures.
- Unexpected trigger-processing errors.
- Meaningful occurrence-processing activity where useful.

Empty polling cycles should generally remain quiet.

### Reconciler

Useful Reconciler events include:

- Startup and shutdown.
- Reconciliation-cycle failures.
- Meaningful recovery activity.

Routine reconciliation cycles that restore nothing do not require verbose logging.

## Exception Logging

Unexpected exceptions should preserve their traceback.

Inside an exception handler:

```
logger.exception(
    "Task processing failed"
)
```

is preferred over manually logging only the exception message.

This preserves:

- Exception type.
- Exception message.
- Stack trace.

That context is especially important for diagnosing failures in long-running background processes.

## Failure Boundaries

Observability records failures but does not decide how the system responds to them.

For example:

```
database temporarily unavailable
        ↓
Reconciler cycle raises
        ↓
exception logged
        ↓
Runtime remains alive
        ↓
next cycle retries
```

The responsibilities are:

```
Observability
    records the failure

Runtime
    determines whether processing continues

Application / Persistence / Queue
    preserve correctness
```

Logging itself never determines retry, recovery, or termination policy.

## Concurrency

Logging may be used safely from concurrent Runtime activity such as the Worker's main processing thread and temporary heartbeat thread.

For example, the heartbeat thread may report:

```
heartbeat failed
claim became untrusted
```

while the main Worker thread continues managing processing.

Logging does not become a synchronization mechanism.

Concurrency correctness remains the responsibility of Worker, Queue, Application, and Persistence behavior.

## Operational Visibility vs. System State

Logs describe system behavior but are never the source of truth.

For example:

```
log:
"Task completed"
```

does not replace:

```
TaskExecution.status = COMPLETED
```

Likewise, logs are not used to:

- Coordinate Workers.
- Determine dependencies.
- Track Queue ownership.
- Determine scheduling state.
- Recover workflow execution.

The boundaries remain:

```
Persistence
    durable execution state

Execution Queue
    temporary delivery state

Observability
    operational visibility
```

If observability infrastructure is unavailable or incomplete, system correctness must continue to derive from the other architectural components.

## Package Organization

The current package should remain small:

```
observability/
├── __init__.py
└── logging.py
```

As capabilities are actually introduced, it may evolve naturally:

```
observability/
├── logging.py
├── metrics.py
└── tracing.py
```

These modules should be added only when their corresponding capabilities exist.

## Testing

Observability requires relatively little direct testing.

Useful tests may verify:

- Configured log levels are accepted.
- Invalid logging configuration is handled appropriately if validation belongs to Observability.
- Important failure paths emit logs where operationally valuable.
- Exception logging preserves diagnostic information where relevant.

Tests should not become tightly coupled to exact log wording.

Most behavioral tests should continue asserting durable state and component interactions rather than treating logging output as application behavior.

## Future Metrics

Metrics may eventually provide quantitative visibility into:

```
tasks processed
task execution duration

workflow completions
workflow failures

queue claims
queue lease expirations

scheduler occurrences processed
reconciliation recoveries
```

Metrics should be introduced when they provide concrete operational value.

Domain and Application behavior should not depend on a particular metrics backend.

## Future Distributed Tracing

Distributed tracing may become useful as execution spans additional processes or external infrastructure.

Potential trace boundaries include:

```
workflow start
    ↓
queue publication
    ↓
Worker claim
    ↓
task processing
    ↓
plugin execution
```

Tracing should describe this lifecycle without becoming required for its correctness.

## External Observability Systems

Logs, metrics, and traces may eventually be exported to external systems.

Conceptually:

```
Application / Runtime
        ↓
Observability
        ↓
logging / metrics / tracing infrastructure
        ↓
external observability platform
```

Business components should not depend directly on those external systems.

The current implementation requires only standard logging. More advanced integrations should be introduced when deployment requirements justify them.

## Current Scope

The current Observability implementation includes:

```
process-wide logging configuration
configurable log level
module-level loggers
exception and traceback logging
runtime operational events
```

The following remain intentionally deferred:

```
metrics
distributed tracing
external log aggregation
dashboards
alerting
```

This establishes the architectural boundary without introducing observability infrastructure the current platform does not yet require.

## Future Evolution

Observability should grow in response to concrete operational requirements.

Potential additions include:

- Metrics collection and export.
- Distributed tracing.
- External log aggregation.
- Dashboards.
- Alerting.
- Correlation identifiers.
- Structured contextual fields.

New capabilities should preserve the central boundary:

> **Observability may describe execution, but system correctness continues to depend on Domain, Application, Persistence, Queue, and Runtime guarantees.**
