# P1 — Strategy architecture audit (no code changed)

Repository: `base_infrastructure`, commit aabd99af, 2026-11-20.
Scope: the Factor, Strategy and Universe architecture, and the STM path from model output to positions. This
audit prepares phases P2–P7; it changes nothing.

---

## 1. Current architecture

```text
Model prediction        SpatioTemporalMomentumModelProvider.score_details     (stm_model_provider.py)
-> Signal               CycleResult.scores {ticker: score}                    (stm_trading_cycle.py, in memory;
                                                                               also written to factor_values)
-> Weight               signals_to_weights()                                  (stm_backtest.py, STM package)
-> Target quantity      UnifiedPortfolioManager.set_holdings()                (unified_portfolio_manager.py)
-> Order quantity       same: order_qty = target_qty - current_qty
-> Order                TradeManager.execute_trade() -> QCAlgorithm.market_order()
-> Position             TradeManager._update_position()                       (Position.quantity += order_qty)
```

### Where each responsibility happens today (STM full project)

| # | Responsibility | File · function | Notes |
|---|---|---|---|
| 1 | Signal generation | `stm_model_provider.py` · `score_details_with_artifact` | `model(X)[0]`, one float per asset (TFT: unbounded; other networks: tanh) |
| 2 | Ranking | — | None |
| 3 | Selection | `stm_trading_cycle.py` · `_eligible` (eligibility only) | Active universe member, close at the session, enough history; no selection by score |
| 4 | Weight construction | `stm_backtest.py` · `signals_to_weights` | `w = s · target_vol / (σ · √P) / N` |
| 5 | Volatility scaling | same | `target_vol / (daily_vol · √periods_per_year)`; σ missing or ≤ 0 gives weight 0 |
| 6 | Gross/net constraints | `signals_to_weights` (gross cap, scale down only); `set_holdings` (`max_gross_weight`, refuses the whole call); no net constraint | Two gross checks in two layers |
| 7 | Target quantity | `unified_portfolio_manager.py` · `set_holdings` L1355–1362 | `int(PV · w / (price · multiplier))`, truncated toward 0 |
| 8 | Current position lookup | `set_holdings` → `_get_current_position_qty` → `_qty_in_container` | Walks main portfolio → sub-portfolios → Position |
| 9 | Order quantity | `set_holdings` L1368 | `target_qty - current_qty` |
| 10 | Buy/sell decision | `set_holdings` L1370–1377 (sign, sells first); side string in `trade_manager.py` · `_register_order` | 0 → no order |
| 11 | Order submission | `TradeManager.execute_trade` → `QCAlgorithm.market_order` → `_submit_order` | Backtest: in-memory ticket, booked at once. Live: `_execute_live` + `OrderLedger` |

The other strategies do the same inside their own cycles, each with its own weight function:

| Function | File | Rule |
|---|---|---|
| `signals_to_weights` | `spatio_temporal_momentum/stm_backtest.py` | Signal × vol scaling ÷ N, gross cap |
| `long_short_weights` | `cross_sectional_momentum/csm_trading_cycle.py` | Rank; long top / short bottom quantile; inverse-vol within each side; each side gross/2 |
| `STMDecileTradingCycle.long_short_weights` | `portfolio_research/stm_decile_cycle.py` | D10 − D1 equal-weight, ± gross/2 |
| `decile_weights` | `portfolio_research/decile_portfolios.py` | Equal weight within each decile (research returns) |
| `DispersionPortfolioConstructionService.construct` | `dispersion/dispersion_portfolio_construction_service.py` | ETF call dispersion legs (contracts), not weights |

---

## 2. Relevant files and their responsibilities

### Factor architecture

| File | Class / function | Responsibility |
|---|---|---|
| `src/domain/entities/factor/factor.py` | `Factor(ABC)` | Metadata only: name, group, subgroup, frequency, data_type, source, definition, id. Validates against `GROUPS`, `SUBGROUPS`, `FREQUENCIES`, `DATA_TYPES`, `SOURCES`. No `calculate` and no dependencies on the base class. |
| `src/domain/entities/factor/dependency_spec.py` | `DependencySpec` | Code-declared dependency: factor type plus filters (group, subgroup, frequency, source…), `lookback`, `entity_symbol` / `entity_type`, `per_entity`, `result_key`. |
| `src/domain/entities/factor/factor_dependency.py` | `FactorDependency` | DB-declared dependency (`factor_dependencies` table: dependent → independent factor, lag, name). |
| `src/application/services/data/entities/factor/factor_value_resolution_service.py` | `FactorValueResolutionService` | The single resolver. `resolve_factor_value(factor, entity, date)`: reuses a stored value, else resolves dependencies, calls `calculate()` and persists. Branch A is `calculate_dependencies` (`_resolve_dynamic_dependencies` → `_resolve_dependency_spec`, `_per_entity_values`, `_related_weights`). Branch B is no dependencies (provider families, e.g. IBKR). Stored `factor_dependencies` rows use `_get_factor_dependencies` / `_resolve_stored_dependencies`. Batch: `resolve_factor_values_batch`, `factor_value_batch_resolution_service.py`. |
| `src/domain/entities/factor/factor_value.py`, `src/infrastructure/models/factor/factor_value.py` | `FactorValue`, `FactorValueModel` | One scalar per (factor_id, entity_id, entity_type, date). |
| `src/infrastructure/models/factor/factor.py` | `FactorModel` | `factors` table, polymorphic on `factor_type`. |
| `src/infrastructure/repositories/mappers/factor/factor_mapper.py` | `FactorMapper`, `DISCRIMINATOR_CLASS_MAP` | Discriminator → domain class dispatch (see the checklist in `src/CLAUDE.md` §1). |
| `src/infrastructure/repositories/local_repo/factor/base_factor_repository.py` | `BaseFactorRepository` | `_create_or_get`, values; one repository per factor type, registered in `repository_factory.py`. |
| `src/domain/entities/factor/constituent_score_factor.py` | `ConstituentScoreFactor` | A generic "score per constituent" factor (Branch B: written by ML pipelines). |
| `.../company_share/company_share_lgbm_cs_quintile_rank_momentum_factor.py` | `CompanyShareLGBMCSQuintileRankMomentumFactor`, `momentum_feature_dependency_specs()` | Depends on the 24 momentum factors (one `DependencySpec` each). `calculate()` delegates to an injected `_provider.predict(dependencies, entity, target_date)` and returns the quintile **1.0–5.0** for ONE share. |
| `.../local_repo/.../company_share_lgbm_cs_quintile_rank_momentum_factor_repository.py` | `_inject_provider` | Injects `LGBMMomentumModelProvider(factory=...)` into the entity. |
| `src/application/services/data/entities/factor/lgbm_momentum/lgbm_momentum_model_provider.py` | `LGBMMomentumModelProvider` | Regime fingerprint, artifact lookup, auto-training, `predict`. |
| `.../company_share/company_share_cross_sectional_momentum_factor.py` | `CompanyShareCrossSectionalMomentumFactor` | The same 24 feature specs; the CSM model's score. |
| `.../company_share/company_share_spatio_temporal_momentum_factor.py` | `CompanyShareSpatioTemporalMomentumFactor` | The STM signal as a stored factor (written by `STMFeatureStore.write_signals`). |
| `.../etf_share/etf_share_implied_dispersion_factor.py`, `etf_share_realized_dispersion_factor.py`, `.../etf_share_option/etf_share_option_dispersion_factor.py` | ETF dispersion factors | **Cross-sectional factors already exist.** Attached to the ETF entity, they read constituents through `per_entity` specs, with ETF weights injected by `_related_weights` (`ETFShareRepository.get_related_weights`). |

### Strategy, run and model

| Concept | Entity (file) | What it represents |
|---|---|---|
| Strategy definition + configuration | `Strategy` (`src/domain/entities/strategy/strategy.py`); rows in `strategies`, `strategy_parameters`, `strategy_parameter_values` | A versioned configuration: `strategy_type` (= project key), parameter sections, typed definition (bar, model type, windows, retraining), `universe_id`, status draft → validated → locked. **It is not a Factor and computes nothing.** `strategy_configuration.py` is a backward-compatible alias. |
| Strategy run | `StrategyExperiment` (`strategy_experiment.py`) | One backtest of a Strategy over a window (`backtest_start`, `backtest_end`, `initial_capital`), with status, pid and results. |
| Backtest run (registry) | `BacktestRun` (`src/domain/entities/backtest/backtest_run.py`); `backtest_runs`, `backtest_run_portfolios`, `backtest_run_models` | One execution of any project (identity, config snapshot, window, status), linked to its portfolios and to the models it used. |
| Model | `MLModel` (`src/domain/entities/ml/ml_model.py`) | Reusable model definition (type, hyper-parameters, target factor). |
| Model run | `ModelTraining` (`ml/model_training.py`), `ModelArtifact` (`ml/model_artifact.py`) | One training execution, and its stored binary. |
| Legacy | `Model`, `Backtest` (`src/domain/entities/backtest/model.py`, `backtest.py`) | Old minimal entities (name / model_id). |
| Configuration services | `src/application/services/strategy/*` (`StrategyService`, `StrategyDesignService`, `ExperimentService`, `project_adapters.py`, `strategy_project_config.apply_strategy`) | Create, version and launch configurations; apply a Strategy onto a project's config. No portfolio logic. |

These concepts are not interchangeable: **Strategy = configuration**, **StrategyExperiment / BacktestRun = runs**,
**MLModel = model**, **ModelTraining = model run**. The requested **TradingStrategy (a Factor) is a new, fifth
concept**, and must not be merged with `Strategy`.

### Universe

| Entity | Table | Columns | Notes |
|---|---|---|---|
| `Universe` | `universes` | id, name, description, universe_type, version | The listing used by strategies (`Strategy.universe_id`). |
| `UniverseFinancialAsset` | `universe_financial_assets` | universe_id, financial_asset_id, start_date, end_date | **No rank, no weight.** Already a pure constituent listing. |
| `UniverseFactor` | `universe_factors` | universe_id, factor_id | Factors attached to a universe (the designer's factor universe). |
| `InvestmentUniverse` (child of Universe) | `investment_universes` | id, entity_type, currency_id | |
| `UniverseConstituent` | `universe_constituents` | universe_id, entity_id, entity_type, start_date, end_date, **weight** | Point-in-time constituents (ETF holdings, DIA). `weight` is the **ETF/index composition weight** (market information), read by the dispersion screener and `ETFShareRepository.get_related_weights`, never a strategy weight. |

Universe has no `get_related_entities` in its repository, so today a Universe cannot be the parent entity of a
cross-sectional factor. ETFs can (`ETFShareRepository.get_related_entities` / `get_related_weights`).

### Execution

| File | Class / function | Responsibility |
|---|---|---|
| `src/application/services/misbuffet/algorithm/unified_portfolio_manager.py` | `UnifiedPortfolioManager.set_holdings` (L1191–1423) | Everything from weights to orders. The responsibilities are listed in §4. |
| same | `_ensure_asset_container`, `_qty_in_container`, `_get_all_held_tickers`, `_select_liquidations`, `_reference_price`, `_has_budget_for_trade`, `_execute` | Container setup, current state, liquidation scope, prices, budget, hand-off to TradeManager. |
| `src/application/services/misbuffet/algorithm/trade_manager.py` | `TradeManager.execute_trade`, `_execute_live`, `_book`, `_register_order`, `_record_fill`, `_update_position`, `_update_cash_for_trade`, `_resolve_holding_id` | Persistence of one trade: Order (side), Transaction, Position, cash leg; live intent / ledger. |
| `src/infrastructure/repositories/local_repo/finance/portfolio/company_share_portfolio_repository.py` | `ensure_sub_portfolio_linked`, `ensure_ticker_holding` | Create CompanySharePortfolio + CompanySharePortfolioPortfolioHolding, and CompanySharePortfolioHolding + Position. |
| `src/application/services/misbuffet/algorithm/base.py` | `QCAlgorithm.market_order`, `_submit_order` | Order ticket; live: transaction handler. |
| `src/domain/entities/finance/holding/portfolio_holding.py` | `PortfolioHolding` | Domain class; on this path it only appears as `'holding_class'` in project configs, which nothing reads. Holdings are created as ORM rows. |

---

## 3. Existing abstractions to reuse, and to avoid

**Reuse**

- **The Factor hierarchy and its persistence** (`factors` polymorphic table, mapper, repository, factory,
  `DISCRIMINATOR_CLASS_MAP`): TradingStrategy goes through the same 9-artefact checklist (`src/CLAUDE.md` §1). No
  parallel strategy-factor table.
- **`calculate_dependencies` + `DependencySpec` + `FactorValueResolutionService`**: the only dependency system
  to use. In particular `per_entity=True` (values per related entity, attributed by symbol) and
  `_related_weights` already give a factor a cross-section, as the ETF dispersion factors do.
- **Ranking and scoring factors stay where they are**: `CompanyShareLGBMCSQuintileRankMomentumFactor`
  (quintile 1–5 per share), `CompanyShareCrossSectionalMomentumFactor`, `CompanyShareSpatioTemporalMomentumFactor`,
  `ConstituentScoreFactor`.
- **`UnifiedPortfolioManager.set_holdings`**: keep its signature and gates. Its weight → quantity → order
  computation is what the rebalancer extracts.
- **`TradeManager`** and the order, transaction and position chain: unchanged.
- **`DispersionPortfolioConstructionService`**: already a construction service for dispersion (legs, contracts,
  N fixed from the full basket). P7 can wrap it behind the new interface instead of rewriting it.
- **The existing weight functions** (`signals_to_weights`, `long_short_weights`, the decile weights) are the
  construction rules to move. They are pure functions, so their behaviour can be pinned by regression tests
  before moving.

**Avoid building on**

- `misbuffet/algorithm/portfolio/portfolio_contruction_model.py · PortfolioConstructionModel`: it subclasses
  `IAlgorithm` (algorithm lifecycle, not a pure constructor), its only user is
  `BlackLittermanPortfolioOptimizationAlgorithm`, and it returns a plain dict. The new construction layer should
  not inherit from it. Its `create_targets(signals) -> weights` contract is the same idea and can be adapted later.
- `Strategy` (configuration): do not turn it into the TradingStrategy factor.
- `UniverseConstituent.weight`: composition data, not a place for strategy weights.

---

## 4. `set_holdings` responsibilities today (for P4)

In order, all inside one method:

1. Format normalisation (`_normalize_target_weights`: string- or class-keyed, weight or quantity).
2. Validation (NaN / infinite targets refused one by one).
3. Gross check (`max_gross_weight`, default 1.0: refuses the whole call).
4. Live gates (reconciler, order ledger drain, start-up recovery) and pending-order exclusion.
5. Portfolio value (`get_portfolio_value`; ≤ 0 → nothing traded).
6. Container setup (`_ensure_asset_container`: sub-portfolio + holding + position rows), **before** any quantity.
7. Liquidation scope (`_select_liquidations`: held − targeted, scoped to the asset classes in the call).
8. Price resolution (`_reference_price`: slice, then fallbacks).
9. Current quantity (`_get_current_position_qty`).
10. Target quantity (`int(PV · w / (price · multiplier))`, or an explicit quantity target).
11. No-trade band (`min_weight_change`, unused by STM).
12. Order quantity and side (`target − current`; 0 skipped; sells list before buys list).
13. Budget check (`_has_budget_for_trade`).
14. Execution (`_execute` → `TradeManager.execute_trade`), then reconciler bookkeeping.

The pure core that a rebalancer can own without IO is 7 (given the held set and classes), 10, 11 and 12: inputs
are the targets, portfolio value, prices, multipliers, current quantities and the held set; the output is a list
of trade instructions. Items 1–6, 8–9, 13 and 14 read or write state and stay where they are.

---

## 5. Proposed extension points

| Component | Proposed location | Shape |
|---|---|---|
| `TradingStrategy` | `src/domain/entities/factor/trading_strategy/trading_strategy.py` (concrete strategies next to it, or under their asset family) | `TradingStrategy(Factor)`, with its own `group` (a new `GROUPS` key, e.g. `"strategy"`) and `calculate_dependencies` returning `DependencySpec`s on ranking or scoring factors. Persisted through the factor checklist: ORM subclass of `FactorModel` (polymorphic identity), mapper, `FactorMapper` dispatch, `DISCRIMINATOR_CLASS_MAP`, port, local repository, factory registration. |
| `TargetPortfolio`, `TargetPortfolioPosition` | `src/domain/entities/finance/portfolio/target_portfolio.py` | Pure, immutable value objects: as-of time, strategy reference, positions (financial asset id or symbol + asset class, `target_weight`, optional `target_quantity`). Not persisted in P3. |
| Portfolio construction | Rules: pure functions in the domain, e.g. `src/domain/entities/finance/portfolio/construction/`. Orchestration: `src/application/services/portfolio_construction/portfolio_construction_service.py` | `PortfolioConstructionService.construct(strategy, inputs) -> TargetPortfolio`, composed of small steps: rank/select (quantile, top-N, threshold), weight (equal, score, inverse-vol, vol-target), normalise / ÷N, gross and net caps, per-asset caps. The STM, CSM and decile rules become compositions of these steps. |
| `PortfolioRebalancer` | `src/application/services/misbuffet/algorithm/portfolio_rebalancer.py` (next to `UnifiedPortfolioManager`) | Pure: `(TargetPortfolio or weights, portfolio_value, prices, multipliers, current_qty, held, scope, band) -> [TradeInstruction(ticker, order_qty, side, reason)]`. `set_holdings` keeps its signature and gates and calls it for the computation. |

### Decisions to settle before P2 (they shape every later phase)

1. **What entity a TradingStrategy value belongs to.** A factor value is one scalar per (factor, entity, date).
   A strategy works across all constituents. Options:
   - (a) The strategy is resolved against a **parent entity**: the Universe (needs a new
     `UniverseRepository.get_related_entities(universe_id, target_date)`, its active members), or an ETF for
     dispersion. Its `per_entity` dependency specs give it every constituent's score. This reuses the existing
     mechanism, as the ETF dispersion factors do.
   - (b) The strategy is evaluated **per constituent** (one value per asset). That cannot rank, because a single
     asset's `calculate()` does not see the others.

   **Recommendation: (a).**
2. **What the TradingStrategy "value" is.** Its natural output is a vector (per-asset interpretation, e.g.
   long / short / flat or a scaled signal), which feeds construction. `factor_values` holds scalars. Options:
   - store nothing at strategy level and keep the vector in memory (the resolution service is used to resolve
     dependencies);
   - persist the per-asset interpretation as values of the strategy factor with entity = constituent;
   - persist only a scalar summary at parent level.

   This decides whether P2 needs a resolution-service entry point that resolves dependencies **without**
   persisting a scalar (today only `resolve_factor_value` and the batch variants are public; dependency
   resolution is private).
3. **Relation between `Strategy` (configuration) and `TradingStrategy` (factor).** Recommendation: keep both. A
   Strategy version references the TradingStrategy factor it runs (and its parameters stay in
   `strategy_parameter_values`). Linking them is a later, additive change.
4. **`UniverseConstituent.weight`.** It is ETF/index composition data used by dispersion, not a strategy weight.
   Keep it (or later expose it as a factor). It does not conflict with "Universe = listing" for strategy purposes.

---

## 6. STM migration plan (safest order)

1. **Pin the current behaviour first (P3/P4, before touching STM):** golden tests on `signals_to_weights` (sign,
   vol scaling, √P with `periods_per_year(bar_minutes)`, ÷N counting assets with invalid vol, gross cap
   scale-down only, σ ≤ 0 → 0), and on `set_holdings` quantities (truncation, multiplier, liquidation scope,
   sells before buys).
2. **Build construction steps that reproduce `signals_to_weights` exactly** (vol-target weighting → ÷N → gross
   cap), and test them against the golden values with a stated tolerance (e.g. 1e-12 relative).
3. **Extract the rebalancer from `set_holdings` without changing its signature**; run the whole misbuffet test
   suite (13 project callers use `set_holdings`).
4. **Add `SpatioTemporalMomentumTradingStrategy`** (the STM signal factor as its dependency; parameters
   `target_vol`, `gross_cap`, `periods_per_year`).
5. **Switch `STMTradingCycle.step` to the strategy → construction → TargetPortfolio path**, keeping
   `CycleResult.weights` filled from the TargetPortfolio, so both algorithms
   (`spatio_temporal_momentum_project_full` and `..._10m_live`) and the progress / report code keep working
   unchanged.
6. **Only then** change the algorithms to pass the TargetPortfolio to `set_holdings` (the live algorithm keeps its
   `shortable.restrict` step, applied to the target).
7. **Leave `signals_to_weights` as a thin wrapper** over the new construction until no caller remains (research
   reports use `stm_backtest` too), then remove it.
8. **Regression:** old weights vs new TargetPortfolio weights, and old vs new order quantities, on synthetic
   panels and on recorded `CycleResult`s; the existing STM tests (`tests/spatio_temporal_momentum/*`,
   `test_stm_10m_live.py`, `tests/strategy/test_strategy_run_from_design.py`).

STM is shared by six projects (`spatio_temporal_momentum_project`, `_full`, `_10m`, `_10m_hourly`, `_10m_live`,
and the decile project's cycle): every one of them uses `STMTradingCycle`, so step 5 affects all of them at once.

---

## 7. Risks to existing behaviour

| Risk | Where | Mitigation |
|---|---|---|
| ÷N counts every scored asset, including those whose vol is invalid (weight 0) | `signals_to_weights` | Reproduce exactly, and test it. |
| The gross cap only scales down, never up | `signals_to_weights` | Same. |
| `periods_per_year` comes from `bar_minutes` (252 daily; intraday differs) | `STMTradingCycle.step` | Pass it through unchanged, and test intraday. |
| The TFT output is unbounded, so weights can exceed what tanh models give and hit the gross cap | model | No clipping may be added by the construction layer. |
| `int()` truncation toward zero, multiplier, sells-before-buys order, liquidation scope (class-keyed vs string-keyed) | `set_holdings` | Golden tests before extraction. |
| Container rows are created before quantities are known (also for tickers that end with 0 orders) | `set_holdings` step 6 | Keep that order; a pure rebalancer must not drop it. |
| Two gross checks: cap in `signals_to_weights`, refusal in `set_holdings` (default 1.0) | both | A config with `gross_exposure_cap > 1` would be refused by `set_holdings` in the full project; keep both checks as they are. |
| `new_decision` is ignored: repeated sessions re-send the same weights | both STM algorithms | Keep as is (behaviour), note as debt. |
| The live path adds the shortable restriction after weights | `_10m_live` algorithm | Keep it after construction, before rebalancing. |
| Six STM projects share the cycle; CSM, deciles and SPX share `set_holdings` | many | Migrate behind unchanged interfaces; run every project's tests. |
| Layering: the LGBM factor repository (infrastructure) imports the application-level provider | `company_share_lgbm_cs_quintile_rank_momentum_factor_repository._inject_provider` | Existing; do not copy this pattern for TradingStrategy. |
| The LGBM factor returns a quintile 1–5 per share (classification), not a raw score | the factor | P5's quintile strategy can read quintiles directly. Re-ranking them would only re-bucket ties: decide which one P5 uses. |
| Naming: `Strategy` (configuration) vs `TradingStrategy` (factor) | domain | Keep both names distinct in code and in the UI. |

---

## 8. Answers to the audit questions in one place

- **Factors are defined** as `Factor` subclasses (metadata + optional `calculate_dependencies` / `calculate`);
  **persisted** in `factors` (polymorphic) and `factor_values` (scalar per entity and date); **evaluated** by
  `FactorValueResolutionService.resolve_factor_value`; **linked** by code (`DependencySpec`) or DB rows
  (`FactorDependency`); **resolved recursively** through `resolve_factor_value` → `_resolve_dynamic_dependencies`
  → `_resolve_dependency_spec` → `resolve_factor_value`.
- **Ranking / scoring factors:** LGBM quintile rank (1–5, per share, provider-backed), CSM score, STM signal,
  generic `ConstituentScoreFactor`. Cross-sectional factors exist for ETFs (dispersion), via `per_entity` specs.
- **Universe** is already a pure listing at `UniverseFinancialAsset` level; `UniverseConstituent.weight` is
  composition data.
- **There is no portfolio-construction layer, no TargetPortfolio and no rebalancer as separate components.**
  Construction rules live inside each strategy's trading cycle; rebalancing and execution are mixed in
  `set_holdings`.
