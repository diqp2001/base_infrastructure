# Project Manager — Market Making (Derivatives)

## Location

`src/application/managers/project_managers/market_making_project/market_making_project_manager.py`

---

## Purpose

The **Market Making Project Manager** is an **application-layer orchestrator** responsible for coordinating **pricing, trading, backtesting, and data management** workflows for **derivatives market making** across:

* **Fixed Income**
* **Equity**
* **Commodity**

This manager operates at a **high level of abstraction**, delegating execution-heavy responsibilities to specialized engines and services, most notably the **Misbuffet Engine** for trading and backtesting.

It does **not** implement pricing models, execution logic, or persistence details directly. Instead, it ensures correct sequencing, consistency, and alignment of domain services, engines, and data flows.

---

## Core Responsibilities

### 1. Market Making Orchestration

* Coordinate end-to-end market making workflows:

  * Instrument universe selection
  * Pricing updates
  * Quote generation
  * Trade decision lifecycle
* Maintain separation between **strategy intent** and **execution mechanics**.

### 2. High-Level Pricing Coordination

* Trigger pricing pipelines for derivatives:

  * Options
  * Futures
  * Swaps / fixed-income derivatives
* Aggregate pricing outputs from src.domain pricing services.
* Ensure pricing inputs (curves, vols, forwards, carry, roll yield) are up to date.

> ⚠️ Pricing models themselves live in **domain services** — this manager only coordinates.

### 3. Trading & Execution Delegation

* Delegate all trading-related execution to the **Misbuffet Engine**:

  * Order generation
  * Order routing
  * Execution simulation or live trading
* **Misbuffet uses Interactive Brokers (IBKR) as the broker service** for live execution.
* This project manager remains agnostic to broker implementation details:

  * No direct IBKR API usage
  * No contract, order, or connection handling
* Broker-specific logic is fully encapsulated inside Misbuffet services.

### 4. Backtesting Coordination

* Configure and launch backtests via Misbuffet:

  * Strategy parameters
  * Instrument universe
  * Time ranges
* Collect and normalize results for downstream analysis.

### 5. Data Management Ownership (Application-Level)

* Act as the **single coordinator** for data flows:

  * Market data ingestion
  * Historical data access
  * Factor and pricing input availability
* Ensure all required data exists before:

  * Pricing
  * Trading
  * Backtesting

> This manager **does not query databases directly** — it relies on repositories and data services.

### 6. Cross-Asset Consistency

* Enforce consistent workflows across asset classes:

  * Fixed income
  * Equity
  * Commodity
* Enable reuse of logic where possible while preserving asset-specific constraints.

---

## What This Manager Is NOT

* ❌ A pricing model
* ❌ A trading strategy
* ❌ A backtesting engine
* ❌ A repository or ORM wrapper
* ❌ A broker adapter

It is a **conductor**, not a musician.

---

## Key Dependencies

### Engines

* **Misbuffet Engine**

  * Trading
  * Backtesting
  * Execution simulation

### Application Services

* Market data services
* Pricing coordination services
* Risk and limits services (optional, future)

### Domain Layer

* Derivative entities
* Pricing factors (volatility, curves, forwards, roll yield)
* Trade and position entities

---

## Expected Public Interface (Conceptual)

```python
class MarketMakingProjectManager:
    def run_pricing_cycle(self) -> None:
        ...

    def run_trading_cycle(self) -> None:
        ...

    def run_backtest(
        self,
        start_date: date,
        end_date: date,
        universe: list[str],
        parameters: dict,
    ) -> BacktestResult:
        ...

    def ensure_data_ready(self) -> None:
        ...
```

> Exact method signatures may evolve — this defines **intent**, not implementation.

---

## Architectural Principles

* **Application-layer only**
* **No direct SQL / ORM usage**
* **No broker-specific logic**
* **Delegation over implementation**
* **Explicit orchestration** over hidden side effects

---

## Interaction Flow (High-Level)

```
MarketMakingProjectManager
        ↓
Ensure Data Availability
        ↓
Pricing Coordination
        ↓
Quote / Signal Generation
        ↓
Misbuffet Engine
   ↳ Trading
   ↳ Backtesting
```

---

## Future Extensions

* Intraday market making support
* Inventory-aware quoting
* Cross-asset hedging coordination
* Risk-based throttling and kill-switches
* Live vs paper trading mode switching

---

## Guiding Philosophy

> *The Project Manager knows **when** and **why** things happen — never **how** they are computed.*

This keeps the system scalable, testable, and aligned with Domain-Driven Design principles.
