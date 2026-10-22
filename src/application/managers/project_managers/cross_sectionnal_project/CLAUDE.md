# CLAUDE.md – cross_sectionnal_project (cross-sectional momentum classifier)

LightGBM **classifier** predicting, for every asset of the paper universe (48 US financials,
`data/paper_universe.py`), whether its next-session return beats the cross-sectional median. At each
retraining an **Optuna study with the Tree-structured Parzen Estimator (TPE)** selects the feature subset
and the LightGBM hyper-parameters. Rebuilt on 2026-10-22 with the structure of
`spatio_temporal_momentum_project_full` (the previous TFT / Black-Litterman copy was removed; git history keeps it).

The signal factor is `CompanyShareCrossSectionalMomentumFactor(CompanyShareFactor)`, the counterpart of
`CompanyShareLGBMCSQuintileRankMomentumFactor`: the same 24 momentum-factor dependencies
(`momentum_feature_dependency_specs`) plus the non-momentum candidates below
(`cross_sectional_feature_dependency_specs`); `calculate()` delegates to an injected provider (`CSMModelProvider`).

## Candidate features (48, `CSMFeatureDefinition`)

| Family | Features | Domain factors |
|---|---|---|
| momentum (24) | return_1d ... momentum_zscore_20d | `LGBMMomentumFeatureDefinition` |
| share turnover | avg_turnover_1m ... avg_turnover_6m (21 x k sessions), share_turnover (last session) | `company_share_liquidity_factors`, `CompanyShareAvgTurnover6mFactor` |
| volume trend | vpt_16w_20d_lag = volume(t-20) x (close(t-20) - close(t-100)) / close(t-100) | `CompanyShareVpt16w20dLagFactor` |
| range | monthly_price_range = high(t) - low(t-21) (existing factor, unchanged) | `CompanyShareMonthlyPriceRangeFactor` |
| return extremes | max_daily_return_6m (126 sessions), min_return_120d (120 sessions) | `company_share_liquidity_factors` |
| relative to SPY | rel_return_spy_1d / 5d / 20d / 3m / 6m = share return - SPY return, same sessions | `company_share_relative_performance_factors` |
| delta-hedging bands | zakamouline / whalley_wilmott x delta_ceiling, delta_floor, ceiling_distance, floor_distance | `company_share_delta_band_factors` |

Delta-hedging bands (owner's choices 2026-10-22): a reference European call per share and session — S = close,
K = 4-month (84-session) moving average, sigma = the share's IBKR implied volatility (close of the
`OPTION_IMPLIED_VOLATILITY` series), r = IBKR 13-week T-bill index IRX (yield x 10, continuously compounded),
maturity 30 days (the horizon of IBKR's implied vol). Black-Scholes delta and gamma; half-band H of
Whalley-Wilmott (1997) and Zakamouline (2009) as in the SPX v2 hedging module, with cost_rate 0.0001 and
risk_aversion 1.0 from the factor library entries (`parameters`, `LIBRARY_PARAMETERS`). Bands: delta +/- H.
Distances: the relative price move after which the call's delta reaches the ceiling (up) / floor (down).

* Share turnover = traded volume (shares): no shares outstanding are stored, so volume / shares outstanding cannot
  be formed (the convention of the existing `avg_turnover_6m`); the level mostly reflects the size of the company.
* SPY is a benchmark: its daily closes are imported (`DailyHistoryUpdater`) and read by the cycle, it is not in the
  universe and is never scored or traded. The relative factors read it through `DependencySpec(entity_symbol='SPY')`.
* Also imported: each share's `OPTION_IMPLIED_VOLATILITY` daily bars (no volume) and the IRX index (`Index`,
  TRADES). A volatility series is never read as a price: readers and the resolver skip the non-price whatToShow
  series (`source_policy.NON_PRICE_WHAT_TO_SHOW`) unless a dependency names that subgroup.
* Candidates present on fewer than `min_feature_coverage` (80%) of the labelled rows of a training window are left
  out of that study (logged), e.g. return_ytd without a close of the previous year.

## How it runs

The Misbuffet engine runs bar by bar (daily clock). `Algorithm.on_data` calls `CSMTradingCycle.step(t)`:

1. frontier -> `t`; `DailyHistoryUpdater` imports IBKR daily TRADES closes (writes only);
2. closes read **through the frontier** (`STMFrontierPriceReader`): a daily bar dated D is known from D+1 00:00;
3. features at the decision session: the **40 candidates of `CSMFeatureDefinition`**, each computed by **its own
   domain factor's `calculate()`** on the windows its DependencySpecs ask for (close / volume / high / low of the
   share, close of SPY for the relative factors) — `CSMFeatureEngine`, cached per asset and date;
4. retrain when due (`retrain_every_days`, 21): Optuna TPE study on the last `training_window` (252) sessions of
   labels known at the session, then the final model on the whole window; saved as an ML artifact;
5. score the eligible assets (probability), store them as `cross_sectional_momentum_signal` factor values;
6. long the top 20% / short the bottom 20% of probabilities, inverse-volatility weights, dollar-neutral,
   gross 1 -> `set_holdings`.

The factor-resolution path gives the same value: `CSMModelProvider.predict` returns the stored decision, or
applies the model valid at the date to `CSMFeatureDefinition.extract(dependencies)` (selected features).

## Optuna TPE (csm_model.optimize)

* search space: `use__<feature>` on/off for each of the 40 candidates (trials with fewer than `min_features`
  are pruned) + num_leaves, max_depth, learning_rate (log), n_estimators, min_child_samples, subsample,
  colsample_bytree, reg_lambda (log);
* `TPESampler(seed, n_startup_trials=10, multivariate=True, group=True)`, 40 trials, 600 s timeout;
* objective = validation AUC averaged over 3 **purged walk-forward folds** of the training window (the last
  `horizon` training dates before each validation block are dropped); `metric: 'long_short_sharpe'` optimises
  the Sharpe of the daily top-minus-bottom quantile spread instead;
* kept per model: selected features, parameters, CV score, every trial value, feature selection frequency in the
  top 20% trials, Optuna hyper-parameter importances, gain importance of the final model.

## Data preload (`config['preload_data']`, default True)

Before the first bar, `CSMModelTrainer.preload` imports every series the run reads — the list of
`cross_sectional_momentum/csm_preload.py`, derived from the candidates and shared with the updater: the 48 shares'
daily TRADES bars, their `OPTION_IMPLIED_VOLATILITY` bars, SPY (CompanyShare, TRADES) and IRX (Index, TRADES), 98
series — from `price_history_start` to `backtest_end` through `BacktestDataPreloadService`
(`services/data/backtest_preload`). Coverage per series -> `results/cross_sectional_momentum/preload.csv`; the loaded
ranges are registered, so a bar still missing there is served from the latest closed stored bar instead of being
requested from IBKR at every step. The updater then only imports new days (live).

## Results report (`/csm/` dashboard, `/csm/results`, `/csm/report.pdf`)

Built after the run (`csm_report.build_report`), saved to `results/cross_sectional_momentum/` with its PDF:

* performance vs Long Only (EW) and a 20-session momentum long/short (same sessions, same construction),
  Sharpe net of 0-20 bps of turnover, cumulative returns and drawdown;
* prediction quality: mean AUC per decision, accuracy, top-minus-bottom spread and its t-stat;
* **feature importance**: gain share of the models used, mean |TreeSHAP| (LightGBM `pred_contrib`) at the
  decisions, % of retrainings whose best trial selected the feature, top-trial selection frequency; selection
  heatmap per retraining; Optuna optimisation history and hyper-parameter importances; one row per retraining;
* **data coverage** (`stm_data_coverage`, NYSE calendar): summary, per asset, per session.

```bash
python -m src.interfaces.flask.app      # http://127.0.0.1:5000/csm/
```

## Structure

```
cross_sectionnal_project/
├── config.py                         # DEFAULT_CONFIG + 'csm' section -> build_csm_configuration
├── project_manager.py                # CrossSectionalMomentumProjectManager: backtest + report + PDF
├── cross_sectionnal_project_manager.py  # former entry point: CrossSectionnal = CrossSectionalMomentumProjectManager
├── data/ paper_universe.py, universe_setup.py, price_ingestion.py (DailyHistoryUpdater)
├── models/model_trainer.py           # CSMModelTrainer(BaseModelTrainer): create_factors + build_cycle
└── backtesting/ backtest_runner.py, base_project_algorithm.py, synthetic_demo.py
```

Reusable services: `src/application/services/data/entities/factor/cross_sectional_momentum/`
(`csm_configuration`, `csm_features`, `csm_model`, `csm_artifact_store`, `csm_signal_store`,
`csm_model_provider`, `csm_trading_cycle`, `csm_report`, `csm_report_renderer`).

## Key rules

* One path for backtest and live; all decision reads through the frontier; a model trained as of session S
  uses labels known at S only (its window ends the session before) and is usable from S on.
* Kept separate: results `results/cross_sectional_momentum/`, models `weights/cross_sectional_momentum/`,
  ML model prefix `csm_`, universe `csm_paper_us_financials`, portfolio `Cross_Sectional_Momentum_Portfolio`.
* History needed: 252-session window + 127-close lookback of max_daily_return_6m (bands: 84 closes) -> `price_history_start`
  2024-11-01 for a backtest from 2026-06-01. `return_ytd` needs a close of the previous year.
* `cross_sectional_ranks` (off) adds per-date ranks; a model using them can only be scored by the cycle.

Tests: `tests/cross_sectional_momentum/test_csm.py`.
