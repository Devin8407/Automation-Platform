# Architecture Documentation

## Purpose

This directory documents the architecture of the Automation Platform.

The goal is not simply to describe the implementation, but to explain the design principles, system boundaries, execution model, and architectural reasoning that guide development.

These documents collectively serve as the primary source of truth for the system architecture.

---

# Reading Order

For someone new to the project, the recommended reading order is:

1. [Architecture Overview](overview.md)
2. [Execution Model](execution-model.md)
3. [Application Layer](application/application-overview.md)
4. [Persistence Layer](persistence/persistence-overview.md)
5. [Project Structure](project-structure.md)
6. [Data Model](data-model.md)

---

# Documents

## Overview

Provides a high-level explanation of the entire system.

Answers:

- What is this system?
- What are the major components?
- How do they interact?

---

## Execution Model

Describes how workflows move through the system.

Answers:

- How does a workflow execute?
- How do workers participate?
- How is work coordinated?

---

## Application Layer

Describes the business capabilities of the platform and the architectural boundary between runtime processes and supporting infrastructure.

Answers:

- Where does business logic live?
- What capabilities does the platform expose?
- How do runtime processes interact with the rest of the system?
- What belongs inside the Application Layer?

---

## Project Structure

Explains the architectural organization of the codebase.

Answers:

- Where should new code live?
- What does each package own?
- How should modules interact?

---

## Data Model

Defines the core business concepts and their relationships.

Answers:

- What data exists?
- Which objects are immutable?
- What runtime state is tracked?

---

# Relationship to ADRs

These documents describe the architecture as it exists today.

The corresponding Architecture Decision Records (ADRs) explain why major architectural decisions were made and document the alternatives that were considered.

Together, the architecture documents and ADRs provide both the current design and the reasoning behind it.
