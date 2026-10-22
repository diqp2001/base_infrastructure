# CLAUDE.md – cross_sectionnal_project (cross-sectional momentum classifier)

LightGBM **classifier** predicting, for every asset of the paper universe (48 US financials,
`data/paper_universe.py`), whether its next-session return beats the cross-sectional median. At each
retraining an **Optuna study with the Tree-structured Parzen Estimator (TPE)** selects the feature subset
and the LightGBM hyper-parameters. Rebuilt on 2026-10-22 with the structure of
`spatio_temporal_momentum_project_full` (the previous TFT / Black-Litterman copy was removed; git history keeps it).

The signal factor is `CompanyShareCrossSectionalMomentumFactor(CompanyShareFactor)`, the counterpart of
`CompanyShareLGBMCSQuintileRankMomentumFactor`: same 24 momentum-factor dependencies
(`momentum_feature_dependency_specs`), `calculate()` delegates to an injected provider (`CSMModelProvider`).

## How it runs

The Misbuffet engine runs bar by bar (daily clock). `Algorithm.on_data` calls `CSMTradingCycle.step(t)`:

1. frontier -> `t`; `DailyHistoryUpdater` imports IBKR daily TRADES closes (writes only);
2. closes read **through the frontier** (`STMFrontierPriceReader`): a daily bar dated D is known from D+1 00:00;
3. features at the decision session: the **24 momentum factors of `LGBMMomentumFeatureDefinition`**
   (return_1d ... momentum_zscore_20d), each computed by **its own domain factor's `calculate()`** on the
   closes window its DependencySpec asks for (`CSMFeatureEngine`, cached per asset and date);
4. retrain when due (`retrain_every_days`, 21): Optuna TPE study on the last `training_window` (252) sessions of
   labels known at the session, then the final model on the whole window; saved as an ML artifact;
5. score the eligible assets (probability), store them as `cross_sectional_momentum_signal` factor values;
6. long the top 20% / short the bottom 20% of probabilities, inverse-volatility weights, dollar-neutral,
   gross 1 -> `set_holdings`.

The factor-resolution path gives the same value: `CSMModelProvider.predict` returns the stored decision, or
applies the model valid at the date to `LGBMMomentumFeatureDefinition.extract(dependencies)` (selected features).

## Optuna TPE (csm_model.optimize)

* search space: `use__<feature>` on/off for each of the 24 candidates (trials with fewer than `min_features`
  are pruned) + num_leaves, max_depth, learning_rate (log), n_estimators, min_child_samples, subsample,
  colsample_bytree, reg_lambda (log);
* `TPESampler(seed, n_startup_trials=10, multivariate=True, group=True)`, 40 trials, 600 s timeout;
* objective = validation AUC averaged over 3 **purged walk-forward folds** of the training window (the last
  `horizon` training dates before each validation block are dropped); `metric: 'long_short_sharpe'` optimises
  the Sharpe of the daily top-minus-bottom quantile spread instead;
* kept per model: selected features, parameters, CV score, every trial value, feature selection frequency in the
  top 20% trials, Optuna hyper-parameter importances, gain importance of the final model.

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
* History needed: 252-session window + 106-session lookback of the 5-month factors -> `price_history_start`
  2024-11-01 for a backtest from 2026-06-01. `return_ytd` needs a close of the previous year.
* `cross_sectional_ranks` (off) adds per-date ranks; a model using them can only be scored by the cycle.

Tests: `tests/cross_sectional_momentum/test_csm.py`.
