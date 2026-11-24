# Classifier model evaluation (added 2026-11-23)

Evaluates the CompanyShare classifier models as CLASSIFIERS — whether they identify which stocks end in the better or
worse future-performance classes — independent of TradingStrategy, portfolio construction and the engine.

Definitions: `src/domain/entities/ml/classifier_evaluation.py`.
- **true class**: realised after T, by the model's own label rule.
- **predicted class**: the argmax at T.
- **class probabilities**: every P(class k) at T, kept in full.
- **probability quintile**: the stocks of ONE date ranked by one P(class k).

```
ClassifierObservationSourcePort (domain/ports/ml)  one adapter per classifier family (classifier_sources.py)
  -> observation table: date, asset, symbol, run_id, true_class, predicted_class, forward_return, p_<k> ...
  -> classification_metrics.evaluate_classification   accuracy, balanced accuracy, per-class / macro precision /
                                                       recall / F1, confusion matrix, log loss, multiclass Brier
  -> probability_quintiles.analyse_probability         per P(class k): quintiles per date, mean / median / count /
                                                       hit rate, Qn - Q1, cumulative (non-overlapping dates),
                                                       correlation matrix (research/statistics.correlation_matrix)
ClassifierEvaluationService.evaluate(EvaluationRequest) -> ClassifierEvaluation
```

## Sources

| family | classes | runs | P(class k) | true class |
|---|---|---|---|---|
| `lgbm_quintile` (`lgbm_mom_*` MLModels) | 1-5 | each trained artifact, in force on `[valid_from, valid_until]`. Evaluable from `valid_from + 11` days, because the training labels reach 11 days past it. | the artifact's `predict_proba` on the 24 momentum features stored at T | the per-date quintile of `return_5d`, read 5-11 calendar days after T |
| `csm` (`csm_*` MLModels, one model per configuration hash) | 0 / 1 | each artifact, from its `trained_as_of` until the next one (`CSMArtifactStore.select`) | the probability stored by the cycle (`CSMSignalStore`) | forward return over `label.horizon` above the date's cross-sectional median of the universe members |

Reads only. No table is added and nothing is trained or written.

## Notes

- **LGBM probabilities:** `LGBMMomentumModelProvider.predict` stores only the argmax. `predict_proba` and
  `class_probabilities` were added; `predict` is unchanged.
- **LGBM trainer, pre-existing issues (not changed):**
  - it ranks the label over its whole training set (a global rank), while the evaluation ranks per date;
  - its labels can be realised after `target_date`.
- **CSM signal store:** it keeps the first value written. When another configuration's runs cover the evaluated
  dates with the same signal factor, the evaluation adds a WARNING note.

## UI

`/powerbuffet/model-evaluation` (`interfaces/flask/web/controllers/model_evaluation_controller.py`, template
`model_evaluation/classifier.html`). Select the model, the run (or walk-forward), the universe, the dates, the horizon
and the probability class. CSV exports via `/powerbuffet/model-evaluation/csv?part=...`.

## Tests

`tests/model_evaluation/` (no database).

## Monthly classifier backtest (added 2026-11-23)

`monthly_classifier_backtest.py` runs the four stock-ranking models on one shared monthly setup, walk-forward. It is
a model evaluation, not an engine backtest: no TradingStrategy, no orders.

- **Universe:** the DJIA point-in-time members (`djia_membership`, from 2020-08-31). Predictions run from 2021-01 to
  2026-10. Training rows before 2020-08-31 use the base members' own history (survivors), as the STM decile project
  does.
- **Prices:** adjusted daily closes from the cached IBKR files (`results/etf_dispersion_stm/price_history`,
  Eulerpool fallback). IBKR is not called.
- **Target:** the next month. 5 classes = the per-date quintile of the next-month return; 2 classes = above the
  date's cross-sectional median.
- **Training:** at each month end T, every model is fit on month-end rows dated before T, over a rolling 120-month
  window, and retrained monthly. `run_id` = the training month (yyyymm).

| model | algorithm | features | classes |
|---|---|---|---|
| `csm` | CSM LightGBM + Optuna TPE (`csm_model.train`) | CSM candidates from closes (`CSMFeatureEngine.features_at`) | 0 / 1 |
| `lgbm_quintile` | `LGBMClassifier` with `LGBMMomentumModelConfiguration`'s parameters | the 24 momentum factors | 1-5 |
| `random_forest` | test_base_project's RandomForest (100 trees, random_state 42), pooled | two lagged monthly returns, last month's daily volatility | 0 / 1 |
| `stm` | STM model A of the decile project (`STMConstituentScorer`, retrained monthly) | its own (month-end closes) | score ranking: predicted class = per-date score quintile vs the 1-5 true classes |

- **Outputs:** `results/classifier_backtests/<stamp>/manifest.json` and `<model>.csv` (the observation table). These
  are read by `ClassifierBacktestFileSource` (model key `monthly_backtest:<stamp>:<model>`) and evaluated on
  `/powerbuffet/model-evaluation`.
- **Run:** `python -m src.application.services.model_evaluation.monthly_classifier_backtest [--models csm,stm]
  [--start 2021-01-01] [--end 2026-10-31] [--csm-trials 25]`

## Binary and quintile views (added 2026-11-23)

Every model gets the same two confusion matrices, whatever its own classes (`observations.cross_sectional_views`):
- the ranking score is P(class 1) for a binary model, Σ k·P(k) for a five-class model, the score for a score model;
- **binary**: the true class = above the date's median forward return, the predicted class = score above the date's
  median score;
- **quintile**: true and predicted classes are the per-date quintiles of the forward return and of the score.

Page section "1b", CSV parts `binary` and `quintile`.

## S&P 500 monthly backtest of CSM (added 2026-11-23)

`sp500_monthly_backtest.py` runs CSM LightGBM + Optuna TPE on the S&P 500, with the same walk-forward as the DJIA
backtest (`mcb.walk_forward`, rolling 120 months, retrained monthly, binary target = above the next-month median).

- **Universe**: `src/application/services/universe/sp500_membership.py`. The point-in-time members are rebuilt from
  Wikipedia: the current list plus the history of changes, rolled back to 2007 (ticker aliases, additions inferred
  from "Date added"). Cache: `results/sp500/membership.json`.
- **Prices**: `sp500_data.py`, Eulerpool daily OHLCV (split-adjusted, not dividend-adjusted), file cache
  `results/sp500/price_history/eulerpool_ohlcv`.
  - Delisted companies are often missing. The member-months without bars are left out.
  - Coverage is written in the manifest: ~77% in 2012, 87% in 2016, 95% in 2019, 98-99.5% from 2021.
- **Statements**: Eulerpool, behind `FileCachedStatementSource` (`results/sp500/statements/eulerpool`). Nothing is
  written to a database.
- **Candidates**:
  - the CSM bar candidates;
  - the 27 liquidity / volume factors (`CSMFeatureConfig(liquidity_volume=True)`);
  - the 5 share-turnover factors (`turnover_features`, each by its domain `calculate()`);
  - the 75 point-in-time fundamentals (`CSMFundamentals`).
- **Outputs**: `results/classifier_backtests/<stamp>/{manifest.json, csm.csv}`, with `universe_label` "S&P 500 PIT".
- **Run**: `python -m src.application.services.model_evaluation.sp500_monthly_backtest [--no-turnover]
  [--no-fundamentals]`. A run takes about 1.5-2 h.
- **Result of run 20261123T204251** (2012-01 .. 2026-10, 81,902 predictions; without turnover): no edge.
  - Accuracy 0.502, log loss 0.701 (worse than a coin flip's 0.693).
  - Q5 − Q1 of P(above median) = +0.18% per month, t = 1.1.
- **Result of run 20261124T090147** (the same setup with the 5 turnover factors, 155 candidates): no edge either.
  - Accuracy 0.505, log loss 0.700.
  - Q5 − Q1 = +0.11% per month, t = 0.6.
  - The predictions are identical to the previous run up to 2018; they differ from 2019.
  - The share count comes from the balance sheet: 493 of the 628 symbols with statements. The others report it only
    on the cover page (dei), which the statement endpoints do not serve.
