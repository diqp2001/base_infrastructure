"""spatio_temporal_momentum_project_10m_live: the 10m strategy wired to build_live_stack (no IBKR, no database)."""

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare

from src.application.managers.project_managers.spatio_temporal_momentum_project_10m import config as backtest_cfg
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live import config as live_cfg
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.backtesting import (
    live_runner as runner_module,
)
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.backtesting.base_project_algorithm import (
    Algorithm,
)
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.backtesting.live_runner import (
    LiveRunner,
)
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.data.price_ingestion import (
    BarHistoryUpdater,
)
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.project_manager import (
    session_window,
)


# ---------------------------------------------------------------- config: same strategy, separate book and data
def test_same_research_parameters_as_the_10m_backtest():
    live, research = live_cfg.get_config(), backtest_cfg.get_config()
    for key in ("features", "model", "prediction_horizon", "bar_minutes", "artifact_selection"):
        assert live["stm"][key] == research["stm"][key], key
    assert live["stm"]["training"] == research["stm"]["training"]
    assert live["training_window"] == research["training_window"]
    assert live_cfg.STM_TICKERS == backtest_cfg.STM_TICKERS
    assert live["bar_size_setting"] == research["bar_size_setting"]


def test_book_signals_models_and_results_are_kept_apart_from_the_backtest():
    live, research = live_cfg.get_config(), backtest_cfg.get_config()
    assert live["Portfolio"]["name"] != research["Portfolio"]["name"]
    assert live["results_dir"] != research["results_dir"]
    assert live["stm"]["artifact_dir"] != research["stm"]["artifact_dir"]
    assert live["stm"]["universe"]["name"] != research["stm"]["universe"]["name"]
    assert live_cfg.STM_SIGNAL_FACTOR_NAME != backtest_cfg.STM_SIGNAL_FACTOR_NAME
    assert live_cfg.STM_ML_MODEL_PREFIX != backtest_cfg.STM_ML_MODEL_PREFIX
    live_names = {f["name"] for f in live["factors"]}
    assert not live_names & {f["name"] for f in research["factors"]}


def test_paper_by_default_and_no_decision_at_the_close():
    live = live_cfg.get_config()["live"]
    assert live["account"].startswith("D") and not live["paper_bar_prices"]      # paper account, real-time quotes
    assert live["client_id"] != 1                                                # data connection uses 1
    assert live_cfg.get_config()["config_interval"]["session_end"] == "15:50"


# ---------------------------------------------------------------- session window
def _calendar(*days, early=None):
    def sessions(start, end):
        return [(d, datetime.combine(d, datetime.min.time()).replace(hour=13 if d == early else 16))
                for d in days if start <= d <= end]
    return sessions


CFG = live_cfg.get_config()
THU, FRI, MON = date(2026, 10, 29), date(2026, 10, 30), date(2026, 11, 2)


@pytest.mark.parametrize("now, expected", [
    (datetime(2026, 10, 29, 8, 0), (datetime(2026, 10, 29, 9, 40), datetime(2026, 10, 29, 15, 50))),
    (datetime(2026, 10, 29, 12, 31), (datetime(2026, 10, 29, 12, 40), datetime(2026, 10, 29, 15, 50))),
    (datetime(2026, 10, 29, 15, 50, 5), (datetime(2026, 10, 29, 15, 50), datetime(2026, 10, 29, 15, 50))),
    (datetime(2026, 10, 29, 16, 30), (datetime(2026, 10, 30, 9, 40), datetime(2026, 10, 30, 15, 50))),
])
def test_session_window(now, expected):
    assert session_window(now, CFG, calendar=_calendar(THU, FRI, MON)) == expected


def test_session_window_after_friday_close_is_monday_and_early_closes_end_earlier():
    assert session_window(datetime(2026, 10, 30, 17, 0), CFG, calendar=_calendar(THU, FRI, MON))[0] == \
        datetime(2026, 11, 2, 9, 40)
    assert session_window(datetime(2026, 10, 29, 9, 0), CFG, calendar=_calendar(THU, early=THU))[1] == \
        datetime(2026, 10, 29, 12, 50)


def test_the_nyse_calendar_is_read_in_exchange_time():
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.project_manager import (
        _nyse_sessions,
    )
    sessions = dict(_nyse_sessions(date(2026, 11, 25), date(2026, 11, 27)))
    assert sessions[date(2026, 11, 25)] == datetime(2026, 11, 25, 16, 0)
    assert sessions[date(2026, 11, 27)] == datetime(2026, 11, 27, 13, 0)           # day after Thanksgiving
    assert date(2026, 11, 26) not in sessions                                      # Thanksgiving


# ---------------------------------------------------------------- bar updater on exchange time
def test_the_bar_updater_counts_new_bars_in_exchange_time():
    now = {"t": pd.Timestamp("2026-10-29 10:12")}
    updater = BarHistoryUpdater(Mock(), ["JPM"], "2026-10-01", now=lambda: now["t"])
    updater._import = Mock(return_value={"JPM": True})
    updater.mark_imported()
    assert updater(pd.Timestamp("2026-10-29 10:10")) is None                     # 10:10 already imported
    now["t"] = pd.Timestamp("2026-10-29 10:20:20")
    assert updater(pd.Timestamp("2026-10-29 10:20")) == {"JPM": True}            # new bar 10:10-10:20
    updater._import.assert_called_once_with("1 D")


# ---------------------------------------------------------------- algorithm: live only, order path first
def _algorithm(live=True, factory=None):
    algorithm = Algorithm()
    algorithm.set_live_mode(live)
    algorithm.project_config = live_cfg.get_config()
    algorithm._entity_service = SimpleNamespace(repository_factory=Mock())
    algorithm._market_data_service, algorithm._market_data_history_service = Mock(), Mock()
    algorithm.register_portfolio = Mock(return_value=SimpleNamespace(id=7, name="book"))
    algorithm.live_stack_factory = factory
    algorithm.trainer = Mock()
    return algorithm


def test_the_algorithm_refuses_to_run_as_a_backtest():
    algorithm = _algorithm(live=False, factory=Mock())
    with pytest.raises(RuntimeError, match="live book"):
        algorithm.initialize()
    algorithm.register_portfolio.assert_not_called()


def test_the_algorithm_builds_the_live_stack_before_the_cycle():
    order = []
    algorithm = _algorithm(factory=lambda a: order.append("stack") or "STACK")
    cycle = SimpleNamespace(ticker_to_entity={"JPM": 1, "BAC": 2}, config=SimpleNamespace(bar_minutes=10),
                            train_now=lambda t: order.append(("pretrain", t.minute % 10)) or 7)
    algorithm.trainer.build_cycle.side_effect = lambda **kw: order.append("cycle") or cycle
    algorithm.initialize()
    # order path first, then the cycle, then one training on the history known now (bar-aligned time)
    assert order == ["stack", "cycle", ("pretrain", 0)] and algorithm.live_stack == "STACK" and algorithm.cycle is cycle
    assert algorithm.universe == {CompanyShare: ["JPM", "BAC"]}          # the engine slices only resolved tickers
    assert algorithm.register_portfolio.call_args.kwargs["portfolio_config"]["name"] == \
        "Spatio_Temporal_Momentum_10m_Live_Portfolio"


def test_the_algorithm_refuses_without_a_live_stack_or_when_it_fails():
    algorithm = _algorithm(factory=None)
    with pytest.raises(RuntimeError, match="live stack factory"):
        algorithm.initialize()
    algorithm = _algorithm(factory=Mock(side_effect=PermissionError("account U1 is a live account")))
    with pytest.raises(PermissionError):
        algorithm.initialize()
    algorithm.trainer.build_cycle.assert_not_called()


# ---------------------------------------------------------------- runner
def test_the_runner_refuses_backtests():
    with pytest.raises(RuntimeError, match="live deployment"):
        LiveRunner(Mock()).run_backtest({})


def _runner_with_stack(monkeypatch, recovery_ok):
    stack = Mock()
    stack.recovery.ensure.return_value = recovery_ok
    stack.recovery.last_report.summary.return_value = "1 blocking discrepancy"
    built = Mock(return_value=stack)
    monkeypatch.setattr(runner_module, "build_live_stack", built)
    runner = LiveRunner(Mock())
    runner.config, runner.broker = live_cfg.get_config(), "BROKER"
    runner.model_trainer = SimpleNamespace(stm_config=SimpleNamespace(universe=SimpleNamespace(tickers=["JPM"])))
    algorithm = SimpleNamespace(_unified_portfolio_manager="UPM", repository_factory="FACTORY", bar_price="BARS")
    return runner, algorithm, stack, built


def test_the_stack_is_built_for_the_configured_paper_account(monkeypatch):
    runner, algorithm, stack, built = _runner_with_stack(monkeypatch, recovery_ok=True)
    assert runner.build_stack(algorithm) is stack
    broker, upm, factory, cfg = built.call_args.args
    assert (broker, upm, factory) == ("BROKER", "UPM", "FACTORY")
    assert cfg.account == "DUR314497" and cfg.strategy == "STM_10M_BANKS" and not cfg.paper_bar_prices
    assert cfg.limits.max_order_notional == 5_000.0
    assert cfg.limits.max_net_exposure == 12_500.0                     # P.07.08: net exposure capped at half
    assert cfg.limits.max_quote_age_seconds == 60
    stack.subscribe.assert_called_once_with(["JPM"])        # B2: real-time quotes price the orders
    assert built.call_args.kwargs["bar_prices"] is None
    assert algorithm.shortable is not None


def test_paper_bar_prices_price_on_the_imported_bars_without_quotes(monkeypatch):
    runner, algorithm, stack, built = _runner_with_stack(monkeypatch, recovery_ok=True)
    monkeypatch.setitem(runner.config["live"], "paper_bar_prices", True)
    runner.build_stack(algorithm)
    stack.subscribe.assert_not_called()                     # no quotes, the gate prices on bars
    assert built.call_args.kwargs["bar_prices"] == "BARS"     # ... the bars the step imported, not new IBKR requests


def test_a_blocked_start_up_recovery_stops_the_run(monkeypatch):
    runner, algorithm, stack, _ = _runner_with_stack(monkeypatch, recovery_ok=False)
    with pytest.raises(RuntimeError, match="1 blocking discrepancy"):
        runner.build_stack(algorithm)
    stack.shutdown.assert_called_once()


# ---------------------------------------------------------------- preload: only what has closed is "complete"
def test_live_preload_registers_coverage_only_up_to_the_last_closed_bar(monkeypatch, tmp_path):
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.models import (
        model_trainer as trainer_module,
    )
    seen = {}

    class Preload:
        def __init__(self, *a, **k):
            pass

        def preload(self, series, start, end):
            seen["end"] = end
            return []

        def to_frame(self, results):
            return pd.DataFrame()

    monkeypatch.setattr(trainer_module, "BacktestDataPreloadService", Preload)
    trainer = trainer_module.STMModelTrainer.__new__(trainer_module.STMModelTrainer)
    trainer.config = {**live_cfg.get_config(), "price_history_start": "2026-10-01",
                      "backtest_end": datetime(2026, 10, 29, 15, 50), "results_dir": str(tmp_path)}
    trainer.stm_config = live_cfg.build_stm_configuration(trainer.config)
    trainer.logger = Mock()
    updater = Mock(tickers=["JPM"])
    trainer.preload(Mock(), updater, now=pd.Timestamp("2026-10-29 12:38"))
    # at 12:38 the 12:30 bar is still open: coverage ends at the 12:20 bar, later bars come from IBKR as they close
    assert seen["end"] == pd.Timestamp("2026-10-29 12:20")
    updater.mark_imported.assert_called_once_with(through=pd.Timestamp("2026-10-29 12:20"))


# ---------------------------------------------------------------- before_step: import the closed bar, then read locally
def test_before_step_imports_the_new_bar_and_extends_the_coverage():
    from src.application.services.data.entities.factor import preloaded_coverage
    preloaded_coverage.clear()
    try:
        preloaded_coverage.register(5, 1, datetime(2026, 10, 1), datetime(2026, 10, 29, 13, 0))
        algorithm = Algorithm()
        algorithm.cycle = SimpleNamespace(data_updater=Mock(return_value={"JPM": True, "BAC": False}),
                                          reader=Mock(load_close_panel=Mock(return_value=pd.DataFrame())),
                                          history_service=Mock(), ticker_to_entity={"JPM": 1},
                                          config=SimpleNamespace(bar_minutes=10))
        step = datetime(2026, 10, 29, 13, 20)
        assert not preloaded_coverage.covers(5, 1, step)
        algorithm.before_step(step)
        algorithm.cycle.data_updater.assert_called_once_with(step)
        assert preloaded_coverage.covers(5, 1, step)                    # slice / valuation / pricing read locally
        assert not preloaded_coverage.covers(5, 1, datetime(2026, 10, 29, 13, 30))
    finally:
        preloaded_coverage.clear()


# ---------------------------------------------------------------- gate prices = the bars the step imported
def test_the_gate_prices_on_the_newest_stored_bar_dated_at_its_real_close():
    algorithm = Algorithm()
    algorithm.config = live_cfg.get_config()
    closes = pd.DataFrame({"JPM": [300.0, 301.5], "BAC": [52.0, None]},
                          index=pd.to_datetime(["2026-10-29 13:30", "2026-10-29 13:40"]))
    reader = Mock()
    reader.load_close_panel.return_value = closes
    history = Mock()
    algorithm.cycle = SimpleNamespace(data_updater=Mock(return_value={"JPM": True, "BAC": True}), reader=reader,
                                      history_service=history, ticker_to_entity={"JPM": 1, "BAC": 2},
                                      config=SimpleNamespace(bar_minutes=10))
    algorithm.before_step(datetime(2026, 10, 29, 14, 0))
    history.set_frontier.assert_called_with(datetime(2026, 10, 29, 14, 0))           # reads through the frontier
    jpm, bac, wfc = algorithm.bar_price("JPM"), algorithm.bar_price("BAC"), algorithm.bar_price("WFC")
    # IBKR served the 13:40 bar at 14:00 (no real-time data): dated 13:50 New York, not 14:00
    assert jpm.price == 301.5 and jpm.as_of == pd.Timestamp("2026-10-29 17:50", tz="UTC")
    assert bac.price == 52.0 and bac.as_of == pd.Timestamp("2026-10-29 17:40", tz="UTC")
    assert wfc.price is None and wfc.unusable_reason


def test_bar_prices_are_refused_outside_paper_bar_mode():
    from src.application.services.misbuffet.live.live_stack import LiveStackConfig, build_live_stack
    from src.domain.entities.finance.order.pre_trade_risk import RiskLimits
    client = Mock()
    client.is_connected.return_value = True
    client.get_managed_accounts.return_value = ["DUR314497"]
    with pytest.raises(ValueError, match="paper_bar_prices"):
        build_live_stack(SimpleNamespace(ib_connection=client), Mock(), Mock(),
                         LiveStackConfig(account="DUR314497", strategy="S", limits=RiskLimits()),
                         bar_prices=lambda s: None)


# ---------------------------------------------------------------- shortable inventory (IBKR short-stock file)
SHORTSTOCK = """#BOF|2026.10.29|14:07:45
#SYM|CUR|NAME|CON|ISIN|REBATERATE|FEERATE|AVAILABLE|FIGI|
BAC|USD|BANK OF AMERICA CORP|1|X|3.6300|0.2500|>10000000|F|
GS|USD|GOLDMAN SACHS GROUP INC|2|X|3.6179|0.2621|2200000|F|
HTB|USD|HARD TO BORROW INC|3|X|-20.0|23.88|0|F|
GS|CAD|GOLDMAN CDR|4|X|1|1|0|F|
"""


def test_the_short_stock_file_is_parsed_per_us_symbol():
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.data.shortable_inventory import (
        parse_shortstock_file,
    )
    inv = parse_shortstock_file(SHORTSTOCK)
    assert inv == {"BAC": (10_000_000, 0.25, 3.63), "GS": (2_200_000, 0.2621, 3.6179), "HTB": (0, 23.88, -20.0)}


def test_shorts_of_names_ibkr_cannot_lend_are_cut_and_the_file_is_read_once_a_day():
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.data.shortable_inventory import (
        ShortableInventory,
    )
    fetch = Mock(return_value=SHORTSTOCK)
    inv = ShortableInventory(fetch=fetch, today=lambda: date(2026, 10, 29))
    weights, cut = inv.restrict({"BAC": -0.1, "HTB": -0.05, "ZZZ": -0.02, "GS": 0.1, "NEW": 0.03})
    assert weights == {"BAC": -0.1, "HTB": 0.0, "ZZZ": 0.0, "GS": 0.1, "NEW": 0.03}     # longs never cut
    assert cut == {"HTB": 0, "ZZZ": 0}
    inv.restrict({"BAC": -0.1})
    fetch.assert_called_once()


def test_without_any_short_stock_file_nothing_is_restricted():
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.data.shortable_inventory import (
        ShortableInventory,
    )
    inv = ShortableInventory(fetch=Mock(side_effect=OSError("ftp down")), today=lambda: date(2026, 10, 29))
    assert inv.restrict({"BAC": -0.1}) == ({"BAC": -0.1}, {})


# ---------------------------------------------------------------- operator commands (database only)
@pytest.fixture
def sqlite_factory():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    engine = create_engine("sqlite://")
    ModelBase.metadata.create_all(engine)
    with Session(engine) as session:
        yield RepositoryFactory(session)


def test_ops_kill_reduce_only_and_enable_change_what_the_session_reads(sqlite_factory, monkeypatch):
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live import ops
    from src.application.services.misbuffet.brokers.trading_controls import TradingControlsService
    monkeypatch.setenv("STM_OPERATOR", "philippe")
    lines = []
    controls = TradingControlsService(sqlite_factory.trading_control_local_repo)
    mode = lambda: controls.mode_for("DUR314497", "STM_10M_BANKS")[0].value  # noqa: E731
    assert mode() == "enabled"
    assert ops.main(["reduce-only", "end of day"], factory=sqlite_factory, out=lines.append) == 0
    assert mode() == "reduce_only"
    ops.main(["kill", "test"], factory=sqlite_factory, out=lines.append)
    ops.main(["enable", "strategy back"], factory=sqlite_factory, out=lines.append)
    assert mode() == "disabled"                                    # the global kill stays in force
    ops.main(["unkill", "test over"], factory=sqlite_factory, out=lines.append)
    assert mode() == "enabled"
    assert controls.history()[-1].changed_by == "philippe"
    assert any("trading: ENABLED" in line for line in lines)


def test_ops_resolve_records_the_reason_and_the_operator(sqlite_factory, monkeypatch):
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live import ops
    from src.domain.entities.finance.order.discrepancy import Discrepancy, DiscrepancyKind
    monkeypatch.setenv("STM_OPERATOR", "philippe")
    repo = sqlite_factory.trading_discrepancy_local_repo
    d = repo.add(Discrepancy(kind=DiscrepancyKind.EXTERNAL_EXECUTION, key="E.1", detail="manual sell", blocking=True,
                             detected_at=datetime(2026, 10, 29, 15, 0)))
    lines = []
    assert ops.main(["resolve", str(d.id), "manual trade in TWS, books adjusted"], factory=sqlite_factory,
                    out=lines.append) == 0
    assert repo.get_open() == [] and "philippe" in repo.get_by_id(d.id).resolution
    assert ops.main(["resolve", "999", "x"], factory=sqlite_factory, out=lines.append) == 1


def test_a_blocked_recovery_after_a_reconnect_does_not_stop_the_session(monkeypatch):
    runner, algorithm, stack, _ = _runner_with_stack(monkeypatch, recovery_ok=False)
    assert runner.build_stack(algorithm, at_start=False) is stack       # orders refused by set_holdings, run goes on
    stack.shutdown.assert_not_called()


def test_before_step_checks_the_connections_first():
    algorithm = Algorithm()
    order = []
    algorithm.live_stack = "OLD"
    algorithm.connection_guard = SimpleNamespace(check=lambda s: order.append(("guard", s)) or "NEW")
    algorithm.cycle = SimpleNamespace(data_updater=None)
    algorithm.before_step(datetime(2026, 10, 30, 9, 40))
    assert order == [("guard", "OLD")] and algorithm.live_stack == "NEW"


def test_the_live_config_pretrains_and_tolerates_late_bars():
    cfg = live_cfg.get_config()
    assert cfg["pretrain_before_first_decision"] and cfg["missing_asset_patience"] == 3
    assert cfg["retrain_every_days"] == 2            # the morning pre-training is the daily one (date-only metadata)
    assert backtest_cfg.get_config().get("missing_asset_patience", 0) == 0          # backtests unchanged


# ---------------------------------------------------------------- P.06.05: decision -> orders
def test_a_decision_is_recorded_before_its_orders_and_stamps_them():
    algorithm = Algorithm()
    algorithm.config = live_cfg.get_config()
    algorithm.initialized = True
    seen = []
    ledger = SimpleNamespace(current_decision_id=None)
    algorithm.live_stack = SimpleNamespace(ledger=ledger)

    class Decisions:
        def add(self, d):
            seen.append(d)
            d.id = 41
            return d
    algorithm._entity_service = SimpleNamespace(repository_factory=SimpleNamespace(
        trading_decision_local_repo=Decisions()))
    result = SimpleNamespace(session=pd.Timestamp("2026-10-30 09:30"), retrained=False, weights={"JPM": -0.1},
                             note="", artifact_id=None)
    algorithm.cycle = SimpleNamespace(step=lambda t: result,
                                      artifact_store=SimpleNamespace(select=lambda s: (SimpleNamespace(id=39), {})))
    upm = Mock()
    upm.set_holdings.side_effect = lambda *a, **k: seen.append(("orders sent with", ledger.current_decision_id)) or {}
    algorithm._unified_portfolio_manager = upm
    algorithm._update_portfolio_value = algorithm._update_performance_tracking = lambda data: None
    algorithm.on_data(SimpleNamespace(time=datetime(2026, 10, 30, 9, 40)))
    decision = seen[0]
    assert (decision.strategy, decision.account, decision.targets, decision.artifact_id) == \
        ("STM_10M_BANKS", "DUR314497", {"JPM": -0.1}, 39)
    assert seen[1] == ("orders sent with", 41) and ledger.current_decision_id is None    # reset afterwards


def test_the_decision_column_is_added_to_an_existing_broker_orders_table(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, inspect, text
    from src.infrastructure.database import base_factory
    url = f"sqlite:///{tmp_path / 'old.sqlite'}"
    with create_engine(url).begin() as conn:                     # a broker_orders table from before P.06.05
        conn.execute(text("CREATE TABLE broker_orders (id INTEGER PRIMARY KEY, order_id INTEGER)"))
    monkeypatch.setattr(base_factory, "get_database_url", lambda db_type: url)
    base_factory.BaseFactory("sqlite")                           # runs create_all + _migrate_schema
    cols = {c["name"] for c in inspect(create_engine(url)).get_columns("broker_orders")}
    assert "decision_id" in cols
