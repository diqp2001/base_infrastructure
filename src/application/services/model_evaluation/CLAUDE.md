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
