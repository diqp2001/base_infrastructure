# CLAUDE.md – Engine

## General Role
The central processing unit of the Lean framework. It orchestrates strategy execution, data delivery, brokerage communication, and result storage.

## Dependencies
- **Depends On**:
  - `AlgorithmFactory`, `Data`, `Common`, `Api`
- **Depended On By**:
  - `Launcher`: Calls Engine to run the backtest/live.
  - `Optimizer`: Launches multiple engine runs.

## Use
Main components include `BacktestingEngine`, `LiveTradingEngine`, `DataFeed`, `TransactionHandler`.

## Invocation
Instantiated by `Launcher` or `Optimizer.Launcher` with the environment context.
