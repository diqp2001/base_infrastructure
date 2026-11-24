"""
Classifier evaluation calculations (pure, no database): classification metrics, confusion matrix, probability
quintiles, their realised returns, cumulative returns, correlations, and the temporal rules (cross-sectional by
date, no information from later dates).
"""

import math

import numpy as np
import pandas as pd
import pytest

from src.application.services.model_evaluation.classification_metrics import (
    confusion_matrix,
    evaluate_classification,
)
from src.application.services.model_evaluation.classifier_evaluation_service import evaluate_observations
from src.application.services.model_evaluation.observations import (
    cross_sectional_classes,
    median_split_classes,
    ordinal_quantile_labels,
    predicted_classes,
    run_in_force,
    validate,
)
from src.application.services.model_evaluation.probability_quintiles import (
    analyse_probability,
    assign_probability_quintiles,
    compound,
)
from src.application.services.research.statistics import quantile_portfolios
from src.domain.entities.ml.classifier_evaluation import ClassifierRun

CLASSES = [1, 2, 3, 4, 5]


# ── A. classification metrics ─────────────────────────────────────────────────────────────────────────────────────

def test_known_classes_give_known_metrics_and_confusion_matrix():
    true = [1, 1, 2, 2, 3, 3, 3]
    pred = [1, 2, 2, 2, 3, 1, 3]
    r = evaluate_classification(true, pred, [1, 2, 3])
    assert r.confusion_matrix == ((1, 1, 0), (0, 2, 0), (1, 0, 2))      # rows = true, columns = predicted
    assert r.accuracy == pytest.approx(5 / 7)
    c1, c2, c3 = r.per_class
    assert (c1.precision, c1.recall, c1.f1) == pytest.approx((1 / 2, 1 / 2, 1 / 2))
    assert (c2.precision, c2.recall) == pytest.approx((2 / 3, 1.0)) and c2.f1 == pytest.approx(0.8)
    assert (c3.precision, c3.recall) == pytest.approx((1.0, 2 / 3)) and c3.f1 == pytest.approx(0.8)
    assert r.balanced_accuracy == pytest.approx((1 / 2 + 1 + 2 / 3) / 3)
    assert r.macro_precision == pytest.approx((1 / 2 + 2 / 3 + 1) / 3)
    assert r.macro_f1 == pytest.approx((0.5 + 0.8 + 0.8) / 3)
    assert r.row_normalised()[2] == pytest.approx([1 / 3, 0, 2 / 3])


def test_metrics_match_sklearn_on_random_five_class_data():
    sk = pytest.importorskip("sklearn.metrics")
    rng = np.random.default_rng(3)
    true = rng.integers(1, 6, 400)
    raw = rng.random((400, 5)) + np.eye(5)[true - 1] * rng.random((400, 1))
    proba = raw / raw.sum(axis=1, keepdims=True)
    pred = predicted_classes(proba, CLASSES)
    r = evaluate_classification(true, pred, CLASSES, proba)
    assert r.accuracy == pytest.approx(sk.accuracy_score(true, pred))
    assert r.balanced_accuracy == pytest.approx(sk.balanced_accuracy_score(true, pred))
    assert r.macro_f1 == pytest.approx(sk.f1_score(true, pred, average="macro"))
    assert r.macro_precision == pytest.approx(sk.precision_score(true, pred, average="macro"))
    assert r.log_loss == pytest.approx(sk.log_loss(true, proba, labels=CLASSES))
    assert np.array(r.confusion_matrix).tolist() == sk.confusion_matrix(true, pred, labels=CLASSES).tolist()
    onehot = np.eye(5)[true - 1]
    assert r.brier_score == pytest.approx(np.mean(((proba - onehot) ** 2).sum(axis=1)))


def test_undefined_metrics_are_none_not_zero_and_missing_rows_are_left_out():
    r = evaluate_classification([1, 1, 2, np.nan], [1, 1, 1, 2], [1, 2, 3])
    c1, c2, c3 = r.per_class
    assert r.n_observations == 3 and r.notes
    assert c2.precision is None and c2.recall == 0.0               # class 2 never predicted
    assert c3.precision is None and c3.recall is None and c3.f1 is None   # class 3 never occurred nor predicted
    assert r.balanced_accuracy == pytest.approx((1.0 + 0.0) / 2)
    with pytest.raises(ValueError):
        confusion_matrix([7], [1], [1, 2])


def test_predicted_class_is_the_argmax_of_the_probabilities():
    p = np.array([[0.1, 0.2, 0.3, 0.25, 0.15], [0.3, 0.3, 0.2, 0.1, 0.1], [np.nan] * 5])
    out = predicted_classes(p, CLASSES)
    assert out[0] == 3 and out[1] == 1 and np.isnan(out[2])          # a tie goes to the first class


# ── B. probability quintiles ──────────────────────────────────────────────────────────────────────────────────────

def _obs(dates, n_assets, prob, fwd, true=None):
    rows = []
    for t, d in enumerate(dates):
        for a in range(n_assets):
            rows.append({"date": pd.Timestamp(d), "asset": a, "run_id": 1, "forward_return": fwd(t, a),
                         "true_class": (true(t, a) if true else np.nan), "predicted_class": np.nan,
                         "p_5": prob(t, a)})
    return pd.DataFrame(rows)


def test_probability_quintiles_rank_one_date_into_equal_groups():
    f = _obs(["2024-01-02"], 10, prob=lambda t, a: [0.9, 0.1, 0.5, 0.3, 0.7, 0.2, 0.8, 0.4, 0.6, 0.05][a],
             fwd=lambda t, a: 0.0)
    q = assign_probability_quintiles(f, "p_5")
    # ascending probability: 9(.05) 1(.1) | 5(.2) 3(.3) | 7(.4) 2(.5) | 8(.6) 4(.7) | 6(.8) 0(.9)
    assert dict(zip(f["asset"], q)) == {9: 1, 1: 1, 5: 2, 3: 2, 7: 3, 2: 3, 8: 4, 4: 4, 6: 5, 0: 5}


def test_quintiles_are_cross_sectional_by_date():
    # date 2's probabilities are all above date 1's: a pooled rank would put date 1 in the low quintiles only
    f = _obs(["2024-01-02", "2024-01-03"], 5, prob=lambda t, a: 0.1 * a + (0.5 if t == 1 else 0.0),
             fwd=lambda t, a: 0.0)
    q = assign_probability_quintiles(f, "p_5")
    for d in f["date"].unique():
        assert sorted(q[f["date"] == d]) == [1, 2, 3, 4, 5]


def test_quintile_returns_match_the_factor_research_quantile_portfolios():
    rng = np.random.default_rng(1)
    dates = pd.bdate_range("2024-01-01", periods=30)
    probs = rng.random((30, 20))
    fwd = rng.normal(0, 0.02, (30, 20))
    f = _obs(dates, 20, prob=lambda t, a: probs[t, a], fwd=lambda t, a: fwd[t, a])
    a = analyse_probability(f, 5)
    ref = quantile_portfolios(pd.DataFrame(probs, index=dates), pd.DataFrame(fwd, index=dates), 5)
    pd.testing.assert_frame_equal(a.mean_returns[a.labels], ref.returns[a.labels], check_freq=False,
                                  check_names=False)
    assert (a.counts == 4).all().all()


def test_group_statistics_median_and_hit_rate():
    # one date, 10 stocks: P(class 5) = asset / 10, forward return = asset, true class 5 for the top two
    f = _obs(["2024-01-02"], 10, prob=lambda t, a: a / 10, fwd=lambda t, a: float(a),
             true=lambda t, a: 5 if a >= 8 else 1)
    a = analyse_probability(f, 5)
    assert a.mean_returns.iloc[0][a.labels].tolist() == [0.5, 2.5, 4.5, 6.5, 8.5]
    assert a.mean_returns.iloc[0]["Q5 - Q1"] == 8.0
    assert a.summary["median_forward_return"].tolist() == [0.5, 2.5, 4.5, 6.5, 8.5]
    assert a.summary["hit_rate"].tolist() == [0, 0, 0, 0, 1]
    assert a.monotonicity == pytest.approx(1.0)


# ── C / G. temporal behaviour and no leakage ──────────────────────────────────────────────────────────────────────

def test_a_later_date_never_changes_an_earlier_assignment():
    rng = np.random.default_rng(5)
    dates = pd.bdate_range("2024-01-01", periods=6)
    probs = rng.random((6, 15))
    fwd = rng.normal(0, 0.01, (6, 15))
    base = _obs(dates, 15, prob=lambda t, a: probs[t, a], fwd=lambda t, a: fwd[t, a])
    altered = base.copy()
    later = altered["date"] > dates[2]
    altered.loc[later, "p_5"] = rng.random(later.sum())                   # the future's probabilities change
    extra = _obs([pd.Timestamp("2024-02-01")], 15, prob=lambda t, a: 1 - a / 20, fwd=lambda t, a: 0.5)
    altered = pd.concat([altered, extra.assign(asset=extra["asset"] + 100)], ignore_index=True)   # new names later
    q0 = assign_probability_quintiles(base, "p_5")
    q1 = assign_probability_quintiles(altered, "p_5")
    early = base["date"] <= dates[2]
    assert q0[early].tolist() == q1[early[early].index].tolist()


def test_true_classes_are_ranked_per_date_with_the_trainers_ordinal_rule():
    labels = ordinal_quantile_labels(pd.Series([0.3, -0.1, 0.2, 0.0, 0.5, 0.4, -0.2, 0.1, 0.6, -0.3]), 5)
    assert labels.tolist() == [4, 2, 3, 2, 5, 4, 1, 3, 5, 1]
    f = pd.DataFrame({"date": pd.to_datetime(["2024-01-02"] * 5 + ["2024-01-03"] * 5), "asset": list(range(5)) * 2,
                      "r": [1, 2, 3, 4, 5, 10, 20, 30, 40, 50]})
    assert cross_sectional_classes(f, "r", 5).tolist() == [1, 2, 3, 4, 5] * 2
    f["r"] = [1, 2, 3, 4, 5, -1, -2, -3, -4, -5]
    assert median_split_classes(f, "r").tolist() == [0, 0, 0, 1, 1, 1, 1, 0, 0, 0]


def test_each_date_is_attributed_to_the_run_in_force():
    runs = [ClassifierRun(1, None, "a", pd.Timestamp("2024-01-01").date(), pd.Timestamp("2024-01-31").date()),
            ClassifierRun(2, None, "b", pd.Timestamp("2024-01-15").date(), None)]
    got = run_in_force(pd.to_datetime(["2023-12-31", "2024-01-10", "2024-01-20", "2024-03-01"]), runs)
    assert got == [None, 1, 2, 2]                                         # a retraining takes over from its date


def test_one_observation_per_date_and_asset_and_valid_probabilities():
    f = _obs(["2024-01-02"], 2, prob=lambda t, a: 0.5, fwd=lambda t, a: 0.0)
    for k in (1, 2, 3, 4):
        f[f"p_{k}"] = 0.125
    validate(f, CLASSES)
    with pytest.raises(ValueError, match="same"):
        validate(pd.concat([f, f]), CLASSES)
    bad = f.copy()
    bad["p_1"] = 0.5
    with pytest.raises(ValueError, match="sum"):
        validate(bad, CLASSES)


# ── E. cumulative returns ─────────────────────────────────────────────────────────────────────────────────────────

def test_cumulative_returns_compound_and_skip_overlapping_periods():
    r = pd.DataFrame({"Q1": [0.1, -0.05, 0.2, 0.0]}, index=pd.bdate_range("2024-01-01", periods=4))
    assert compound(r)["Q1"].tolist() == pytest.approx([0.1, 1.1 * 0.95 - 1, 1.1 * 0.95 * 1.2 - 1,
                                                        1.1 * 0.95 * 1.2 - 1])
    two = compound(r, horizon=2)                                        # 2-bar returns: every 2nd date only
    assert list(two.index) == list(r.index[::2])
    assert two["Q1"].tolist() == pytest.approx([0.1, 1.1 * 1.2 - 1])


# ── F. correlation matrix ─────────────────────────────────────────────────────────────────────────────────────────

def test_quintile_return_correlations():
    dates = pd.bdate_range("2024-01-01", periods=8)
    base = np.array([0.01, -0.02, 0.03, 0.0, 0.015, -0.01, 0.02, -0.005])
    other = np.array([0.3, 0.1, -0.2, 0.4, -0.1, 0.0, 0.2, -0.3])
    # quintile returns by construction: Q1 = base, Q2 = 2 base, Q3 = -base, Q4 = Q5 = other (5 stocks per date)
    series = {1: base, 2: 2 * base, 3: -base, 4: other, 5: other}
    rows = []
    for t, d in enumerate(dates):
        for q in range(1, 6):
            rows.append({"date": d, "asset": q, "run_id": 1, "forward_return": series[q][t], "true_class": np.nan,
                         "predicted_class": np.nan, "p_5": q / 10})
    a = analyse_probability(pd.DataFrame(rows), 5)
    c = a.correlation
    assert c.loc["Q1", "Q2"] == pytest.approx(1.0)
    assert c.loc["Q1", "Q3"] == pytest.approx(-1.0)
    assert c.loc["Q4", "Q5"] == pytest.approx(1.0)
    assert c.loc["Q1", "Q4"] == pytest.approx(np.corrcoef(base, other)[0, 1])
    assert np.diag(c) == pytest.approx([1.0] * 5)


# ── H. any classifier: the whole flow on a binary and a five-class model ──────────────────────────────────────────

@pytest.mark.parametrize("classes", [[0, 1], [1, 2, 3, 4, 5]])
def test_the_evaluation_flow_works_for_any_number_of_classes(classes):
    rng = np.random.default_rng(len(classes))
    rows = []
    for d in pd.bdate_range("2024-01-01", periods=40):
        fwd = rng.normal(0, 0.02, 25)
        for a in range(25):
            raw = rng.random(len(classes)) + np.eye(len(classes))[min(int((fwd[a] + 0.04) / 0.08 * len(classes)),
                                                                     len(classes) - 1)]
            p = raw / raw.sum()
            rows.append({"date": d, "asset": a, "run_id": 1, "forward_return": fwd[a], **{
                f"p_{k}": p[i] for i, k in enumerate(classes)}})
    f = pd.DataFrame(rows)
    f["true_class"] = (cross_sectional_classes(f, "forward_return", len(classes)) if len(classes) == 5
                       else median_split_classes(f, "forward_return"))
    f["predicted_class"] = predicted_classes(f[[f"p_{k}" for k in classes]].to_numpy(), classes)
    ev = evaluate_observations(f, classes)
    assert ev.classification.n_observations == len(f)
    assert set(ev.probability_quintiles) == set(classes)
    top = ev.probability_quintiles[classes[-1]]
    assert top.mean_returns["Q5 - Q1"].mean() > 0                       # the planted signal is found
    assert len(ev.per_run) == 1 and not math.isnan(ev.per_run["accuracy"].iloc[0])


# ── the same binary and quintile views for every model ───────────────────────────────────────────────────────────

def test_binary_and_quintile_views_rank_every_model_the_same_way():
    from src.application.services.model_evaluation.observations import cross_sectional_views, ranking_score
    fwd = [0.05, -0.02, 0.01, 0.03, -0.04, 0.00, 0.02, -0.01, 0.04, -0.03]
    order = np.argsort(np.argsort(fwd))                               # 0 = worst .. 9 = best
    base = pd.DataFrame({"date": pd.Timestamp("2024-01-31"), "asset": range(10), "forward_return": fwd})
    binary = base.assign(p_0=1 - (order + 1) / 11, p_1=(order + 1) / 11)      # P(class 1) ranks perfectly
    five = base.copy()                                                 # the expected class ranks perfectly
    raw = np.exp(np.outer(order / 3.0, np.arange(1, 6)))               # higher order -> mass on higher classes
    for j, k in enumerate(CLASSES):
        five[f"p_{k}"] = raw[:, j] / raw.sum(axis=1)
    score = base.assign(score=order / 9.0)
    assert ranking_score(binary, [0, 1]).tolist() == binary["p_1"].tolist()
    assert ranking_score(five, CLASSES).tolist() == pytest.approx(
        (five[[f"p_{k}" for k in CLASSES]].to_numpy() @ np.arange(1, 6)).tolist())
    for frame, classes, score_only in ((binary, [0, 1], False), (five, CLASSES, False), (score, CLASSES, True)):
        views = cross_sectional_views(frame, classes, score_only)
        for view, (true, predicted) in views.items():
            assert true.tolist() == predicted.tolist(), (view, classes)            # a perfect ranking: diagonal
        r = evaluate_classification(*[s.to_numpy() for s in views["quintile"]], CLASSES)
        assert r.accuracy == 1.0 and np.diag(r.confusion_matrix).tolist() == [2] * 5
        r2 = evaluate_classification(*[s.to_numpy() for s in views["binary"]], [0, 1])
        assert r2.confusion_matrix == ((5, 0), (0, 5))


def test_the_evaluation_carries_both_views():
    rng = np.random.default_rng(9)
    rows = []
    for d in pd.bdate_range("2024-01-01", periods=10):
        for a in range(20):
            p = rng.dirichlet(np.ones(5))
            rows.append({"date": d, "asset": a, "run_id": 1, "forward_return": rng.normal(0, 0.02),
                         "true_class": float(rng.integers(1, 6)), "predicted_class": float(np.argmax(p) + 1),
                         **{f"p_{k}": p[k - 1] for k in CLASSES}})
    ev = evaluate_observations(pd.DataFrame(rows), CLASSES)
    assert set(ev.cross_sectional) == {"binary", "quintile"}
    assert ev.cross_sectional["binary"].classes == (0, 1) and ev.cross_sectional["quintile"].classes == (1, 2, 3, 4, 5)
    assert ev.cross_sectional["quintile"].n_observations == 200 == ev.cross_sectional["binary"].n_observations
    assert ev.ranking_label().startswith("the expected class")
