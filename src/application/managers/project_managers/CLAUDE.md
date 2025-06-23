# CLAUDE.md – Project Managers

This folder contains **project-specific managers**, designed to orchestrate logic for self-contained workflows or model pipelines.

## Role
A **project manager** acts as a controller or coordinator for a specific ML or data project. It bundles:
- Model logic (training, prediction, evaluation)
- Configuration or hyperparameters
- Storage interaction (data in/out)

## Guidelines
- Should subclass from a shared `BaseProjectManager` if applicable
- Maintain high cohesion: each manager should serve a single modeling purpose
- Avoid tight coupling to infrastructure — rely on interfaces where possible

Use this folder for any logic that's tied to **project-level orchestration** rather than reusable domain logic.
