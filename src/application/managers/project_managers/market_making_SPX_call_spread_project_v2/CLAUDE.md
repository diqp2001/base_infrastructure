# CLAUDE.md – market_making_SPX_call_spread_project_v2

## Purpose

Same SPX / SPY call market-making strategy as `market_making_SPX_call_spread_project`
(same universe, factors, bar size, backtest window, Strategy, hedging bands, pricing and
volatility models), restructured like the Spatio-Temporal Momentum projects:

* the Misbuffet algorithm is thin: at each bar it calls `SPXCallSpreadTradingCycle.step`;
* the cycle holds every decision, in the original `on_data` order, and is engine-agnostic
  (it only needs a portfolio gateway), so the same code runs in backtest and live;
* the project manager launches the engine, writes live progress (`progress.json`) and a
  final summary (`results.json`) to `config['results_dir']`, and raises when the engine
  failed (BaseBacktestRunner hides engine failures in its summary text).

The original project is left untouched.

---

## Structure

```
market_making_SPX_call_spread_project_v2/
├── config.py                      # DEFAULT_CONFIG (copy of the original + v2 names, results_dir,
│                                  #   option_entry_weight, hedge_symbol), get_config, get_trading_config
├── project_manager.py             # MarketMakingSPXCallSpreadV2ProjectManager: run -> engine, progress, results.json, MLflow
├── data/
│   ├── factor_updater.py          # FactorUpdater: universe entities once; per bar frontier + factor batch
│   └── position_book.py           # PositionBook: open option holdings + greeks resolved at the bar
├── models/
│   ├── model_trainer.py           # MMModelTrainer(BaseModelTrainer): ensure_factors + build_cycle (TWS check)
│   ├── pricing_model.py           # copy (Black-Scholes + greeks, used by Strategy)
│   └── volatility_model.py        # copy (IV surface, used by Strategy)
├── strategy/
│   ├── trading_cycle.py           # SPXCallSpreadTradingCycle.step -> CycleResult
│   ├── market_making_strategy.py  # copy (Strategy: manage_existing_positions, portfolio delta hedge)
│   ├── risk_manager.py            # copy
│   └── hedging/                   # copy (rebalancing bands, WW-NTBN policy)
├── backtesting/
│   ├── backtest_runner.py         # BacktestRunner(BaseBacktestRunner)
│   └── base_project_algorithm.py  # Algorithm(BaseProjectAlgorithm) + PortfolioGateway
├── reporting/
│   ├── spx_report.py              # SPXReport + build_report(results.json summary, data_report.txt)
│   ├── spx_report_renderer.py     # figures, HTML tables, build_pdf (matplotlib PdfPages)
│   └── spx_report_store.py        # report.pkl / report.pdf in results_dir; `python -m ...spx_report_store`
│                                  #   rebuilds the report of the last run from its files
└── utils/progress.py              # MMProgressTracker (progress.json)
```

Tests: `tests/market_making_spx_v2/` (no TWS): `python -m pytest tests/market_making_spx_v2`
- `test_spx_v2_project.py`, `test_spx_v2_order_legs.py` — fakes only, no DB;
- `test_spx_v2_greeks.py` — PositionBook on in-memory SQLite (option position, dated SOFR contract):
  greeks reach the positions, every miss is a WARNING, the universe registers the SOFR contract of
  every backtest date, missing greeks are not a hedged book. The last three gaps are strict xfails.

Performance report (same as the Spatio-Temporal Momentum projects): at the end of a run the manager writes
`report.pkl` and `report.pdf` to `results_dir` (`save_report`, from `results.json` + `data_report.txt`):
run summary, metrics (total / annualised return, vol, downside deviation, MDD, Sharpe, Sortino, Calmar, hit
rate, avg gain / avg loss, annualised with the run's bar frequency), portfolio value + drawdown, P&L per bar
and return distribution, book delta / gamma with the hedges, the orders, and the data issues grouped by root
cause. Notes flag bars whose value did not move (stale valuation) and bars where greeks did not resolve.
Flask (read-only, `src/interfaces/flask/web/controllers/spx_v2_controller.py`): `/spx_v2/` live progress,
`/spx_v2/results` figures and tables, `/spx_v2/report.pdf`. Tests: `tests/market_making_spx_v2/test_spx_v2_report.py`.

Data report: `results_dir/data_report.txt` is rewritten at the end of every `on_data` (bar), and once more
when the run ends or fails (its path is in
`results.json` as `data_report`). Built by `utils/data_report.DataReport`, created with the cycle in
`MMModelTrainer.build_cycle`:
1. checks at start — universe entities created, the SR3 contract of every backtest date registered,
   a factor definition for every greek;
2. greeks that did not resolve, grouped by option / greek / root cause (first / last bar, count), with
   the dependency tree of the first occurrence from
   `services/data/entities/factor/factor_dependency_explainer.FactorDependencyExplainer`: each node's
   value, or why it is missing (`no_definition` + the stored definitions, `no_related_entity` + the
   dated SOFR contract for a currency, `no_observation` + the latest stored value);
3. bars where the hedge was decided while a position had no greeks.
Explanations are capped per run (`PositionBook.MAX_EXPLANATIONS`); the explainer resolves values the
same way the run does.

Greeks and the hedge: `PositionBook.market_data` logs a WARNING (option symbol, greek, bar time) for
every greek that does not resolve. A position without greeks is counted as delta / gamma 0 by
`evaluate_portfolio_delta_hedge` — an empty `greeks` dict means the book looks hedged. Usual causes:
the bar's SOFR contract (`front_month_symbol('SR3', date)`) not in the universe and not returned by
IBKR; delta / gamma / vega resolved before implied vol in a fresh store.

---

## Per-bar flow

```
Algorithm.on_data(slice)
  └─ SPXCallSpreadTradingCycle.step(bar_time, slice, PortfolioGateway(UnifiedPortfolioManager))
       1. FactorUpdater.update(t)            set_frontier(t) + _create_or_get_factor_value_batch
                                             (a failure skips the bar: no trade)
       2. option entry                       quantity(option) == 0 -> set_holdings({CompanyShareOption:
                                             {name: universe option, weight: option_entry_weight}})
       3. PositionBook                       non-zero CompanyShareOptionPortfolioHoldings + delta / gamma /
                                             vega / IV / mid resolved at t (FactorValueResolutionService)
       4. Strategy.manage_existing_positions exits + aggregate portfolio delta-hedge decision (band)
       5. hedge                              should_hedge -> set_holdings({CompanyShare: {name: SPY,
                                             quantity: target_hedge_delta}})
  └─ portfolio value, performance tracking, value_history, progress
```

Wiring (`Algorithm.initialize` -> `MMModelTrainer.build_cycle`): the cycle uses the
ALGORITHM's MarketDataService / MarketDataHistoryService (its frontier) and repository
factory; the engine still builds its slices from the trainer's data loader, whose
MarketDataService gets `_universe_name = project_name` in `setup_components`.

Run:
```python
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.project_manager import (
    MarketMakingSPXCallSpreadV2ProjectManager,
)
results = MarketMakingSPXCallSpreadV2ProjectManager().run()
```
Needs TWS on 127.0.0.1:7497 with a free client id: do not run it while another project
(e.g. a Spatio-Temporal Momentum run) is connected with the same client id.

---

## Separate state from the original project

| | original | v2 |
|---|---|---|
| project / universe name | `market_making_spx_call_spread` | `market_making_spx_call_spread_v2` |
| portfolio | `SPX_Call_Spread_Portfolio` | `SPX_Call_Spread_V2_Portfolio` |
| MLflow experiment | `market_making_spx_call_spread` | `market_making_spx_call_spread_v2` |
| results | — | `results/market_making_spx_call_spread_v2/` |

Kept from the original: `PositionBook` reads option holdings of ALL portfolios (the option
sub-portfolios have no holding row linking them to the main portfolio), so option positions
of another project in the same database are part of the hedged book.

## Differences vs the original project

| Original | v2 | Why |
|---|---|---|
| all logic in `Algorithm.on_data` | `SPXCallSpreadTradingCycle.step`, algorithm only delegates | STM structure; same code for backtest and live |
| entities re-created and factors prepared by `ModelTrainer.train_complete_pipeline` every bar | entities once at initialize; per bar only frontier + factor batch | same factor values, fewer DB calls |
| factor refresh on the trainer's history service | on the algorithm's history service (frontier at the bar) | one frontier per algorithm, as in STM |
| days to expiry from `datetime.now()` | from the bar time | correct in backtest |
| option ticker / -0.2 / `SPY` hard-coded | `universe[CompanyShareOption][0]`, `option_entry_weight`, `hedge_symbol` | configurable |
| SPY bar missing -> exception (bar lost) | hedge still sent; spot only logged | spot was only used for logging |
| `strategy_positions` table enrichment, `_execute_spread_trade`, spread-opportunity generator, mock simulation, tensor / GBM stubs | dropped | never reached in the original run path |
| engine failure reported as success | raised, `progress.json` status `failed` | as in STM managers |
