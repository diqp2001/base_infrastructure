# CLAUDE.md – stm_monthly_decile_project

## Monthly cross-sectional deciles of the spatio-temporal momentum model (created 2026-11-16)

**Research question:** each month, rank the Dow members by the STM model's score. Do the higher deciles outperform the
lower ones over the next month, and do Eulerpool fundamentals widen the D10 − D1 spread?

### Owner's choices (2026-11-16)

- **Model.** The existing STM pipeline (the 10m_live code: features, TFT, Sharpe loss, `STMWalkForwardTrainer`) on
  **monthly bars**.
  - One row is one month-end close (the last trading day of the month).
  - The target is the next month's return: `prediction_horizon = 1` row, the existing configurable STM target.
  - The model is retrained at every monthly rebalance.
- **Universe.** The Dow members in force at each rebalance: `src/application/services/universe/djia_membership.py`,
  point-in-time from 2020-08-31.
- **Deciles.** D1 has the lowest scores and D10 the highest. Each decile is equal-weighted and held one month.
- **The Misbuffet engine trades D10 − D1:** +0.5 spread equally over D10 and −0.5 over D1 (`long_short_gross` 1.0).
  Every decile's performance is computed by the cycle and reported through time.
- **Model A** uses the price features. **Model B** adds Eulerpool point-in-time fundamentals
  (`deciles.use_eulerpool_fundamentals`). Both use the same members, dates, target, deciles and weighting.

## Rebalance period (since 2026-11-20, owner's request)

Monthly is the project's design and default. `deciles.rebalance_every` can also be every N trading days, weeks or
months (`'5d'`, `'1w'`, `'2w'`, `'3mo'`); the strategy designer's Trading frequency sets it.

- One model row is one period-end close (`period_end_panel(daily, T, 'D' | 'W' | 'M')`). The cycle rebalances at
  the last trading day of the latest completed period, every N periods.
- `stm.features.annualisation` and the decile statistics' `periods_per_year` follow the period: 252, 52 or 12,
  divided by N (`config.periods_per_year`).
- `retrain_every_rebalances` counts rebalances. The designer's Training frequency converts to it, counting a week
  as 5 trading days and a month as 21.
- The other row counts keep their numbers but now mean periods: `return_horizons`, `lookback`,
  `rolling_window_rows`, `prediction_horizon` and the MACD windows. Weekly with the monthly defaults is
  1/3/6/12-week horizons and a 120-week training window. Set them for the period you choose.
- A non-monthly run registers its models as `stm_decile_<token>_<variant>`; monthly keeps `stm_monthly_decile_*`.
- The report still says "month" in its labels (best / worst month): read it as "period".

## Flow (inside the Misbuffet engine, one daily bar at a time)

```
Dow members at T (IndexMembership)              daily IBKR closes -> MarketDataService -> factor_values
        |                                          read through the frontier (KnownClosesReader)
        v
month-end close panel up to T (month_end_panel)
        v
model A: STMConstituentScorer (STM pipeline, monthly rows, retrained)    model B: same + fundamentals
        v                                                                    (CSMFundamentals, Eulerpool)
scores -> assign_deciles (D1 lowest .. D10 highest) -> equal weights -> DecileResearch (turnover, costs)
        v
engine: Algorithm.on_data -> set_holdings({CompanyShare: D10 +, D1 -}) -> orders / positions / valuation
        v
next month: settle every variant (member returns T -> T+1) -> decile returns -> cumulative, D10 - D1, statistics
```

`STMDecileTradingCycle.step(t)` (`.../portfolio_research/stm_decile_cycle.py`) only uses closes known at t: a
close dated D is known from D+1 00:00. Its rebalance is the last trading day T of the month before t's month, so the
first step of a month sees T's close. The prediction at T is settled with the closes at the next T.

## Prices: dividend-adjusted research closes (since 2026-11-18, owner's choice)

Two IBKR daily series are imported for every member: `TRADES` (split-adjusted, no dividends) and `ADJUSTED_LAST`
(split- and dividend-adjusted). The model's features and the decile returns read `deciles.research_price_series`
(`ADJUSTED_LAST`): total returns, so high-yield names are not penalised. The Misbuffet engine still trades and
values at `TRADES` closes and pays no dividends, so the engine's P&L remains a price-return P&L.

- `ADJUSTED_LAST` is in `source_policy.EXPLICIT_ONLY_WHAT_TO_SHOW`: no reader without a subgroup (resolution service,
  STM / CSM readers, other projects) ever reads it in place of a traded price.
- IBKR serves it only up to now (empty endDateTime; `InteractiveBrokersBroker.get_historical_data` enforces it). The
  series is back-adjusted as of the import day: returns are exact, levels are not traded prices. A later partial
  import would only append new dates (stored bars are never overwritten), joining two adjustment bases if a dividend
  fell in between: to extend the window, delete the stored ADJUSTED_LAST values first and import the series whole.
- WBA (file caches, not at IBKR) is not dividend-adjusted.

## Point-in-time fundamentals (model B)

- **Path:** `RepositoryFactory.enable_provider_family('eulerpool')` → its statements → `CSMFundamentals`
  (`.../cross_sectional_momentum/csm_fundamentals.py`) → `extra_features(dates, assets)`.
- **Stamping:** each value is stamped when it became public, at min(filing + 1 day, SEC deadline + 1 day). A value
  known at the T 00:00 stamp may be used at T. It is carried forward until the next filing or until stale (1q:
  200 days).
- **Features:** `FUNDAMENTAL_FEATURES`, 11 names:
  - ROE and ROA (TTM);
  - gross, operating and net margin (TTM);
  - revenue, net income and total assets growth (yoy);
  - EPS and FCF growth (1y);
  - debt to equity.
- **Not available:** valuation ratios (they read a daily close) and market capitalisation; neither is served.
- **Preprocessing** (shared `build_feature_panel(extra_features=..., extra_feature_groups=...)`), since 2026-11-18
  **sector-neutral** (`deciles.fundamental_scaling = 'sector_neutral'`, owner's choice): on each date a member's
  value minus its GICS sector's mean (`djia_membership.SECTORS`), divided by ONE standard deviation of those
  residuals across all the grouped members; a member alone in its sector that date (CVX; DOW / SHW when only one
  has a value) keeps the plain z-score across all members. Clipped to ±3. A missing value becomes 0, never a later
  observation. `'cross_sectional'` = the previous scaling across all members. The sectors are today's GICS
  classification for every date (V moved from IT to Financials in March 2023).
- **Storage:** statements are fetched once per share and kept IN MEMORY. Nothing from Eulerpool goes to the
  database. Model B needs the Eulerpool key.

## Outputs (`results/stm_monthly_deciles/<run time>/`, rewritten after every month)

| file | contents |
|---|---|
| `predictions.csv` | rebalance, variant, symbol, score, rank, percentile, decile, model trained at, next month's return |
| `decile_returns_{gross,net}.csv` | D1..D10 and LS (D10 − D1) per month, per variant |
| `cumulative_{gross,net}.csv` | ∏(1+R) − 1 of the same series |
| `turnover.csv` | one-way turnover of every decile at every rebalance |
| `summary.json` | see below |
| `deciles_cumulative.png` | per variant: every decile's cumulative return through time (red D1 → blue D10) and D10 − D1 |

`summary.json` holds, per decile and LS, gross and net:

- cumulative return, annualised return, annualised volatility, Sharpe;
- max drawdown, Calmar, win rate;
- average, median, best and worst month;
- average turnover.

It also holds the monotonicity measures (Spearman of decile vs average and median return, the monthly rank IC, the
average D10 − D1 spread) and the A vs B long-short comparison. Net returns deduct traded notional ×
`transaction_cost_bps` (5).

`status.json` in `results/stm_monthly_deciles/` follows the run.

## Structure (as spatio_temporal_momentum_project_10m / etf_dispersion_stm_project)

```
stm_monthly_decile_project/
├── config.py                      # DEFAULT_CONFIG (engine keys + 'deciles' / 'stm'), build_* helpers, variants()
├── project_manager.py             # STMMonthlyDecileProjectManager: Misbuffet backtest + decile report
├── data/universe_setup.py         # the shared DJIA membership + IndexUniverseSetup
├── data/price_ingestion.py        # the shared DailyHistoryUpdater / file caches
├── models/model_trainer.py        # DecileModelTrainer(BaseModelTrainer): build_cycle, model B's fundamentals
└── backtesting/
    ├── backtest_runner.py         # BacktestRunner(BaseBacktestRunner)
    ├── base_project_algorithm.py  # Algorithm(BaseProjectAlgorithm): on_data -> cycle.step -> set_holdings
    └── synthetic_demo.py          # the same cycle on synthetic closes, in-memory SQLite (tests)
```

## Shared services (reusable)

| service | role |
|---|---|
| `stm_decile_cycle.py` | `STMDecileTradingCycle` and `month_end_panel` |
| `stm_constituent_scorer.py` (moved from `dispersion/`) | the STM pipeline in memory; new `extra_features` |
| `stm_dataset.build_feature_panel(extra_features=...)` | point-in-time extra feature panels; new `cross_sectional_zscore` |
| `stm_metrics` | `periods_per_year` (default 252, unchanged for every caller) |
| `portfolio_research/decile_portfolios.py` | deciles, weights, turnover, costs, returns, cumulative, statistics, monotonicity |
| `portfolio_research/decile_report.py` | the report and chart |
| `universe/djia_membership.py`, `universe/index_universe_setup.py` | the Dow membership and its universe setup |
| `backtest_preload/daily_price_sources.py`, `known_closes_reader.py` | daily price sources and the known-closes reader |

Some of these moved out of `etf_dispersion_stm_project`, which re-exports them.

## Limits

- **Small deciles.** The Dow has 30 members, so a decile has about 3. The universe is configurable through the
  membership, but the STM network models every asset jointly, so its input grows with the universe.
- **History and eligibility.** The membership is point-in-time from 2020-08-31 only. A member needs 120 months of
  closes (`rolling_window_rows`): DOW (listed 2019) is unscored and in no decile.
- **WBA** (delisted 2025) is not at IBKR. Its closes come from the Eulerpool file cache.

## Run

```python
from src.application.managers.project_managers.stm_monthly_decile_project.project_manager import (
    STMMonthlyDecileProjectManager,
)
STMMonthlyDecileProjectManager().run()
```

This needs the IBKR gateway for the preload of daily bars from 2007, and the Eulerpool key for model B.

Tests: `tests/stm_monthly_deciles/test_monthly_deciles.py` (synthetic, in memory, ~2 min).
