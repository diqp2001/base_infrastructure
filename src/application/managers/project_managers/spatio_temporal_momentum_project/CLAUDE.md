# CLAUDE.md – spatio_temporal_momentum_project

## Purpose

Integration of **"Spatio-Temporal Momentum: Jointly Learning Time-Series and
Cross-Sectional Strategies"** (Tan, Roberts, Zohren 2023) using the PyTorch
reference implementation <https://github.com/KurochkinAlexey/SpatioTemporalMomentum>
as the source of truth for the maths and the models.

The model receives, at decision date *t*, a tensor
`[assets x lookback x features]` and outputs **one signal per asset jointly**
(cross-sectional information flows because every asset's features enter the
same network). It is not a per-asset univariate momentum model.

The project runs **inside the Misbuffet engine, bar by bar, exactly as it would live**.
At each bar the algorithm calls `STMTradingCycle.step(t)`, which:

1. advances the `MarketDataHistoryService` frontier to *t*;
2. lets `DailyHistoryUpdater` import new IBKR bars (writes only);
3. reads closes **only through the frontier** (`get_factor_value_panel`): a daily bar
   dated D is visible from D+1 00:00, so at a 16:00 bar the decision uses D-1's close;
4. decides eligibility on history known at *t* (never on an asset's future history);
5. retrains when due (`retrain_every_days`, default 365) or when a model asset left the
   universe: train on data known at *t*, validation = latest `val_days`, no test fold;
   the artifact is used **from the next session** (selection needs validation_end < session);
6. scores the universe, stores the signals, returns vol-scaled weights -> `set_holdings`.

Reusable logic lives in `src/application/services/data/entities/factor/spatio_temporal_momentum/`.

---

## Structure

```
spatio_temporal_momentum_project/
├── config.py                      # DEFAULT_CONFIG (+ 'stm', 'factors', retrain_every_days)
├── project_manager.py             # launches the Misbuffet backtest; post-run decisions report
├── data/
│   ├── sector_constituents.py     # reference sectors (full list commented; 2/sector for testing)
│   ├── universe_setup.py          # Universe + UniverseConstituent
│   └── price_ingestion.py         # DailyHistoryUpdater (MarketDataService, write-only)
├── models/model_trainer.py        # STMModelTrainer(BaseModelTrainer): create_factors + build_cycle
└── backtesting/
    ├── backtest_runner.py         # BacktestRunner(BaseBacktestRunner) + decisions_report
    └── base_project_algorithm.py  # Algorithm(BaseProjectAlgorithm): on_data -> cycle.step
```

Misbuffet components used: `BaseBacktestRunner`, `BaseProjectAlgorithm`,
`BaseModelTrainer` (factor creation), `BaseDataLoader`/`EntityService`,
`MarketDataService` (entities + IBKR import), `MarketDataHistoryService` (frontier reads),
`UnifiedPortfolioManager` (orders, transactions, positions).

Reusable services (`.../factor/spatio_temporal_momentum/`):

| Module | Role | Reference origin |
|---|---|---|
| `stm_trading_cycle.py` | per-bar loop (frontier, retrain policy, scoring, weights) | — |
| `stm_configuration.py` | every research parameter | notebook cell 17, features.py defaults |
| `stm_features.py` | DeepMomentum + MACD features | `src/features.py` (bfill removed) |
| `stm_dataset.py` | panel, samples `[S,N,T,F]`, splits, scaler, inference X | `src/data.py` |
| `stm_tft.py`, `stm_simple_models.py` | TFT / LSTM / SLP / MLP / TCN | verbatim |
| `stm_models.py` | `SpatioTemporalMomentumNet`: `[B,N,T,F] -> [B,N]` | multivariate concat |
| `stm_losses.py`, `stm_training.py` | Sharpe loss, one training window | `src/utils.py`, cell 19 |
| `stm_walk_forward.py` | `train_as_of` (live/backtest) and `run` (research windows) | cell 19 loop |
| `stm_backtest.py`, `stm_metrics.py` | captured returns with costs, baselines, metrics | `evaluation.ipynb` |
| `stm_price_history.py` | `STMFrontierPriceReader` (decisions) / direct reader (post-run report) | — |
| `stm_universe.py`, `stm_feature_store.py`, `stm_artifact_store.py`, `stm_model_provider.py` | persistence + inference | LGBM pattern |

Run:
```python
from src.application.managers.project_managers.spatio_temporal_momentum_project.project_manager import (
    SpatioTemporalMomentumProjectManager,
)
results = SpatioTemporalMomentumProjectManager().run()   # Misbuffet backtest, backtest_start..backtest_end
```

### Flask dashboard (`/stm/`) — read-only viewer

```bash
python -m src.interfaces.flask.app        # then open http://127.0.0.1:5000/stm/
```

* Runs are started OUTSIDE the web app (e.g. `src/main.py`). Every
  `SpatioTemporalMomentumProjectManager.run()` writes to `config['results_dir']`
  (`results/spatio_temporal_momentum/`):
  `progress.json` (live, `STMProgressTracker(persist_path=...)`), then `report.pkl` + `report.pdf`
  (`stm_report_store.save_report`) when the run completes, or the error when it fails.
* The dashboard only reads those files, so a run can be followed from a browser opened at
  any time, and the latest stored results (`/stm/results`, `/stm/report.pdf`) survive restarts.
* Report caveats (also printed in the report): no DMN reference model; TSMOM/CSMOM use the
  longest configured return horizon; SHAP via Expected Gradients (no `shap` dependency).
* `backtesting/synthetic_demo.py` runs the same cycle on synthetic data (used by the dashboard test).

---

## Key rules

* **One path for backtest and live.** No up-front training, no separate research backtest.
  `decisions_report` only evaluates, after the run, what the engine decided.
* **All decision reads go through the frontier.** Use `STMFrontierPriceReader`; the direct
  `STMPriceHistoryReader` is for post-run evaluation only.
* **4-month setup (user decision 2026-10-01).** `training_window` 84 = the rolling history
  the model is trained on and the only history the system needs (~4 months). Everything fits
  inside it: features (returns 1/5/10/21d, vol span 20, MACD 2/6, 4/12, 8/24 normalised over
  10/10) are valid from row 22, the model input window is 21 sessions (TFT 14 + 7), so each
  training has ~42 samples (validation = last 14 calendar days). Retrain every 30 days.
  Restore the reference windows in `STM_FEATURES` / `stm.model` for the paper's setup.
* **IBKR import**: requests must end within 6 months, so the updater requests up to today;
  bars beyond *t* exist in the DB during a backtest but are invisible through the frontier.
* `SpatioTemporalMomentumModelProvider.default_config` is set by `STMModelTrainer` so
  repository-injected providers use the project configuration.

## Intentional differences vs the reference

| Reference | Here | Why |
|---|---|---|
| `.bfill()` on vol / MACD stds | removed; rows dropped by warm-up | look-ahead; values identical from row 314 |
| no purge between folds | last `purge_days` rows of train/val dropped | labels of those rows are realised in the next fold |
| models trained up front for fixed yearly windows | trained inside the engine when due, on data known at the bar | identical code backtest/live; regression test proves equal weights for equal dates |
| signal at close D trades D->D+1 | decision at a 16:00 bar uses D-1's close (bar D closes at D+1 00:00) | frontier availability rule; configurable via bar time |
| universe filtered by >3000 rows, then sampled | sampled from the full sector lists (optional `eligible` filter); short histories dropped at alignment and reported | the yfinance length filter cannot be reproduced; delisted tickers (ATVI, PXD, MRO, CDAY) are reported missing |
| best checkpoint file must exist | falls back to final weights if no epoch > 0 improved | avoids a crash on very short runs |
| `empyrical` metrics | re-implemented (`stm_metrics.py`) | dependency not installed |
| 252-day features, expanding history, yearly folds | 21-day max features, rolling 84-session window, monthly retrain | project decision: run on 4 months of data |
| TFT 63 / 42, MLP default, 2 epochs | TFT 21 / 14 default, 100 epochs + early stopping | project decision |
| baselines not in repo | long_only, tsmom, csmom, macd (Baz phi) | standard momentum comparisons |
