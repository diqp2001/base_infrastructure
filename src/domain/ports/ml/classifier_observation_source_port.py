"""
ClassifierObservationSourcePort — where the evaluation gets a classifier's out-of-sample observations from.

One adapter per classifier family (its label rule, its prediction outputs, its runs). The evaluation service only
sees the observation table, so it works for any CompanyShare classifier.

Observation table (pandas DataFrame, one row per prediction date x financial asset):
    date             the prediction date T (the model's inputs and probabilities are known at T)
    asset            the CompanyShare entity id
    symbol           its ticker (display)
    run_id           the model run (artifact) in force at T — never mixed silently: every row says which run
    true_class       the realised class (model's label rule, from returns AFTER T); NaN when not yet realised
    predicted_class  argmax of the probabilities at T
    forward_return   return from T to T + horizon (realised after T)
    p_<k>            P(class k) at T, one column per class
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from src.domain.entities.ml.classifier_evaluation import ClassifierModelRef, ClassifierRun


class ClassifierObservationSourcePort(ABC):

    kind: str = ""

    @abstractmethod
    def models(self) -> List[ClassifierModelRef]:
        """The stored models of this family."""

    @abstractmethod
    def runs(self, model: ClassifierModelRef) -> List[ClassifierRun]:
        """The model's runs (trainings with an artifact), oldest first."""

    @abstractmethod
    def observations(self, model: ClassifierModelRef, run_id: Optional[int], universe_id: Optional[int],
                     start: date, end: date, horizon: Optional[int] = None):
        """ObservationResult (frame = the observation table above, the horizon used, notes) for one run
        (``run_id``) or, with None, every run on the dates it was in force (walk-forward). ``horizon`` =
        forward-return bars (None: the model's label horizon)."""
