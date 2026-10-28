"""Statistics of factor research and regressions, on synthetic data with known answers (no database)."""

import numpy as np
import pandas as pd
import pytest

from src.application.services.research import statistics as st


def _panel(values, start="2026-01-02", freq="B"):
    values = np.asarray(values, dtype=float)
    return pd.DataFrame(values, index=pd.date_range(start, periods=values.shape[0], freq=freq),
                        columns=[f"S{i}" for i in range(values.shape[1])])


def test_pearson_and_spearman_use_only_pairs_present_in_both():
    x = np.array([1, 2, 3, 4, 5, np.nan, 7, 8, 9, 10, 11, 12], dtype=float)
    y = np.array([2, 4, 6, 8, 10, 12, np.nan, 16, 18, 20, 22, 1000], dtype=float)
    p = st.correlation(x, y, "pearson", min_obs=5)
    s = st.correlation(x, y, "spearman", min_obs=5)
    assert p.n == s.n == 10                                       # the two rows with a NaN are dropped
    assert s.value == pytest.approx(1.0)                          # monotone: rank correlation is exactly 1
    assert 0.5 < p.value < 1.0                                    # the outlier pulls Pearson down
    assert p.value == pytest.approx(np.corrcoef(x[[0, 1, 2, 3, 4, 7, 8, 9, 10, 11]],
                                                y[[0, 1, 2, 3, 4, 7, 8, 9, 10, 11]])[0, 1])


def test_constant_series_and_short_samples_give_no_coefficient_with_the_reason():
    assert st.correlation([1] * 20, range(20)).note == "constant series"
    short = st.correlation(range(5), range(5), min_obs=10)
    assert short.value is None and short.n == 5 and "insufficient" in short.note
    with pytest.raises(ValueError):
        st.correlation(range(20), range(20), "kendall")


def test_the_matrix_is_symmetric_and_reports_each_pairs_sample():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.normal(size=(50, 3)), columns=["a", "b", "c"])
    df.loc[:9, "c"] = np.nan
    coef, n, notes = st.correlation_matrix(df)
    assert np.allclose(coef.to_numpy(), coef.to_numpy().T, equal_nan=True)
    assert (n.loc["a", "b"], n.loc["a", "c"], n.loc["c", "c"]) == (50, 40, 40)
    assert coef.loc["a", "a"] == pytest.approx(1.0)


def test_pooled_and_cross_sectional_correlations_are_different_things():
    """Within each date the two factors are perfectly ranked together, but their date-level means move in
    opposite directions: cross-sectional correlation 1 every date, pooled correlation negative."""
    rows_a, rows_b = [], []
    for t in range(20):
        base = np.arange(10, dtype=float)
        rows_a.append(base + 100 * t)
        rows_b.append(base - 100 * t)
    a, b = _panel(rows_a), _panel(rows_b)
    xs = st.cross_sectional_correlations(a, b, min_assets=5)
    assert xs.summary["mean"] == pytest.approx(1.0) and xs.summary["dates_with_value"] == 20
    assert (xs.counts == 10).all()
    pooled = st.pooled_correlation(a, b)
    assert pooled.value < -0.9 and pooled.n == 200


def test_forward_returns_are_stamped_at_the_decision_and_never_look_ahead():
    closes = _panel([[100], [110], [121], [np.nan], [130]])
    fwd = st.forward_returns(closes, 1)
    assert fwd.iloc[0, 0] == pytest.approx(0.10)                  # decided at t0, earned from t0 to t1
    assert fwd.iloc[1, 0] == pytest.approx(0.10)
    assert np.isnan(fwd.iloc[2, 0]) and np.isnan(fwd.iloc[3, 0])  # a missing close is not filled
    assert np.isnan(fwd.iloc[-1, 0])                              # no future for the last row
    fwd2 = st.forward_returns(closes, 2)
    assert fwd2.iloc[0, 0] == pytest.approx(0.21)


def test_quantile_portfolios_sort_on_the_factor_and_earn_the_forward_return():
    factor = _panel([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]] * 3)
    fwd = _panel([[0.01 * i for i in range(10)]] * 3)
    fwd.iloc[2, 0] = np.nan                                       # S0 has no forward return at t2
    q = st.quantile_portfolios(factor, fwd, n_quantiles=5)
    assert q.returns.iloc[0].tolist() == pytest.approx([0.005, 0.025, 0.045, 0.065, 0.085, 0.08])
    assert q.counts.iloc[0].tolist() == [2, 2, 2, 2, 2] and q.counts.iloc[2].sum() == 9
    assert np.isnan(q.turnover.iloc[0, 0]) and q.turnover.iloc[1].tolist() == [0.0] * 5
    assert q.value_weighted is None
    caps = _panel([[1.0] * 9 + [3.0]] * 3)
    vw = st.quantile_portfolios(factor, fwd, n_quantiles=5, market_caps=caps).value_weighted
    assert vw.iloc[0]["Q5"] == pytest.approx((0.08 * 1 + 0.09 * 3) / 4)


def test_performance_states_its_assumptions_numerically():
    r = pd.Series([0.01, -0.02, 0.03, 0.0], index=pd.date_range("2026-01-02", periods=4, freq="B"))
    p = st.performance(r, 252)
    assert p["cumulative_return"] == pytest.approx(1.01 * 0.98 * 1.03 - 1)
    assert p["max_drawdown"] == pytest.approx(0.02)
    assert p["sharpe"] == pytest.approx(r.mean() / r.std(ddof=1) * np.sqrt(252))


def test_ols_recovers_known_coefficients_with_hac_inference():
    rng = np.random.default_rng(42)
    n = 2000
    X = pd.DataFrame({"MKT_RF": rng.normal(0, 0.01, n), "SMB": rng.normal(0, 0.005, n),
                      "HML": rng.normal(0, 0.005, n)}, index=pd.date_range("2018-01-01", periods=n, freq="B"))
    e = np.zeros(n)
    shocks = rng.normal(0, 0.002, n)
    for i in range(n):                                            # autocorrelated errors: HAC widens the bands
        e[i] = 0.5 * (e[i - 1] if i else 0.0) + shocks[i]
    y = 0.0002 + 1.2 * X["MKT_RF"] - 0.4 * X["SMB"] + 0.3 * X["HML"] + e
    res = st.ols(y, X, hac=True)
    coef = dict(zip(res.names, res.coef))
    assert coef["MKT_RF"] == pytest.approx(1.2, abs=0.03) and coef["SMB"] == pytest.approx(-0.4, abs=0.06)
    assert coef["HML"] == pytest.approx(0.3, abs=0.06) and coef["alpha"] == pytest.approx(0.0002, abs=0.0002)
    assert res.n == n and res.df == n - 4 and res.hac_lags == st.newey_west_lags(n)
    assert res.se[0] > res.se_classical[0] * 1.3                 # positive autocorrelation -> larger HAC errors
    assert all(lo < c < hi for lo, c, hi in zip(res.ci_low, res.coef, res.ci_high))
    assert res.r2 > 0.9 and res.adj_r2 < res.r2
    assert res.diagnostics["durbin_watson"] < 1.5                 # the autocorrelation is visible


def test_ols_uses_only_aligned_rows_and_warns_on_short_samples():
    idx = pd.date_range("2026-01-02", periods=12, freq="B")
    X = pd.DataFrame({"f": np.arange(12, dtype=float)}, index=idx)
    y = pd.Series(1 + 2 * np.arange(12, dtype=float), index=idx)
    y.iloc[3] = np.nan
    res = st.ols(y, X, hac=False)
    assert res.n == 11 and dict(zip(res.names, res.coef))["f"] == pytest.approx(2.0)
    assert any("short sample" in w for w in res.warnings)
    with pytest.raises(ValueError):
        st.ols(y.iloc[:2], X.iloc[:2])


def test_rolling_regression_and_compounding():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2026-01-02", periods=120, freq="B")
    X = pd.DataFrame({"m": rng.normal(0, 0.01, 120)}, index=idx)
    y = 0.5 * X["m"].where(np.arange(120) < 60, 2.0 * X["m"] / 0.5) + rng.normal(0, 1e-4, 120)
    roll = st.rolling_ols(y, X, window=30)
    assert roll["m"].iloc[0] == pytest.approx(0.5, abs=0.02) and roll["m"].iloc[-1] == pytest.approx(2.0, abs=0.02)
    assert roll.index[0] == idx[29]
    intraday = pd.Series([0.01, 0.02, -0.01], index=pd.to_datetime(["2026-01-02 10:00", "2026-01-02 15:00",
                                                                    "2026-01-05 10:00"]))
    daily = st.compound_to(intraday, "D")
    assert daily.iloc[0] == pytest.approx(1.01 * 1.02 - 1) and len(daily) == 2
