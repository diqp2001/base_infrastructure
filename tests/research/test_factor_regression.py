"""Factor regressions of strategy returns: synthetic data with known coefficients (no database, no network)."""

import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from src.application.services.research.factor_regression import (
    FactorAnalysisConfig,
    FactorDataMissing,
    analyse,
    compare,
)
from src.application.services.research.factor_returns import FactorReturnService, market_proxy_from_closes
from src.application.services.research.project_returns import (
    StrategyReturns,
    infer_bar_minutes,
    realised_index,
    strategies_of,
)
from src.domain.entities.research.factor_models import EXCESS, TOTAL
from src.infrastructure.research.factor_return_files import (
    FactorReturnFileStore,
    FrenchLibraryImporter,
    parse_french_csv,
)

FRENCH_SAMPLE = """This file was created using the 202608 CRSP database.
The 1-month TBill return is from Ibbotson and Associates Inc.

,Mkt-RF,SMB,HML,RF
20260803,    0.52,   -0.11,    0.20,   0.016
20260804,   -1.10,    0.35,   -0.05,   0.016
20260805,    0.08,    0.01,    0.12,   0.016

Annual Factors: January-December
,Mkt-RF,SMB,HML,RF
2025,  12.00,  -3.00,  1.00,  4.50

Copyright 2026 Eugene F. Fama and Kenneth R. French
"""


def _factors(n=1500, seed=3, rf=0.0001):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-02", periods=n)
    return pd.DataFrame({"MKT_RF": rng.normal(0.0004, 0.01, n), "SMB": rng.normal(0, 0.005, n),
                         "HML": rng.normal(0, 0.005, n), "RMW": rng.normal(0, 0.004, n),
                         "CMA": rng.normal(0, 0.004, n), "RF": np.full(n, rf)}, index=idx)


def _strategy(f, betas, alpha=0.0002, convention=EXCESS, noise=0.001, seed=4):
    rng = np.random.default_rng(seed)
    excess = alpha + sum(b * f[k] for k, b in betas.items()) + rng.normal(0, noise, len(f))
    r = excess + (f["RF"] if convention == TOTAL else 0.0)
    return StrategyReturns("S", r, convention, None, "synthetic")


@pytest.mark.parametrize("model,betas", [
    ("capm", {"MKT_RF": 0.8}),
    ("ff3", {"MKT_RF": 1.1, "SMB": 0.5, "HML": -0.3}),
    ("ff5", {"MKT_RF": 0.9, "SMB": 0.2, "HML": 0.1, "RMW": 0.4, "CMA": -0.6}),
])
def test_the_standard_models_recover_known_betas(model, betas):
    f = _factors()
    res = analyse(_strategy(f, betas), f, FactorAnalysisConfig(model=model))
    got = dict(zip(res.regression.names, res.regression.coef))
    for k, b in betas.items():
        assert got[k] == pytest.approx(b, abs=0.03)
    assert got["alpha"] == pytest.approx(0.0002, abs=5e-5)
    assert res.alpha_annualised["alpha"] == pytest.approx(got["alpha"] * 252)
    assert res.sample["aligned_periods"] == len(f) and res.regression.n == len(f)


def test_a_custom_model_uses_the_requested_factor_returns():
    f = _factors()
    f["MOM_LS"] = np.random.default_rng(9).normal(0, 0.006, len(f))
    res = analyse(_strategy(f, {"MOM_LS": 0.7}), f, FactorAnalysisConfig(model="custom", factors=["MOM_LS"]))
    assert res.factors == ["MOM_LS"] and dict(zip(res.regression.names, res.regression.coef))["MOM_LS"] == \
        pytest.approx(0.7, abs=0.03)
    with pytest.raises(ValueError):
        analyse(_strategy(f, {}), f, FactorAnalysisConfig(model="custom", factors=[]))


def test_the_risk_free_rate_is_subtracted_once_for_total_returns_only():
    f = _factors(rf=0.0003)
    total = _strategy(f, {"MKT_RF": 1.0}, alpha=0.0, convention=TOTAL)
    res = analyse(total, f, FactorAnalysisConfig(model="capm"))
    assert res.alpha_annualised["alpha"] == pytest.approx(0.0, abs=0.01)          # RF removed exactly once
    wrong = analyse(total, f, FactorAnalysisConfig(model="capm", convention=EXCESS))
    assert wrong.alpha_annualised["alpha"] == pytest.approx(0.0003 * 252, abs=0.01)  # RF left in: shows as alpha
    with pytest.raises(FactorDataMissing):
        analyse(total, f.drop(columns="RF"), FactorAnalysisConfig(model="capm"))


def test_missing_periods_are_dropped_and_counted_never_filled():
    f = _factors(n=300)
    s = _strategy(f, {"MKT_RF": 1.0})
    f2 = f.copy()
    f2.iloc[10:20, 0] = np.nan                                                      # 10 days without the market
    res = analyse(s, f2, FactorAnalysisConfig(model="capm"))
    assert res.sample["aligned_periods"] == 290 and res.sample["strategy_periods_without_factor_data"] == 10
    assert any("have no factor data" in w for w in res.warnings)


def test_factor_data_ending_before_the_strategy_is_refused_not_fabricated():
    f = _factors(n=100)
    s = StrategyReturns("late", pd.Series(0.001, index=pd.bdate_range("2026-10-05", periods=5)), EXCESS, None, "x")
    with pytest.raises(FactorDataMissing) as e:
        analyse(s, f, FactorAnalysisConfig(model="capm"))
    assert "factor data ends" in str(e.value)


def test_weekly_and_monthly_analyses_compound_both_sides():
    f = _factors(n=1000)
    res = analyse(_strategy(f, {"MKT_RF": 1.0}, noise=0.0002), f, FactorAnalysisConfig(model="capm", frequency="W-FRI"))
    assert res.periods_per_year == 52 and 190 < res.regression.n < 205
    assert dict(zip(res.regression.names, res.regression.coef))["MKT_RF"] == pytest.approx(1.0, abs=0.05)
    m = analyse(_strategy(f, {"MKT_RF": 1.0}, noise=0.0002), f, FactorAnalysisConfig(model="capm", frequency="M"))
    assert m.periods_per_year == 12 and 45 <= m.regression.n <= 48              # ~47 months of 1000 sessions


def test_contributions_fitted_and_residual_add_up_and_rolling_is_reported():
    f = _factors(n=400)
    res = analyse(_strategy(f, {"MKT_RF": 0.9, "SMB": 0.3, "HML": 0.1}), f,
                  FactorAnalysisConfig(model="ff3", rolling_window=60))
    total = res.contributions.sum(axis=1) + res.series["alpha"] + res.series["residual"]
    assert np.allclose(total, res.series["strategy"])
    assert res.rolling is not None and {"MKT_RF", "MKT_RF_low", "r2"} <= set(res.rolling.columns)
    assert len(res.rolling) == res.regression.n - 60 + 1


def test_comparisons_use_one_common_sample():
    f = _factors(n=500)
    a = _strategy(f, {"MKT_RF": 1.0}, seed=1)
    b = StrategyReturns("B", _strategy(f, {"MKT_RF": 0.2}, seed=2).returns.iloc[100:], EXCESS, None, "x")
    out = compare([a, b], f, FactorAnalysisConfig(model="capm"))
    assert out["periods"] == 400 and set(out["rows"].index) == {"S", "B"}
    assert out["rows"].loc["B", "beta MKT_RF"] == pytest.approx(0.2, abs=0.05)


# ── stamping of project returns ─────────────────────────────────────────────────────────────────────────────────

def test_decision_stamped_returns_are_moved_to_the_bar_where_they_are_realised():
    daily = pd.DatetimeIndex(["2026-07-02", "2026-07-06"])                     # 07-03 is a holiday (early close day)
    assert list(realised_index(daily, None)) == list(pd.DatetimeIndex(["2026-07-06", "2026-07-07"]))
    intraday = pd.DatetimeIndex(["2026-10-05 15:40", "2026-10-05 15:50"])
    assert list(realised_index(intraday, 10)) == list(pd.DatetimeIndex(["2026-10-05 15:50", "2026-10-06 09:30"]))
    assert infer_bar_minutes(intraday) == 10 and infer_bar_minutes(daily) is None


def test_report_strategies_get_their_default_convention():
    from types import SimpleNamespace
    idx = pd.bdate_range("2026-06-01", periods=5)
    report = SimpleNamespace(model_name="M", returns=pd.DataFrame({"M": 0.01, "Long Only (EW)": 0.02}, index=idx))
    s = strategies_of(report, "csm")
    assert s["M"].convention == EXCESS and s["Long Only (EW)"].convention == TOTAL
    assert s["M"].returns.index[0] == pd.Timestamp("2026-06-02")                # realised the next session
    spx = strategies_of(SimpleNamespace(returns=pd.Series([0.01, 0.02], index=idx[:2])), "spx")
    assert spx["SPX v2 portfolio"].convention == TOTAL and spx["SPX v2 portfolio"].returns.index[0] == idx[0]


# ── factor return sources ────────────────────────────────────────────────────────────────────────────────────────

def test_french_files_are_parsed_to_decimals_and_stop_at_the_annual_table(tmp_path):
    frame = parse_french_csv(FRENCH_SAMPLE)
    assert list(frame.columns) == ["MKT_RF", "SMB", "HML", "RF"] and len(frame) == 3
    assert frame.loc["2026-08-04", "MKT_RF"] == pytest.approx(-0.011)
    with pytest.raises(ValueError):
        parse_french_csv("nothing here")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("F-F_Research_Data_Factors_daily.CSV", FRENCH_SAMPLE)
    store = FactorReturnFileStore(tmp_path)
    meta = FrenchLibraryImporter(store, fetch=lambda url: buf.getvalue()).import_dataset("ff3_daily")
    assert meta["rows"] == 3 and meta["last"] == "2026-08-05" and "French" in meta["source"]
    assert store.load("ff3_daily").loc["2026-08-03", "SMB"] == pytest.approx(-0.0011)
    csv = "date,Mkt-RF,RF\n2026-01-02,1.0,0.02\n2026-01-05,-0.5,0.02\n"
    FrenchLibraryImporter(store).import_csv("my_factors", csv, unit="percent")
    assert store.load("my_factors").loc["2026-01-05", "MKT_RF"] == pytest.approx(-0.005)
    assert {m["name"] for m in store.list()} == {"ff3_daily", "my_factors"}


def test_the_local_market_proxy_uses_the_previous_t_bill_rate():
    idx = pd.bdate_range("2026-01-02", periods=3)
    frame = market_proxy_from_closes(pd.Series([100.0, 101.0, 100.0], index=idx),
                                     pd.Series([40.0, 41.0, 42.0], index=idx))
    rf1 = 40.0 / 10 / 100 / 252
    assert frame.index[0] == idx[1] and frame.loc[idx[1], "RF"] == pytest.approx(rf1)
    assert frame.loc[idx[1], "MKT_RF"] == pytest.approx(0.01 - rf1)
    service = FactorReturnService(FactorReturnFileStore(), market_closes=lambda: {"SPY": pd.Series(dtype=float),
                                                                                  "IRX": pd.Series(dtype=float)})
    with pytest.raises(LookupError):
        service.load("local_market")
