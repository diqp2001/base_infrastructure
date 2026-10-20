"""
Portfolio value through every layer of the portfolio tree, after each transaction.

    Portfolio (main)                                    "Portfolio Value"
      ├─ CurrencyPortfolio                              "Currency Portfolio Value"
      │    └─ cash holding                              "Currency Portfolio Holding Value"
      └─ CompanySharePortfolio                          "Company Share Portfolio Value"
           └─ share holdings (AAPL, MSFT)               "Portfolio Company Share Holding Value"

Each step books a transaction (TradeManager) or moves a price, revalues the main portfolio
(get_portfolio_value, which recomputes the whole tree) and checks every layer against
independently computed figures, plus the invariants:

    main = cash portfolio + share portfolio
    share portfolio = sum of its holdings, holding = quantity x last closed price
    cash portfolio = cash holding = cash position

Prices come from raw daily closes (bars stamped at their start, usable once closed). ZZZ is
created first and priced at 999 so share ids never coincide with holding ids.
"""

import logging
from datetime import datetime

import pytest

from src.infrastructure.models.finance.holding.company_share_portfolio_holding import CompanySharePortfolioHoldingModel
from src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding import (
    CompanySharePortfolioPortfolioHoldingModel,
)
from tests.misbuffet.sqlite_portfolio import SqlitePortfolio

logging.getLogger("sqlite_portfolio").setLevel(logging.CRITICAL)
logging.getLogger("src.application.services.data.entities.factor.factor_value_resolution_service").setLevel(logging.CRITICAL)

FRI, MON, TUE, WED = datetime(2026, 1, 2), datetime(2026, 1, 5), datetime(2026, 1, 6), datetime(2026, 1, 7)
MON_16, TUE_16, WED_16 = MON.replace(hour=16), TUE.replace(hour=16), WED.replace(hour=16)
CASH = 100_000.0


class Tree:
    """SqlitePortfolio + readers for the value of every layer at a valuation time."""

    def __init__(self, cash=CASH, engine=None):
        self.p = SqlitePortfolio(cash=cash, shares=("ZZZ", "AAPL", "MSFT"), engine=engine)
        self.p.upm._algorithm.bar_size_setting = "1 day"
        self.p.seed_close("ZZZ", FRI, 999.0)

    def close(self, ticker, bar_day, price):
        self.p.seed_close(ticker, bar_day, price)

    def unchanged_bars(self, when):
        """The feed delivers a daily bar every session: a share whose price did not move in the session due at
        `when` (the previous trading day's bar) gets that bar at its last close. A share never priced keeps no bar
        (bars are only usable for the session they belong to: bar_calendar.bar_is_current)."""
        from src.domain.entities.factor.bar_calendar import previous_trading_day
        from src.infrastructure.models.factor.factor import CompanyShareFactorModel
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        close = self.p.session.query(CompanyShareFactorModel).filter_by(name="close", frequency="1d").first()
        if close is None:
            return
        due = datetime.combine(previous_trading_day(when.date()), datetime.min.time())
        rows = self.p.session.query(FactorValueModel).filter(FactorValueModel.factor_id == close.id,
                                                             FactorValueModel.date <= due).all()
        latest = {}
        for r in sorted(rows, key=lambda r: r.date):
            latest[r.entity_id] = r
        for entity_id, r in latest.items():
            if r.date.replace(tzinfo=None) < due:
                self.p.session.add(FactorValueModel(factor_id=close.id, entity_id=entity_id,
                                                    entity_type=r.entity_type, date=due, value=r.value))
        self.p.session.commit()

    def trade(self, ticker, qty, price, when):
        self.p.upm._algorithm.time = when
        assert self.p.trade(ticker, qty, price, when=when), f"{ticker} {qty:+d} @ {price} not booked"

    def revalue(self, when) -> float:
        self.p.upm._algorithm.time = when
        self.unchanged_bars(when)
        value = self.p.upm.get_portfolio_value(backtest_date=when)
        return float(getattr(value, "value", value))

    def _value(self, factor_name, entity_id, when):
        rows = [r for r in self.p.factor_values(factor_name) if r[1] == entity_id and r[2] == when]
        return rows[-1][3] if rows else None

    def share_portfolio_id(self):
        link = self.p.session.query(CompanySharePortfolioPortfolioHoldingModel).filter_by(
            container_id=self.p.portfolio.id).one_or_none()
        return link.asset_id if link else None

    def holding_id(self, ticker):
        share = self.p.factory.company_share_local_repo.get_by_symbol(ticker)
        holding = self.p.session.query(CompanySharePortfolioHoldingModel).filter_by(asset_id=share.id).one_or_none()
        return holding.id if holding else None

    def layers(self, when):
        """Value of every layer stored by the last revaluation at `when`."""
        cash_rows = [r for r in self.p.factor_values("Currency Portfolio Value") if r[2] == when]
        out = {
            "main": self._value("Portfolio Value", self.p.portfolio.id, when),
            "cash_portfolio": cash_rows[-1][3] if cash_rows else None,
            "cash_holding": ([r for r in self.p.factor_values("Currency Portfolio Holding Value") if r[2] == when]
                             or [(None, None, None, None)])[-1][3],
            "share_portfolio": self._value("Company Share Portfolio Value", self.share_portfolio_id(), when)
            if self.share_portfolio_id() else None,
        }
        for ticker in ("AAPL", "MSFT"):
            hid = self.holding_id(ticker)
            out[ticker] = self._value("Portfolio Company Share Holding Value", hid, when) if hid else None
        return out

    def assert_consistent(self, layers):
        """Invariants between the layers and with the books."""
        holdings = sum(v for k, v in layers.items() if k in ("AAPL", "MSFT") and v is not None)
        assert layers["share_portfolio"] == pytest.approx(holdings)
        assert layers["cash_portfolio"] == pytest.approx(layers["cash_holding"])
        assert layers["cash_portfolio"] == pytest.approx(self.p.cash())
        assert layers["main"] == pytest.approx(layers["cash_portfolio"] + layers["share_portfolio"])


@pytest.fixture
def tree():
    t = Tree()
    t.close("AAPL", FRI, 150.0)
    t.close("MSFT", FRI, 400.0)
    yield t
    t.p.close()


class TestTransactionsChangeEveryLayer:

    def test_before_any_transaction_the_portfolio_is_its_cash(self, tree):
        assert tree.revalue(MON_16) == CASH
        layers = tree.layers(MON_16)
        assert (layers["main"], layers["cash_portfolio"], layers["cash_holding"]) == (CASH, CASH, CASH)
        assert layers["share_portfolio"] is None            # no share sub-portfolio until the first trade

    def test_buy_at_the_valuation_price_moves_value_from_cash_to_shares(self, tree):
        tree.trade("AAPL", 10, 150.0, MON_16)
        assert tree.revalue(MON_16) == CASH                  # conservation: 1 500 cash became 1 500 of shares
        layers = tree.layers(MON_16)
        assert (layers["cash_portfolio"], layers["share_portfolio"], layers["AAPL"]) == (98_500.0, 1_500.0, 1_500.0)
        tree.assert_consistent(layers)

    def test_buy_below_the_close_raises_the_main_portfolio_value(self, tree):
        tree.trade("AAPL", 10, 145.0, MON_16)                # filled 5 below the 150 close
        assert tree.revalue(MON_16) == CASH + 50.0
        layers = tree.layers(MON_16)
        assert (layers["cash_portfolio"], layers["share_portfolio"], layers["AAPL"]) == (98_550.0, 1_500.0, 1_500.0)
        tree.assert_consistent(layers)

    def test_price_move_changes_holding_share_portfolio_and_main_but_not_cash(self, tree):
        tree.trade("AAPL", 10, 150.0, MON_16)
        tree.revalue(MON_16)
        tree.close("AAPL", MON, 160.0)                       # Monday bar, closed by Tuesday 16:00
        assert tree.revalue(TUE_16) == CASH + 100.0
        before, after = tree.layers(MON_16), tree.layers(TUE_16)
        assert (after["AAPL"], after["share_portfolio"]) == (1_600.0, 1_600.0)
        assert after["cash_portfolio"] == before["cash_portfolio"] == 98_500.0
        assert after["main"] - before["main"] == pytest.approx(100.0)
        tree.assert_consistent(after)

    def test_sell_realises_the_gain_into_cash(self, tree):
        tree.trade("AAPL", 10, 150.0, MON_16)
        tree.close("AAPL", MON, 160.0)
        tree.trade("AAPL", -4, 160.0, TUE_16)
        assert tree.revalue(TUE_16) == CASH + 100.0          # 6 x 160 + cash 99 140
        layers = tree.layers(TUE_16)
        assert (layers["cash_portfolio"], layers["AAPL"], layers["share_portfolio"]) == (99_140.0, 960.0, 960.0)
        tree.assert_consistent(layers)

    def test_second_share_adds_a_holding_to_the_same_sub_portfolio(self, tree):
        tree.trade("AAPL", 10, 150.0, MON_16)
        tree.trade("MSFT", 5, 400.0, MON_16)
        assert tree.revalue(MON_16) == CASH
        layers = tree.layers(MON_16)
        assert (layers["AAPL"], layers["MSFT"], layers["share_portfolio"]) == (1_500.0, 2_000.0, 3_500.0)
        assert layers["cash_portfolio"] == 96_500.0
        assert tree.p.session.query(CompanySharePortfolioPortfolioHoldingModel).count() == 1
        tree.assert_consistent(layers)

    def test_short_position_has_negative_value_in_every_layer_above_it(self, tree):
        tree.trade("MSFT", -3, 400.0, MON_16)
        assert tree.revalue(MON_16) == CASH
        layers = tree.layers(MON_16)
        assert (layers["MSFT"], layers["share_portfolio"], layers["cash_portfolio"]) == (-1_200.0, -1_200.0, 101_200.0)
        tree.assert_consistent(layers)


class TestAcrossSeveralDays:

    def test_every_layer_follows_the_books_day_after_day(self, tree):
        """Trades and price moves over three sessions; every layer is checked after each session."""
        # Monday: buy at Friday's closes -> value only moves from cash to shares
        tree.trade("AAPL", 10, 150.0, MON_16)
        tree.trade("MSFT", 2, 400.0, MON_16)
        assert tree.revalue(MON_16) == CASH
        mon = tree.layers(MON_16)
        assert (mon["cash_portfolio"], mon["AAPL"], mon["MSFT"], mon["share_portfolio"]) == \
            (97_700.0, 1_500.0, 800.0, 2_300.0)
        tree.assert_consistent(mon)

        # Tuesday: Monday closes AAPL 155 / MSFT 390, buy 5 more AAPL at 155
        tree.close("AAPL", MON, 155.0)
        tree.close("MSFT", MON, 390.0)
        tree.trade("AAPL", 5, 155.0, TUE_16)
        assert tree.revalue(TUE_16) == pytest.approx(100_030.0)   # +50 AAPL, -20 MSFT
        tue = tree.layers(TUE_16)
        assert (tue["cash_portfolio"], tue["AAPL"], tue["MSFT"], tue["share_portfolio"]) == \
            (96_925.0, 2_325.0, 780.0, 3_105.0)
        tree.assert_consistent(tue)

        # Wednesday: Tuesday closes AAPL 150 / MSFT 410, sell all MSFT at 410
        tree.close("AAPL", TUE, 150.0)
        tree.close("MSFT", TUE, 410.0)
        tree.trade("MSFT", -2, 410.0, WED_16)
        assert tree.revalue(WED_16) == pytest.approx(99_995.0)    # AAPL -25 on the 5 bought at 155, MSFT +20
        wed = tree.layers(WED_16)
        assert (wed["cash_portfolio"], wed["AAPL"], wed["share_portfolio"]) == (97_745.0, 2_250.0, 2_250.0)
        assert wed["MSFT"] in (0.0, None)                         # flat holding contributes nothing
        tree.assert_consistent(wed)

        # earlier snapshots are not rewritten by later sessions
        assert tree.layers(MON_16) == mon and tree.layers(TUE_16) == tue
