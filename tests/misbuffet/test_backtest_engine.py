"""
Checklist section 6 — BaseBacktestRunner lifecycle and BacktestingTransactionHandler fills.

Misbuffet / the engine / the monitoring recorder are patched: nothing runs, nothing is written.
``expectedFailure`` tests name a known bug in their docstring.
"""

import logging
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from src.application.services.misbuffet.common import Symbol
from src.application.services.misbuffet.common.enums import OrderDirection, OrderStatus
from src.application.services.misbuffet.common.orders import LimitOrder, MarketOrder
from src.application.services.misbuffet.engine import base_backtest_runner
from src.application.services.misbuffet.engine.base_backtest_runner import BaseBacktestRunner
from src.application.services.misbuffet.engine.transaction_handlers import BacktestingTransactionHandler

logging.getLogger("Runner").setLevel(logging.CRITICAL)
logging.getLogger("BacktestingTransactionHandler").setLevel(logging.CRITICAL)


class Runner(BaseBacktestRunner):

    def __init__(self, setup_ok=True):
        super().__init__(database_service=Mock())
        self.setup_ok = setup_ok
        self.algorithm = object()
        self.created = 0

    def setup_components(self, config):
        return self.setup_ok

    def create_algorithm_instance(self):
        self.created += 1
        return self.algorithm


def fake_misbuffet(result=None, error=None):
    engine = Mock()
    if error:
        engine.run.side_effect = error
    else:
        engine.run.return_value = result
    launched = Mock()
    launched.start_engine.return_value = engine
    return Mock(launch=Mock(return_value=launched)), engine


class BacktestRunnerTest(unittest.TestCase):

    CONFIG = {"backtest_start": "2026-01-02", "backtest_end": "2026-02-02 16:00:00", "initial_capital": 50_000,
              "universe": ["SPY"], "project_name": "unit"}

    def setUp(self):
        recorder = MagicMock()
        recorder.start.return_value = recorder
        self.recorder = recorder
        patches = [
            patch("src.application.services.monitoring.job_tracker.JobRecorder", return_value=recorder),
            patch("src.application.services.monitoring.log_store.install_monitoring_log_handler"),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def run_with(self, runner, misbuffet):
        with patch.object(base_backtest_runner, "Misbuffet", misbuffet):
            return runner.run_backtest(dict(self.CONFIG))

    def test_success_stores_results_and_passes_the_algorithm(self):
        runner = Runner()
        misbuffet, engine = fake_misbuffet(result=Mock(summary=Mock(return_value="ok")))
        out = self.run_with(runner, misbuffet)
        self.assertTrue(out["success"])
        launcher_config = engine.run.call_args.args[0]
        self.assertIs(launcher_config.algorithm, runner.algorithm)
        self.assertFalse(launcher_config.live_mode)
        self.assertEqual(launcher_config.custom_config["initial_capital"], 50_000)
        self.assertFalse(runner.is_running)
        self.assertTrue(runner.get_backtest_status()["has_results"])
        self.assertTrue(runner.get_backtest_results()["has_results"])
        self.recorder.finish.assert_called_once_with(True, error=None)

    def test_setup_failure_never_builds_the_algorithm(self):
        runner = Runner(setup_ok=False)
        misbuffet, engine = fake_misbuffet()
        out = self.run_with(runner, misbuffet)
        self.assertFalse(out["success"])
        self.assertEqual(runner.created, 0)
        engine.run.assert_not_called()
        self.assertFalse(self.recorder.finish.call_args.args[0])

    def test_engine_error_is_reported_and_running_flag_cleared(self):
        runner = Runner()
        misbuffet, _ = fake_misbuffet(error=RuntimeError("engine exploded"))
        out = self.run_with(runner, misbuffet)
        self.assertEqual((out["success"], out["error"]), (False, "engine exploded"))
        self.assertFalse(runner.is_running)
        self.assertEqual(runner.get_backtest_results()["has_results"], False)

    def test_bad_date_fails_cleanly(self):
        runner = Runner()
        misbuffet, engine = fake_misbuffet()
        with patch.object(base_backtest_runner, "Misbuffet", misbuffet):
            out = runner.run_backtest({**self.CONFIG, "backtest_start": "05/01/2026"})
        self.assertFalse(out["success"])
        engine.run.assert_not_called()

    def test_async_refuses_a_second_run_and_stop_when_idle(self):
        runner = Runner()
        runner.is_running = True
        self.assertEqual(runner.run_backtest_async(dict(self.CONFIG))["status"], "already_running")
        runner.is_running = False
        self.assertEqual(runner.stop_backtest()["status"], "not_running")


def market(qty, ticker="SPY"):
    return MarketOrder(symbol=Symbol.create_equity(ticker), quantity=qty,
                       direction=OrderDirection.BUY if qty > 0 else OrderDirection.SELL)


class BacktestingHandlerFillTest(unittest.TestCase):

    def setUp(self):
        self.handler = BacktestingTransactionHandler()
        self.handler._fill_delay_seconds = 0
        self.algorithm = Mock()
        with patch.object(BacktestingTransactionHandler, "_start_simulation"):   # fills driven by hand
            self.handler.initialize(self.algorithm, None)

    def fills(self):
        return [c.args[0] for c in self.algorithm.on_order_event.call_args_list
                if c.args[0].status == OrderStatus.FILLED]

    def test_market_buy_fills_at_price_plus_slippage(self):
        order = market(10)
        self.handler.update_market_price(order.symbol, Decimal("200"))
        self.handler.process_order(order)
        self.handler._simulate_order_execution(order)
        fill, = self.fills()
        self.assertEqual((fill.fill_quantity, fill.fill_price), (10, Decimal("200.2")))
        self.assertEqual(order.status, OrderStatus.FILLED)

    def test_market_sell_receives_price_minus_slippage(self):
        order = market(-10)
        self.handler.update_market_price(order.symbol, Decimal("200"))
        self.handler.process_order(order)
        self.handler._simulate_order_execution(order)
        self.assertEqual(self.fills()[0].fill_price, Decimal("199.8"))

    def test_limit_buy_waits_for_its_price_and_never_pays_more(self):
        order = LimitOrder(symbol=Symbol.create_equity("SPY"), quantity=5, limit_price=Decimal("199"),
                           direction=OrderDirection.BUY)
        self.handler.update_market_price(order.symbol, Decimal("200"))
        self.handler.process_order(order)
        self.handler._simulate_order_execution(order)
        self.assertEqual(self.fills(), [])
        self.handler.update_market_price(order.symbol, Decimal("198.9"))
        self.handler._simulate_order_execution(order)
        self.assertLessEqual(self.fills()[0].fill_price, Decimal("199"))

    def test_filled_order_is_not_filled_twice(self):
        order = market(10)
        self.handler.update_market_price(order.symbol, Decimal("200"))
        self.handler.process_order(order)
        self.handler._simulate_order_execution(order)
        self.handler._simulate_order_execution(order)
        self.assertEqual(len(self.fills()), 1)

    def test_no_price_means_no_fill(self):
        order = market(10, "NOPRICE")
        self.handler.process_order(order)
        self.handler._simulate_order_execution(order)
        self.assertEqual(self.fills(), [])

    def test_fill_uses_the_price_known_when_the_order_was_placed(self):
        order = market(10)
        self.handler.update_market_price(order.symbol, Decimal("200"))
        self.handler.process_order(order)
        self.handler.update_market_price(order.symbol, Decimal("260"))     # next bar arrives first
        self.handler._simulate_order_execution(order)
        self.assertEqual(self.fills()[0].fill_price, Decimal("200.2"))


if __name__ == "__main__":
    unittest.main()
