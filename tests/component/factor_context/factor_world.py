"""
A small market on SQLite for end-to-end factor resolution (no IBKR):

  shares AAPL / MSFT   260 daily bars (open, high, low, close, volume; group "price", source ibkr),
                       bars stamped at their start; the last closed bar before T is Friday 2026-01-02
  portfolio TEST       100 000 USD; AAPL 10 and MSFT 5 bought at their last close
  USD                  CurrencyRateFactor 1.0 at T
  SR3H6                the front-month SOFR future at T (raw close 96.25 -> 3.75 %)
  AAPL 180 C 2026-03-20   option on AAPL (out of the money, close 8.00)

`entity_for(class name)` returns the entity a factor is resolved on.
"""

import contextlib
import functools
import io
import logging
import math
from datetime import date, datetime, timedelta
from unittest.mock import patch

from src.application.services.data.entities.factor.factor_value_resolution_service import FactorValueResolutionService
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.infrastructure.models.factor.factor_value import FactorValueModel
from tests.misbuffet.sqlite_portfolio import SqlitePortfolio

T = datetime(2026, 1, 5, 16, 0)
LAST_BAR = datetime(2026, 1, 2)
N_BARS = 260
OPTION_SYMBOL = "AAPL  260320C00180000"
FUTURE_SYMBOL = "SR3H6"
RAW_NAMES = ("open", "high", "low", "close", "volume")

logging.getLogger("factor_world").setLevel(logging.CRITICAL)
logging.getLogger("sqlite_portfolio").setLevel(logging.CRITICAL)


def bar_days(n=N_BARS, last=LAST_BAR):
    days, day = [], last
    while len(days) < n:
        if day.weekday() < 5:
            days.append(day)
        day -= timedelta(days=1)
    return list(reversed(days))


def close_series(scale=1.0):
    """Deterministic, trending with swings (so drawdowns / downside deviation are not degenerate)."""
    return [scale * (100.0 + 0.3 * i + 4.0 * math.sin(i / 6.0)) for i in range(N_BARS)]


class FactorWorld:

    def __init__(self):
        self.p = SqlitePortfolio(cash=100_000.0, shares=("ZZZ", "AAPL", "MSFT"))
        self.p.upm._algorithm.bar_size_setting = "1 day"
        self.s = self.p.session
        self.f = self.p.factory
        self.days = bar_days()
        self.closes = {"AAPL": close_series(1.0), "MSFT": close_series(2.0)}
        self.share = {t: self.f.company_share_local_repo.get_by_symbol(t) for t in ("AAPL", "MSFT")}
        self._seed_share_bars()
        self.p.upm._algorithm.time = T
        for ticker, qty in (("AAPL", 10), ("MSFT", 5)):
            assert self.p.trade(ticker, qty, self.closes[ticker][-1], when=T)
        self.usd = self._usd()
        self._seed_currency_rate()
        self.future = self._seed_future()
        self.option = self._seed_option()
        self.service = FactorValueResolutionService(factory=self.f, logger=logging.getLogger("factor_world"))

    # ---- seeding ---------------------------------------------------------------------------
    def _raw_factor(self, model_cls, name, factor_type, entity_type_group="price"):
        factor = self.s.query(model_cls).filter_by(name=name, group=entity_type_group).first()
        if factor is None:
            factor = model_cls(name=name, group=entity_type_group, subgroup="ohlc", frequency="1d",
                               data_type="numeric", source="ibkr", definition=name, factor_type=factor_type)
            self.s.add(factor)
            self.s.commit()
        return factor

    def _seed_share_bars(self):
        from src.infrastructure.models.factor.factor import CompanyShareFactorModel
        factors = {n: self._raw_factor(CompanyShareFactorModel, n, "company_share_factor") for n in RAW_NAMES}
        for ticker, closes in self.closes.items():
            for i, (day, c) in enumerate(zip(self.days, closes)):
                bar = {"open": c - 0.5, "high": c + 1.0, "low": c - 1.0, "close": c, "volume": 1_000_000.0 + i}
                for name, value in bar.items():
                    self.s.add(FactorValueModel(factor_id=factors[name].id, entity_id=self.share[ticker].id,
                                                entity_type="CompanyShare", date=day, value=repr(value)))
        self.s.commit()

    def _usd(self):
        from src.infrastructure.models.finance.financial_assets.currency import CurrencyModel
        row = self.s.query(CurrencyModel).filter(CurrencyModel.symbol == "USD").first()
        return self.f.get_local_repository("Currency").get_by_id(row.id)

    def _seed_currency_rate(self):
        from src.domain.entities.factor.finance.financial_assets.currency.currency_rate_factor import CurrencyRateFactor
        repo = self.f.get_local_repository("CurrencyRateFactor")
        d = CurrencyRateFactor()
        rate = repo._create_or_get(CurrencyRateFactor, d.name, group=d.group, subgroup=d.subgroup,
                                   data_type=d.data_type, source=d.source, frequency=d.frequency)
        self.s.add(FactorValueModel(factor_id=rate.id, entity_id=self.usd.id, entity_type="Currency",
                                    date=T, value="1.0"))
        self.s.commit()

    def _seed_future(self):
        from src.domain.entities.finance.financial_assets.derivatives.future.bond_future import BondFuture
        from src.infrastructure.models.factor.factor import BondFutureFactorModel
        future = self.f.get_local_repository("BondFuture").add(BondFuture(
            id=None, name=f"{FUTURE_SYMBOL} Bond Future", symbol=FUTURE_SYMBOL, start_date=date(2025, 3, 1),
            currency_id=self.usd.id, exchange_id=1, underlying_asset_id=self.usd.id))
        close = self._raw_factor(BondFutureFactorModel, "close", "bond_future_factor")
        for day in self.days[-30:]:
            self.s.add(FactorValueModel(factor_id=close.id, entity_id=future.id, entity_type="BondFuture",
                                        date=day, value="96.25"))
        self.s.commit()
        return future

    def _seed_option(self):
        from src.infrastructure.models.factor.factor import CompanyShareOptionFactorModel
        from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_option import (
            CompanyShareOptionModel,
        )
        from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import (
            CompanyShareOption,
        )
        # built like the IBKR contract import (CompanyShareOptionRepository._create_or_get cannot create
        # an option locally: it never sets the NOT NULL start_date / exchange_id)
        repo = self.f.get_local_repository("CompanyShareOption")
        option = repo.add(CompanyShareOption(
            id=None, name=f"{OPTION_SYMBOL} option", symbol=OPTION_SYMBOL, currency_id=self.usd.id,
            underlying_asset_id=self.share["AAPL"].id, exchange_id=1, option_type="call",
            start_date=date(2025, 6, 1), end_date=date(2026, 3, 20), strike_price=180.0, multiplier=100,
            expiry="20260320"))
        assert self.s.get(CompanyShareOptionModel, option.id).strike_price == 180.0
        factors = {n: self._raw_factor(CompanyShareOptionFactorModel, n, "company_share_option_factor")
                   for n in ("open", "high", "low", "close")}
        self.option_closes = [8.0 + 0.4 * math.sin(i / 2.0) for i in range(29)] + [8.0]   # last close 8.00
        for day, close_ in zip(self.days[-30:], self.option_closes):
            for name, value in (("open", close_ - 0.1), ("high", close_ + 0.4), ("low", close_ - 0.4), ("close", close_)):
                self.s.add(FactorValueModel(factor_id=factors[name].id, entity_id=option.id,
                                            entity_type="CompanyShareOption", date=day, value=repr(value)))
        self.s.commit()
        return repo.get_by_id(option.id)

    def option_portfolio(self):
        """CompanyShareOptionPortfolio under the main portfolio holding 2 contracts (built like set_holdings)."""
        from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import (
            CompanyShareOption,
        )
        if getattr(self, "_option_portfolio_id", None) is None:
            self._option_portfolio_id = self.p.upm._ensure_asset_container(OPTION_SYMBOL, T, asset_class=CompanyShareOption)
            assert self.p.tm.execute_trade(ticker=OPTION_SYMBOL, order_qty=2, price=8.0,
                                           portfolio_id=self._option_portfolio_id, current_time=T,
                                           submit_order_fn=self.p.market_order, main_portfolio_id=self.p.portfolio.id)
        return self._option_portfolio_id

    def portfolio_option(self):
        """A CompanySharePortfolioOption (option on a share portfolio), stored like the import does."""
        from src.domain.entities.finance.financial_assets.derivatives.option.company_share_portfolio_option import (
            CompanySharePortfolioOption,
        )
        repo = self.f.get_local_repository("CompanySharePortfolioOption")
        return repo.add(CompanySharePortfolioOption(
            id=None, name="TEST_CS 180 C", symbol="TESTCS260320C180", currency_id=self.usd.id,
            underlying_asset_id=self.share["AAPL"].id, option_type="call", start_date=date(2025, 6, 1),
            end_date=date(2026, 3, 20), strike_price=180.0, multiplier=100))

    # ---- entities ---------------------------------------------------------------------------
    def holding(self, model_cls, **filters):
        row = self.s.query(model_cls).filter_by(**filters).first()
        key = model_cls.__name__.removesuffix("Model")
        return self.f.get_local_repository(key).get_by_id(row.id) if row else None

    def portfolio(self, key, portfolio_id):
        return self.f.get_local_repository(key).get_by_id(portfolio_id)

    def entity_for(self, factor_name):
        from src.infrastructure.models.finance.holding.company_share_portfolio_holding import (
            CompanySharePortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding import (
            CompanySharePortfolioPortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.holding.currency_portfolio_holding import CurrencyPortfolioHoldingModel
        from src.infrastructure.models.finance.holding.currency_portfolio_portfolio_holding import (
            CurrencyPortfolioPortfolioHoldingModel,
        )
        cs_link = self.s.query(CompanySharePortfolioPortfolioHoldingModel).first()
        cash = self.s.query(CurrencyPortfolioHoldingModel).first()
        table = {
            "CompanySharePortfolioHoldingValueFactor":
                lambda: self.holding(CompanySharePortfolioHoldingModel, asset_id=self.share["AAPL"].id),
            "CompanySharePortfolioPortfolioHoldingValueFactor":
                lambda: self.holding(CompanySharePortfolioPortfolioHoldingModel),
            "CurrencyPortfolioHoldingValueFactor": lambda: self.holding(CurrencyPortfolioHoldingModel),
            "CurrencyPortfolioPortfolioHoldingValueFactor": lambda: self.holding(CurrencyPortfolioPortfolioHoldingModel),
            "CompanySharePortfolioValueFactor": lambda: self.portfolio("CompanySharePortfolio", cs_link.asset_id),
            "CompanySharePortfolioPriceReturnFactor":
                lambda: self.portfolio("CompanySharePortfolio", cs_link.asset_id),
            "CompanySharePortfolioEqualWeightReturnFactor":
                lambda: self.portfolio("CompanySharePortfolio", cs_link.asset_id),
            "CurrencyPortfolioValueFactor": lambda: self.portfolio("CurrencyPortfolio", cash.currency_portfolio_id),
            "PortfolioValueFactor":                         # full tree: cash + shares + options
                lambda: (self.option_portfolio(), self.portfolio("Portfolio", self.p.portfolio.id))[1],
        }
        if factor_name in table:
            return table[factor_name]()
        if factor_name.startswith("CompanyShareOptionPortfolio"):
            from src.infrastructure.models.finance.holding.company_share_option_portfolio_holding import (
                CompanyShareOptionPortfolioHoldingModel,
            )
            from src.infrastructure.models.finance.holding.company_share_option_portfolio_portfolio_holding import (
                CompanyShareOptionPortfolioPortfolioHoldingModel,
            )
            portfolio_id = self.option_portfolio()
            return {
                "CompanyShareOptionPortfolioHoldingValueFactor":
                    lambda: self.holding(CompanyShareOptionPortfolioHoldingModel),
                "CompanyShareOptionPortfolioPortfolioHoldingValueFactor":
                    lambda: self.holding(CompanyShareOptionPortfolioPortfolioHoldingModel),
            }.get(factor_name, lambda: self.portfolio("CompanyShareOptionPortfolio", portfolio_id))()
        if factor_name.startswith("CompanySharePortfolioOption"):
            return self.portfolio_option()
        if factor_name.startswith("CompanyShareOption"):
            return self.option
        if factor_name.startswith("CompanyShare"):
            return self.share["AAPL"]
        if factor_name.startswith("Currency"):
            return self.usd
        if factor_name.startswith("BondFuture"):
            return self.future
        return None

    # ---- resolution -------------------------------------------------------------------------
    def definition(self, cls):
        d = cls()
        return self.f.get_local_repository(cls.__name__)._create_or_get(
            cls, d.name, group=d.group, subgroup=d.subgroup, data_type=d.data_type, source=d.source,
            frequency=d.frequency or "1d")

    def resolve(self, cls, entity, when=T, provider=None):
        """(value or None, the dependencies calculate() received or None if never called).

        `provider` replaces the model provider of ML factors (`_provider.predict(deps, entity, date)`)."""
        captured = {}
        real = cls.calculate
        definition = self.definition(cls)
        if provider is not None:
            definition._provider = provider

        @functools.wraps(real)                              # the service inspects calculate's signature
        def spy(self_, *args, **kwargs):
            deps = kwargs.get("dependencies", args[0] if args else kwargs)
            if not captured:
                captured.update(deps if isinstance(deps, dict) else {"_args": deps})
            return real(self_, *args, **kwargs)

        with patch.object(cls, "calculate", spy), contextlib.redirect_stdout(io.StringIO()):
            fv = self.service.resolve_factor_value(definition, entity, when)
        value = None if fv is None or fv.value is None else float(fv.value)
        return value, (captured or None)

    def close(self):
        self.p.close()
