# Automation Platform

> A production-style workflow automation platform focused on clean architecture, asynchronous execution, and extensible backend design.

## Overview

Automation Platform is a backend application for defining and executing automated workflows.

The platform separates workflow orchestration from task execution using background workers and an execution queue. It is designed to emphasize maintainability, extensibility, and production-oriented software engineering practices over feature count.


## Engineering Goals

This project focuses on demonstrating:

- Backend architecture
- Workflow orchestration
- Background workers
- REST APIs
- PostgreSQL
- FastAPI
- Docker
- Testing
- Configuration management
- Logging
- Documentation
- CI/CD
- Extensible software design


## Planned Features

- Workflow definitions
- Multiple trigger types
- Background workers
- Queue-driven execution
- Task extension points
- Execution history
- REST API
- Scheduling
- Containerized deployment


## Architecture

The platform is implemented as a modular monolith with clearly defined module boundaries.

A central Workflow Engine orchestrates workflow execution while background workers asynchronously execute individual tasks. Trigger types and task types are implemented through interface-based extension points to encourage extensibility without increasing coupling.

For additional architectural documentation, see:

- [Architecture Overview](docs/architecture/overview.md)
- [Architecture Decision Records](docs/adr/README.md)


## Project Status

The project is currently under active development.

Current progress includes:

- Repository setup
- Development tooling
- Initial architecture
- Architecture Decision Records (ADRs)

Upcoming milestones include:

- Domain model
- Persistence layer
- Workflow engine
- Background workers
- REST API


## Documentation

Additional technical documentation is available in the [`docs`](docs/) directory.

- [Architecture Overview](docs/architecture/overview.md)
- [Architecture Decision Records](docs/adr/README.md)


## License

This project is licensed under the MIT License.
