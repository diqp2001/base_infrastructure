"""
SPX v2 — the option positions the hedge sees must carry their greeks, and a miss must be loud.

Regression for positions reaching evaluate_portfolio_delta_hedge with greeks == {}: the hedge then counts
them as delta / gamma 0 and the book looks hedged. Runs PositionBook (load_positions -> market_data ->
enrich, as SPXCallSpreadTradingCycle.step does) on the SQLite market of
tests/component/factor_context/factor_world.py: AAPL option position, USD, dated SOFR future SR3H6.
"""

import logging
import math
from datetime import datetime, timedelta

import pytest

from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2 import config as v2_config
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.data.position_book import (
    FACTOR_REPO_KEYS, PositionBook,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.strategy.market_making_strategy import (
    Strategy,
)
from src.domain.entities.finance.financial_assets.derivatives.future.bond_future import BondFuture
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.future.bond_future_repository import (
    BondFutureRepository,
)
from tests.component.factor_context.factor_catalog import factor_classes
from tests.component.factor_context.factor_world import FUTURE_SYMBOL, OPTION_SYMBOL, T, FactorWorld

GREEKS = ("delta", "gamma", "vega", "implied_vol")
BOOK_LOGGER = "PositionBook"


@pytest.fixture
def world():
    w = FactorWorld()
    w.option_portfolio()                                        # 2 contracts held -> one open position
    for key, repo_key in FACTOR_REPO_KEYS.items():              # definitions, as the v2 config creates them
        w.definition(dict(factor_classes())[repo_key])
    yield w
    w.close()


def book(w):
    return PositionBook(w.f, session_provider=lambda: w.s)


def positions_with_greeks(w, when=T):
    pb = book(w)
    positions = pb.load_positions(when)
    pb.enrich(positions, pb.market_data(positions, when))
    return positions


def warnings_about(caplog, text):
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING and text in r.getMessage()]


# ---- 1. the greeks reach the positions ---------------------------------------------------------

def test_every_position_gets_every_greek_from_an_empty_store(world):
    """Regression: delta / gamma / vega (resolved before implied vol) left implied vol unresolvable."""
    [position] = positions_with_greeks(world).values()
    assert position["symbol"] == OPTION_SYMBOL
    assert {g: math.isfinite(position["greeks"].get(g, math.nan)) for g in GREEKS} == {g: True for g in GREEKS}


def resolve_implied_vol_first(w, when=T):
    """What resolving 'implied_vol' before delta / gamma / vega in FACTOR_REPO_KEYS would do."""
    iv = dict(factor_classes())["CompanyShareOptionImpliedVolFactor"]
    option = w.f.get_local_repository("CompanyShareOption").get_by_symbol(OPTION_SYMBOL)
    return w.resolve(iv, option, when)[0]


def test_every_greek_resolves_once_implied_vol_is_resolved_first(world):
    """Either order works: implied vol first, then delta / gamma / vega."""
    assert resolve_implied_vol_first(world) == pytest.approx(0.3091, abs=1e-3)
    [position] = positions_with_greeks(world).values()
    greeks = position["greeks"]
    assert set(GREEKS) <= set(greeks) and all(math.isfinite(greeks[g]) for g in GREEKS)
    assert 0 < greeks["delta"] < 1 and greeks["gamma"] > 0 and greeks["vega"] > 0   # a long OTM call
    assert position["current_price"] == pytest.approx(8.0)


def test_greeks_are_read_at_the_bar_time(world):
    """A bar without a usable rate contract gives no greeks — never the greeks of another date."""
    resolve_implied_vol_first(world)
    later = T + timedelta(days=120)                                           # front contract then: SR3M6
    [position] = positions_with_greeks(world, later).values()
    assert "implied_vol" not in position["greeks"]


def test_every_greek_resolves_with_mid_price_already_stored_at_another_frequency(world):
    """The reported run: mid_price stored at 5m, implied vol needs company_share_value / mid_price at 1d.
    The 1d definitions are created (get or create by name AND frequency) instead of returning the 5m one."""
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_mid_price_factor import (
        CompanyShareMidPriceFactor,
    )
    d = CompanyShareMidPriceFactor()
    repo = world.f.get_local_repository("CompanyShareMidPriceFactor")
    five = repo._create_or_get(CompanyShareMidPriceFactor, d.name, group=d.group, subgroup=d.subgroup,
                               data_type=d.data_type, source=d.source, frequency="5m")
    assert five.frequency == "5m"
    [position] = positions_with_greeks(world).values()
    assert set(GREEKS) <= set(position["greeks"]), position["greeks"]
    assert {f.frequency for f in repo.get_all() if f.name == d.name} >= {"5m", "1d"}


# ---- 2. a miss is loud -------------------------------------------------------------------------

def test_missing_rate_contract_is_logged_for_every_greek(world, caplog):
    """The reported failure: the bar's SOFR contract is not stored and IBKR is unavailable."""
    from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
    world.s.query(FinancialAssetModel).filter(FinancialAssetModel.symbol == FUTURE_SYMBOL).update(
        {"symbol": "SR3Z6"})                                                  # only another contract left
    world.s.commit()
    with caplog.at_level(logging.WARNING, logger=BOOK_LOGGER):
        [position] = positions_with_greeks(world).values()
    assert position["greeks"] == {}
    for greek in GREEKS:
        assert warnings_about(caplog, f"{OPTION_SYMBOL}: {greek} did not resolve"), greek


def test_unknown_option_is_logged(world, caplog):
    with caplog.at_level(logging.WARNING, logger=BOOK_LOGGER):
        assert book(world).market_data({"p": {"symbol": "NOT AN OPTION"}}, T) == {}
    assert warnings_about(caplog, "NOT AN OPTION: not found")


def test_missing_factor_definition_is_logged(caplog):
    w = FactorWorld()
    try:
        w.option_portfolio()
        with caplog.at_level(logging.WARNING, logger=BOOK_LOGGER):
            book(w).market_data({"p": {"symbol": OPTION_SYMBOL}}, T)          # no greek definitions stored
        assert warnings_about(caplog, "No CompanyShareOptionDeltaFactor factor definition stored")
    finally:
        w.close()


# ---- 3. the configuration provides what the greeks need ----------------------------------------

@pytest.mark.xfail(strict=True, reason="the v2 universe registers only SR3Z6, but the Aug-2026 backtest window "
                                       "needs SR3U6 (front SOFR contract before 21 Sep): unless IBKR returns it "
                                       "at run time, the rate — and every greek — fails on every bar")
def test_universe_registers_the_sofr_contract_of_every_backtest_date():
    cfg = v2_config.get_config()
    start = datetime.strptime(cfg["backtest_start"], "%Y-%m-%d %H:%M:%S").date()
    end = datetime.strptime(cfg["backtest_end"], "%Y-%m-%d %H:%M:%S").date()
    needed = {BondFutureRepository.front_month_symbol("SR3", start + timedelta(days=d))
              for d in range((end - start).days + 1)}
    registered = set(v2_config.DEFAULT_CONFIG.get("universe", {}).get(BondFuture, [])
                     or cfg.get("universe", {}).get(BondFuture, []))
    assert needed <= registered, f"missing SOFR contracts: {sorted(needed - registered)}"


# ---- 4. the hedge never treats missing greeks as a hedged book ---------------------------------

@pytest.mark.xfail(strict=True, reason="evaluate_portfolio_delta_hedge reads greeks.get('delta', 0): a position "
                                       "without greeks counts as delta 0, the book looks hedged and no hedge "
                                       "is sent, with no error")
def test_a_position_without_greeks_is_reported_not_counted_as_zero_delta():
    strategy = Strategy(v2_config.get_config())
    positions = {"cso_holding_1": {"id": "cso_holding_1", "symbol": OPTION_SYMBOL, "size": -10, "greeks": {},
                                   "time_to_expiry": 0.2, "days_to_expiry": 73}}
    decision = strategy.evaluate_portfolio_delta_hedge({"spy_price": 640.0}, positions=positions)
    assert decision.get("error") or decision.get("reason") == "missing_greeks", decision
