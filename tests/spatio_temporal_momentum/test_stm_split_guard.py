"""P.08.03 split guard: a split-like jump in the stored closes makes the ticker not eligible (in-memory, no IBKR)."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_split_guard import (
    SplitGuardConfig,
    split_like_jumps,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_trading_cycle import STMTradingCycle
from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService
from tests.spatio_temporal_momentum.helpers import make_factory, tiny_config

GUARD = SplitGuardConfig(tolerance=0.03)
BARS = pd.date_range("2026-10-01 09:30", periods=400, freq="10min")


def panel(**jumps):
    """Random-walk closes around 50 for AAA / BBB / CCC; jumps = {ticker: (bar index, factor applied from there)}."""
    rng = np.random.default_rng(7)
    data = {t: 50 * np.exp(np.cumsum(rng.normal(0, 0.002, len(BARS)))) for t in ("AAA", "BBB", "CCC")}
    for ticker, (i, factor) in jumps.items():
        data[ticker][i:] = data[ticker][i:] * factor
    return pd.DataFrame(data, index=BARS)


def test_normal_moves_are_not_splits():
    assert split_like_jumps(panel(), GUARD) == {}


@pytest.mark.parametrize("factor,ratio", [(0.5, 2.0), (1 / 3, 3.0), (2 / 3, 1.5), (10.0, 0.1)])
def test_forward_and_reverse_splits_are_found(factor, ratio):
    jumps = split_like_jumps(panel(BBB=(250, factor)), GUARD)
    assert list(jumps) == ["BBB"] and jumps["BBB"].bar == BARS[250]
    assert jumps["BBB"].ratio == pytest.approx(ratio, rel=0.02)


def test_a_large_move_that_is_no_split_ratio_is_kept():
    assert split_like_jumps(panel(CCC=(100, 0.6)), GUARD) == {}            # -40 %: 1.67 is no split ratio


def test_gaps_in_the_series_are_skipped_not_read_as_jumps():
    closes = panel(AAA=(300, 0.5))
    closes.loc[BARS[295]:BARS[305], "AAA"] = np.nan                         # the split falls inside a gap
    assert split_like_jumps(closes, GUARD)["AAA"].ratio == pytest.approx(2.0, rel=0.02)
    assert split_like_jumps(panel(), GUARD, tickers=["AAA", "ZZZ"]) == {}


def test_no_guard_without_its_config():
    assert SplitGuardConfig.from_config(None) is None and SplitGuardConfig.from_config({}) is None
    assert SplitGuardConfig.from_config({"tolerance": 0.05}).tolerance == 0.05


def test_the_cycle_excludes_a_split_ticker_from_the_eligible_assets_and_reports_it_once():
    factory, session, engine = make_factory()
    try:
        history = MarketDataHistoryService(SimpleNamespace(entity_service=SimpleNamespace(repository_factory=factory)))
        logs = []
        cfg = tiny_config()
        cycle = STMTradingCycle(factory, cfg, history, {"AAA": 1, "BBB": 2, "CCC": 3}, history_start="2026-01-01",
                                persist=False, log=logs.append, split_guard=GUARD)
        cycle._required_rows = lambda: 10
        closes = panel(BBB=(250, 0.5))
        assert cycle._eligible(closes, BARS[-1]) == ["AAA", "CCC"]
        assert cycle._eligible(closes, BARS[-1]) == ["AAA", "CCC"]
        assert len([m for m in logs if "SPLIT GUARD" in m and "BBB" in m]) == 1          # reported once
        assert cycle._eligible(closes, BARS[200]) == ["AAA", "BBB", "CCC"]            # before the jump: eligible
        cycle.split_guard = None
        assert cycle._eligible(closes, BARS[-1]) == ["AAA", "BBB", "CCC"]
    finally:
        session.close()
        engine.dispose()


def test_both_10m_projects_switch_the_guard_on():
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m import config as research
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live import config as live
    for cfg in (research.get_config(), live.get_config()):
        assert SplitGuardConfig.from_config(cfg["split_guard"]).tolerance == 0.03
