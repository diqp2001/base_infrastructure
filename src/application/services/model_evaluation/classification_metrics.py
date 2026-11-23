"""
Classification metrics — TRUE class vs PREDICTED class (pure numpy, no I/O).

* confusion matrix: rows = true class, columns = predicted class, in the model's class order;
* per class: precision = TP / predicted, recall = TP / true (support), F1 = harmonic mean; undefined (None) when its
  denominator is 0, never silently 0;
* accuracy = share on the diagonal; balanced accuracy = mean recall over the classes that occurred;
* macro precision / recall / F1 = unweighted mean over the classes where the value is defined;
* with the class probabilities: log loss = -mean log p(true class) (p clipped to [1e-15, 1]) and the multiclass Brier
  score = mean over observations of sum_k (p_k - 1[true = k])^2 (0 = perfect, 2 = worst).
Observations without a true class or a predicted class are left out (their count is in the notes).
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

from src.domain.entities.ml.classifier_evaluation import ClassificationEvaluationResult, PerClassMetrics

EPS = 1e-15


def confusion_matrix(true: Sequence, predicted: Sequence, classes: Sequence[int]) -> np.ndarray:
    index = {int(k): i for i, k in enumerate(classes)}
    m = np.zeros((len(classes), len(classes)), dtype=int)
    for t, p in zip(true, predicted):
        if t is None or p is None or not np.isfinite(t) or not np.isfinite(p):
            continue
        if int(t) not in index or int(p) not in index:
            raise ValueError(f"class outside {list(classes)}: true {t}, predicted {p}")
        m[index[int(t)], index[int(p)]] += 1
    return m


def _ratio(num: float, den: float) -> Optional[float]:
    return float(num) / float(den) if den else None


def _mean(values) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return float(np.mean(vals)) if vals else None


def evaluate_classification(true: Sequence, predicted: Sequence, classes: Sequence[int],
                            probabilities: Optional[np.ndarray] = None) -> ClassificationEvaluationResult:
    """``probabilities``: one row per observation, one column per class (same order as ``classes``)."""
    classes = tuple(int(k) for k in classes)
    t = np.asarray(true, dtype=float)
    p = np.asarray(predicted, dtype=float)
    ok = np.isfinite(t) & np.isfinite(p)
    notes = []
    if (~ok).any():
        notes.append(f"{int((~ok).sum())} observations without a true or predicted class left out")
    m = confusion_matrix(t[ok], p[ok], classes)
    n = int(m.sum())
    per_class = []
    for i, k in enumerate(classes):
        tp, support, pred = int(m[i, i]), int(m[i, :].sum()), int(m[:, i].sum())
        precision, recall = _ratio(tp, pred), _ratio(tp, support)
        f1 = (2 * precision * recall / (precision + recall)
              if precision is not None and recall is not None and (precision + recall) > 0
              else (0.0 if precision is not None and recall is not None else None))
        per_class.append(PerClassMetrics(k, precision, recall, f1, support, pred))
    log_loss = brier = None
    if probabilities is not None and n:
        prob = np.asarray(probabilities, dtype=float)
        if prob.shape != (len(t), len(classes)):
            raise ValueError(f"probabilities shape {prob.shape}, expected {(len(t), len(classes))}")
        usable = ok & np.isfinite(prob).all(axis=1)
        if usable.any():
            idx = np.array([classes.index(int(x)) for x in t[usable]])
            pu = prob[usable]
            log_loss = float(-np.mean(np.log(np.clip(pu[np.arange(len(idx)), idx], EPS, 1.0))))
            onehot = np.zeros_like(pu)
            onehot[np.arange(len(idx)), idx] = 1.0
            brier = float(np.mean(((pu - onehot) ** 2).sum(axis=1)))
        if (ok & ~np.isfinite(prob).all(axis=1)).any():
            notes.append("observations without probabilities left out of log loss / Brier")
    return ClassificationEvaluationResult(
        classes=classes, n_observations=n,
        accuracy=_ratio(np.trace(m), n),
        balanced_accuracy=_mean(c.recall for c in per_class),
        macro_precision=_mean(c.precision for c in per_class),
        macro_recall=_mean(c.recall for c in per_class),
        macro_f1=_mean(c.f1 for c in per_class),
        per_class=tuple(per_class),
        confusion_matrix=tuple(tuple(int(x) for x in row) for row in m),
        log_loss=log_loss, brier_score=brier, notes=tuple(notes))
