# CLAUDE.md – Data

## General Role
Manages the acquisition, formatting, and consumption of market data. It supports data feeds, custom data sources, and Lean data types.

## Dependencies
- **Depends On**:
  - `Common`: For data models.
- **Depended On By**:
  - `Engine`: For historical and live data feeds.
  - `Algorithm`: For consuming data within strategies.

## Use
Includes classes like `SubscriptionDataReader`, `DataManager`, and source adapters for custom data.

## Invocation
Instantiated and managed by the `Engine` and `DataFeed` modules.
