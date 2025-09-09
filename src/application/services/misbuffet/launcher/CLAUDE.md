# CLAUDE.md – Launcher

## General Role
Bootstraps and runs the Lean Engine. This module is used for launching backtests or live algorithms on local or remote machines.

## Dependencies
- **Depends On**:
  - `Engine`, `Common`, `AlgorithmFactory`
- **Depended On By**:
  - External scripts or CLI that run Lean locally.

## Use
Loads configuration, instantiates the Engine, and runs the algorithm.

## Invocation
Entry point in `Program.cs` or `main.py` to run Lean.
