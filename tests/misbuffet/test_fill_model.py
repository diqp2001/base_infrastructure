"""P.08.04 backtest fills with costs: buy at the ask, sell at the bid, IBKR commission (in-memory SQLite, no IBKR)."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_price_history import (
    STMFrontierPriceReader,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import frequency
from src.application.services.misbuffet.algorithm.fill_model import (
    BidAskFillModel,
    CommissionModel,
    Fill,
    StoredBidAskQuotes,
)
from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService
from tests.misbuffet.sqlite_portfolio import SqlitePortfolio

FIXED = CommissionModel(per_share=0.005, minimum=1.0, max_pct_of_value=0.01)      # IBKR Fixed, US stocks
COSTS = {"fill": "bid_ask", "max_quote_age_minutes": 10,
         "commission": {"per_share": 0.005, "minimum": 1.0, "max_pct_of_value": 0.01}}


def test_commission_per_share_with_minimum_and_cap():
    assert FIXED(100, 50.0) == 1.0                        # 0.50 -> minimum 1.00
    assert FIXED(-3000, 12.36) == 15.0                    # 0.005 x 3000, a sell too
    assert FIXED(10, 5.0) == 0.5                          # 1 % of 50 USD caps the minimum


def test_buys_pay_the_ask_and_sells_receive_the_bid():
    model = BidAskFillModel.from_config(COSTS, quotes=lambda t, when: (49.98, 50.02))
    assert model("JPM", 300, 50.0, datetime(2026, 11, 3, 10)) == Fill(50.02, 1.5)
    assert model("JPM", -300, 50.0, datetime(2026, 11, 3, 10)) == Fill(49.98, 1.5)


@pytest.mark.parametrize("quote,word", [(None, "no bid / ask"), ((50.1, 50.0), "invalid"), ((0.0, 1.0), "invalid")])
def test_no_usable_quote_means_no_fill(quote, word):
    fill = BidAskFillModel(lambda t, when: quote, FIXED)("JPM", 10, 50.0, datetime(2026, 11, 3, 10))
    assert fill.price is None and word in fill.reason


def test_the_config_must_ask_for_bid_ask_fills():
    with pytest.raises(ValueError):
        BidAskFillModel.from_config({**COSTS, "fill": "close"}, quotes=lambda t, w: None)
    with pytest.raises(KeyError):
        CommissionModel.from_config({"per_share": 0.005})                 # no default commission values


@pytest.fixture
def book():
    b = SqlitePortfolio(cash=100_000.0, shares=("JPM",))
    yield b
    b.close()


def test_a_backtest_trade_is_booked_at_the_ask_with_its_commission(book):
    book.tm.fill_model = BidAskFillModel(lambda t, when: (99.9, 100.1), FIXED)
    assert book.trade("JPM", 300, 100.0)
    assert book.qty("JPM") == 300 and book.cash() == pytest.approx(100_000.0 - 300 * 100.1 - 1.5)
    assert book.trade("JPM", -300, 100.0)
    assert book.qty("JPM") == 0
    assert book.cash() == pytest.approx(100_000.0 - 300 * 0.2 - 3.0)       # the spread and two commissions


def test_a_trade_without_a_quote_is_neither_sent_nor_booked(book):
    sent = []
    book.tm.fill_model = BidAskFillModel(lambda t, when: None, FIXED)
    assert not book.trade("JPM", 10, 100.0, submit=lambda *a, **k: sent.append(a))
    assert sent == [] and book.qty("JPM") == 0 and book.cash() == 100_000.0 and book.orders() == []


# ---------------------------------------------------------------- stored BID / ASK bars
BAR = 10
T = datetime(2026, 11, 3, 10, 0)                         # decision time: the 09:50 bar has just closed


def seed(session, subgroup, values, entity_id=1):
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    factor = CompanyShareFactorModel(name="close", group="price", subgroup=subgroup, frequency=frequency(BAR),
                                     data_type="numeric", source="ibkr", definition="close",
                                     factor_type="company_share_factor")
    session.add(factor)
    session.commit()
    session.bulk_insert_mappings(FactorValueModel, [
        {"factor_id": factor.id, "entity_id": entity_id, "entity_type": "CompanyShare", "date": start,
         "value": repr(px)} for start, px in values])
    session.commit()


@pytest.fixture
def history(book):
    service = MarketDataHistoryService(SimpleNamespace(entity_service=SimpleNamespace(repository_factory=book.factory)))
    service.set_frontier(T)
    return service


def bars(*prices, last_start=T - timedelta(minutes=BAR)):
    return [(last_start - timedelta(minutes=BAR * i), px) for i, px in enumerate(reversed(prices))][::-1]


def test_stored_quotes_are_the_bid_and_ask_closes_of_the_bar_just_closed(book, history):
    seed(book.session, "BID", bars(49.0, 49.9))
    seed(book.session, "ASK", bars(49.2, 50.1))
    seed(book.session, "BID", [(T, 60.0)])                          # the 10:00 bar is still open: hidden
    quotes = StoredBidAskQuotes(history, {"JPM": 1}, frequency(BAR), BAR, max_age=timedelta(0))
    assert quotes("JPM", T) == (49.9, 50.1)
    assert quotes("XOM", T) is None


def test_stale_or_one_sided_quotes_are_refused(book, history):
    seed(book.session, "BID", bars(49.9, last_start=T - timedelta(minutes=3 * BAR)))
    seed(book.session, "ASK", bars(50.1, last_start=T - timedelta(minutes=3 * BAR)))
    assert StoredBidAskQuotes(history, {"JPM": 1}, frequency(BAR), BAR, max_age=timedelta(minutes=10))("JPM", T) is None
    assert StoredBidAskQuotes(history, {"JPM": 1}, frequency(BAR), BAR,
                              max_age=timedelta(minutes=20))("JPM", T) == (49.9, 50.1)


def test_the_stm_close_reader_never_reads_a_bid_or_ask_close_as_the_price(book, history):
    seed(book.session, "TRADES", bars(50.0, 50.5))
    seed(book.session, "BID", bars(1.0, 1.0))
    seed(book.session, "ASK", bars(99.0, 99.0))
    closes = STMFrontierPriceReader(history, frequency=frequency(BAR), bar_minutes=BAR).load_close_panel({1: "JPM"})
    assert list(closes["JPM"].dropna()) == [50.0, 50.5]


def test_the_10m_backtest_imports_bid_and_ask_bars_for_its_fills():
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.config import get_config
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.models.model_trainer import (
        STMModelTrainer as ModelTrainer,
    )
    trainer = ModelTrainer.__new__(ModelTrainer)
    trainer.config = get_config()
    assert trainer.what_to_show() == ("TRADES", "BID", "ASK")
    assert BidAskFillModel.from_config(trainer.config["execution_costs"], quotes=lambda t, w: None).commission == FIXED
    trainer.config = {**trainer.config, "execution_costs": None}
    assert trainer.what_to_show() == ("TRADES",)
