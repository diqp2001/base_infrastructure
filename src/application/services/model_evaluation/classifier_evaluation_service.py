"""
ClassifierEvaluationService — evaluates a CompanyShare classifier run as a CLASSIFIER, not as a strategy.

    observation source (one adapter per classifier family: ClassifierObservationSourcePort)
      -> observation table: date T, asset, run, true class (realised after T), predicted class, forward return,
         P(class k) for every k (known at T)
      -> classification metrics + confusion matrix          (true class vs predicted class)
      -> for every P(class k): probability quintiles per date, their realised returns, cumulative returns,
         correlation matrix                                    (probability ranking vs realised performance)

No TradingStrategy, portfolio construction, rebalancer or engine is involved. ``evaluate_observations`` works on any
observation table, so any classifier (any number of classes) can be evaluated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Sequence

import pandas as pd

from src.application.services.model_evaluation.classification_metrics import evaluate_classification
from src.application.services.model_evaluation.observations import (
    cross_sectional_views,
    probability_columns,
    validate,
)
from src.application.services.model_evaluation.probability_quintiles import (
    ProbabilityQuintileAnalysis,
    analyse_all,
    analyse_probability,
)
from src.domain.entities.ml.classifier_evaluation import (
    ClassificationEvaluationResult,
    ClassifierModelRef,
    ClassifierRun,
)


@dataclass(frozen=True)
class EvaluationRequest:
    model_key: str
    run_id: Optional[int]            # None = walk-forward: every run on the dates it was in force
    universe_id: Optional[int]
    start: date
    end: date
    horizon: Optional[int] = None    # forward-return bars of the quintile returns (None = the label horizon)
    n_quantiles: int = 5


@dataclass
class ClassifierEvaluation:
    model: Optional[ClassifierModelRef]
    runs: List[ClassifierRun]
    classes: List[int]
    horizon: int
    observations: pd.DataFrame
    classification: ClassificationEvaluationResult
    probability_quintiles: Dict[int, ProbabilityQuintileAnalysis]
    per_run: pd.DataFrame                       # run_id -> observations, dates, accuracy, macro F1
    notes: List[str] = field(default_factory=list)
    score_only: bool = False                    # a ranking score instead of class probabilities
    # the same two views for every model (observations.cross_sectional_views): 'binary' (above / below the date's
    # median) and 'quintile' (per-date quintiles), true from the forward return, predicted from the ranking score
    cross_sectional: Dict[str, ClassificationEvaluationResult] = field(default_factory=dict)

    def ranking_label(self) -> str:
        if self.score_only:
            return "the score"
        if len(self.classes) == 2:
            from src.domain.entities.ml.classifier_evaluation import class_label
            return f"P({class_label(self.classes[-1], self.classes)})"
        return "the expected class (sum of k x P(k))"

    def output_label(self, k: int) -> str:
        """'P(Q5)' / 'P(class 1)', or 'score' for a score model."""
        from src.domain.entities.ml.classifier_evaluation import class_label
        return "score" if self.score_only else f"P({class_label(k, self.classes)})"


def evaluate_observations(frame: pd.DataFrame, classes: Sequence[int], horizon: int = 1, n_quantiles: int = 5,
                          model: Optional[ClassifierModelRef] = None, runs: Sequence[ClassifierRun] = (),
                          notes: Sequence[str] = (), score_only: Optional[bool] = None) -> ClassifierEvaluation:
    """``score_only``: the model outputs a ranking score (column 'score'), not class probabilities — the predicted
    class is given by the source (e.g. the score's per-date quintile) and the score's quintiles are analysed against
    the best class (default: from ``model.output``)."""
    classes = [int(k) for k in classes]
    if score_only is None:
        score_only = model is not None and model.output == "score"
    obs = validate(frame, classes, score_only)
    probs = None if score_only else obs[probability_columns(classes)].to_numpy(dtype=float)
    classification = evaluate_classification(obs["true_class"].to_numpy(dtype=float),
                                             obs["predicted_class"].to_numpy(dtype=float), classes, probs)
    rows = []
    for run_id, g in obs.groupby("run_id"):
        r = evaluate_classification(g["true_class"].to_numpy(dtype=float), g["predicted_class"].to_numpy(dtype=float),
                                    classes)
        rows.append({"run_id": int(run_id), "first_date": g["date"].min().date(), "last_date": g["date"].max().date(),
                     "dates": g["date"].nunique(), "observations": r.n_observations, "accuracy": r.accuracy,
                     "balanced_accuracy": r.balanced_accuracy, "macro_f1": r.macro_f1})
    per_run = pd.DataFrame(rows).set_index("run_id") if rows else pd.DataFrame()
    all_notes = list(notes) + list(classification.notes)
    if obs.empty:
        all_notes.append("no observation in the window")
    cross_sectional = {}
    for view, (true, predicted) in cross_sectional_views(obs, classes, score_only, n_quantiles).items():
        view_classes = [0, 1] if view == "binary" else list(range(1, n_quantiles + 1))
        cross_sectional[view] = evaluate_classification(true.to_numpy(dtype=float), predicted.to_numpy(dtype=float),
                                                        view_classes)
    if score_only:
        top = classes[-1]
        quintiles = {top: analyse_probability(obs.assign(**{f"p_{top}": obs["score"]}), top, n_quantiles,
                                              int(horizon))}
        all_notes.append("score model: no class probabilities — its score quintiles are analysed against the best "
                         "class; no log loss / Brier score")
    else:
        quintiles = analyse_all(obs, classes, n_quantiles, int(horizon))
    return ClassifierEvaluation(model=model, runs=list(runs), classes=classes, horizon=int(horizon), observations=obs,
                                classification=classification, probability_quintiles=quintiles,
                                per_run=per_run, notes=all_notes, score_only=bool(score_only),
                                cross_sectional=cross_sectional)


class ClassifierEvaluationService:

    def __init__(self, sources: Sequence):
        self.sources = {s.kind: s for s in sources}

    def models(self) -> List[ClassifierModelRef]:
        out = []
        for s in self.sources.values():
            out.extend(s.models())
        return out

    def model(self, key: str) -> ClassifierModelRef:
        found = next((m for m in self.models() if m.key == key), None)
        if found is None:
            raise KeyError(f"unknown classifier model {key!r}")
        return found

    def runs(self, key: str) -> List[ClassifierRun]:
        model = self.model(key)
        return self.sources[model.kind].runs(model)

    def evaluate(self, request: EvaluationRequest) -> ClassifierEvaluation:
        model = self.model(request.model_key)
        source = self.sources[model.kind]
        runs = source.runs(model)
        if request.run_id is not None:
            runs = [r for r in runs if r.run_id == request.run_id]
            if not runs:
                raise KeyError(f"run {request.run_id} is not a run of {model.name}")
        result = source.observations(model, request.run_id, request.universe_id, request.start, request.end,
                                     request.horizon)
        frame, horizon, notes = result.frame, result.horizon, result.notes
        return evaluate_observations(frame, model.classes, horizon, request.n_quantiles, model=model, runs=runs,
                                     notes=notes)
