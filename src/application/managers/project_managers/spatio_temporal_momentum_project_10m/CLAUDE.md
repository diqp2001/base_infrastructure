# CLAUDE.md – spatio_temporal_momentum_project_10m

## Intraday STM: model TRAINED on 10-minute bars (option A, owner's choice 2026-10-21)

Same strategy, paper universe and reusable services as `spatio_temporal_momentum_project_full`, but one
row = one **10-minute bar** instead of one session, and a new decision every 10 minutes. It is not the daily
model re-scored intraday: features, labels, training and scoring are all on 10-minute bars.

* Universe = the paper's US Equities (Appendix B), `data/paper_universe.py`, 48 tickers.
* Every window is counted in bars (39 per 09:30-16:00 session, `stm_time.bars_per_session(10)`):
  - returns over 1 / 3 / 6 / 39 bars (10 min, 30 min, 1 h, 1 session); vol span 39;
    MACD (3,9), (6,18), (12,36) normalised over 39; winsorise half-life 39;
  - model input window 24 bars = 4 h (TFT encoder 16 + decoder 8);
  - label = the next bar's return (`prediction_horizon` 1);
  - rolling training window `training_window` = 390 bars (10 sessions); validation = last 3 calendar days;
  - annualisation `periods_per_year(10)` = 252 x 39 (features, weights and report metrics).
* Retrain every day (`retrain_every_days` 1); a model is used from the bar after its validation end.
* Data: IBKR **TRADES** 10-minute bars (`bar_size_setting` '10 mins'); the account has no US-equity quote
  permission, so MIDPOINT is refused (BI-037). IBKR serves at least 3 months of 10-minute bars in one request.
* Engine clock: `config_interval {'custom_interval_minutes': 10, 'session_start': '09:40', 'session_end': '16:00'}`
  — the engine skips the night (first decision 09:40 when the 09:30 bar has closed, last at 16:00).
* Kept separate from the daily projects: results `results/spatio_temporal_momentum_10m/`,
  models `weights/spatio_temporal_momentum_10m/`, ML model prefix `stm10m_`, feature factors `stm10m_*`
  (subgroup `minutes`, frequency `10m`), signal factor `spatio_temporal_momentum_signal_10m`,
  universe `stm_paper_us_financials_10m`, portfolio `Spatio_Temporal_Momentum_10m_Portfolio`.
  Dashboard: `/stm/?project=10m`.

## How the shared STM services handle bars

`STMConfiguration.bar_minutes` (None = daily, unchanged behaviour; 10 here) drives
`stm_time` (`bar_key`, `next_key`, `bars_per_session`, `periods_per_year`, `frequency`):

| Daily (`bar_minutes` None) | Intraday (`bar_minutes` 10) |
|---|---|
| row key = session date (`normalize`) | row key = bar start floored to 10 minutes |
| close factor frequency `1d`, visible from D+1 00:00 | frequency `10m`, bar stamped 10:00 visible from 10:10 |
| feature/signal factors subgroup `daily`, frequency `1d` | subgroup `minutes`, frequency `10m` |
| annualisation 252 | 252 x 39 |

The frontier rule is the MarketDataHistoryService one (raw bars stamped at their START, usable once
`start + bar length <= frontier`), so a decision at 10:10 sees the 10:00 bar and nothing later.

---

The project runs **inside the Misbuffet engine, bar by bar, exactly as it would live**.
At each bar the algorithm calls `STMTradingCycle.step(t)`, which:

1. advances the `MarketDataHistoryService` frontier to *t*;
2. lets `BarHistoryUpdater` import new IBKR 10-minute bars (writes only): the whole history once
   (whole weeks ending now), then the last day after each new bar;
3. reads closes **only through the frontier** (`STMFrontierPriceReader`, frequency `10m`);
4. decides eligibility on history known at *t*;
5. retrains when due: train on data known at *t*, validation = latest `val_days`, no test fold;
6. scores the universe, stores the signals, returns vol-scaled weights -> `set_holdings`.

## Structure

```
spatio_temporal_momentum_project_10m/
├── config.py                      # DEFAULT_CONFIG; every window in 10-minute bars
├── project_manager.py             # SpatioTemporalMomentum10mProjectManager: backtest + post-run report
├── data/
│   ├── paper_universe.py          # paper's 46 US financials + replacements
│   ├── sector_constituents.py     # reference sectors (not used)
│   ├── universe_setup.py          # Universe + UniverseConstituent
│   └── price_ingestion.py         # BarHistoryUpdater (MarketDataService, write-only)
├── models/model_trainer.py        # STMModelTrainer(BaseModelTrainer): create_factors + build_cycle
└── backtesting/
    ├── backtest_runner.py         # BacktestRunner(BaseBacktestRunner)
    ├── base_project_algorithm.py  # Algorithm(BaseProjectAlgorithm): on_data -> cycle.step
    └── synthetic_demo.py          # same cycle on synthetic 10-minute closes (tests)
```

Run:
```python
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.project_manager import (
    SpatioTemporalMomentum10mProjectManager,
)
results = SpatioTemporalMomentum10mProjectManager().run()   # backtest_start..backtest_end, every 10 minutes
```

## Key rules

* **One path for backtest and live**; `report` only evaluates what the engine decided.
* **All decision reads go through the frontier** (`STMFrontierPriceReader`).
* **IBKR import**: requests end now (6-month end-date limit); bars beyond *t* exist in the DB during a
  backtest but are invisible through the frontier.
* Training cost: retraining every day on 390 bars x 48 assets; keep `n_epochs` / early stopping in mind
  when lengthening the backtest window.
* Not modelled: the overnight gap is treated as one more bar (the first bar's return includes it);
  no intraday transaction costs beyond the report's cost scenarios.

Tests: `tests/spatio_temporal_momentum/test_stm_intraday.py`.
