# CLAUDE.md – spatio_temporal_momentum_project_10m_hourly

## STM 10m model, portfolio rebalanced every 60 minutes (owner's request, 2026-11-03)

A copy of `spatio_temporal_momentum_project_10m` (see its CLAUDE.md for the model, features, data and the
shared STM services) with one change: **the engine decides and trades every 60 minutes instead of every 10**.

Why: the P.08.04 comparison (5–9 Oct 2026, ask / bid fills + IBKR Fixed commission) showed the 10-minute
rebalance re-sizing ~24 banks per decision; costs (2.2 % of capital in a week) exceeded the gross gain
(+1.26 % without costs, −0.91 % with). This project tests the slower rebalance alone; STM 10m tests the
0.5 % no-trade band alone (`rebalance.min_weight_change`).

* Same model: 10-minute bars, same features, label = next 10-minute bar, daily retraining, same TFT.
* Engine clock: `config_interval {'custom_interval_minutes': 60, 'session_start': '10:30', 'session_end': '16:00'}`
  -> decisions at 10:30, 11:30, ..., 15:30 ET (6 per session), each on the 10-minute bars closed at that time
  (frontier). The 15:30 position is held overnight. `REBALANCE_MINUTES` in `config.py`.
* Costs: same `execution_costs` as STM 10m (ask / bid of the decision bar + IBKR Fixed), wired by the shared
  `BaseProjectAlgorithm.attach_execution_costs`; BID / ASK bars imported with TRADES.
* No no-trade band (`rebalance.min_weight_change` None).
* Kept separate from STM 10m: results `results/spatio_temporal_momentum_10m_hourly/`,
  models `weights/spatio_temporal_momentum_10m_hourly/`, ML model prefix `stm10mh_`, feature factors
  `stm10mh_*`, signal factor `spatio_temporal_momentum_signal_10m_hourly_banks`, universe
  `stm_us_banks_10m_hourly`, portfolio `Spatio_Temporal_Momentum_10m_Hourly_Portfolio`.
  Dashboard: `/stm/?project=10m_hourly`. The 10-minute price bars themselves are shared (raw IBKR factors).

## Reading the results

The portfolio value of the engine (`results_dir`, dashboard) is the strategy's P&L with costs. The research
report's paper tables still score each decision on the **next 10-minute bar** (the model's label), not on the
hour the position is actually held, so compare projects on portfolio value, not on those tables.

## Run

```python
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_hourly.project_manager import (
    SpatioTemporalMomentum10mHourlyProjectManager,
)
results = SpatioTemporalMomentum10mHourlyProjectManager().run()   # backtest_start..backtest_end, every 60 minutes
```

TWS (paper login) on 127.0.0.1:7497 serves the history; no order reaches IBKR in a backtest.
