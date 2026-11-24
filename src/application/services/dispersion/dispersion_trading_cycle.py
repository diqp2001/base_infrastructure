"""
DispersionTradingCycle - the monthly model-filtered ETF dispersion, one engine step at a time (the dispersion
counterpart of STMTradingCycle). The Misbuffet algorithm calls ``step(t)`` at every bar and sends the returned
TargetPortfolio (option contracts) to set_holdings; ``option_price(symbol)`` is the modelled price of a leg (the algorithm's price
resolver: orders and the daily valuation).

At a step, with the closes KNOWN at t only (KnownClosesReader: the members' and the ETF's daily IBKR bars through the
MarketDataHistoryService frontier - a daily close dated D is known from D+1 00:00):
  1. nothing new known since the previous step -> nothing to do (the open legs are re-marked to model);
  2. the open trade's expiry has settled (the last close on or before the expiry is known) -> both strategies are
     settled at that close (payoffs + net initial premium, A and B), the traded legs are closed at their intrinsic
     value (quantity 0);
  3. the latest known close is a monthly roll day (the close on which a monthly expiry settles) inside the backtest
     window -> the next trade is opened at that close: members in force that day (IndexMembership), price weights,
     modelled ATM call of the ETF and of EVERY member, N from the full basket, STM scores (closes up to that day),
     selection, A and B (DispersionPortfolioConstructionService). The engine trades ``traded`` (B by default); the
     other strategy is tracked alongside for the comparison.
     Strategy architecture: STM scores + ETF weights -> ETFCallDispersionTradingStrategy (StrategySignals) ->
     construct_dispersion_trade (selection + sizing) -> dispersion_target_portfolio -> result.target_portfolio
     (ETF calls short N, selected constituent calls long; the legs settled this step at 0 contracts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from dataclasses import replace
from datetime import datetime
from typing import Callable, Dict, List, Mapping, Optional

import pandas as pd

from src.application.services.dispersion.dispersion_portfolio_construction_service import (
    WHOLE,
    ConstructedTrade,
    DispersionPortfolioConstructionService,
    SettledStrategy,
    StrategyLegs,
)
from src.application.services.dispersion.dispersion_target_portfolio import (
    construct_dispersion_trade,
    dispersion_target_portfolio,
    occ_symbol,
)
from src.application.services.dispersion.index_membership import IndexMembership
from src.application.services.dispersion.model_selection import ModelFilterConfig
from src.application.services.dispersion.realized_payoff import expiry_for, settlement_day, third_fridays
from src.application.services.dispersion.screen_config import DispersionScreenConfig
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_constituent_scorer import ConstituentScores, STMConstituentScorer
from src.application.services.data.backtest_preload.known_closes_reader import (  # noqa: F401  (re-exported)
    KnownClosesReader,
    known_through,
)
from src.domain.entities.factor.trading_strategy.etf_call_dispersion_strategy import ETFCallDispersionTradingStrategy
from src.domain.entities.finance.portfolio.target_portfolio import TargetPortfolio, TargetPortfolioPosition

ORIGINAL, MODEL_FILTERED = "original", "model_filtered"
CALL = "C"


@dataclass
class MonthResult:
    opened: date
    expiry: Optional[date]
    trade: Optional[ConstructedTrade] = None
    scores: Optional[ConstituentScores] = None
    original: Optional[SettledStrategy] = None
    filtered: Optional[SettledStrategy] = None
    settled_on: Optional[date] = None
    replication_ratio: Optional[float] = None
    option_symbols: Dict[str, str] = field(default_factory=dict)      # underlying -> option symbol
    problem: Optional[str] = None

    @property
    def complete(self) -> bool:
        return self.original is not None and self.filtered is not None


@dataclass
class DispersionStepResult:
    time: pd.Timestamp
    session: Optional[date] = None                       # latest close known at the step
    targets: Dict[str, int] = field(default_factory=dict)   # option symbol -> target contracts (of target_portfolio)
    target_portfolio: Optional[TargetPortfolio] = None      # what the strategy wants to hold (contracts)
    opened: Optional[MonthResult] = None
    settled: Optional[MonthResult] = None
    note: str = ""


class DispersionTradingCycle:
    ROLL_GRACE_DAYS = 5        # a roll day older than this at the step (a gap in the data) opens no trade

    def __init__(self, membership: IndexMembership, reader: KnownClosesReader, scorer: STMConstituentScorer,
                 pricer, constructor: DispersionPortfolioConstructionService,
                 model_filter: ModelFilterConfig, screen: DispersionScreenConfig, start: date, end: date,
                 traded: str = MODEL_FILTERED, register_option: Optional[Callable[..., None]] = None,
                 log: Optional[Callable[[str], None]] = None):
        if traded not in (ORIGINAL, MODEL_FILTERED):
            raise ValueError(f"traded must be {ORIGINAL!r} or {MODEL_FILTERED!r}")
        if constructor.contracts != WHOLE:
            raise ValueError("the engine trades whole contracts: DispersionPortfolioConstructionService('whole')")
        self.membership = membership
        self.reader = reader
        self.scorer = scorer
        self.pricer = pricer
        self.constructor = constructor
        self.model_filter = model_filter
        self.screen = screen
        self.start, self.end = start, end
        self.traded = traded
        self.register_option = register_option or (lambda **kw: None)
        self.log = log or (lambda m: None)
        self.months: List[MonthResult] = []
        self.open_month: Optional[MonthResult] = None
        self._closes: pd.DataFrame = pd.DataFrame()
        self._session: Optional[date] = None
        self._last_roll: Optional[date] = None
        self._marks: Dict[str, tuple] = {}       # option symbol -> (session, price) of the latest mark
        self._legs: Dict[str, dict] = {}          # option symbol -> {underlying, strike, expiry, is_etf, exit}
        self.strategy = ETFCallDispersionTradingStrategy()

    def _add_targets(self, result: DispersionStepResult, target: TargetPortfolio) -> None:
        """Add ``target``'s positions to the step's TargetPortfolio (a step can settle a month and open the next)."""
        if result.target_portfolio is not None:
            target = replace(target, positions=tuple(result.target_portfolio) + tuple(target))
        result.target_portfolio = target
        result.targets = {p.symbol: int(round(p.target_quantity)) for p in target}

    # -- the step --
    def step(self, now) -> DispersionStepResult:
        now = pd.Timestamp(now)
        result = DispersionStepResult(time=now)
        closes = self.reader.closes(now)
        etf = self.membership.etf
        if closes.empty or etf not in closes or closes[etf].dropna().empty:
            result.note = f"no {etf} close known yet"
            return result
        self._closes = closes
        session = closes[etf].dropna().index[-1].date()
        result.session = session
        if session == self._session:
            result.note = "nothing new known since the previous step"
            return result
        self._session = session
        etf_days = {d.date(): v for d, v in closes[etf].dropna().items()}

        # an expiry is settled once a close dated on or after it is known (its settlement close is then final:
        # the expiry's own close, or the last one before it when the exchange was closed that Friday)
        if self.open_month is not None and session >= self.open_month.expiry:
            settled = settlement_day(etf_days, self.open_month.expiry)
            if settled is None:
                self.open_month.problem = f"no {etf} close at the {self.open_month.expiry} expiry"
                self.log(f"[DISP-STM] {self.open_month.problem}: the legs stay open")
            else:
                self._settle(self.open_month, settled, closes, result)

        roll = self._latest_roll(etf_days, session)
        if (roll is not None and roll != self._last_roll and self.open_month is None
                and self.start <= roll <= self.end and roll >= self.membership.base_date):
            self._last_roll = roll
            self._open(roll, closes, result)
        if not result.note:
            result.note = "open trade marked to model" if self.open_month else "no open trade"
        return result

    def _latest_roll(self, etf_days: Mapping[date, float], session: date) -> Optional[date]:
        """The latest roll day (the close a monthly expiry settles on) that is final at ``session``, if recent."""
        rolls = [f for f in third_fridays(session - timedelta(days=40), session) if f <= session]
        if not rolls:
            return None
        roll = settlement_day(etf_days, rolls[-1])
        if roll is None or (session - roll).days > self.ROLL_GRACE_DAYS:
            return None
        return roll

    # -- opening --
    def _open(self, opened: date, closes: pd.DataFrame, result: DispersionStepResult) -> None:
        expiry = expiry_for(opened, self.screen)
        month = MonthResult(opened, expiry)
        etf = self.membership.etf
        members = self.membership.members_at(opened)
        today = {s: float(v) for s, v in closes.loc[pd.Timestamp(opened)].items() if pd.notna(v)}
        try:
            if expiry is None:
                raise ValueError("no monthly expiry within the DTE range")
            weights = self.membership.price_weights(opened, today)
        except ValueError as e:
            month.problem = str(e)
            return self._skip(month, result)
        month.replication_ratio = self.membership.replication_ratio(opened, today)
        etf_leg = self.pricer.atm_call(etf, closes[etf], opened, expiry, is_etf=True)
        legs = [self.pricer.atm_call(s, closes[s], opened, expiry, weight=weights[s]) for s in members]
        missing = [s for s, leg in zip(members, legs) if leg is None]
        if etf_leg is None or missing:
            month.problem = f"no modelled ATM call for {([etf] if etf_leg is None else []) + missing}"
            return self._skip(month, result)

        month.scores = self.scorer.score(closes.loc[:pd.Timestamp(opened)], members, pd.Timestamp(opened))
        as_of = datetime.combine(opened, datetime.min.time())
        signals = self.strategy.evaluate({"score": {s: [v] for s, v in month.scores.scores.items()},
                                          "weights": weights}, as_of=as_of)
        month.trade = construct_dispersion_trade(signals, etf_leg, legs, opened, expiry, self.model_filter,
                                                 unscored=month.scores.unscored, constructor=self.constructor)

        traded = self._traded_legs(month.trade)
        for leg in [etf_leg] + legs:
            symbol = occ_symbol(leg.symbol, expiry, leg.strike)
            month.option_symbols[leg.symbol] = symbol
            self._legs[symbol] = {"underlying": leg.symbol, "strike": leg.strike, "expiry": expiry,
                                  "is_etf": leg.symbol == etf, "exit": None}
        for underlying, qty in [(etf, -traded.etf_contracts)] + [(s, q) for s, q in traded.positions.items()]:
            leg = etf_leg if underlying == etf else next(l for l in legs if l.symbol == underlying)
            symbol = month.option_symbols[underlying]
            self.register_option(symbol=symbol, underlying=underlying, expiry=expiry, strike=leg.strike,
                                 multiplier=leg.multiplier, is_etf=underlying == etf, day=opened)
        self._add_targets(result, dispersion_target_portfolio(month.trade, as_of=as_of, strategy=self.traded,
                                                              strategy_name=self.strategy.name))
        self.open_month = month
        self.months.append(month)
        result.opened = month
        t = month.trade
        self.log(f"[DISP-STM] open {opened} -> {expiry}: N={t.etf_contracts} short {etf} calls, "
                 f"{len(t.filtered.positions)}/{len(t.original.positions)} constituents selected, "
                 f"short {t.short_premium:,.0f} full {t.full_basket_premium:,.0f} "
                 f"selected {t.selected_basket_premium:,.0f} unused {t.unused_premium:,.0f} (traded: {self.traded})")

    def _skip(self, month: MonthResult, result: DispersionStepResult) -> None:
        self.months.append(month)
        result.note = f"{month.opened}: {month.problem}"
        self.log(f"[DISP-STM] {result.note}")

    def _traded_legs(self, trade: ConstructedTrade) -> StrategyLegs:
        return trade.filtered if self.traded == MODEL_FILTERED else trade.original

    # -- settlement --
    def _settle(self, month: MonthResult, settled: date, closes: pd.DataFrame, result: DispersionStepResult) -> None:
        etf = self.membership.etf
        at = {s: float(v) for s, v in closes.loc[pd.Timestamp(settled)].items() if pd.notna(v)}
        members = list(month.trade.original.positions)
        absent = [s for s in [etf] + members if s not in at]
        if absent:
            month.problem = f"no close at the {month.expiry} expiry for {absent}"
            self.log(f"[DISP-STM] {month.problem}: the legs stay open")
            return
        prices = {s: at[s] for s in members}
        month.original = self.constructor.settle(month.trade, month.trade.original, at[etf], prices)
        month.filtered = self.constructor.settle(month.trade, month.trade.filtered, at[etf], prices)
        month.settled_on = settled
        traded = self._traded_legs(month.trade)
        closing = []
        for underlying in [etf] + list(traded.positions):
            symbol = month.option_symbols[underlying]
            leg = self._legs[symbol]
            leg["exit"] = max(at[underlying] - leg["strike"], 0.0)
            closing.append(TargetPortfolioPosition(
                symbol=symbol, target_weight=0.0, target_quantity=0.0,
                asset_type="ETFShareOption" if underlying == etf else "CompanyShareOption"))
        self._add_targets(result, TargetPortfolio(
            as_of=datetime.combine(settled, datetime.min.time()), positions=tuple(closing),
            strategy_name=self.strategy.name, construction="etf_call_dispersion:settlement"))
        self.open_month = None
        result.settled = month
        self.log(f"[DISP-STM] settled {month.opened} -> {month.expiry} at the {settled} close: "
                 f"P&L A {month.original.pnl:,.0f} B {month.filtered.pnl:,.0f}")

    # -- prices for the engine --
    def option_price(self, symbol: str) -> Optional[float]:
        """Modelled price of a leg at the latest known close (its intrinsic value once settled); None when the
        symbol is not a leg of this cycle."""
        leg = self._legs.get(symbol)
        if leg is None:
            return None
        if leg["exit"] is not None:
            return leg["exit"]
        series = self._closes.get(leg["underlying"])
        if series is None or self._session is None:
            return None
        if self._marks.get(symbol, (None,))[0] != self._session:
            self._marks[symbol] = (self._session, self.pricer.mark(symbol, leg, series, self._session))
        return self._marks[symbol][1]

    def is_leg(self, symbol: str) -> bool:
        return symbol in self._legs

    def is_etf_leg(self, symbol: str) -> bool:
        return bool(self._legs.get(symbol, {}).get("is_etf"))
