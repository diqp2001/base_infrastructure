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
