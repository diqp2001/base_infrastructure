"""
Tests of market_making_SPX_call_spread_project_v2 (no database, no TWS: fakes only).

Run:  python -m unittest discover -s tests/market_making_spx_v2 -t .
"""

import json
import os
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace

from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2 import config as v2_config
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.backtesting.base_project_algorithm import (
    Algorithm,
    PortfolioGateway,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.data.factor_updater import (
    FactorUpdater,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.data.position_book import (
    PositionBook,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.project_manager import (
    MarketMakingSPXCallSpreadV2ProjectManager,
    expected_bars,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.strategy.market_making_strategy import (
    Strategy,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.strategy.trading_cycle import (
    CycleResult,
    SPXCallSpreadTradingCycle,
    bar_close,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.utils.progress import (
    MMProgressTracker,
)
from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import CompanyShareOption
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare

OPTION = "SPY   281215C00775000"
T0 = datetime(2026, 8, 5, 16, 0)


# ---------------------------------------------------------------------------- fakes
class FakePortfolio:
    def __init__(self, quantities=None):
        self.quantities = dict(quantities or {})
        self.calls = []

    def quantity(self, ticker):
        return self.quantities.get(ticker, 0)

    def set_holdings(self, targets, data=None):
        self.calls.append(targets)
        # the option entry opens a short position
        spec = targets.get(CompanyShareOption)
        if spec:
            self.quantities[spec['name']] = -2
        return {}


class FakeBook:
    """Position book whose positions depend on what the portfolio holds."""

    def __init__(self, portfolio, greeks=None):
        self.portfolio = portfolio
        self.greeks = greeks or {'delta': 0.6, 'gamma': 0.01, 'vega': 1.0, 'implied_vol': 0.2}
        self.times = []

    def load_positions(self, time):
        self.times.append(time)
        qty = self.portfolio.quantity(OPTION)
        if not qty:
            return {}
        return {'cso_holding_1': {'id': 'cso_holding_1', 'symbol': OPTION, 'size': qty, 'greeks': {},
                                  'time_to_expiry': 2.3, 'days_to_expiry': 860}}

    def market_data(self, positions, time):
        return {p['symbol']: {'greeks': dict(self.greeks), 'current_price': 12.5} for p in positions.values()}

    enrich = staticmethod(PositionBook.enrich)


class FakeStrategy:
    def __init__(self, hedge=None, error=None):
        self.hedge = hedge or {'should_hedge': False}
        self.error = error
        self.seen = None

    def manage_existing_positions(self, positions=None, market_data=None, position_market_data=None):
        self.seen = positions
        if self.error:
            return {'error': self.error}
        return {'exited_position_ids': [], 'portfolio_hedge': self.hedge}


class FakeUpdater:
    def __init__(self, fail=False):
        self.fail = fail
        self.times = []

    def update(self, time):
        self.times.append(time)
        if self.fail:
            raise RuntimeError("IBKR timeout")


class Sym:
    """Hashable stand-in for a Misbuffet Symbol (``.value`` is the ticker)."""

    def __init__(self, value):
        self.value = value


def slice_with(symbol, close, time=T0):
    return SimpleNamespace(time=time, bars={Sym(symbol): SimpleNamespace(close=close)})


def make_cycle(portfolio, strategy=None, updater=None, **kw):
    return SPXCallSpreadTradingCycle(
        strategy=strategy or FakeStrategy(), position_book=FakeBook(portfolio),
        factor_updater=updater or FakeUpdater(), option_ticker=OPTION, log=lambda m: None, **kw)


# ---------------------------------------------------------------------------- trading cycle
class TestTradingCycle(unittest.TestCase):

    def test_flat_book_enters_option_then_reads_book_after_entry(self):
        portfolio = FakePortfolio()
        strategy = FakeStrategy()
        result = make_cycle(portfolio, strategy).step(T0, slice_with("SPY", 640.0), portfolio)
        self.assertEqual(portfolio.calls, [{CompanyShareOption: {'name': OPTION, 'weight': -0.2}}])
        self.assertEqual(result.option_order, portfolio.calls[0])
        self.assertEqual(result.positions, 1)                      # entry visible to step 3
        pos = strategy.seen['cso_holding_1']
        self.assertEqual(pos['greeks']['delta'], 0.6)              # greeks merged in
        self.assertEqual(pos['current_price'], 12.5)
        self.assertIsNone(result.hedge_order)

    def test_held_option_is_not_reentered(self):
        portfolio = FakePortfolio({OPTION: -2})
        result = make_cycle(portfolio).step(T0, slice_with("SPY", 640.0), portfolio)
        self.assertEqual(portfolio.calls, [])
        self.assertIsNone(result.option_order)
        self.assertEqual(result.note, "no trade")

    def test_hedge_uses_target_delta_as_hedge_symbol_quantity(self):
        portfolio = FakePortfolio({OPTION: -2})
        hedge = {'should_hedge': True, 'target_hedge_delta': 1.2, 'portfolio_delta': -1.2,
                 'portfolio_gamma': -0.02, 'hedge_direction': 'buy'}
        result = make_cycle(portfolio, FakeStrategy(hedge)).step(T0, slice_with("SPY", 641.5), portfolio)
        self.assertEqual(portfolio.calls, [{CompanyShare: {'name': 'SPY', 'quantity': 1.2}}])
        self.assertEqual(result.hedge_spot, 641.5)
        self.assertEqual(result.portfolio_delta, -1.2)
        self.assertTrue(result.traded)

    def test_factor_failure_skips_the_bar(self):
        portfolio = FakePortfolio()
        result = make_cycle(portfolio, updater=FakeUpdater(fail=True)).step(T0, slice_with("SPY", 1), portfolio)
        self.assertIn("IBKR timeout", result.error)
        self.assertEqual(portfolio.calls, [])
        self.assertFalse(result.factors_updated)

    def test_strategy_error_is_reported_without_hedge(self):
        portfolio = FakePortfolio({OPTION: -2})
        result = make_cycle(portfolio, FakeStrategy(error="boom")).step(T0, slice_with("SPY", 1), portfolio)
        self.assertIn("boom", result.error)
        self.assertIsNone(result.hedge_order)

    def test_book_and_factors_are_read_at_the_bar_time(self):
        portfolio = FakePortfolio({OPTION: -2})
        updater = FakeUpdater()
        cycle = make_cycle(portfolio, updater=updater)
        cycle.step(T0, slice_with("SPY", 1), portfolio)
        self.assertEqual(updater.times, [T0])
        self.assertEqual(cycle.position_book.times, [T0])

    def test_real_strategy_decides_a_hedge_for_a_short_call(self):
        """The copied Strategy runs inside the cycle and returns a hedge decision structure."""
        portfolio = FakePortfolio({OPTION: -10})
        cycle = make_cycle(portfolio, Strategy(v2_config.get_config()))
        result = cycle.step(T0, slice_with("SPY", 640.0), portfolio)
        self.assertIsNone(result.error, result.error)
        self.assertIn('should_hedge', result.portfolio_hedge)
        self.assertAlmostEqual(result.portfolio_delta, 0.6 * -10)
        if result.portfolio_hedge['should_hedge']:
            self.assertEqual(list(portfolio.calls[-1]), [CompanyShare])

    def test_summary_is_json_serialisable(self):
        portfolio = FakePortfolio()
        result = make_cycle(portfolio).step(T0, slice_with("SPY", 1), portfolio)
        payload = json.loads(json.dumps(result.summary(), default=str))
        self.assertEqual(payload['option_order'], {'CompanyShareOption': {'name': OPTION, 'weight': -0.2}})

    def test_bar_close_reads_slice_and_dict(self):
        self.assertEqual(bar_close(slice_with("SPY", 5), "SPY"), 5.0)
        self.assertIsNone(bar_close(slice_with("AAPL", 5), "SPY"))
        self.assertEqual(bar_close({'bars': {"SPY": SimpleNamespace(close=7)}}, "SPY"), 7.0)


# ---------------------------------------------------------------------------- data layer
class TestFactorUpdater(unittest.TestCase):

    def _history(self):
        calls = []
        created = []

        class Repo:
            def _create_or_get(self, **kw):
                created.append(('container', kw.get('name')))
                return SimpleNamespace(id=99, name=kw.get('name'))

        mds = SimpleNamespace(
            entity_service=SimpleNamespace(repository_factory=SimpleNamespace(get_local_repository=lambda c: Repo())),
            create_entity_from_ticker_item=lambda t, c: (created.append((c.__name__, t)) or SimpleNamespace(id=len(created), ticker=t)),
        )
        history = SimpleNamespace(
            market_data_service=mds,
            set_frontier=lambda t: calls.append(('frontier', t)),
            _create_or_get_factor_value_batch=lambda **kw: calls.append(('batch', kw['date'], len(kw['entities']))),
        )
        return history, calls, created

    def test_entities_once_and_frontier_before_batch(self):
        history, calls, created = self._history()
        universe = {CompanyShare: ["AAPL", "SPY"],
                    CompanyShareOption: {"args": {"name": "BOX"}, "components": {CompanyShare: ["MSFT"]}}}
        updater = FactorUpdater(history, universe, [{'factor_entity': object()}], '8 hours', '3 D')
        self.assertEqual(len(updater.ensure_entities()), 4)
        updater.update(T0)
        updater.update(T0.replace(day=6))
        self.assertEqual(len(created), 4)                                    # created once, not per bar
        self.assertEqual(calls[0], ('frontier', T0))
        self.assertEqual(calls[1], ('batch', T0, 4))

    def test_no_factors_still_advances_frontier(self):
        history, calls, _ = self._history()
        FactorUpdater(history, {}, [], '8 hours', '3 D').update(T0)
        self.assertEqual(calls, [('frontier', T0)])


class TestPositionBook(unittest.TestCase):

    def test_reads_non_zero_option_holdings_with_dte_at_bar_time(self):
        from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_option import (
            CompanyShareOptionModel,
        )
        from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
        from src.infrastructure.models.finance.holding.company_share_option_portfolio_holding import (
            CompanyShareOptionPortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.position import PositionModel

        rows = {
            CompanyShareOptionPortfolioHoldingModel: [
                SimpleNamespace(id=1, position_id=10, company_share_option_id=5),
                SimpleNamespace(id=2, position_id=11, company_share_option_id=5),   # flat -> skipped
                SimpleNamespace(id=3, position_id=None, company_share_option_id=5),  # no position -> skipped
            ],
            PositionModel: [SimpleNamespace(id=10, quantity=-3, position_type='SHORT'),
                            SimpleNamespace(id=11, quantity=0, position_type='LONG')],
            CompanyShareOptionModel: [SimpleNamespace(id=5, expiry='20261218', strike_price=775.0)],
            FinancialAssetModel: [SimpleNamespace(id=5, symbol=OPTION)],
        }

        class Query:
            def __init__(self, items):
                self.items = items

            def all(self):
                return self.items

            def filter_by(self, id):
                return Query([r for r in self.items if r.id == id])

            def first(self):
                return self.items[0] if self.items else None

        session = SimpleNamespace(query=lambda model: Query(rows[model]))
        positions = PositionBook(factory=None, session_provider=lambda: session).load_positions(datetime(2026, 12, 8))
        self.assertEqual(list(positions), ['cso_holding_1'])
        pos = positions['cso_holding_1']
        self.assertEqual((pos['symbol'], pos['size'], pos['strikes']['long']), (OPTION, -3, 775.0))
        self.assertEqual(pos['days_to_expiry'], 10)                           # measured at the bar, not today

    def test_enrich_merges_greeks_and_price(self):
        positions = {'p': {'symbol': 'X', 'greeks': {'delta': 0.1}}}
        PositionBook.enrich(positions, {'X': {'greeks': {'gamma': 0.2}, 'current_price': 3.0}})
        self.assertEqual(positions['p']['greeks'], {'delta': 0.1, 'gamma': 0.2})
        self.assertEqual(positions['p']['current_price'], 3.0)


# ---------------------------------------------------------------------------- algorithm
class TestAlgorithm(unittest.TestCase):

    def test_on_data_delegates_to_cycle_and_tracks_progress(self):
        algo = Algorithm()
        algo.initialized = True
        upm = SimpleNamespace(_get_current_position_qty=lambda t: 0, set_holdings=lambda targets, data=None: {},
                              portfolio_repo=SimpleNamespace(session='S'))
        algo.gateway = PortfolioGateway(upm)
        seen = []
        algo.cycle = SimpleNamespace(step=lambda t, d, g: seen.append((t, g)) or CycleResult(time=t, note="no trade"))
        with tempfile.TemporaryDirectory() as tmp:
            algo.progress_tracker = MMProgressTracker(persist_path=os.path.join(tmp, "progress.json"))
            algo.progress_tracker.start("backtest", bars_total=2)
            algo.on_data(slice_with("SPY", 1))
            snap = MMProgressTracker.read_snapshot(os.path.join(tmp, "progress.json"))
        self.assertEqual(seen, [(T0, algo.gateway)])
        self.assertEqual(len(algo.cycle_results), 1)
        self.assertEqual(algo.value_history[0][0], T0)
        self.assertEqual((snap['bars_done'], snap['percent']), (1, 50.0))
        self.assertEqual(algo.gateway.session(), 'S')


# ---------------------------------------------------------------------------- config + manager
class TestConfigAndManager(unittest.TestCase):

    def test_config_keeps_strategy_but_separates_state_from_original(self):
        from src.application.managers.project_managers.market_making_SPX_call_spread_project import config as v1
        a, b = v2_config.get_config(), v1.get_config()
        for key in ('universe', 'factors', 'bar_size_setting', 'duration_str', 'backtest_end', 'config_interval'):
            self.assertEqual(a[key], b[key], key)
        # v2 starts on 24 Aug 2026 (owner's decision, 2026-10-21): IBKR has no history for the option before that date
        self.assertEqual(a['backtest_start'], '2026-08-24 16:00:00')
        self.assertNotEqual(a['project_name'], b['project_name'])
        self.assertNotEqual(a['Portfolio']['name'], b['Portfolio']['name'])
        self.assertNotEqual(a['mlflow_experiment_name'], b['mlflow_experiment_name'])
        self.assertTrue(a['results_dir'].endswith('market_making_spx_call_spread_v2'))
        self.assertEqual((a['option_entry_weight'], a['hedge_symbol']), (-0.2, 'SPY'))

    def test_expected_bars(self):
        cfg = {'backtest_start': '2026-08-03 16:00:00', 'backtest_end': '2026-08-07 16:00:00',
               'config_interval': {'custom_interval_days': 1}}
        self.assertEqual(expected_bars(cfg), 5)
        cfg['config_interval'] = {'custom_interval_minutes': 5}
        self.assertEqual(expected_bars(cfg), 5 * 78)

    def _manager(self, tmp, engine_result, cycle_results):
        cfg = dict(v2_config.get_config(), results_dir=tmp, mlflow_experiment_name='spx_v2_unittest',
                   mlflow_tracking_uri=os.path.join(tmp, 'mlruns'))
        manager = MarketMakingSPXCallSpreadV2ProjectManager(config=cfg, database_service=object())
        algorithm = SimpleNamespace(cycle=object(), cycle_results=cycle_results,
                                    value_history=[(T0, 1_000_000.0)], portfolio_value=1_000_000.0)

        def run_backtest(config):
            manager.runner.algorithm_instance = algorithm
            return engine_result
        manager.runner.run_backtest = run_backtest
        manager._start_mlflow = lambda: None
        return manager

    def test_run_writes_progress_and_results(self):
        steps = [CycleResult(time=T0, option_order={CompanyShareOption: {'name': OPTION, 'weight': -0.2}}),
                 CycleResult(time=T0, hedge_order={CompanyShare: {'name': 'SPY', 'quantity': 1.0}}),
                 CycleResult(time=T0, error="factor refresh failed: x")]
        with tempfile.TemporaryDirectory() as tmp:
            manager = self._manager(tmp, {'success': True, 'misbuffet_result': 'ok', 'execution_time': 1.0}, steps)
            out = manager.run()
            saved = json.load(open(os.path.join(tmp, 'results.json'), encoding='utf-8'))
            progress = MMProgressTracker.read_snapshot(os.path.join(tmp, 'progress.json'))
        self.assertEqual((saved['bars'], saved['option_entries'], saved['hedges']), (3, 1, 1))
        self.assertEqual(len(saved['step_errors']), 1)
        self.assertEqual(saved['portfolio_values'][0]['value'], 1_000_000.0)
        self.assertEqual(progress['status'], 'completed')
        self.assertEqual(out['summary']['bars'], 3)

    def test_engine_failure_hidden_in_summary_is_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = self._manager(tmp, {'success': True, 'misbuffet_result': '❌ Backtest failed: TWS down'}, [])
            with self.assertRaises(RuntimeError) as ctx:
                manager.run()
            progress = MMProgressTracker.read_snapshot(os.path.join(tmp, 'progress.json'))
        self.assertIn('TWS down', str(ctx.exception))
        self.assertEqual(progress['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
