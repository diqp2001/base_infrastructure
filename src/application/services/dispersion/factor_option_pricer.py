"""
FactorOptionPricer - the dispersion trading cycle's option prices from the FACTOR chain the engine values the
portfolio with, so a trade is sized at the price it is then valued at:

    ETFShareOptionValueFactor / CompanyShareOptionValueFactor
        = the option's IBKR quote (MIDPOINT close) when IBKR has one,
          else its model price: Black-Scholes on the underlying's close, the underlying's IBKR implied volatility
          (OPTION_IMPLIED_VOLATILITY) and the IRX rate (share_option_model_price).

For each leg opened: the ATM strike on a listed-style grid (ShareOptionFactor.select_atm_strike), the option entity
(``register_option``), ONE attempt at the option's IBKR quotes over its life (``import_quotes``: the preload service,
which also records the window as covered so the valuation never asks IBKR again), then the value resolved at the
moment the opening close is known (the next day 00:00: a daily bar dated D is closed at D+1 00:00).
Same interface as ModelledOptionPricer (atm_call / mark), so the cycle does not know which pricer it runs with.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Callable, Dict, Optional

import pandas as pd

from src.application.services.dispersion.modelled_option_pricing import strike_grid
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (
    Leg,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.share_option_factor import (
    ShareOptionFactor,
)

MULTIPLIER = 100.0


def known_at(day: date) -> datetime:
    """When the close of ``day`` is known (its daily bar is closed): the next day 00:00."""
    return datetime.combine(day + timedelta(days=1), time(0, 0))


class FactorOptionPricer:

    def __init__(self, factory, resolution_service, register_option: Callable[..., object],
                 import_quotes: Optional[Callable[[str, bool, date, date], None]] = None,
                 occ_symbol: Optional[Callable[[str, date, float], str]] = None,
                 log: Optional[Callable[[str], None]] = None):
        from src.application.services.dispersion.dispersion_target_portfolio import occ_symbol as _occ
        self.factory = factory
        self.service = resolution_service
        self.register_option = register_option
        self.import_quotes = import_quotes
        self.occ_symbol = occ_symbol or _occ
        self.log = log or logging.getLogger(__name__).info
        self._tried: set = set()
        self._definitions: Dict[bool, object] = {}

    def _value_definition(self, is_etf: bool):
        if is_etf not in self._definitions:
            from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_value_factor import (
                CompanyShareOptionValueFactor,
            )
            from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_value_factor import (
                ETFShareOptionValueFactor,
            )
            cls = ETFShareOptionValueFactor if is_etf else CompanyShareOptionValueFactor
            d = cls()
            self._definitions[is_etf] = self.factory.get_local_repository(cls.__name__)._create_or_get(
                cls, d.name, group=d.group, subgroup=d.subgroup, data_type=d.data_type, source=d.source,
                frequency="1d")
        return self._definitions[is_etf]

    def value(self, option, is_etf: bool, when: datetime) -> Optional[float]:
        fv = self.service.resolve_factor_value(self._value_definition(is_etf), option, when)
        if fv is None or fv.value is None:
            return None
        v = float(fv.value)
        return v if v >= 0 else None

    def _option(self, symbol: str, underlying: str, expiry: date, strike: float, is_etf: bool, day: date):
        option = self.register_option(symbol=symbol, underlying=underlying, expiry=expiry, strike=strike,
                                      multiplier=MULTIPLIER, is_etf=is_etf, day=day)
        if self.import_quotes is not None and symbol not in self._tried:
            self._tried.add(symbol)
            try:
                self.import_quotes(symbol, is_etf, day, expiry)
            except Exception as e:                       # no quotes: the model price is the value
                self.log(f"[DISP-STM] IBKR quotes of {symbol}: {e!r}")
        return option

    # -- the cycle's interface --
    def atm_call(self, symbol: str, closes: pd.Series, opened: date, expiry: date, weight: float = 1.0,
                 is_etf: bool = False) -> Optional[Leg]:
        upto = closes[closes.index <= pd.Timestamp(opened)].dropna()
        if upto.empty or upto.index[-1].date() != opened or (expiry - opened).days <= 0:
            return None
        spot = float(upto.iloc[-1])
        strike = ShareOptionFactor.select_atm_strike(strike_grid(spot), spot)
        if strike is None:
            return None
        option = self._option(self.occ_symbol(symbol, expiry, strike), symbol, expiry, strike, is_etf, opened)
        price = self.value(option, is_etf, known_at(opened)) if option is not None else None
        if price is None or price <= 0:
            return None
        return Leg(symbol=symbol, spot=spot, strike=strike, multiplier=MULTIPLIER, bid=price, ask=price,
                   weight=weight)

    def mark(self, symbol: str, leg: dict, closes: pd.Series, session: date) -> Optional[float]:
        """The value of an open leg at the latest known close (the engine's valuation price)."""
        option = self._option(symbol, leg["underlying"], leg["expiry"], leg["strike"], leg["is_etf"], session)
        return self.value(option, leg["is_etf"], known_at(session)) if option is not None else None


class SymbolRoutedPricer:
    """``primary`` for every underlying except ``fallback_symbols``, which ``fallback`` prices (e.g. a member the
    engine stores no close / implied vol for). Same interface (atm_call / mark)."""

    def __init__(self, primary, fallback, fallback_symbols=(), log: Optional[Callable[[str], None]] = None):
        self.primary, self.fallback = primary, fallback
        self.fallback_symbols = set(fallback_symbols)
        self.log = log or (lambda m: None)
        self._noted: set = set()

    def _for(self, underlying: str):
        if underlying in self.fallback_symbols:
            if underlying not in self._noted:
                self._noted.add(underlying)
                self.log(f"[DISP-STM] {underlying}: options priced with realised volatility on file-cache closes "
                         f"(no stored close / IBKR implied vol)")
            return self.fallback
        return self.primary

    def atm_call(self, symbol, closes, opened, expiry, weight=1.0, is_etf=False):
        return self._for(symbol).atm_call(symbol, closes, opened, expiry, weight=weight, is_etf=is_etf)

    def mark(self, symbol, leg, closes, session):
        return self._for(leg["underlying"]).mark(symbol, leg, closes, session)
