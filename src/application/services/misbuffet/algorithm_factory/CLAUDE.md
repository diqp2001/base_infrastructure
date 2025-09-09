# CLAUDE.md – AlgorithmFactory

## General Role
The `AlgorithmFactory` is responsible for creating instances of algorithms. It uses reflection or script execution to generate an instance of `QCAlgorithm`.

## Dependencies
- **Depends On**:
  - `Common`: For interfaces and reflection utilities.
  - `Algorithm`: For the strategy classes.
- **Depended On By**:
  - `Engine`: To instantiate algorithms in a consistent and pluggable way.

## Use
Encapsulates the logic for discovering, compiling, and initializing user-defined algorithms.

## Invocation
Used internally by the `Engine` to load user strategy code into memory.
