"""
Every factor whose calculate() is wired to the resolution service (see test_factor_dependency_wiring.py)
is resolved end to end through FactorValueResolutionService on a seeded SQLite market (factor_world.py):

  test_calculate_receives_every_dependency   one test per factor, fresh world each time —
      calculate() is called, every declared dependency arrives non-empty, the result is a finite number
  test_value_*                               independent checks of the values that have a closed form
  test_history_factor_receives_a_close_history
                                             price-history factors (returns, MAs, momentum, risk, ...)
                                             must receive a close series, not one bar's fields

Known failures are strict xfails with the reason, so a fix flips them.
"""

import math
from datetime import date

import pytest

from src.domain.entities.factor.dependency_spec import DependencySpec
from tests.component.factor_context.factor_catalog import (
    declared_dependencies, dependency_name, factor_classes, instantiate,
)
from tests.component.factor_context.factor_world import T, FactorWorld

pytestmark = pytest.mark.filterwarnings("ignore")

KNOWN = {
    "CompanyShareLGBMCSQuintileRankMomentumFactor": "its inputs are price-history factors (returns, Sharpe, MAs, ...) "
                                                    "that resolve to None without a lookback (see "
                                                    "test_history_factor_receives_a_close_history)",
    "CompanySharePortfolioEqualWeightReturnFactor": "its dependency CompanySharePriceReturnFactor cannot be built "
                                                    "with defaults, so it is never resolved",
    "CompanySharePortfolioPriceReturnFactor": "depends on raw CompanySharePortfolioFactor observations "
                                              "(portfolio prices) that nothing produces",
    "CompanySharePortfolioOptionImpliedDivYieldFactor": "depends on CompanyShareOptionImpliedDivYieldFactor, "
                                                        "which never resolves (string dependency on the raw "
                                                        "CompanyShareOptionFactor)",
    "CompanySharePortfolioOptionImpliedVolFactor": "depends on CompanyShareOptionImpliedCorrFactor, which never "
                                                   "resolves (string dependency on the raw CompanyShareOptionFactor)",
}
# factors that delegate to an injected model provider: the test injects a stand-in and checks the
# service hands the dependencies to it
ML_FACTORS = {"CompanyShareLGBMCSQuintileRankMomentumFactor", "CompanyShareSpatioTemporalMomentumFactor",
              "CompanyShareOptionImpliedVolMlFactor"}


def _wired():
    from unittest.mock import MagicMock, patch

    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    from tests.component.factor_context.test_factor_dependency_wiring import problems_of
    with patch.object(RepositoryFactory, "create_ibkr_client", return_value=None):
        factory = RepositoryFactory(MagicMock())
        return [(name, cls) for name, cls in factor_classes() if not problems_of(cls, factory)]


WIRED = _wired()


HISTORY_MODULES = {"company_share_return_factors", "company_share_ma_factors", "company_share_momentum_change_factors",
                   "company_share_trend_factors", "company_share_risk_factors", "company_share_drawdown_factors",
                   "company_share_composite_momentum_factors"}


def is_history_factor(cls):
    """Return / MA / momentum / slope / risk / drawdown signal computed from raw CompanyShareFactor prices."""
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
        CompanyShareFactor,
    )
    deps = declared_dependencies(instantiate(cls))
    return (cls.__module__.rsplit(".", 1)[-1] in HISTORY_MODULES and len(deps) == 1
            and isinstance(deps[0], DependencySpec) and deps[0].factor_type is CompanyShareFactor)


HISTORY = [(n, c) for n, c in WIRED if is_history_factor(c)]


class StandInProvider:
    """Model provider double: records what the factor hands to the model and returns a fixed signal."""

    def __init__(self):
        self.calls = []

    def predict(self, dependencies, entity, target_date):
        self.calls.append((dict(dependencies), entity, target_date))
        return 0.42


@pytest.fixture
def world():
    w = FactorWorld()
    yield w
    w.close()


def delivered(captured, name):
    value = (captured or {}).get(name)
    return value is not None and value != []


@pytest.mark.parametrize("cls", [pytest.param(c, id=n, marks=[pytest.mark.xfail(strict=True, reason=KNOWN[n])]
                                              if n in KNOWN else []) for n, c in WIRED
                                 if not is_history_factor(c)])     # history factors: see the tests at the end
def test_calculate_receives_every_dependency(world, cls):
    entity = world.entity_for(cls.__name__)
    assert entity is not None, "no entity for this factor in the test world"
    provider = StandInProvider() if cls.__name__ in ML_FACTORS else None
    value, captured = world.resolve(cls, entity, provider=provider)

    assert captured is not None, "calculate() was never called"
    missing = [dependency_name(d) for d in declared_dependencies(instantiate(cls))
               if not delivered(captured, dependency_name(d))]
    assert missing == [], f"dependencies not delivered to calculate(): {missing}"
    assert value is not None and math.isfinite(value), f"no usable value: {value!r}"
    if provider is not None:
        [(deps, model_entity, model_date)] = provider.calls
        assert (value, model_entity.id, model_date) == (0.42, entity.id, T)


# ---- independent values -----------------------------------------------------------------------

def factor(name):
    return dict(factor_classes())[name]


def value_of(world, name, **kwargs):
    value, _ = world.resolve(factor(name), world.entity_for(name), **kwargs)
    return value


def fresh(name):
    """Value of `name` resolved alone in a new world (no state shared with other checks)."""
    w = FactorWorld()
    try:
        return value_of(w, name)
    finally:
        w.close()


def test_value_share_price_chain_is_the_last_closed_bar(world):
    last = world.closes["AAPL"][-1]                                     # Friday's bar values Monday 16:00
    assert fresh("CompanyShareMidPriceFactor") == pytest.approx(last)
    assert fresh("CompanyShareValueFactor") == pytest.approx(last)


def test_value_holdings_and_portfolios(world):
    aapl, msft = 10 * world.closes["AAPL"][-1], 5 * world.closes["MSFT"][-1]
    cash = world.p.cash()
    assert value_of(world, "CompanySharePortfolioHoldingValueFactor") == pytest.approx(aapl)
    assert value_of(world, "CompanySharePortfolioValueFactor") == pytest.approx(aapl + msft)
    assert value_of(world, "CompanySharePortfolioPortfolioHoldingValueFactor") == pytest.approx(aapl + msft)
    assert value_of(world, "CurrencyPortfolioHoldingValueFactor") == pytest.approx(cash)
    assert value_of(world, "CurrencyPortfolioValueFactor") == pytest.approx(cash)
    assert value_of(world, "CurrencyPortfolioPortfolioHoldingValueFactor") == pytest.approx(cash)


def test_value_main_portfolio_sums_cash_shares_and_options(world):
    total = value_of(world, "PortfolioValueFactor")                     # builds the option sub-portfolio too
    options = 2 * 8.0                                                   # quantity x option value (see multiplier gap)
    expected = world.p.cash() + 10 * world.closes["AAPL"][-1] + 5 * world.closes["MSFT"][-1] + options
    assert total == pytest.approx(expected)


def test_value_option_holding_is_quantity_times_option_value(world):
    assert value_of(world, "CompanyShareOptionPortfolioHoldingValueFactor") == pytest.approx(2 * 8.0)
    assert value_of(world, "CompanyShareOptionPortfolioValueFactor") == pytest.approx(2 * 8.0)


def test_value_rates_follow_the_dated_sofr_future(world):
    """SR3H6 close 96.25 -> R = (100 - F) / 100 = 3.75 %, through BondFuture -> Currency -> option."""
    for name, expected in (("BondFutureAnnualizedYieldFactor", 0.0375), ("CurrencyYieldFactor", 0.0375),
                           ("CompanyShareOptionRFYieldFactor", 0.0375), ("CurrencyValueFactor", 1.0)):
        assert fresh(name) == pytest.approx(expected), name


def black_scholes_call(S, K, r, sigma, t):
    d1 = (math.log(S / K) + (r + sigma * sigma / 2) * t) / (sigma * math.sqrt(t))
    n = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
    return S * n(d1) - K * math.exp(-r * t) * n(d1 - sigma * math.sqrt(t)), n(d1)


def test_value_option_mid_value_and_implied_vol_reprice_the_market(world):
    assert fresh("CompanyShareOptionMidPriceFactor") == pytest.approx(8.0)
    assert fresh("CompanyShareOptionValueFactor") == pytest.approx(8.0)
    sigma = value_of(world, "CompanyShareOptionImpliedVolFactor")
    t = (date(2026, 3, 20) - T.date()).days / 365.0
    price, _ = black_scholes_call(world.closes["AAPL"][-1], 180.0, 0.0375, sigma, t)
    assert price == pytest.approx(8.0, abs=1e-3)


def test_value_option_delta_is_n_of_d1(world):
    """From an empty store (no resolution-order dependence any more): delta = N(d1) at the implied vol."""
    delta = value_of(world, "CompanyShareOptionDeltaFactor")
    sigma = value_of(world, "CompanyShareOptionImpliedVolFactor")
    t = (date(2026, 3, 20) - T.date()).days / 365.0
    _, n_d1 = black_scholes_call(world.closes["AAPL"][-1], 180.0, 0.0375, sigma, t)
    assert delta == pytest.approx(n_d1, rel=1e-6)


@pytest.mark.parametrize("first, then", [
    ("CompanyShareMidPriceFactor", "CompanyShareValueFactor"),
    ("BondFutureAnnualizedYieldFactor", "CurrencyYieldFactor"),
    ("CompanyShareOptionMidPriceFactor", "CompanyShareOptionValueFactor"),
])
def test_a_dependency_resolved_first_does_not_block_its_dependent(world, first, then):
    """Regression: definitions were looked up by name only, so a dependency stored at its default frequency
    (mid_price 5m) was returned for a spec asking another one (1d, frequency=SELF) and never matched it.
    _create_or_get now gets or creates the definition at the requested frequency."""
    assert value_of(world, first) is not None
    assert value_of(world, then) is not None


def test_value_option_price_uses_the_option_strike_and_expiry(world):
    """Regression: the price used the factor's own K / T (K = spot, T = 1y), not the option's strike / expiry."""
    sigma = value_of(world, "CompanyShareOptionImpliedVolFactor")
    price = value_of(world, "CompanyShareOptionPriceFactor")
    t = (date(2026, 3, 20) - T.date()).days / 365.0
    expected, _ = black_scholes_call(world.closes["AAPL"][-1], 180.0, 0.0375, sigma, t)
    assert price == pytest.approx(expected, rel=1e-4)                  # == the market price it was implied from


@pytest.mark.xfail(strict=True, reason="TradeManager books option trades without the contract multiplier: "
                                       "2 contracts at 8.00 move cash by 16, not 1 600 (and the option holding "
                                       "is valued at 16)")
def test_option_trade_and_value_use_the_contract_multiplier(world):
    cash_before = world.p.cash()
    world.option_portfolio()                                            # buys 2 contracts at 8.00
    assert cash_before - world.p.cash() == pytest.approx(2 * 8.0 * 100)


# ---- price-history factors --------------------------------------------------------------------

@pytest.mark.parametrize("cls", [pytest.param(c, id=n) for n, c in HISTORY])
def test_history_factor_receives_only_close_prices(world, cls):
    """Regression: DependencySpec(CompanyShareFactor, group='price') matched open / high / low / close / volume,
    so e.g. return_1d was (volume - open) / open. The specs now name the field: name_in=['close']."""
    _, captured = world.resolve(cls, world.share["AAPL"])
    assert captured is not None, "calculate() was never called"
    prices = [float(v) for v in captured["CompanyShareFactor"]]
    assert prices and set(prices) <= set(world.closes["AAPL"]), "values other than closes were delivered"


@pytest.mark.xfail(strict=True, reason="the resolution service has no lookback: DependencySpec delivers the close "
                                       "at the target date (one value), not the trailing close series a return / "
                                       "moving average / slope / risk factor needs — those resolve to None")
@pytest.mark.parametrize("cls", [pytest.param(c, id=n) for n, c in HISTORY])
def test_history_factor_receives_a_close_history(world, cls):
    _, captured = world.resolve(cls, world.share["AAPL"])
    prices = [float(v) for v in captured["CompanyShareFactor"]]
    closes = world.closes["AAPL"]
    assert len(prices) >= 2
    assert prices == pytest.approx(closes[-len(prices):]), "not the trailing close series"


@pytest.mark.xfail(strict=True, reason="see test_history_factor_receives_a_close_history")
@pytest.mark.parametrize("name, lookback", [("CompanyShareReturn1DFactor", 1), ("CompanyShareReturn5DFactor", 5),
                                            ("CompanyShareReturn20DFactor", 20)])
def test_value_returns_over_their_window(world, name, lookback):
    closes = world.closes["AAPL"]
    assert value_of(world, name) == pytest.approx(closes[-1] / closes[-1 - lookback] - 1)


def test_catalog_split():
    """Bookkeeping: every wired factor is covered here; history factors are a subset."""
    assert len(WIRED) >= 80 and 40 <= len(HISTORY) < len(WIRED)
