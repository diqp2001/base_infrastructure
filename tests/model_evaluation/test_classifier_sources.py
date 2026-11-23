"""
The two classifier observation sources (LGBM quintile momentum, cross-sectional momentum) on fake repositories:
runs, probabilities at T, true class and forward return AFTER T, no leakage, and one service evaluating both.
"""

import json
from datetime import date
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMConfiguration,
)
from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_feature_definition import (
    LGBMMomentumFeatureDefinition,
)
from src.application.services.model_evaluation.classifier_evaluation_service import (
    ClassifierEvaluationService,
    EvaluationRequest,
)
from src.application.services.model_evaluation.classifier_sources import (
    CSMObservationSource,
    LGBMQuintileObservationSource,
)

ASSETS = list(range(1, 11))
DAYS = pd.date_range("2024-01-01", "2024-03-31", freq="D")        # calendar days: the label is at T + 5 days
CLOSE_ID, RET5_ID, SIGNAL_ID = 999, 500, 700
CSM_KEY = "csm:8:" + CSMConfiguration().model_hash()[:12]


def _typed(class_name, fid, **kw):
    obj = type(class_name, (), {})()
    obj.id = fid
    for k, v in kw.items():
        setattr(obj, k, v)
    return obj


class FakeData:
    def __init__(self, panels):
        self.panels = panels                                 # factor id -> DataFrame (dates x entity ids)

    def membership(self, universe_id):
        return [(a, date(2023, 1, 1), None) for a in ASSETS]

    def panel(self, fid, ids, start, end):
        p = self.panels.get(fid, pd.DataFrame())
        if p.empty:
            return p
        return p.loc[(p.index >= pd.Timestamp(start)) & (p.index <= pd.Timestamp(end)), [i for i in ids if i in p]]

    def symbols(self, ids):
        return {i: f"S{i}" for i in ids}

    def close_factor_id(self, frequency):
        return CLOSE_ID


def _factory(models, trainings, artifacts, factors):
    return SimpleNamespace(
        ml_model_local_repo=SimpleNamespace(get_all=lambda: models),
        model_training_local_repo=SimpleNamespace(get_by_model=lambda mid: trainings.get(mid, [])),
        model_artifact_local_repo=SimpleNamespace(get_by_training_and_type=lambda tid, t: artifacts.get(tid, [])),
        investment_universe_local_repo=SimpleNamespace(get_by_name=lambda n: SimpleNamespace(id=1)),
        factor_local_repo=SimpleNamespace(get_all=lambda: factors))


# ── LGBM quintile momentum ────────────────────────────────────────────────────────────────────────────────────────

class ScoreModel:
    """A fitted-classifier stand-in: P(class k) grows with k x the first feature (return_1d)."""
    classes_ = np.array([1, 2, 3, 4, 5])

    def __init__(self, scale=1.0):
        self.scale = scale
        self.seen = []

    def predict_proba(self, X):
        self.seen.append(np.array(X, copy=True))
        z = np.outer(X[:, 0] * self.scale, np.arange(1, 6))
        e = np.exp(z - z.max(axis=1, keepdims=True))
        return e / e.sum(axis=1, keepdims=True)

    def predict(self, X):                                  # sklearn's rule: the class of the highest probability
        return self.classes_[np.argmax(self.predict_proba(X), axis=1)]


def _lgbm_world(seed=0):
    rng = np.random.default_rng(seed)
    signal = pd.DataFrame(rng.normal(0, 1, (len(DAYS), len(ASSETS))), index=DAYS, columns=ASSETS)
    panels, factors = {}, []
    # return_5d stored at T + 5 = the forward return of T: follows the signal of T, plus noise. The same stored
    # factor is also a feature (its value at T is the trailing return), as in the trainer.
    fwd = signal * 0.01 + rng.normal(0, 0.002, signal.shape)
    for i, (cls, _) in enumerate(LGBMMomentumFeatureDefinition.FEATURE_MAP):
        if cls == "CompanyShareReturn5DFactor":
            factors.append(_typed(cls, RET5_ID))
            panels[RET5_ID] = fwd.shift(5)
            continue
        fid = 100 + i
        factors.append(_typed(cls, fid))
        panels[fid] = signal if i == 0 else pd.DataFrame(rng.normal(0, 1, signal.shape), index=DAYS, columns=ASSETS)
    meta = lambda a, b: json.dumps({"valid_from": a, "valid_until": b, "sha256": "x"})  # noqa: E731
    artifacts = {10: [SimpleNamespace(id=1001, location="a", artifact_metadata=meta("2024-01-01", "2024-01-31"))],
                 11: [SimpleNamespace(id=1002, location="b", artifact_metadata=meta("2024-02-01", "2024-03-31"))]}
    factory = _factory([SimpleNamespace(id=3, name="lgbm_mom_abc")],
                       {3: [SimpleNamespace(id=10, status="completed"), SimpleNamespace(id=11, status="completed")]},
                       artifacts, factors)
    return factory, FakeData(panels), signal, fwd


def _lgbm_source(world, models=None):
    factory, data, _, _ = world
    models = models or {1001: ScoreModel(), 1002: ScoreModel(2.0)}
    return LGBMQuintileObservationSource(factory, data, model_loader=lambda a: models[int(a.id)]), models


def test_lgbm_runs_are_the_artifacts_and_start_after_their_training_labels():
    source, _ = _lgbm_source(_lgbm_world())
    (model,) = source.models()
    assert model.classes == (1, 2, 3, 4, 5) and model.key == "lgbm_quintile:3"
    runs = source.runs(model)
    assert [(r.run_id, r.valid_from, r.valid_until, r.evaluable_from) for r in runs] == [
        (1001, date(2024, 1, 1), date(2024, 1, 31), date(2024, 1, 12)),
        (1002, date(2024, 2, 1), date(2024, 3, 31), date(2024, 2, 12))]


def test_lgbm_observations_use_each_runs_model_on_the_features_known_at_t():
    world = _lgbm_world()
    source, models = _lgbm_source(world)
    (model,) = source.models()
    out = source.observations(model, None, 1, date(2024, 1, 1), date(2024, 3, 20))
    f = out.frame
    assert set(f["run_id"]) == {1001, 1002}
    assert f[f["run_id"] == 1001]["date"].between("2024-01-12", "2024-01-31").all()
    assert f[f["run_id"] == 1002]["date"].between("2024-02-12", "2024-03-20").all()
    assert f[[f"p_{k}" for k in range(1, 6)]].sum(axis=1).to_numpy() == pytest.approx(1.0)
    signal = world[2]
    row = f.iloc[0]
    expected = ScoreModel().predict_proba(np.array([[signal.at[row["date"], row["asset"]]] + [0] * 23]))[0]
    assert [row[f"p_{k}"] for k in range(1, 6)] == pytest.approx(expected)
    assert row["predicted_class"] == float(np.argmax(expected) + 1)


def test_lgbm_true_class_and_forward_return_come_from_the_period_after_t():
    world = _lgbm_world()
    source, _ = _lgbm_source(world)
    (model,) = source.models()
    f = source.observations(model, 1001, 1, date(2024, 1, 1), date(2024, 1, 31)).frame
    fwd = world[3]
    for _, r in f.head(20).iterrows():                    # the label of T = return_5d stored at T + 5 days
        assert r["forward_return"] == pytest.approx(fwd.at[r["date"], r["asset"]])
    for d, g in f.groupby("date"):                         # quintiles of the forward return, per date
        order = g.sort_values("forward_return")["true_class"].tolist()
        assert order == sorted(order) and sorted(order) == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]


def _frame(world):
    source = _lgbm_source(world)[0]
    return source.observations(source.models()[0], None, 1, date(2024, 1, 1), date(2024, 2, 20)).frame


def test_lgbm_no_future_data_changes_what_is_known_at_t():
    cutoff = "2024-01-25"
    base, changed = _lgbm_world(), _lgbm_world()
    # every value stored from the cutoff on changes: the label return (also a feature) and another feature
    changed[1].panels[RET5_ID].loc[cutoff:] += 0.5
    changed[1].panels[100].loc[cutoff:] = 99.0
    fa, fb = _frame(base), _frame(changed)
    known_at_t = ["date", "asset", "run_id", "predicted_class"] + [f"p_{k}" for k in range(1, 6)]
    early_a, early_b = fa[fa["date"] < cutoff], fb[fb["date"] < cutoff]
    pd.testing.assert_frame_equal(early_a[known_at_t].reset_index(drop=True),
                                  early_b[known_at_t].reset_index(drop=True))
    # ... while the realised side of a date whose forward window reaches the cutoff does change (it is AFTER T)
    late_window = early_a["date"] >= pd.Timestamp(cutoff) - pd.Timedelta(days=5)
    assert not np.allclose(early_a.loc[late_window, "forward_return"],
                           early_b.loc[early_b["date"] >= pd.Timestamp(cutoff) - pd.Timedelta(days=5),
                                       "forward_return"])


# ── cross-sectional momentum (binary) ─────────────────────────────────────────────────────────────────────────────

def _csm_world():
    rng = np.random.default_rng(2)
    cfg = CSMConfiguration()
    days = pd.bdate_range("2024-01-01", "2024-03-29")
    closes = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (len(days), len(ASSETS))), axis=0)),
                          index=days, columns=ASSETS)
    fwd = closes.shift(-1) / closes - 1
    prob = (1 / (1 + np.exp(-fwd.fillna(0) * 300))) * 0.8 + 0.1               # informative, in (0.1, 0.9)
    meta = lambda as_of: json.dumps({"model_hash": cfg.model_hash(), "trained_as_of": as_of})  # noqa: E731
    factors = [_typed("CompanyShareCrossSectionalMomentumFactor", SIGNAL_ID, name=cfg.signal_factor_name,
                      frequency="1d")]
    factory = _factory([SimpleNamespace(id=8, name="csm_lightgbm_x", configuration=cfg.to_dict())],
                       {8: [SimpleNamespace(id=20, status="completed"), SimpleNamespace(id=21, status="completed")]},
                       {20: [SimpleNamespace(id=2001, artifact_metadata=meta("2024-01-02"))],
                        21: [SimpleNamespace(id=2002, artifact_metadata=meta("2024-02-15")),
                             SimpleNamespace(id=2003, artifact_metadata=json.dumps(
                                 {"model_hash": "f" * 64, "trained_as_of": "2024-02-01",
                                  "configuration": {"label": {"horizon": 2}}}))]}, factors)
    return factory, FakeData({CLOSE_ID: closes, SIGNAL_ID: prob}), closes, prob


def test_csm_observations_binary_classes_runs_in_force_and_median_label():
    factory, data, closes, prob = _csm_world()
    source = CSMObservationSource(factory, data)
    models = {m.key: m for m in source.models()}
    assert set(models) == {CSM_KEY, "csm:8:" + "f" * 12}                  # one model per configuration
    assert "horizon" not in models[CSM_KEY].label_horizon and "2 sessions" in models["csm:8:" + "f" * 12].label_horizon
    model = models[CSM_KEY]
    assert model.classes == (0, 1)
    runs = source.runs(model)
    assert [(r.run_id, r.valid_from, r.valid_until) for r in runs] == [
        (2001, date(2024, 1, 2), date(2024, 2, 14)), (2002, date(2024, 2, 15), None)]
    f = source.observations(model, None, 1, date(2024, 1, 1), date(2024, 3, 29)).frame
    assert f[f["date"] < "2024-02-15"]["run_id"].eq(2001).all() and f[f["date"] >= "2024-02-15"]["run_id"].eq(2002).all()
    assert (f["p_0"] + f["p_1"]).to_numpy() == pytest.approx(1.0)
    r = f.iloc[3]
    fwd = closes.shift(-1) / closes - 1
    assert r["forward_return"] == pytest.approx(fwd.at[r["date"], r["asset"]])
    assert r["true_class"] == float(fwd.loc[r["date"]][r["asset"]] > fwd.loc[r["date"]].median())
    assert f[f["date"] == closes.index[-1]]["true_class"].isna().all()       # the last date has no future yet


def test_one_service_evaluates_both_classifier_families():
    lgbm_world = _lgbm_world()
    lgbm_source, _ = _lgbm_source(lgbm_world)
    csm_factory, csm_data, _, _ = _csm_world()
    service = ClassifierEvaluationService([lgbm_source, CSMObservationSource(csm_factory, csm_data)])
    keys = {m.key for m in service.models()}
    assert {"lgbm_quintile:3", CSM_KEY} <= keys
    ev5 = service.evaluate(EvaluationRequest("lgbm_quintile:3", None, 1, date(2024, 1, 1), date(2024, 3, 20)))
    ev2 = service.evaluate(EvaluationRequest(CSM_KEY, None, 1, date(2024, 1, 1), date(2024, 3, 28)))
    assert ev5.classes == [1, 2, 3, 4, 5] and len(ev5.classification.confusion_matrix) == 5
    assert ev2.classes == [0, 1] and len(ev2.classification.confusion_matrix) == 2
    # informative planted signals: the top-class probability ranks the realised returns
    assert ev5.probability_quintiles[5].summary["mean_forward_return"].iloc[-1] > \
        ev5.probability_quintiles[5].summary["mean_forward_return"].iloc[0]
    assert ev2.probability_quintiles[1].monotonicity > 0.5
    assert ev5.classification.accuracy > 0.2 and set(ev5.per_run.index) == {1001, 1002}
    with pytest.raises(KeyError):
        service.evaluate(EvaluationRequest("lgbm_quintile:3", 4242, 1, date(2024, 1, 1), date(2024, 3, 20)))


def test_csm_warns_when_another_configuration_writes_the_same_signal_on_the_evaluated_dates():
    factory, data, _, _ = _csm_world()
    source = CSMObservationSource(factory, data)
    model = next(m for m in source.models() if m.key == CSM_KEY)
    notes = source.observations(model, None, 1, date(2024, 1, 1), date(2024, 3, 29)).notes
    shared = [n for n in notes if n.startswith("WARNING")]
    assert len(shared) == 1 and "ffffffff" in shared[0] and "2024-02-01" in shared[0]
    early = source.observations(model, None, 1, date(2024, 1, 1), date(2024, 1, 31)).notes
    assert not [n for n in early if n.startswith("WARNING")]            # before the other configuration existed


def test_the_lgbm_provider_exposes_the_full_probabilities_and_predict_is_unchanged():
    from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_model_provider import (
        LGBMMomentumModelProvider,
        class_probabilities,
    )
    provider = LGBMMomentumModelProvider()
    provider._get_or_train_model = lambda d: ScoreModel()
    deps = {cls: [0.7] for cls, _ in LGBMMomentumFeatureDefinition.FEATURE_MAP}
    proba = provider.predict_proba(deps, None, date(2024, 1, 5))
    assert set(proba) == {1, 2, 3, 4, 5} and sum(proba.values()) == pytest.approx(1.0)
    assert provider.predict(deps, None, date(2024, 1, 5)) == float(max(proba, key=proba.get))   # its argmax
    missing = dict(deps)
    missing.pop("CompanyShareSharpe20DFactor")
    assert provider.predict_proba(missing, None, date(2024, 1, 5)) is None
    model = ScoreModel()
    model.classes_ = np.array([1, 2, 3, 5])                       # a class absent from the training labels
    model.predict_proba = lambda X: np.full((len(X), 4), 0.25)
    labels, p = class_probabilities(model, np.zeros((2, 24)))
    assert labels == [1, 2, 3, 5] and p.shape == (2, 4)
