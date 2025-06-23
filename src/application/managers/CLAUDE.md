# CLAUDE.md – Application Managers

This folder contains **application-level managers** that coordinate domain logic and infrastructure access. They serve as orchestrators or service-layer components in a **Domain-Driven Design (DDD)** architecture.

## Purpose
Managers encapsulate workflows, combining:
- Domain entities (`src/domain`)
- Infrastructure components (e.g., repositories, models)

They **do not** contain business logic themselves, but execute use cases.

## Design Guidelines
- One manager per use-case family or bounded context
- Managers are stateless unless explicitly required
- Prefer dependency injection over direct imports

## Example Use Cases
- Loading a model and making predictions
- Coordinating domain services with repositories
- Managing project orchestration logic
