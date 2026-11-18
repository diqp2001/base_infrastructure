"""Option value when the market has no quote (2026-11-16): IBKR's quotes first, else Black-Scholes on the
underlying's close, its IBKR implied volatility (OPTION_IMPLIED_VOLATILITY) and the IRX rate - for an option on a
company share and on an ETF share, and the ETF option holding valued in its ETFShareOptionPortfolio. SQLite, no IBKR."""

import math
from datetime import date

import pytest

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_model_price_factor import (
    CompanyShareOptionModelPriceFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_value_factor import (
    CompanyShareOptionValueFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_model_price_factor import (
    ETFShareOptionModelPriceFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_value_factor import (
    ETFShareOptionValueFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.share_option_model_price import (
    black_scholes_merton,
)
from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import CompanyShareOption
from src.domain.entities.finance.financial_assets.derivatives.option.etf_share_option import ETFShareOption
from tests.component.factor_context.factor_world import LAST_BAR, N_BARS, T, FactorWorld

IV_LAST = 0.25 + 0.0001 * (N_BARS - 1)          # the shares' last implied vol (FactorWorld._seed_band_inputs)
RATE = math.log1p(42.0 / 1000.0)               # IRX 42.0 = 4.2 %


@pytest.fixture(scope="module")
def world():
    w = FactorWorld()
    yield w
    w.close()


def expected(spot, strike, expiry, sigma=IV_LAST):
    return black_scholes_merton(spot, strike, RATE, sigma, (expiry - T.date()).days / 365.0, "call")


def unquoted_share_option(w):
    """An AAPL call with no quote series at all (an expired contract in a backtest)."""
    repo = w.f.get_local_repository("CompanyShareOption")
    symbol = "AAPL  260417C00175000"
    return repo.get_by_symbol(symbol) or repo.add(CompanyShareOption(
        id=None, name="AAPL 175 C", symbol=symbol, currency_id=w.usd.id, underlying_asset_id=w.share["AAPL"].id,
        exchange_id=1, option_type="call", start_date=date(2025, 12, 1), end_date=date(2026, 4, 17),
        strike_price=175.0, multiplier=100, expiry="20260417"))


def etf_option(w):
    """A call on the ETF 'TEST' (FactorWorld.etf_option: no quotes, the ETF's implied vol 0.18)."""
    return w.etf_option()


def test_the_model_price_is_black_scholes_on_the_underlying_close_implied_vol_and_irx(world):
    option = unquoted_share_option(world)
    value, deps = world.resolve(CompanyShareOptionModelPriceFactor, option)
    spot = world.closes["AAPL"][-1]                                  # the last closed bar (2026-01-02)
    assert deps["spot"] == [spot] and deps["implied_vol"] == [pytest.approx(IV_LAST)] and deps["rate"] == [42.0]
    assert value == pytest.approx(expected(spot, 175.0, date(2026, 4, 17)), rel=1e-9)


def test_a_share_option_without_quotes_is_valued_at_its_model_price(world):
    option = unquoted_share_option(world)
    value, deps = world.resolve(CompanyShareOptionValueFactor, option)
    assert not deps.get("CompanyShareOptionMidPriceFactor")
    assert value == pytest.approx(expected(world.closes["AAPL"][-1], 175.0, date(2026, 4, 17)), rel=1e-6)


def test_an_etf_option_is_valued_at_its_ibkr_mid_else_its_model_price(world):
    option = etf_option(world)
    model, deps = world.resolve(ETFShareOptionModelPriceFactor, option)
    spot = world.etf_closes[-1]
    assert deps["spot"] == [spot] and deps["implied_vol"] == [0.18]
    assert model == pytest.approx(expected(spot, 540.0, date(2026, 2, 20), sigma=0.18), rel=1e-9)
    value, deps = world.resolve(ETFShareOptionValueFactor, option)
    assert not deps.get("market") and value == pytest.approx(model, rel=1e-6)

    # an option IBKR quotes (MIDPOINT closes, 12.00): the market price wins over the model
    quoted = world.etf_option(quoted=True)
    value, deps = world.resolve(ETFShareOptionValueFactor, quoted)
    assert deps["market"] == [12.0] and deps["ETFShareOptionModelPriceFactor"] and value == pytest.approx(12.0)


def test_an_expired_option_is_worth_its_intrinsic_value(world):
    from src.domain.entities.factor.finance.financial_assets.derivatives.option.share_option_model_price import (
        model_price,
    )
    option = unquoted_share_option(world)
    after = {"entity": option, "target_date": date(2026, 4, 17), "spot": [190.0], "implied_vol": [0.3],
             "rate": [42.0]}
    assert model_price(after) == pytest.approx(15.0)
    assert model_price({**after, "spot": [170.0]}) == 0.0
    assert model_price({**after, "target_date": date(2026, 1, 5), "implied_vol": []}) is None   # no vol, no value


def test_a_short_etf_option_holding_is_valued_in_its_sub_portfolio(world):
    """set_holdings' path: the ETF option's ESO sub-portfolio, a fill of -18 contracts, then the engine's valuation
    (PortfolioService) values the holding at -18 x model price x 100."""
    from src.application.services.data.entities.factor.finance.portfolio_service import PortfolioService
    etf_option(world)
    repo = world.f.get_local_repository("ETFShareOption")
    symbol = "TEST  260320C00545000"
    option = repo.get_by_symbol(symbol) or repo.add(ETFShareOption(
        id=None, name="TEST 545 C", symbol=symbol, currency_id=world.usd.id, underlying_asset_id=world.etf().id,
        exchange_id=1, option_type="call", start_date=date(2025, 12, 1), end_date=date(2026, 3, 20),
        strike_price=545.0, multiplier=100, expiry="20260320"))
    assert option is not None
    upm, main = world.p.upm, world.p.portfolio.id
    service = PortfolioService(world.s, world.f, market_data_service=None)
    before = float(service.calculate_value(main, as_of_date=T, frequency="1d"))
    sub = upm._ensure_asset_container(symbol, T, asset_class=ETFShareOption)
    assert sub is not None and sub != main
    world.p.tm._update_position(symbol, -18, main)
    assert upm._qty_in_container(symbol, main) == -18
    model = expected(world.etf_closes[-1], 545.0, date(2026, 3, 20), sigma=0.18)
    after = float(service.calculate_value(main, as_of_date=T.replace(hour=18), frequency="1d"))
    assert after - before == pytest.approx(-18 * model * 100, rel=1e-6)


def test_the_cycle_pricer_prices_an_atm_leg_through_the_factor_chain(world):
    """FactorOptionPricer (the engine's pricer): ATM strike on the grid, the option entity registered, ONE attempt at
    its IBKR quotes, then ETFShareOptionValueFactor at the moment the opening close is known."""
    import pandas as pd
    from src.application.services.dispersion.factor_option_pricer import FactorOptionPricer, known_at
    etf_option(world)
    etf = world.etf()
    repo = world.f.get_local_repository("ETFShareOption")
    tried = []

    def register_option(symbol, underlying, expiry, strike, multiplier, is_etf, day):
        return repo.get_by_symbol(symbol) or repo.add(ETFShareOption(
            id=None, name=symbol, symbol=symbol, currency_id=world.usd.id, underlying_asset_id=etf.id, exchange_id=1,
            option_type="call", start_date=day, end_date=expiry, strike_price=strike, multiplier=multiplier,
            expiry=expiry.strftime("%Y%m%d")))

    pricer = FactorOptionPricer(world.f, world.service, register_option,
                                import_quotes=lambda *a: tried.append(a[0]))
    closes = pd.Series(world.etf_closes, index=pd.DatetimeIndex(world.days))
    opened, expiry = LAST_BAR.date(), date(2026, 2, 20)
    leg = pricer.atm_call("TEST", closes, opened, expiry, is_etf=True)
    spot = world.etf_closes[-1]
    assert leg.spot == spot and abs(leg.strike - spot) <= 2.5 and leg.bid == leg.ask
    model = black_scholes_merton(spot, leg.strike, RATE, 0.18, (expiry - known_at(opened).date()).days / 365.0, "call")
    assert leg.ask == pytest.approx(model, rel=1e-6)
    assert len(tried) == 1
    symbol = tried[0]
    mark = pricer.mark(symbol, {"underlying": "TEST", "strike": leg.strike, "expiry": expiry, "is_etf": True},
                       closes, opened)
    assert mark == pytest.approx(leg.ask) and len(tried) == 1           # quotes tried once per option
