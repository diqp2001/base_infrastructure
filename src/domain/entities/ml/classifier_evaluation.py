"""
Classifier evaluation — what a CompanyShare classifier is judged on, independent of any TradingStrategy.

Four notions, never mixed:

    TRUE CLASS            the class the stock REALISED after the prediction date T, from its forward return over the
                          model's own label definition (e.g. the cross-sectional quintile of the forward return, 1 =
                          worst .. 5 = best; or 'beat the cross-sectional median' = 1 / 0). Known only after T.
    PREDICTED CLASS       the model's class at T (argmax of its class probabilities). Known at T.
    CLASS PROBABILITIES   P(class k) for every class k, as the model output them at T. Kept in full: the predicted
                          class alone loses the ranking information.
    PROBABILITY QUINTILE  at a date T, the stocks ranked by ONE class probability (e.g. P(class 5)) and cut into five
                          equal-count groups: Q1 = lowest probability .. Q5 = highest. Cross-sectional by date, from
                          probabilities known at T. It is NOT the true class and NOT the predicted class.

Model classification = true class vs predicted class (confusion matrix, accuracy, F1 ...).
Model probability ranking = P(class k) quintiles vs the realised forward return (does a higher P(class 5) earn more?).
Model return performance = the compounded forward returns of the probability quintiles through time.
How model outputs become positions (TradingStrategy / portfolio construction) is outside this evaluation.

This module holds the run descriptor and the result value objects (pure Python). The calculations are in
src/application/services/model_evaluation/.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ClassifierModelRef:
    """A classifier model whose runs can be evaluated (a stored MLModel and its kind)."""
    key: str                         # '<kind>:<ml model id>'
    kind: str                        # e.g. 'csm' (binary), 'lgbm_quintile' (5 classes)
    name: str
    classes: Tuple[int, ...]         # the model's class labels, worst performance first
    true_class_definition: str       # how the realised class is computed (the model's own label rule)
    label_horizon: str               # the forward period of the label, e.g. '5 trading days (return_5d at T+5..11d)'


@dataclass(frozen=True)
class ClassifierRun:
    """One training of a model (one artifact) and the dates it may be evaluated on, out of sample.

    ``valid_from`` / ``valid_until``: the dates the run is the model in force (inclusive; None = open).
    ``evaluable_from``: the first prediction date whose forward period the training labels cannot have seen (later
    than ``valid_from`` when the training labels were realised after it)."""
    run_id: int                      # the ModelArtifact id
    training_id: Optional[int]
    label: str
    valid_from: Optional[date]
    valid_until: Optional[date]
    evaluable_from: Optional[date] = None
    notes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class PerClassMetrics:
    label: int
    precision: Optional[float]       # None when the class was never predicted
    recall: Optional[float]          # None when the class never occurred
    f1: Optional[float]
    support: int                     # true observations of the class
    predicted: int                   # observations predicted as the class


@dataclass(frozen=True)
class ClassificationEvaluationResult:
    """True class vs predicted class over the evaluated observations."""
    classes: Tuple[int, ...]
    n_observations: int
    accuracy: Optional[float]
    balanced_accuracy: Optional[float]           # mean recall over the classes that occurred
    macro_precision: Optional[float]             # mean over the classes with a defined value
    macro_recall: Optional[float]
    macro_f1: Optional[float]
    per_class: Tuple[PerClassMetrics, ...]
    confusion_matrix: Tuple[Tuple[int, ...], ...]          # rows = true class, columns = predicted class (counts)
    log_loss: Optional[float] = None                       # with the class probabilities
    brier_score: Optional[float] = None                    # multiclass: mean over observations of sum_k (p_k - y_k)^2
    notes: Tuple[str, ...] = ()

    def row_normalised(self) -> List[List[Optional[float]]]:
        """Each true-class row as shares of its observations: where did the stocks that ended in class k get
        classified? (None for a class that never occurred.)"""
        out = []
        for row in self.confusion_matrix:
            total = sum(row)
            out.append([c / total if total else None for c in row])
        return out

    def metrics(self) -> Dict[str, Optional[float]]:
        return {"accuracy": self.accuracy, "balanced_accuracy": self.balanced_accuracy,
                "macro_precision": self.macro_precision, "macro_recall": self.macro_recall,
                "macro_f1": self.macro_f1, "log_loss": self.log_loss, "brier_score": self.brier_score}


def class_label(k: int, classes: Sequence[int]) -> str:
    """'Q1'..'Q5' for quintile classes, 'class 0' / 'class 1' otherwise."""
    return f"Q{k}" if tuple(classes) == tuple(range(1, len(classes) + 1)) and len(classes) == 5 else f"class {k}"
