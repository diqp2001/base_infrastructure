"""
FactorNormalizer and calculate_performance_metrics — invariants over arbitrary inputs (Hypothesis)
plus the look-ahead property of the "cross-sectional" z-score.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from src.application.services.misbuffet.data.factor_normalizer import FactorNormalizer
from src.application.services.misbuffet.engine.performance_metrics import calculate_performance_metrics

pytestmark = pytest.mark.property


@pytest.fixture(scope="module")
def normalizer():
    with patch("src.application.services.misbuffet.data.factor_normalizer.CompanyShareRepositoryLocal",
               return_value=MagicMock()):
        return FactorNormalizer(MagicMock())


values = arrays(np.float64, st.integers(3, 60), elements=st.floats(-1e6, 1e6, allow_nan=False))
non_constant = values.filter(lambda v: np.ptp(v) > 1e-6 * max(1.0, np.max(np.abs(v))))
daily_returns = st.lists(st.floats(-0.5, 0.5, allow_nan=False), min_size=2, max_size=400)


class TestNormalizationInvariants:

    @settings(max_examples=200, deadline=None)
    @given(v=non_constant)
    def test_zscore_has_zero_mean_and_unit_std(self, normalizer, v):
        z = normalizer._zscore_normalize(v)
        assert np.mean(z) == pytest.approx(0.0, abs=1e-6)
        assert np.std(z) == pytest.approx(1.0, rel=1e-6)

    @settings(max_examples=200, deadline=None)
    @given(v=non_constant, a=st.floats(0.01, 100), b=st.floats(-1e3, 1e3))
    def test_zscore_ignores_positive_affine_rescaling(self, normalizer, v, a, b):
        assert normalizer._zscore_normalize(a * v + b) == pytest.approx(normalizer._zscore_normalize(v), abs=1e-5)

    @settings(max_examples=200, deadline=None)
    @given(v=non_constant)
    def test_minmax_maps_onto_zero_one_and_keeps_order(self, normalizer, v):
        m = normalizer._minmax_normalize(v)
        assert m.min() == pytest.approx(0.0) and m.max() == pytest.approx(1.0)
        order = np.argsort(v, kind="stable")
        assert np.all(np.diff(m[order]) >= -1e-12)

    @settings(max_examples=200, deadline=None)
    @given(v=non_constant)
    def test_rank_is_within_zero_one_and_monotone(self, normalizer, v):
        r = normalizer._rank_normalize(v)
        assert r.min() == 0.0 and r.max() == 1.0
        for i in range(len(v)):
            for j in range(len(v)):
                if v[i] < v[j]:
                    assert r[i] < r[j]

    @settings(max_examples=200, deadline=None)
    @given(v=values, lo=st.floats(0.0, 0.2), hi=st.floats(0.8, 1.0))
    def test_winsorize_clips_to_the_percentiles(self, normalizer, v, lo, hi):
        w = normalizer._winsorize(v, (lo, hi))
        assert w.min() >= np.percentile(v, lo * 100) - 1e-9
        assert w.max() <= np.percentile(v, hi * 100) + 1e-9

    @pytest.mark.xfail(strict=True, reason="GAP: _apply_cross_sectional_zscore z-scores each ticker over its "
                                           "whole history (mean / std include later dates), so values at a date "
                                           "depend on the future; it is not cross-sectional either")
    def test_cross_sectional_zscore_does_not_use_future_values(self, normalizer):
        dates = pd.date_range("2026-01-01", periods=6)
        history = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], index=dates)
        extended = pd.concat([history, pd.Series([100.0], index=[dates[-1] + pd.Timedelta(days=1)])])
        early = normalizer._apply_cross_sectional_zscore({"AAA": history}, "AAA", "f")
        later = normalizer._apply_cross_sectional_zscore({"AAA": extended}, "AAA", "f")
        assert later.loc[dates] == pytest.approx(early.loc[dates])


class TestPerformanceMetricInvariants:

    @settings(max_examples=200, deadline=None)
    @given(returns=daily_returns)
    def test_bounds(self, returns):
        final = 100_000 * float(np.prod(1 + np.array(returns)))
        m = calculate_performance_metrics(returns, 100_000, final)
        assert -1.0 <= m["max_drawdown"] <= 0.0
        assert 0.0 <= m["win_rate"] <= 1.0
        assert m["volatility"] >= 0.0
        assert m["worst_day"] <= m["best_day"]
        assert m["total_trading_days"] == len(returns)

    @settings(max_examples=200, deadline=None)
    @given(returns=daily_returns)
    def test_total_return_reconciles_with_compounded_returns(self, returns):
        final = 100_000 * float(np.prod(1 + np.array(returns)))
        m = calculate_performance_metrics(returns, 100_000, final)
        assert m["total_return"] == pytest.approx(float(np.prod(1 + np.array(returns))) - 1, rel=1e-9, abs=1e-12)

    @settings(max_examples=200, deadline=None)
    @given(r=st.floats(-0.05, 0.05), n=st.integers(2, 300))
    def test_constant_returns_have_zero_volatility_and_zero_sharpe(self, r, n):
        returns = [r] * n
        m = calculate_performance_metrics(returns, 100_000, 100_000 * (1 + r) ** n)
        assert m["volatility"] == 0.0
        assert m["sharpe_ratio"] == 0.0

    @settings(max_examples=100, deadline=None)
    @given(returns=st.lists(st.floats(0.0, 0.05), min_size=2, max_size=100))
    def test_never_losing_series_has_no_drawdown(self, returns):
        m = calculate_performance_metrics(returns, 100_000, 100_000 * float(np.prod(1 + np.array(returns))))
        assert m["max_drawdown"] == 0.0
