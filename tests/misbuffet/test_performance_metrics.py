"""Tests for misbuffet/engine/performance_metrics.py — no DB required."""

import unittest

from src.application.services.misbuffet.engine.performance_metrics import calculate_performance_metrics


class TestCalculatePerformanceMetrics(unittest.TestCase):

    def _flat_returns(self, n=252, daily=0.001):
        return [daily] * n

    # ------------------------------------------------------------------
    # Basic structure
    # ------------------------------------------------------------------

    def test_returns_all_keys(self):
        metrics = calculate_performance_metrics(self._flat_returns(), 100_000, 125_000)
        for key in ('total_return', 'annualized_return', 'volatility', 'sharpe_ratio',
                    'max_drawdown', 'win_rate', 'total_trading_days', 'best_day', 'worst_day'):
            self.assertIn(key, metrics)

    def test_total_trading_days(self):
        returns = self._flat_returns(n=100)
        metrics = calculate_performance_metrics(returns, 100_000, 110_000)
        self.assertEqual(metrics['total_trading_days'], 100)

    # ------------------------------------------------------------------
    # Total return
    # ------------------------------------------------------------------

    def test_total_return_positive(self):
        metrics = calculate_performance_metrics(self._flat_returns(), 100_000, 110_000)
        self.assertAlmostEqual(metrics['total_return'], 0.10, places=6)

    def test_total_return_negative(self):
        metrics = calculate_performance_metrics(self._flat_returns(), 100_000, 90_000)
        self.assertAlmostEqual(metrics['total_return'], -0.10, places=6)

    def test_total_return_zero(self):
        metrics = calculate_performance_metrics(self._flat_returns(), 100_000, 100_000)
        self.assertAlmostEqual(metrics['total_return'], 0.0, places=6)

    # ------------------------------------------------------------------
    # Win rate
    # ------------------------------------------------------------------

    def test_win_rate_all_positive(self):
        returns = [0.01] * 10
        metrics = calculate_performance_metrics(returns, 100_000, 110_000)
        self.assertAlmostEqual(metrics['win_rate'], 1.0)

    def test_win_rate_all_negative(self):
        returns = [-0.01] * 10
        metrics = calculate_performance_metrics(returns, 100_000, 90_000)
        self.assertAlmostEqual(metrics['win_rate'], 0.0)

    def test_win_rate_mixed(self):
        returns = [0.01, -0.01, 0.01, -0.01]
        metrics = calculate_performance_metrics(returns, 100_000, 100_000)
        self.assertAlmostEqual(metrics['win_rate'], 0.5)

    # ------------------------------------------------------------------
    # Best / worst day
    # ------------------------------------------------------------------

    def test_best_and_worst_day(self):
        returns = [0.05, -0.03, 0.01, 0.02, -0.01]
        metrics = calculate_performance_metrics(returns, 100_000, 104_000)
        self.assertAlmostEqual(metrics['best_day'], 0.05)
        self.assertAlmostEqual(metrics['worst_day'], -0.03)

    # ------------------------------------------------------------------
    # Volatility and Sharpe
    # ------------------------------------------------------------------

    def test_zero_volatility_gives_zero_sharpe(self):
        # Constant returns → zero std → sharpe should be 0.0 not division error
        returns = [0.001] * 252
        metrics = calculate_performance_metrics(returns, 100_000, 128_000)
        self.assertEqual(metrics['sharpe_ratio'], 0.0)

    def test_sharpe_positive_for_positive_returns(self):
        import numpy as np
        rng = [0.002, -0.001, 0.003, 0.001, -0.0005] * 50
        metrics = calculate_performance_metrics(rng, 100_000, 115_000)
        # With net positive drift sharpe should be positive
        self.assertGreater(metrics['sharpe_ratio'], 0)

    # ------------------------------------------------------------------
    # Max drawdown
    # ------------------------------------------------------------------

    def test_max_drawdown_non_positive(self):
        returns = [0.05, -0.1, 0.03, -0.02, 0.01]
        metrics = calculate_performance_metrics(returns, 100_000, 98_000)
        self.assertLessEqual(metrics['max_drawdown'], 0)

    def test_max_drawdown_zero_for_monotone_up(self):
        returns = [0.01] * 10
        metrics = calculate_performance_metrics(returns, 100_000, 110_000)
        self.assertAlmostEqual(metrics['max_drawdown'], 0.0, places=6)

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_empty_returns_returns_error(self):
        result = calculate_performance_metrics([], 100_000, 100_000)
        self.assertIn('error', result)

    def test_single_return(self):
        metrics = calculate_performance_metrics([0.05], 100_000, 105_000)
        self.assertNotIn('error', metrics)
        self.assertEqual(metrics['total_trading_days'], 1)


if __name__ == '__main__':
    unittest.main()
