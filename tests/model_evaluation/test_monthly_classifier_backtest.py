"""
Monthly classifier backtest harness on synthetic in-memory closes (no database, no price files): walk-forward
training strictly before T, next-month labels, the RandomForest port's inputs, the score model's predicted class,
and the result files read back by the classifier evaluation.
"""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.application.services.model_evaluation import monthly_classifier_backtest as mb
from src.application.services.model_evaluation.backtest_file_source import ClassifierBacktestFileSource
from src.application.services.model_evaluation.classifier_evaluation_service import (
    ClassifierEvaluationService,
    EvaluationRequest,
)

SYMBOLS = [f"S{i:02d}" for i in range(15)]


def _data(seed=0):
    """Daily closes 2012..2022; a stock's next-month return follows its last-month return (planted momentum)."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2012-01-02", "2022-12-30")
    months = days.to_period("M")
    drift = {}
    closes = np.zeros((len(days), len(SYMBOLS)))
    level = np.full(len(SYMBOLS), 100.0)
    prev_month_ret = rng.normal(0, 0.05, len(SYMBOLS))
    month_start = level.copy()
    for i, p in enumerate(months):
        if i == 0 or p != months[i - 1]:
            if i:
                prev_month_ret = level / month_start - 1
            month_start = level.copy()
            drift[p] = 0.5 * prev_month_ret / 21 + rng.normal(0, 0.03, len(SYMBOLS)) / 21
        level = level * (1 + drift[p] + rng.normal(0, 0.004, len(SYMBOLS)))
        closes[i] = level
    frame = pd.DataFrame(closes, index=days, columns=SYMBOLS)
    month_ends = pd.DatetimeIndex(days.to_series().groupby(months).max().to_numpy())
    return mb.MonthlyData(closes=frame, month_ends=month_ends, members_at=lambda d: list(SYMBOLS))


def test_next_month_labels_are_per_date_quintiles_and_median_splits():
    data = _data()
    fwd = data.forward_returns()
    t = data.month_ends[30]
    nxt = data.month_ends[31]
    assert fwd.loc[t, "S03"] == pytest.approx(data.closes.loc[nxt, "S03"] / data.closes.loc[t, "S03"] - 1)
    labels = mb.true_classes(fwd, data.members_at, 5)
    one = labels[labels["date"] == t].sort_values("forward_return")
    assert one["true_5"].tolist() == [1] * 3 + [2] * 3 + [3] * 3 + [4] * 3 + [5] * 3
    assert one["true_2"].sum() == 7                       # above the median of 15 names
    assert labels["date"].max() < data.month_ends[-1]      # the last month end has no next month yet


def test_random_forest_inputs_are_known_at_t():
    data = _data()
    f = mb.random_forest_features(data)
    m = data.monthly()
    t, t1, t2 = data.month_ends[40], data.month_ends[39], data.month_ends[38]
    assert f.loc[(t, "S05"), "return_lag1"] == pytest.approx(m.loc[t, "S05"] / m.loc[t1, "S05"] - 1)
    assert f.loc[(t, "S05"), "return_lag2"] == pytest.approx(m.loc[t1, "S05"] / m.loc[t2, "S05"] - 1)
    in_month = data.closes.loc[(data.closes.index.to_period("M") == t.to_period("M")), "S05"]
    assert f.loc[(t, "S05"), "volatility"] == pytest.approx(
        data.closes["S05"].pct_change().loc[in_month.index].std())


class SpyModel(mb._Tabular):
    classes = [0, 1]
    fits = []

    def fit(self, rows, y):
        SpyModel.fits.append(rows.index.get_level_values("date").max())

    def predict_proba(self, rows):
        return np.full((len(rows), 2), 0.5)


def test_every_model_is_fit_on_rows_dated_before_the_prediction_date():
    data = _data()
    labels = mb.true_classes(data.forward_returns(), data.members_at, 5)
    feats = mb.random_forest_features(data)
    cfg = mb.MonthlyBacktestConfig(start="2020-01-01", end="2020-12-31", training_window_months=36)
    dates = mb.decision_dates(data, cfg)
    SpyModel.fits = []
    pred = mb.walk_forward(SpyModel, feats, labels, "true_2", dates, data.members_at, cfg, log=lambda m: None)
    assert len(SpyModel.fits) == len(dates) == 12
    for t, last_train in zip(dates, SpyModel.fits):
        prev = data.month_ends[data.month_ends < t][-1]
        assert last_train == prev                        # the latest row used is the previous month end
    assert set(pred["run_id"]) == {int(t.strftime("%Y%m")) for t in dates}


def test_a_score_model_predicts_its_per_date_score_quintile():
    data = _data()
    labels = mb.true_classes(data.forward_returns(), data.members_at, 5)
    t = data.month_ends[50]
    pred = pd.DataFrame({"date": t, "asset": SYMBOLS, "score": np.linspace(-1, 1, 15), "run_id": 1})
    obs = mb.observations(pred, labels, [1, 2, 3, 4, 5], "true_5")
    assert obs.sort_values("score")["predicted_class"].tolist() == [1] * 3 + [2] * 3 + [3] * 3 + [4] * 3 + [5] * 3
    assert obs["true_class"].notna().all() and obs["forward_return"].notna().all()


def test_a_run_writes_files_the_evaluation_reads(tmp_path):
    data = _data()
    cfg = mb.MonthlyBacktestConfig(start="2020-01-01", end="2021-12-31", models=("lgbm_quintile", "random_forest",
                                                                                "csm"), csm_trials=3,
                                   training_window_months=48)
    out = mb.run(cfg, out_dir=tmp_path / "bt", data=data, log=lambda m: None)
    source = ClassifierBacktestFileSource(tmp_path)
    models = {m.key.split(":")[-1]: m for m in source.models()}
    assert set(models) == {"lgbm_quintile", "random_forest", "csm"}
    assert models["lgbm_quintile"].classes == (1, 2, 3, 4, 5) and models["csm"].classes == (0, 1)
    service = ClassifierEvaluationService([source])
    ev = service.evaluate(EvaluationRequest(models["random_forest"].key, None, None, date(2020, 1, 1),
                                            date(2021, 12, 31)))
    assert ev.classification.n_observations == 24 * 15 and len(ev.runs) == 24
    assert ev.probability_quintiles[1].summary["observations"].sum() == 24 * 15
    # the planted momentum is found by the LGBM quintile model: P(Q5) ranks the next-month returns
    q5 = service.evaluate(EvaluationRequest(models["lgbm_quintile"].key, None, None, date(2020, 1, 1),
                                            date(2021, 12, 31))).probability_quintiles[5]
    assert q5.summary["mean_forward_return"].iloc[-1] > q5.summary["mean_forward_return"].iloc[0]
    assert (out / "manifest.json").exists()
