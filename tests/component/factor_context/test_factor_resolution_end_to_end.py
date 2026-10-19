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

import contextlib
import math
import random
from datetime import date
from unittest.mock import patch

import pytest

from src.domain.entities.factor.dependency_spec import DependencySpec
from tests.component.factor_context.factor_catalog import (
    NOT_SERVICE_RESOLVABLE, declared_dependencies, dependency_name, factor_classes, instantiate,
)
from tests.component.factor_context.factor_world import T, FactorWorld

pytestmark = pytest.mark.filterwarnings("ignore")

KNOWN = {
    "CompanySharePortfolioPriceReturnFactor": "depends on raw CompanySharePortfolioFactor observations "
                                              "(portfolio prices) that nothing produces",
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
        return [(name, cls) for name, cls in factor_classes()
                if name not in NOT_SERVICE_RESOLVABLE and not problems_of(cls, factory)]


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
    with library_parameters(model_parameters(0.3)):
        value, captured = world.resolve(cls, entity, provider=provider)

    assert captured is not None, "calculate() was never called"
    missing = [dependency_name(d) for d in declared_dependencies(instantiate(cls))
               if not delivered(captured, dependency_name(d))]
    assert missing == [], f"dependencies not delivered to calculate(): {missing}"
    assert value is not None and math.isfinite(value), f"no usable value: {value!r}"
    if provider is not None:
        [(deps, model_entity, model_date)] = provider.calls
        assert (value, model_entity.id, model_date) == (0.42, entity.id, T)


# ---- option pricing models: parameters from the factor library ------------------------------

def model_parameters(sigma, paths=4000, steps=20):
    """Library parameters under which every model collapses to Black-Scholes at volatility sigma
    (no vol of vol / jumps / rate vol / skew), with a small Monte Carlo for the simulated ones."""
    mc = {"monte_carlo_paths": paths, "n_steps": steps}
    heston = dict(mc, v0=sigma * sigma, theta=sigma * sigma, kappa=1.0, xi=1e-4, rho=0.0)
    return {
        "CompanyShareOptionHestonPriceFactor": heston,
        "CompanyShareOptionHestonSLVPriceFactor": heston,
        "CompanyShareOptionBatesPriceFactor": dict(heston, lambda_j=0.0, mu_j=0.0, sigma_j=0.0),
        "CompanyShareOptionSABRPriceFactor": {"alpha": sigma, "beta": 1.0, "rho": 0.0, "nu": 0.0},
        "CompanyShareOptionHullWhitePriceFactor": dict(mc, a=0.1, sigma_r=1e-6, rho=0.0),
        "CompanyShareOptionDupireLocalVolatilityPriceFactor": dict(mc, beta=1.0),
    }


@contextlib.contextmanager
def library_parameters(by_class):
    """The factor library entries carry these model parameters (keyed by factor class name)."""
    from src.application.services.data.entities.factor.factor_library import factor_definition_config as config
    real = config.library_parameters
    with patch.object(config, "library_parameters", lambda f: by_class.get(type(f).__name__, real(f))):
        yield


MODEL_PRICERS = sorted(model_parameters(0.3))
TOLERANCE = {"CompanyShareOptionSABRPriceFactor": 1e-6}               # closed form; the rest are Monte Carlo (0.75)


@pytest.mark.parametrize("name", MODEL_PRICERS)
def test_value_option_model_reprices_the_market_under_library_parameters(world, name):
    """Each model reduced to Black-Scholes (parameters from its library entry) at the option's implied vol gives
    back the option's market price, 8.00 — S, r, sigma from data and K, T, call/put from the option."""
    random.seed(7)
    sigma = value_of(world, "CompanyShareOptionImpliedVolFactor")
    with library_parameters(model_parameters(sigma)):
        value = value_of(world, name)
    assert value == pytest.approx(8.0, abs=TOLERANCE.get(name, 0.75))


@pytest.mark.parametrize("name", MODEL_PRICERS)
def test_option_model_without_its_library_parameters_gives_no_value(world, name):
    """The library entries name no model parameters (v0, kappa, alpha, ...): missing data, no default model."""
    assert value_of(world, name) is None


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


@pytest.mark.parametrize("name, sign", [("BondFutureDiscountedValueFactor", -1), ("BondFutureForwardPriceFactor", 1)])
def test_value_bond_future_carry(world, name, sign):
    """close 96.25 carried at the USD yield (3.75 %, from the dated SOFR future) to the future's expiry (18 Mar)."""
    t = (date(2026, 3, 18) - T.date()).days / 365.0
    assert value_of(world, name) == pytest.approx(96.25 * math.exp(sign * 0.0375 * t), rel=1e-9)


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


def option_inputs(world):
    sigma = value_of(world, "CompanyShareOptionImpliedVolFactor")
    t = (date(2026, 3, 20) - T.date()).days / 365.0
    return world.closes["AAPL"][-1], 180.0, 0.0375, sigma, t


def test_value_option_model_prices_reprice_the_market(world):
    """BSM and CRR at the option's implied vol give back its market price (8.00); CRR within its tree error."""
    assert value_of(world, "CompanyShareOptionBlackScholesMertonPriceFactor") == pytest.approx(8.0, abs=1e-3)
    w2 = FactorWorld()
    try:
        assert value_of(w2, "CompanyShareOptionCoxRossRubinsteinPriceFactor") == pytest.approx(8.0, abs=0.05)
    finally:
        w2.close()


def test_value_option_rho(world):
    S, K, r, sigma, t = option_inputs(world)
    d2 = (math.log(S / K) + (r - sigma * sigma / 2) * t) / (sigma * math.sqrt(t))
    n = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
    assert value_of(world, "CompanyShareOptionRhoFactor") == pytest.approx(K * t * math.exp(-r * t) * n(d2), rel=1e-6)


def test_value_option_realised_vol_and_variance(world):
    """Annualised over the last 22 closes (21 log returns), sample statistics."""
    closes_ = world.option_closes[-22:]
    logs = [math.log(closes_[i] / closes_[i - 1]) for i in range(1, len(closes_))]
    m = sum(logs) / len(logs)
    var = sum((x - m) ** 2 for x in logs) / (len(logs) - 1)
    assert value_of(world, "CompanyShareOptionVolFactor") == pytest.approx(math.sqrt(var) * math.sqrt(252), rel=1e-9)
    assert fresh("CompanyShareOptionVarFactor") == pytest.approx(var * 252, rel=1e-9)


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


def lookback_of(cls):
    return declared_dependencies(instantiate(cls))[0].lookback


@pytest.mark.parametrize("cls", [pytest.param(c, id=n) for n, c in HISTORY])
def test_history_factor_receives_its_window_of_trailing_closes(world, cls):
    """Regression: the service had no lookback (one close per factor). Each history factor declares its window
    (DependencySpec.lookback) and receives exactly that many closed daily closes, oldest first, ending at the
    last closed bar (Friday's for Monday 16:00) — and a finite value."""
    value, captured = world.resolve(cls, world.share["AAPL"])
    prices = [float(v) for v in captured["CompanyShareFactor"]]
    closes = world.closes["AAPL"]
    window = lookback_of(cls)
    if window == "ytd":                                       # last 2025 close (base) + every 2026 close
        first_2026 = next(i for i, d in enumerate(world.days) if d.year == T.year)
        assert prices == pytest.approx(closes[first_2026 - 1:])
    else:
        assert len(prices) == window and prices == pytest.approx(closes[-window:])
    assert value is not None and math.isfinite(value)


@pytest.mark.parametrize("cls", [pytest.param(c, id=n) for n, c in HISTORY])
def test_history_factor_without_its_full_window_gives_no_value(world, cls):
    """A window that is not fully stored is missing data, not a value over a shorter window."""
    window = lookback_of(cls)
    if window == "ytd" or window <= 2:
        pytest.skip("window always available in this world")
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    keep = world.days[-(window - 1):]                         # one close short of the window
    world.s.query(FactorValueModel).filter(FactorValueModel.entity_id == world.share["AAPL"].id,
                                           FactorValueModel.date < keep[0]).delete()
    world.s.commit()
    value, captured = world.resolve(cls, world.share["AAPL"])
    assert value is None


def test_a_bar_still_open_at_the_target_is_never_in_the_series(world):
    """Monday's bar (stamped Monday 00:00) is stored but not closed at Monday 16:00: no look-ahead."""
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    close = world.s.query(CompanyShareFactorModel).filter_by(name="close").first()
    world.s.add(FactorValueModel(factor_id=close.id, entity_id=world.share["AAPL"].id, entity_type="CompanyShare",
                                 date=T.replace(hour=0), value="999.0"))
    world.s.commit()
    value, captured = world.resolve(dict(factor_classes())["CompanySharePriceVsMA20Factor"], world.share["AAPL"])
    assert 999.0 not in captured["CompanyShareFactor"]
    assert captured["CompanyShareFactor"] == pytest.approx(closes(world)[-20:])


# ---- independent values of every family ------------------------------------------------------

def closes(world):
    return world.closes["AAPL"]


def ret(c, n):
    return c[-1] / c[-1 - n] - 1


def mean(xs):
    return sum(xs) / len(xs)


def daily_returns(c, n):
    window = c[-(n + 1):]
    return [window[i] / window[i - 1] - 1 for i in range(1, len(window))]


EXPECTED = {
    "CompanyShareReturn1DFactor": lambda c: ret(c, 1),
    "CompanyShareReturn5DFactor": lambda c: ret(c, 5),
    "CompanyShareReturn20DFactor": lambda c: ret(c, 20),
    "CompanyShareReturn3MFactor": lambda c: ret(c, 63),
    "CompanyShareReturn5MFactor": lambda c: ret(c, 105),
    "CompanySharePriceVsMA20Factor": lambda c: c[-1] / mean(c[-20:]) - 1,
    "CompanySharePriceVsMA100Factor": lambda c: c[-1] / mean(c[-100:]) - 1,
    "CompanyShareMA5VsMA10Factor": lambda c: mean(c[-5:]) / mean(c[-10:]) - 1,
    "CompanyShareMA20VsMA50Factor": lambda c: mean(c[-20:]) / mean(c[-50:]) - 1,
    "CompanyShareMomentumAcceleration20D50DFactor": lambda c: ret(c, 20) - (c[-21] / c[-51] - 1),
    "CompanyShareReturnChange5DFactor": lambda c: ret(c, 5) - (c[-6] / c[-11] - 1),
    "CompanyShareSharpe20DFactor": lambda c: (lambda r: mean(r) / (sum((x - mean(r)) ** 2 for x in r)
                                                                   / (len(r) - 1)) ** 0.5)(daily_returns(c, 20)),
    "CompanyShareSortino50DFactor": lambda c: (lambda r: mean(r) / (mean([x * x for x in r if x < 0])) ** 0.5)(
        daily_returns(c, 50)),
    "CompanyShareDrawdownFrom5MHighFactor": lambda c: (max(c[-105:]) - c[-1]) / max(c[-105:]),
    "CompanyShareDaysSince5MHighFactor": lambda c: float(104 - c[-105:].index(max(c[-105:]))),
    "CompanyShareShortTermMomentumFactor": lambda c: ret(c, 1),
    "CompanyShareMediumTermMomentumFactor": lambda c: ret(c, 21),
    "CompanyShareMomentumZScore20DFactor": lambda c: (c[-1] - mean(c[-20:])) / (
        sum((x - mean(c[-20:])) ** 2 for x in c[-20:]) / 20) ** 0.5,
}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_value_of_history_factor(world, name):
    assert value_of(world, name) == pytest.approx(EXPECTED[name](closes(world)), rel=1e-9, abs=1e-12)


def test_value_of_the_year_to_date_return(world):
    """Base = the last close of the previous year (the world has bars on 2026-01-01 and 2026-01-02)."""
    first_2026 = next(i for i, d in enumerate(world.days) if d.year == T.year)
    base = closes(world)[first_2026 - 1]
    assert value_of(world, "CompanyShareReturnYTDFactor") == pytest.approx(closes(world)[-1] / base - 1)


def volumes(world):
    return [1_000_000.0 + i for i in range(len(world.days))]           # as seeded by FactorWorld


SERIES_EXPECTED = {
    "CompanySharePriceReturnFactor": lambda w: ret(closes(w), 1),                         # subgroup daily
    "CompanyShareAvgTurnover6mFactor": lambda w: mean(volumes(w)[-126:]),
    "CompanyShareMonthlyPriceRangeFactor": lambda w: (closes(w)[-1] + 1.0) - (closes(w)[-21] - 1.0),
    "CompanyShareVpt52w20dLagFactor": lambda w: volumes(w)[-21] * (closes(w)[-21] - closes(w)[-273]) / closes(w)[-273],
    "CompanyShareOptionPriceReturnFactor": lambda w: w.option_closes[-1] / w.option_closes[-2] - 1,
    # AAPL and MSFT (2 x AAPL's closes) have the same daily return: their equal-weight mean is that return
    "CompanySharePortfolioEqualWeightReturnFactor": lambda w: ret(closes(w), 1),
    "IndexPriceReturnFactor": lambda w: (lambda c: c[-1] / c[-2] - 1)(w.index_closes["Index"]),
    "IndexFuturePriceReturnFactor": lambda w: (lambda c: c[-1] / c[-2] - 1)(w.index_closes["IndexFuture"]),
    "IndexFutureOptionPriceReturnFactor": lambda w: (lambda c: c[-1] / c[-2] - 1)(w.index_closes["IndexFutureOption"]),
}


@pytest.mark.parametrize("name", sorted(SERIES_EXPECTED))
def test_value_of_series_factor(world, name):
    """Former library-route factors (two prices with lags) now read their window of closed bars (lookback):
    return over the subgroup window, mean of 126 volumes, high 1 bar ago - low 21 bars ago, VPT 52w + 20d."""
    value = value_of(world, name)
    assert value == pytest.approx(SERIES_EXPECTED[name](world), rel=1e-9)


@pytest.mark.parametrize("subgroup, bars", [("weekly", 5), ("monthly", 21)])
def test_price_return_window_follows_the_subgroup(world, subgroup, bars):
    value, captured = world.resolve(factor("CompanySharePriceReturnFactor"), world.share["AAPL"],
                                    name=f"return_{subgroup}", subgroup=subgroup)
    assert len(captured["prices"]) == bars + 1
    assert value == pytest.approx(ret(closes(world), bars), rel=1e-9)


def test_trend_slope_is_the_least_squares_slope(world):
    import numpy as np
    c = closes(world)[-20:]
    assert value_of(world, "CompanyShareTrendSlope20DFactor") == pytest.approx(float(np.polyfit(range(20), c, 1)[0]))


def test_catalog_split():
    """Bookkeeping: every wired factor is covered here; history factors are a subset."""
    assert len(WIRED) >= 80 and 40 <= len(HISTORY) < len(WIRED)
