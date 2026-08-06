# Configuration Architecture

## Purpose

Configuration defines how external runtime values enter the Automation Platform and become available to executable processes.

Configuration follows one primary flow:

```text
Environment Variables
        ↓
load_settings()
        ↓
typed, immutable Settings
        ↓
Runtime Bootstrap
        ↓
dependency construction
```

Components receive configuration explicitly rather than reading environment variables themselves.

> **External configuration is loaded once at process startup, converted into typed immutable Settings, and passed explicitly into dependency construction.**

## Responsibilities

Configuration owns:

- Defining application settings.
- Loading values from the runtime environment.
- Parsing raw values into appropriate Python types.
- Providing defaults where appropriate.
- Validating configuration constraints.
- Producing immutable `Settings` for process startup.

It does **not** own:

- Application service construction.
- Database resource construction.
- Logging behavior.
- Runtime execution.
- Workflow orchestration.
- Queue behavior.
- Persistence behavior.

Those responsibilities remain with bootstrap and their respective architectural subsystems.

## Design Principles

- Load external configuration at process startup.
- Represent configuration through typed `Settings`.
- Keep Settings immutable after loading.
- Pass configuration explicitly.
- Keep environment access out of business logic.
- Validate unsafe or invalid configuration before the process starts.
- Centralize parsing and defaults.
- Avoid globally accessible Settings.
- Keep configuration independent of individual Runtime implementations where practical.
- Prefer simple environment-based configuration until concrete requirements justify something more complex.

## Settings

Runtime configuration is represented by a frozen `Settings` dataclass.

Conceptually:

```python
@dataclass(frozen=True)
class Settings:
    database_url: str
    echo_sql: bool

    queue_type: str
    queue_lease_timeout: timedelta

    worker_poll_interval: timedelta
    worker_heartbeat_interval: timedelta

    reconciliation_interval: timedelta
    scheduler_poll_interval: timedelta

    log_level: str
```

The exact fields evolve with platform capabilities.

The architectural requirement is that consumers receive **parsed application-level values**, not raw environment strings.

For example:

```text
WORKER_HEARTBEAT_INTERVAL_SECONDS
        ↓
configuration parsing
        ↓
timedelta
        ↓
Worker construction
```

The Worker does not perform that conversion itself.

## Immutable Startup Configuration

Settings are loaded once and remain unchanged for the lifetime of the process:

```text
environment
    ↓
load once
    ↓
immutable Settings
    ↓
process lifetime
```

Runtime configuration is therefore startup state rather than mutable global application state.

If configuration changes, the process is restarted with new external values.

This keeps behavior predictable and avoids synchronization requirements around live configuration mutation.

## Environment Boundary

Environment variables are the external runtime configuration boundary.

Current examples include:

```text
DATABASE_URL
ECHO_SQL

QUEUE_TYPE
QUEUE_LEASE_TIMEOUT_SECONDS

WORKER_POLL_INTERVAL_SECONDS
WORKER_HEARTBEAT_INTERVAL_SECONDS

RECONCILIATION_INTERVAL_SECONDS
SCHEDULER_POLL_INTERVAL_SECONDS

LOG_LEVEL
```

Environment variables are strings at the operating-system boundary.

The Configuration subsystem converts them into types such as:

```text
str
bool
timedelta
```

Individual components never need to interpret those raw values.

## Parsing, Defaults, and Validation

Configuration parsing is centralized in the loader.

Common parsing behavior includes:

- Required values.
- Boolean conversion.
- Numeric conversion.
- Duration construction.
- Default values.
- Constraint validation.

Conceptually:

```text
Environment
    │
    │ raw strings
    ▼
Configuration Loader
    │
    │ parse
    │ apply defaults
    │ validate
    ▼
Settings
```

### Required Values

Values without a meaningful universal default are required.

For example:

```text
DATABASE_URL
```

must identify the database used by the process.

### Defaults

Settings may provide sensible defaults where platform-wide behavior can be defined consistently.

Examples include:

- Polling intervals.
- Logging level.

Defaults belong to Configuration rather than individual Runtime implementations.

### Validation

Invalid or unsafe configuration fails during startup.

Basic validation includes constraints such as positive timing values.

Configuration may also validate relationships between settings when they represent operational safety requirements.

For example:

```text
queue lease timeout
        ≥
multiple heartbeat intervals
```

A Worker must have sufficient opportunity to renew its lease before that lease becomes eligible for reclamation.

Unsafe timing relationships should therefore prevent startup rather than allowing the process to operate with invalid assumptions.

## Runtime-Specific Consumption

The Settings object may describe configuration for the complete application, while individual Runtime processes consume only the subset they require.

For example:

```text
Worker
├── queue lease timeout
├── worker polling interval
└── worker heartbeat interval

Reconciler
└── reconciliation interval

Scheduler
└── scheduler polling interval
```

Runtime classes do not load Settings themselves.

Bootstrap uses Settings to construct the dependencies and Runtime configuration required by that executable process.

## Bootstrap Integration

Each Runtime follows the same configuration boundary:

```text
load Settings
    ↓
configure process-level concerns
    ↓
build Infrastructure
    ↓
construct subsystem dependencies
    ↓
construct Application services
    ↓
construct Runtime
    ↓
run
```

For example:

```text
Worker bootstrap
    ↓
load Settings
    ↓
configure logging
    ↓
build Infrastructure
    ↓
build Queue + Application services
    ↓
construct Worker
    ↓
run
```

Scheduler and Reconciler use the same general pattern while constructing different dependency graphs.

This keeps configuration loading at the composition root rather than inside Runtime classes or business components.

## Relationship to Infrastructure

Configuration and Infrastructure answer different questions.

| Configuration                                | Infrastructure                                                           |
| -------------------------------------------- | ------------------------------------------------------------------------ |
| What runtime values should this process use? | What shared technical resources should be constructed from those values? |
| Loads `DATABASE_URL`                         | Creates SQLAlchemy Engine                                                |
| Loads `ECHO_SQL`                             | Configures Engine behavior                                               |
| Produces `Settings`                          | Produces shared resources                                                |

Conceptually:

```text
Environment
    ↓
Configuration
    ↓
Settings
    ↓
Infrastructure
    ↓
Engine + SessionFactory
```

Configuration supplies values such as:

```text
database_url
echo_sql
```

Infrastructure uses those values to construct database resources.

Configuration does not construct the Engine itself.

## Relationship to Observability

Configuration may define process-level observability values such as:

```text
log_level
```

Bootstrap passes those values to Observability:

```text
Settings.log_level
        ↓
configure_logging(...)
        ↓
process logging behavior
```

The responsibilities remain separate:

```text
Configuration
    defines the configured value

Observability
    implements its operational meaning
```

This keeps Configuration from owning logging behavior.

## No Global Settings

The architecture deliberately avoids loading Settings into globally imported state:

```python
settings = load_settings()
```

and then allowing arbitrary modules to access it.

That pattern would create hidden dependencies and make tests depend on process-wide configuration.

Instead:

```text
bootstrap
    ↓
load Settings
    ↓
construct dependency
    ↓
inject dependency
```

Configuration dependencies remain visible at composition boundaries.

## Local Development and Deployment

The external boundary remains environment variables regardless of how those variables are supplied.

### Local Development

A `.env` file may be used as a development convenience:

```text
.env
    ↓
environment variables
    ↓
load_settings()
```

The `.env` file is not a second configuration architecture.

### Deployment

Container or deployment tooling supplies the same environment boundary:

```text
Docker Compose / deployment environment
        ↓
environment variables
        ↓
Runtime process
        ↓
load_settings()
```

The application therefore uses the same configuration model across local development and deployment.

## Testing

Configuration tests should focus on the external configuration boundary.

Important cases include:

- Required values are enforced.
- Defaults are applied correctly.
- Boolean values are parsed correctly.
- Numeric and duration values are parsed correctly.
- Invalid values are rejected.
- Unsafe relationships between timing settings are rejected.

Application, Runtime, and subsystem tests should generally construct the configuration or dependencies they require directly rather than relying on process environment state.

This keeps most tests independent of Configuration infrastructure.

## Future Evolution

Potential additions include:

- API host and port settings.
- Health endpoint configuration.
- Metrics configuration.
- Alternative Queue connection settings.
- Additional Runtime-specific intervals.
- Deployment-specific tuning.

New settings should preserve the existing boundary:

```text
external values
    ↓
single configuration boundary
    ↓
typed + validated + immutable Settings
    ↓
explicit dependency construction
```

More complex configuration systems should be introduced only when concrete requirements make the environment-based model insufficient.
