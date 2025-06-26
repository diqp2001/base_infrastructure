# CLAUDE.md – Common

## General Role
A central library containing interfaces, data types, order models, indicators, enumerations, and shared utilities used across all other modules.

## Dependencies
- **Depends On**:
  - Minimal third-party utilities only (e.g., MathNet, Newtonsoft).
- **Depended On By**:
  - All modules: `Algorithm`, `Engine`, `Data`, `Api`, etc.

## Use
Defines shared contracts like `QCAlgorithm`, `Security`, `Order`, `Slice`, `SubscriptionDataConfig`.

## Invocation
All parts of LEAN import and rely on definitions from `Common`.
