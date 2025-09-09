# CLAUDE.md – Algorithm

## General Role
The `Algorithm` folder contains core trading strategy logic. It defines user-created algorithms, specifying how data is processed and trades are executed. These algorithms subclass the `QCAlgorithm` class.

## Dependencies
- **Depends On**: 
  - `Common`: For base classes like `QCAlgorithm`, `Security`, and indicators.
  - `Data`: For receiving data streams into the algorithm.
- **Depended On By**:
  - `Engine`: To run the logic during backtesting or live trading.
  - `Launcher`, `Optimizer`: To run and analyze the user’s algorithm.

## Use
This is the folder where strategies are implemented, typically using `Initialize()` and `OnData()` methods in a class that inherits from `QCAlgorithm`.

## Invocation
Called by `Engine` through dynamic loading when a backtest or live run begins.
