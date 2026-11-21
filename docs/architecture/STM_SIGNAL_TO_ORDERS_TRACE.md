# STM full project: from model output to orders (current implementation)

Project: `src/application/managers/project_managers/spatio_temporal_momentum_project_full`
Traced at commit aabd99af (2026-11-20). Read-only investigation: no code was changed.

**Summary.** The STM model's score per stock becomes a target weight inside the STM package itself
(`signals_to_weights`, called from `STMTradingCycle.step`). There is no ranking, no threshold and no
top-N selection. A generic method, `UnifiedPortfolioManager.set_holdings`, turns the weights into order
quantities and decides buy or sell. There is no separate portfolio-construction component, and no stored
target portfolio.

---

## 1. STM factor layer

Folder: `src/application/services/data/entities/factor/spatio_temporal_momentum/`

| Purpose | File · class / function | What it does | Inputs → outputs |
|---|---|---|---|
| Configuration | `stm_configuration.py` · `STMConfiguration`, `STMFeatureConfig`, `STMModelConfig`, `STMTrainingConfig`, `STMUniverseConfig` | Holds every research setting; built by the project's `config.build_stm_configuration()` | Project config dict → frozen config objects |
| Price reads | `stm_price_history.py` · `STMFrontierPriceReader.load_close_panel` | Reads closes only up to the frontier (no look-ahead) | `{entity_id: ticker}`, start → close panel (dates × tickers) |
| Feature definitions | `stm_features.py` · `compute_asset_features` | Winsorises prices; computes vol-normalised returns per horizon, MACD signals, daily vol, and the training target (forward return × vol_target / annualised vol) | One close series → feature frame |
| Feature values | `stm_dataset.py` · `align_close_panel`, `build_feature_panel`, `build_samples`, `build_inference_input` | Keeps only dates where every asset has a close, then builds features, targets and daily vol per date and asset | Close panel → `FeaturePanel` (features, target, daily_vol) → model tensors |
| Model | `stm_models.py` · `SpatioTemporalMomentumNet`, `build_model` | `forward()` returns one value per asset at the last time step | `[batch, lookback, assets, features]` → `[batch, assets]` |
| Network bodies | `stm_tft.py` (TFT), `stm_simple_models.py` (LSTM / MLP / SLP / conv) | TFT ends in a plain linear layer; the others end in `tanh` | — |
| Training | `stm_training.py` · `train_window`; `stm_losses.py` · `sharpe_loss` | Adam with early stopping on validation Sharpe. The loss is −Sharpe of `pred × return`, so the output is trained to act as a position | Train / validation samples → state dict |
| Retraining in time | `stm_walk_forward.py` · `STMWalkForwardTrainer.train_as_of` | Trains on data known at the decision date; validation is the last `val_days` | Panel, as-of date → `WindowResult` (artifact id) |
| Model storage | `stm_artifact_store.py` · `STMArtifactStore.save_artifact`, `select`, `load` | Persists models; `select` only returns a model whose `validation_end < as_of` | Model + metadata ↔ stored artifact |
| Prediction | `stm_model_provider.py` · `SpatioTemporalMomentumModelProvider.score_details` / `score_details_with_artifact` | Rebuilds features up to the session and runs the model | Session → `[{ticker, entity_id, score, daily_vol}]` |
| Signal persistence | `stm_feature_store.py` · `STMFeatureStore.write_signals` (and `read_signals`) | Writes each score as a factor value (`factor_type='company_share_spatio_temporal_momentum_factor'`; the full project's signal factor name is `spatio_temporal_momentum_signal_full`). `read_signals` has no caller in `src` | `{entity_id: score}` → `factor_values` rows |
| Signal → weights | `stm_backtest.py` · `signals_to_weights` | Volatility-scaled weights with a gross cap (formula in section 4) | scores, daily vols → `{ticker: weight}` |
| Orchestration | `stm_trading_cycle.py` · `STMTradingCycle.step` (`_eligible`, `_retrain_due`, `_train`) | Once per engine step: read, choose eligible assets, retrain when due, score, compute weights, store signals | time `now` → `CycleResult` (scores, daily_vol, weights) |

---

## 2. Execution path (backtest, the only path this project runs)

```text
[spatio_temporal_momentum_project_full/project_manager.py]
SpatioTemporalMomentumFullProjectManager.run() -> ._run()
    |
[misbuffet/engine/base_backtest_runner.py]
BaseBacktestRunner.run_backtest(config)
    |- [project]/backtesting/backtest_runner.py  BacktestRunner.setup_components()         -> STMModelTrainer(...)
    |- [project]/backtesting/backtest_runner.py  BacktestRunner.create_algorithm_instance() -> Algorithm, set_trainer
    '- Misbuffet.launch() -> start_engine() -> run(LauncherConfiguration)
    |
[misbuffet/engine/misbuffet_engine.py]
MisbuffetEngine.run(config) -> _run_simulation()       (time loop)
    |   once, at start
[project]/backtesting/base_project_algorithm.py  Algorithm.initialize()
    |- [misbuffet/algorithm/base.py] QCAlgorithm.register_portfolio()
    |     -> UnifiedPortfolioManager.register_portfolio_with_config()
    '- [project]/models/model_trainer.py  STMModelTrainer.build_cycle()
          DailyHistoryUpdater.ensure_entities(), UniverseSetup.register(), ensure_factors() -> STMTradingCycle(...)
    |   every step
[misbuffet/engine/misbuffet_engine.py]  self.algorithm.on_data(data_slice)
    |
[project]/backtesting/base_project_algorithm.py  Algorithm.on_data(data)
    |
[stm_trading_cycle.py]  STMTradingCycle.step(bar_time)
    |- history_service.set_frontier(now); data_updater(now)
    |- STMFrontierPriceReader.load_close_panel()            -> closes
    |- _eligible(closes, session)                           -> eligible tickers
    |- _retrain_due() -> _train()
    |     align_close_panel -> build_feature_panel -> STMWalkForwardTrainer.train_as_of
    |     -> _train_split -> train_window (sharpe_loss) -> STMArtifactStore.save_artifact
    |- SpatioTemporalMomentumModelProvider.score_details(session)
    |     artifact_store.select -> score_details_with_artifact -> build_inference_input -> model(X)
    |- signals_to_weights(scores, daily_vol, target_vol, gross_cap, periods_per_year)  -> result.weights
    '- STMFeatureStore.write_signals(session, {entity_id: score})
    |
[misbuffet/algorithm/unified_portfolio_manager.py]
UnifiedPortfolioManager.set_holdings({CompanyShare: [{'name': t, 'weight': w}, ...]}, data)
    |- _normalize_target_weights()
    |- gross check against max_gross_weight (default 1.0)
    |- get_portfolio_value(backtest_date)
    |- _ensure_asset_container(ticker)
    |     [local_repo/finance/portfolio/company_share_portfolio_repository.py]
    |     ensure_sub_portfolio_linked()   -> CompanySharePortfolio + CompanySharePortfolioPortfolioHolding
    |     ensure_ticker_holding()         -> CompanySharePortfolioHolding + Position(quantity 0)
    |- _select_liquidations(held - targeted)
    |- per ticker: _reference_price(), _get_current_position_qty() -> _qty_in_container()
    |     target_qty = int(PV * weight / (price * multiplier));  order_qty = target_qty - current_qty
    |- sorted into sells (order_qty < 0) and buys (> 0); _has_budget_for_trade()
    '- _execute()   (sells first, then buys)
    |
[misbuffet/algorithm/trade_manager.py]
TradeManager.execute_trade(ticker, order_qty, price, portfolio_id=<sub-portfolio>, ...)
    |- _resolve_holding_id()      finds the holding, or creates PositionModel + HoldingModel
    |- submit_order_fn = QCAlgorithm.market_order() -> _submit_order()   (backtest: in-memory ticket)
    '- _book_atomically(_book):
          _register_order()         -> Order(side "BUY"/"SELL", quantity |order_qty|, status FILLED)
          _record_fill()            -> Transaction
          _update_position()        -> Position.quantity += order_qty  (LONG / SHORT)
          _update_cash_for_trade()  -> cash Order + Transaction on the CurrencyPortfolio
    |
CompanySharePortfolioHolding -> Position
(the share's holding inside the CompanySharePortfolio sub-portfolio)
```

---

## 3. Where the model output becomes a signal

| Question | Answer, with the code |
|---|---|
| What does the model output per asset? | One float per asset: `SpatioTemporalMomentumNet.forward` returns `forward_sequence(x)[:, -1, :]`. |
| Is it in [-1, +1]? | Not with this project's model. The config uses `'model_type': 'tft'`, and the TFT ends in `output_layer = nn.Linear(...)` with no `tanh`, so the score is unbounded. The LSTM, MLP, SLP and conv models end in `torch.tanh`, which bounds them to [-1, 1]. |
| Where is it stored? | In memory in `CycleResult.scores`. It is also written to `factor_values` by `STMFeatureStore.write_signals`. |
| What entity represents it? | A `FactorValue` of the signal factor (`factor_type company_share_spatio_temporal_momentum_factor`, entity type CompanyShare). There is no Signal entity. |
| Where is it read for portfolio construction? | Nowhere from the database. Weights are computed in memory from `result.scores` in the same `step()`; `read_signals` has no caller in `src`. |
| Ranked? | No. |
| Long/short threshold? | No. The sign of the score is the side. |
| Top-N / bottom-N? | No. Every scored asset gets a weight. |
| Magnitude used directly for sizing? | Yes, linearly. |
| Normalised? | Divided by N, the number of scored assets. Then, only if Σ\|w\| exceeds the cap, all weights are rescaled down to the cap. Weights are never scaled up. |
| Volatility scaling? | Yes: × target_vol / (daily_vol × √periods_per_year). daily_vol is the EWM vol from the features. |
| Sector or universe constraint? | No sector constraint. Universe rules only decide eligibility in `_eligible`: the asset must be an active universe member, have enough history and have a close at the session. The live project also has a split guard and a shortable-stock filter. |

---

## 4. The formula that sets target holdings

In `stm_backtest.signals_to_weights`, with values from the full project's config (`target_vol` 0.15,
`gross_exposure_cap` 1.0, daily bars so `periods_per_year` 252):

```text
w_i = s_i * target_vol / (sigma_i * sqrt(252)) / N        (w_i = 0 if sigma_i is missing or <= 0)
if sum(|w|) > gross_cap:   w_i = w_i * gross_cap / sum(|w|)
```

In `UnifiedPortfolioManager.set_holdings` (lines 1355–1368):

```text
target_qty = int(portfolio_value * w_i / (price_i * multiplier_i))     (truncated toward zero)
order_qty  = target_qty - current_qty
```

So the pipeline is: score → volatility scaling → ÷N → gross cap → weight → quantity → difference.
There is no ranking or selection step.

---

## 5. PortfolioHolding

- **The `PortfolioHolding` domain class** appears only as `'holding_class': PortfolioHolding` in the
  project config's `Portfolio` section. Nothing on the misbuffet trading path reads `holding_class`.
- **The holdings actually used** are ORM rows:

  | Action | Where |
  |---|---|
  | Created | `CompanySharePortfolioRepository.ensure_sub_portfolio_linked` and `ensure_ticker_holding`, called from `UnifiedPortfolioManager._ensure_asset_container`. As a fallback, `TradeManager._resolve_holding_id` creates `PositionModel` + `HoldingModel` if none exists. |
  | Updated | `TradeManager._update_position`: `Position.quantity += order_qty`, position type set to LONG or SHORT. |
  | Read | `UnifiedPortfolioManager._get_current_position_qty`, `_qty_in_container` and `_get_all_held_tickers`, which walk main portfolio → CompanySharePortfolio → holdings. |
  | Linked to an order | `TradeManager._register_order` puts `holding_id` on the Order row. |

- **Signal, target, current, order:**
  - The signal is `CycleResult.scores` (in memory).
  - The target is `CycleResult.weights` (in memory, never stored as an entity). The target quantity
    exists only as the local variable `target_qty`.
  - The current holding is the Position quantity in the database.
  - The trade is `order_qty = target_qty − current_qty`, computed in `set_holdings` (line 1368).
    So yes, "target − current = trade", and that is the place.

---

## 6. BUY / SELL generation

| Stage | File · function | Key variables and logic |
|---|---|---|
| STM signal | `stm_trading_cycle.py` · `STMTradingCycle.step` | `result.scores` |
| Target portfolio | `stm_backtest.py` · `signals_to_weights` | `result.weights` |
| Target holding | `unified_portfolio_manager.py` · `set_holdings` | `target_pct`, `target_qty`, `portfolio_value`, `price`, `multiplier` |
| Rebalance | same | `current_qty`, `order_qty = target_qty − current_qty`; held CompanyShares that are no longer targeted (`to_liquidate`) get a target of 0 |
| Order | `trade_manager.py` · `execute_trade` → `_register_order`; `base.py` · `QCAlgorithm._submit_order` | `"side": "BUY" if order_qty > 0 else "SELL"`; `OrderDirection.BUY if quantity > 0 else SELL` |

Where each decision is made:

- **BUY or SELL:** the sign of `order_qty` in `set_holdings`. A negative quantity goes to the sells
  list, which runs first; a positive one goes to buys.
- **No trade**, from most to least common:
  - `order_qty == 0`, skipped;
  - no weights (no eligible model yet), so `set_holdings` is never called;
  - no price, or the budget check fails, so that ticker is skipped;
  - Σ|w| above `max_gross_weight`, so the whole call is refused;
  - a `min_weight_change` band exists in `set_holdings`, but STM doesn't pass it.
- **Repeated sessions:** both STM algorithms ignore `CycleResult.new_decision`. A step that repeats the
  previous session returns the same weights, and `set_holdings` is called again with them.

---

## 7. Backtest, paper and live

- **The full project is backtest only.** No ledger or reconciler is attached and `live_mode` is false.
  `_submit_order` creates an in-memory ticket, and `TradeManager` books the fill straight away at the
  reference price (adjusted only if a fill model is attached).
- **Live (and paper)** is a separate project, `spatio_temporal_momentum_project_10m_live`
  (`live_runner.py`, wired by `misbuffet/live/live_stack.build_live_stack`). Paper and live use the same
  code against different IBKR accounts.
- **Shared between them:** `STMTradingCycle.step`, `signals_to_weights`, and `set_holdings` with the
  same weights.
- **Where they diverge:**
  - the live algorithm restricts shorts to stocks IBKR can lend (`shortable.restrict` sets the rest
    to 0), records each decision (`record_decision`), and passes `max_gross_weight`;
  - `set_holdings` live gates: reconciler, order ledger drain, start-up recovery;
  - `TradeManager._execute_live`: the intent is recorded, the order sent through the transaction
    handler and broker (with the pre-trade risk gate), and booked only when the execution comes back
    through the `OrderLedger`.
- So the portfolio-construction logic is the same in both paths. Only the execution and safety layers
  differ.

---

## 8. STM-specific vs generic

- **STM-specific:**
  - features, dataset, models, training, walk-forward, artifacts and provider;
  - the eligibility and retraining schedule in `STMTradingCycle`;
  - portfolio construction too: `signals_to_weights` sits in the STM package (`stm_backtest.py`) and
    only `STMTradingCycle` calls it.

  The other projects do the same in their own cycle code. For example, the decile project has
  `STMDecileTradingCycle.long_short_weights`.
- **Generic:**
  - `BaseBacktestRunner`, the Misbuffet engine, `BaseProjectAlgorithm` / `QCAlgorithm`;
  - `UnifiedPortfolioManager.set_holdings` (weights → quantities → orders, liquidation, gates), which
    works for any asset class through the `<AssetClass>Portfolio` repositories;
  - `TradeManager` (orders, fills, positions, cash), the portfolio repositories, and the live stack.

---

## 9. The architecture as implemented

```text
STM Features      stm_features / stm_dataset.build_feature_panel
      |
STM Model         STMWalkForwardTrainer.train_as_of -> SpatioTemporalMomentumModelProvider.score_details
      |
STM Signal        CycleResult.scores   (also written to factor_values; never read back)
      |
signals_to_weights()  inside STMTradingCycle.step   (vol scaling, /N, gross cap)
      |
Target Portfolio  CycleResult.weights {ticker: weight}   (in memory only)
      |
UnifiedPortfolioManager.set_holdings()   target_qty, order_qty = target - current, sells then buys
      |
TradeManager.execute_trade() -> QCAlgorithm.market_order() -> Order / Transaction / Position
```

1. **Where is the signal converted into a target holding?** In `STMTradingCycle.step`, which calls
   `signals_to_weights` to produce weights. The quantity comes later, in `set_holdings`.
2. **Where is the size or weight set?** The weight in `signals_to_weights`; the quantity in
   `set_holdings` (`int(PV × w / (price × multiplier))`).
3. **Where is buy or sell decided?** In `set_holdings`, by the sign of
   `order_qty = target_qty − current_qty`. The side string is then written in
   `TradeManager._register_order`.
4. **Is there a dedicated portfolio-construction component?** No. It is one function inside the STM
   package, and each strategy's cycle computes its own weights.
5. **STM-specific or generic?** Signal → weights is STM-specific (it lives in the STM package and only
   `STMTradingCycle` calls it), although the function itself is a pure, general formula.
   Weights → orders is generic.
6. **To run another strategy on another universe today, you would reuse:**
   - `BaseBacktestRunner`;
   - a `BaseProjectAlgorithm` subclass whose `on_data` builds `{AssetClass: [{'name', 'weight'}]}`;
   - `UnifiedPortfolioManager.set_holdings` and `TradeManager`;
   - the portfolio repositories and, for live, the live stack.

   You would write your own signal → weight step, or import `signals_to_weights` from the STM package.
7. **What is missing?**
   - A portfolio-construction layer between signals and execution: one interface for signals → target
     portfolio (ranking/selection, normalisation, risk scaling, constraints).
   - A stored target-portfolio entity. Targets exist only in memory; the live path keeps a decision
     record via `record_decision`.

   Constraints are currently spread across four places:
   - `signals_to_weights` (gross cap);
   - `set_holdings` (gross check, budget);
   - the live shortable filter;
   - the pre-trade gate.

   The Strategy / `strategy_parameters` tables added recently only store configuration; they don't
   construct portfolios.
