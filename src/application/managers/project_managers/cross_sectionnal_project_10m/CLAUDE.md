# cross_sectionnal_project_10m — intraday cross-sectional momentum

The daily `cross_sectionnal_project` (LightGBM classifier, features and hyper-parameters chosen by Optuna TPE) on
**10-minute bars**, with a decision every 10 minutes and the model **retrained every day**. Created 2026-10-26.

## Design (owner's choice 2026-10-26: trained on 10-minute bars)

The model is trained on 10-minute bars, as in `spatio_temporal_momentum_project_10m`. It is not the daily model
re-scored intraday.

| | daily project | this project |
|---|---|---|
| bars | `1 day` | `10 mins` (`CSMConfiguration.bar_minutes = 10`) |
| candidate windows | sessions | 10-minute bars (the `return_20d` factor = 20 bars = 200 minutes) |
| label | next session above the cross-sectional median | next 10-minute bar above the median |
| training window | 252 sessions | 390 bars (10 sessions) |
| retraining | every 21 days | every day, at the first bar of the session (`retrain_every_days = 1`) |
| decisions | one per session (16:00) | every 10 minutes, 09:40 .. 16:00 |
| sizing volatility | EWM span 20 sessions | EWM span 39 bars (1 session) |
| annualisation | 252 | 252 × 39 |

The candidate features are the same 48 domain factors (`CSMFeatureDefinition`). The feature engine feeds each factor
the last N bars its `DependencySpec`s ask for, so on 10-minute panels every window is counted in bars. A candidate
present on fewer than 80 % of the training rows is left out of the Optuna study: `return_ytd` (needs a close of the
previous year), and anything whose series IBKR does not serve at 10 minutes (e.g. the IRX index) drops out this way.

## Fundamental candidates (added 2026-11-16, Eulerpool)

Besides the 48 bar factors, ten point-in-time fundamentals of the issuers are candidates (`FUNDAMENTAL_FEATURES` in
`config.py`, `csm.features.fundamentals`): `fund_roe_ttm_1q`, `fund_roa_ttm_1q`, `fund_net_income_growth_yoy_1q`,
`fund_net_income_growth_ttm_1q`, `fund_total_assets_growth_yoy_1q`, `fund_roe_1y`, `fund_roa_1y`,
`fund_net_income_growth_1y`, `fund_total_assets_growth_1y`, `fund_eps_growth_1y`.

- Source: `fundamentals_source = 'eulerpool'` -> `RepositoryFactory.enable_provider_family` -> its statements
  (`FinancialStatementSourcePort`). `CSMModelTrainer.build_fundamentals` builds the shared `CSMFundamentals`
  (`.../factor/cross_sectional_momentum/csm_fundamentals.py`); no key -> the run stops with an error.
- Each value = the domain factor's `calculate()` on the statement windows its DependencySpecs ask for, read like the
  resolver reads a point-in-time series (stamp = publication: Eulerpool's SEC-deadline availability; max_age /
  max_gap). A bar never sees a statement published after it.
- Statements are fetched once per share (12 Eulerpool requests, ~576 for the universe) and kept IN MEMORY: no
  fundamental value is written to the database.
- Chosen for coverage (probe 2026-11-16): 92-98 % of the 48 shares in Sep-Oct 2026. Margins, EBITDA, debt, FCF and
  operating income are mostly absent for banks (0-15 %) and are not configured; equity growth (42 %) neither.
- They are constant between filings (in the Sep-Oct 2026 window only 1-2 shares get a new filing): they carry
  cross-sectional, not intraday, information. A model that selects them can only be scored by the trading cycle
  (CSMModelProvider returns None for a single-entity resolution, as for cs_rank features).

## Files

- `config.py`: `BAR_MINUTES`, `TRAINING_WINDOW`, the engine clock (`config_interval`), its own names (universe
  `csm_paper_us_financials_10m`, signal factor `cross_sectional_momentum_signal_10m`, model prefix `csm10m_`, portfolio
  `Cross_Sectional_Momentum_10m_Portfolio`, `results/cross_sectional_momentum_10m`, `weights/cross_sectional_momentum_10m`).
- `data/price_ingestion.py`: `BarHistoryUpdater`, which imports 10-minute bars of the shares and the extra series.
- `models/model_trainer.py`: preload (every series at 10 minutes), `build_fundamentals` and `build_cycle`.
- `backtesting/base_project_algorithm.py`: per-bar `timings.csv` (slice / cycle / orders / valuation).
- `backtesting/synthetic_demo.py`: the same cycle on synthetic 10-minute bars in in-memory SQLite (tests).

## Shared code it relies on (bar size is a parameter there)

- `CSMConfiguration.bar_minutes` (None = daily; left out of the model hash when None, so daily models keep theirs).
- `CSMTradingCycle`: readers at `frequency(bar_minutes)`; logs say "bars" instead of "sessions".
- `CSMSignalStore`: signal factor `subgroup='minutes'`, `frequency='10m'`.
- `csm_report.build_report`: bar-to-bar returns, annualised with `periods_per_year(bar_minutes)`, coverage on the
  10-minute NYSE grid.

## Run

```python
from src.application.managers.project_managers.cross_sectionnal_project_10m.project_manager import (
    CrossSectionalMomentum10mProjectManager,
)
CrossSectionalMomentum10mProjectManager().run()      # dashboard: http://127.0.0.1:5000/csm/?project=csm_10m
```

Tests: `tests/cross_sectional_momentum/test_csm_10m.py`, `tests/cross_sectional_momentum/test_csm_fundamentals.py`.
