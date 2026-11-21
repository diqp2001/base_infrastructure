# Strategy architecture refactor: final report (P1–P7)

2026-11-20. Commits on `main`:

| Phase | Commit |
|---|---|
| P1 + P2 | `1d56d1b0` |
| P3 | `73bbdae1` |
| P4 | `0d039d43` |
| P5 | `966e499f` |
| P6 | `cdc8efd5` |
| P7 | the commit after `cdc8efd5` |

## 1. Final architecture

```
UNIVERSE                    Universe / UniverseFinancialAsset: members in force on a date (no score, rank or weight)
    |                       UniverseRepository.get_related_entities(universe_id, date); an ETF gives its holdings + weights
    v
FACTORS                     Factor + DependencySpec, resolved by FactorValueResolutionService (unchanged)
    |
    v
RANKING / SCORING FACTORS   LGBM quintile rank, STM signal, CSM score ... (unchanged; models stay in their providers)
    |                       resolution_service.resolve_dependencies(strategy, parent, date)
    v
TRADING STRATEGY            TradingStrategy(Factor): calculate_dependencies + evaluate() -> StrategySignals
    |                       LGBMQuintileLongShortStrategy, SpatioTemporalMomentumTradingStrategy,
    |                       ETFCallDispersionTradingStrategy
    v
PORTFOLIO CONSTRUCTION      selection -> weighting -> adjustments (domain steps), PortfolioConstructionMethod,
    |                       PortfolioConstructionService; dispersion: dispersion_target_portfolio (contracts)
    v
TARGET PORTFOLIO            TargetPortfolio / TargetPortfolioPosition: what the strategy WANTS (the boundary)
    |
    v
PORTFOLIO REBALANCER        PortfolioRebalancer.plan / plan_target: target - current -> sells then buys
    |
    v
EXECUTION                   UnifiedPortfolioManager.set_holdings (gates) -> TradeManager -> broker (unchanged)
    |
    v
POSITION                    Position / PortfolioHolding: what the account HOLDS (unchanged)
```

Everything above `TargetPortfolio` is investment logic. Everything below it is account and execution logic.

**Unchanged since P1:**
- `Position`, `Order`, `Transaction`, the holding entities and their ORM models;
- `TradeManager`;
- the brokers.

Check: `git diff 1d56d1b0~1 HEAD -- trade_manager.py brokers/ finance/order finance/transaction finance/holding models/finance` is empty.

## 2. Files created

**Domain**
- `src/domain/entities/factor/trading_strategy/trading_strategy.py`: `TradingStrategy`, `StrategySignals`. Plus its `__init__.py`.
- `src/domain/entities/factor/trading_strategy/lgbm_quintile_long_short_strategy.py` (P5).
- `src/domain/entities/factor/trading_strategy/spatio_temporal_momentum_strategy.py` (P6).
- `src/domain/entities/factor/trading_strategy/etf_call_dispersion_strategy.py` (P7).
- `src/domain/ports/factor/trading_strategy/trading_strategy_port.py`, plus its `__init__.py`.
- `src/domain/entities/finance/portfolio/target_portfolio.py`.
- `src/domain/entities/finance/portfolio/construction/steps.py`, `construction_method.py`, plus its `__init__.py`.

**Application**
- `src/application/services/data/entities/factor/trading_strategy_evaluation_service.py`.
- `src/application/services/portfolio_construction/portfolio_construction_service.py`, plus its `__init__.py`.
- `src/application/services/misbuffet/algorithm/portfolio_rebalancer.py`.
- `src/application/services/dispersion/dispersion_target_portfolio.py` (P7).

**Infrastructure**
- `src/infrastructure/repositories/mappers/factor/trading_strategy_mapper.py`.
- `src/infrastructure/repositories/local_repo/factor/trading_strategy_repository.py`.

**Tests**
- `tests/strategy/test_trading_strategy_factor.py`.
- `tests/strategy/test_portfolio_construction.py`.
- `tests/strategy/test_lgbm_quintile_strategy.py`.
- `tests/strategy/test_dispersion_readiness.py`.
- `tests/misbuffet/test_portfolio_rebalancer.py`.
- `tests/spatio_temporal_momentum/test_stm_target_portfolio.py`.

**Docs**
- `docs/architecture/P1_STRATEGY_ARCHITECTURE_AUDIT.md`.
- `docs/architecture/STM_SIGNAL_TO_ORDERS_TRACE.md`.
- `docs/architecture/STRATEGY_ARCHITECTURE_FINAL_REPORT.md` (this file).

## 3. Files modified

| File | Change |
|---|---|
| `src/domain/entities/factor/factor.py` | `strategy` group, `trading_strategy` subgroup |
| `src/infrastructure/models/factor/factor.py` | `TradingStrategyModel` (identity `trading_strategy`, existing `factors` table: no migration) |
| `src/infrastructure/repositories/mappers/factor/factor_mapper.py` | dispatch + `DISCRIMINATOR_CLASS_MAP` |
| `src/infrastructure/repositories/repository_factory.py` | `TradingStrategy` repository |
| `src/infrastructure/repositories/local_repo/universe/universe_repository.py` | `get_related_entities` (members in force) |
| `src/application/services/data/entities/factor/factor_value_resolution_service.py` | public `resolve_dependencies` |
| `src/application/services/misbuffet/algorithm/unified_portfolio_manager.py` | `set_holdings` delegates the quantity loop to the rebalancer; accepts a `TargetPortfolio` |
| `src/application/services/data/entities/factor/spatio_temporal_momentum/stm_trading_cycle.py` | strategy, then construction, then `CycleResult.target_portfolio` |
| `src/application/services/data/entities/factor/spatio_temporal_momentum/stm_backtest.py` | `signals_to_weights` is a thin wrapper |
| `src/application/managers/project_managers/spatio_temporal_momentum_project_full/backtesting/base_project_algorithm.py` | `set_holdings(result.target_portfolio)` |
| `src/application/managers/project_managers/spatio_temporal_momentum_project_10m_live/backtesting/base_project_algorithm.py` | the same; shortable restriction applied via `TargetPortfolio.with_weights` |
| `tests/component/factor_context/factor_catalog.py` | `TradingStrategy` listed as not producing a scalar |
| `tests/spatio_temporal_momentum/test_stm_10m_live.py` | fake cycle result has `target_portfolio` |
| CLAUDE.md files under `src/domain/entities/factor/`, `src/domain/entities/finance/` and `src/application/services/misbuffet/algorithm/` | P2–P6 sections |

## 4. Files deleted

None.

## 5. Tests run and results

Final full run, `python -m pytest tests` (2026-11-20):

| Result | Count |
|---|---|
| Passed | 2708 |
| Failed | 0 |
| Skipped | 127 (SQL Server / IBKR / missing optional project folders) |
| Expected failures | 9 (already marked before the refactor) |

Duration: 34 min 53 s.

| Area | Tests |
|---|---|
| Factor dependency resolution | `tests/component/factor_context`, `tests/repositories` |
| TradingStrategy dependency resolution | `test_trading_strategy_factor.py` |
| LGBM quintile construction | `test_lgbm_quintile_strategy.py` |
| TargetPortfolio and construction | `test_portfolio_construction.py` |
| Rebalancing | `test_portfolio_rebalancer.py` (includes the golden test against the pre-P4 loop) |
| STM regression | `test_stm_target_portfolio.py` |
| STM backtest | `tests/spatio_temporal_momentum` |
| STM live path | `test_stm_10m_live.py` |
| Execution | `tests/misbuffet` (order safety, ledger, recovery, trading controls, set_holdings chain) |
| Repositories | `tests/repositories` |

## 6. STM migration summary

**Old path:** `score_details` → `signals_to_weights` (inside the cycle) → `{CompanyShare: [...]}` → `set_holdings`.

**New path:** `score_details` → `SpatioTemporalMomentumTradingStrategy.signals` → `volatility_targeted_signals` → `TargetPortfolio` → `set_holdings` → `PortfolioRebalancer` → `TradeManager`.

**Unchanged STM rules:**
- w = s · target_vol / (σ · √P) / N;
- the gross cap only scales down;
- an asset without a usable volatility gets 0 and still counts in N;
- P comes from the bar size.

**Regression:** the old rule is frozen in the test.
- Weights match within rel 1e-12 / abs 1e-15 over 400 decisions.
- Target and order quantities are identical over 200 scenarios with holdings and liquidations.
- The real cycle, run with a tiny model, returns the old weights.

**Projects:**
- `_full` and `_10m_live` pass the `TargetPortfolio` itself.
- The other STM-based projects read `CycleResult.weights`, which is filled from the same construction, so there is no duplicate logic.

## 7. LGBM strategy summary

`LGBMQuintileLongShortStrategy`:
- It reads `CompanyShareLGBMCSQuintileRankMomentumFactor` per universe member, through the existing resolution. It has no model logic.
- It holds Q5 long and Q1 short, with equal weight per side and each side at gross/2. Q2–Q4 hold nothing.

**Quintile modes:**
- Default: the factor's own label, rounded.
- `cross_sectional`: re-ranks the values with the decile project's rule (ties broken by symbol).

**Edge cases:**
- Constituents without a value are left out.
- An empty side gives an empty target (the CSM rule).

**End to end:** `TradingStrategyEvaluationService.target_portfolio(strategy, universe, date)`.

## 8. Future dispersion implementation path

**Today (P7, readiness):**
- `ETFCallDispersionTradingStrategy` declares the constituents' ranking factor (STM signal) per entity of the ETF. The resolution service adds the ETF `weights`.
- `evaluate` gives the scores, with the ETF weights in the context.
- `construct_dispersion_trade` runs the existing `select_constituents`, which excludes names expected to fall, and then `DispersionPortfolioConstructionService.construct`:
  - N short ETF calls are fixed from the full basket;
  - the constituent calls replicate the ETF weights;
  - premiums are at bid / ask.
- `dispersion_target_portfolio` gives a `TargetPortfolio` of contracts: the ETF call short N, the selected calls long q_i. Premiums and net dollar delta are in its context.
- The rebalancer turns it into trades. Nothing in execution changed.

**Next steps:**
1. **Legs from factors:** build the `Leg`s from stored option factors instead of the screener's market snapshot:
   - ATM call selection;
   - `CompanyShareOption*` / `ETFShareOption*` mid price;
   - delta factors.

   A small leg-builder service in `application/services/dispersion/` would do this.
2. **Delta constraint:** a partial delta-neutral step on contract quantities. Scale the long basket, or the hedge, until |net dollar delta| ≤ a limit; P3's `ExposureLimit` does the same for weights. Add it to `dispersion_target_portfolio` once the target rule (how partial) is decided.
3. **Wire the dispersion cycle:** send `DispersionTradingCycle`'s `result.targets` through `dispersion_target_portfolio` → `set_holdings(target, liquidate_unlisted=False)`. Only once the dispersion screener project may trade; it is read-only today (P.11).
4. **Database identity:** give `ETFCallDispersionTradingStrategy`, the LGBM and STM strategies their own factor identities (ORM subclass, dispatch, repository) when a strategy row is needed.

## 9. Remaining technical debt

- **CSM:** `long_short_weights` (`csm_trading_cycle.py`) duplicates `quantile_long_short_inverse_volatility`. The only difference: CSM breaks exact score ties by input order, construction by symbol. Moving CSM onto the construction layer is a small behaviour decision on ties. It wasn't done, to keep CSM unchanged.
- **Decile project:** `stm_decile_cycle.long_short_weights` / `decile_weights` have their own quantile rule, which matches `steps.quantile_labels`. It wasn't migrated: it's another project, and its research decile records use it.
- **Other STM projects:** `spatio_temporal_momentum_project`, `_10m`, `_10m_hourly` and `etf_dispersion_stm_project` still call `set_holdings` with class-keyed dicts. The STM ones use the shared construction through `CycleResult.weights`. Switching them to `set_holdings(result.target_portfolio)` is a one-line change each.
- **SPX call-spread market making (v1 / v2):** sizes option contracts in its own strategy code. It's a project-specific construction, not moved.
- **misbuffet `PortfolioConstructionModel` (Black-Litterman):** legacy and unrelated to the new layer. Kept as is.
- **Concrete strategies:** they have no database identity yet; only base `TradingStrategy` rows persist (see 8.4).
- **Layering:** the LGBM factor repository (infrastructure) still injects the application-level model provider. It pre-dates the refactor and wasn't copied.
- **Rebalancer trade order:** it orders trades by symbol within sells and within buys. Before, the order came from Python's set ordering, which isn't stable across runs. This only matters when the budget check runs out of cash part-way through a rebalance.
- **Shortable restriction:** the live restriction rewrites target weights (`with_weights`). A construction adjustment step would be cleaner once a second live strategy needs it.
