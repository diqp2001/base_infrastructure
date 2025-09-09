# CLAUDE.md – Optimizer

## General Role
Provides optimization logic to test different parameter combinations across algorithms, typically in a grid or genetic search manner.

## Dependencies
- **Depends On**:
  - `Common`, `Engine`
- **Depended On By**:
  - `Optimizer.Launcher`: Manages and runs the optimization session.

## Use
Defines objective functions and optimization loops using cloud or local resources.

## Invocation
Called through the optimizer CLI or `Optimizer.Launcher`.
