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
from src.application.services.model_evaluation.observations import probability_columns, validate
from src.application.services.model_evaluation.probability_quintiles import (
    ProbabilityQuintileAnalysis,
    analyse_all,
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


def evaluate_observations(frame: pd.DataFrame, classes: Sequence[int], horizon: int = 1, n_quantiles: int = 5,
                          model: Optional[ClassifierModelRef] = None, runs: Sequence[ClassifierRun] = (),
                          notes: Sequence[str] = ()) -> ClassifierEvaluation:
    classes = [int(k) for k in classes]
    obs = validate(frame, classes)
    probs = obs[probability_columns(classes)].to_numpy(dtype=float)
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
    return ClassifierEvaluation(model=model, runs=list(runs), classes=classes, horizon=int(horizon), observations=obs,
                                classification=classification,
                                probability_quintiles=analyse_all(obs, classes, n_quantiles, int(horizon)),
                                per_run=per_run, notes=all_notes)


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
