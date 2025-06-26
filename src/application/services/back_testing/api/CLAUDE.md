# CLAUDE.md – Api

## General Role
Handles communication with the QuantConnect cloud. This includes uploading results, downloading datasets, and managing backtests and projects remotely.

## Dependencies
- **Depends On**:
  - `Common`: For API models.
- **Depended On By**:
  - `Engine`: For uploading live results or logs.
  - `Launcher`: To sync project files and results.

## Use
Provides RESTful client interfaces and models to communicate with QC's API.

## Invocation
Directly used by cloud or hybrid deployments that require syncing with the QuantConnect web platform.
