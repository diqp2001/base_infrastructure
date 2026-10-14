"""
CurrencyYieldFactor — the benchmark rate future is the contract of the calculation date.

The contract symbol encodes its expiry (SR3H6 = Mar-2026, SR3M6 = Jun-2026, SR3Z6 = Dec-2026), so
the currency's related entity must be the contract computed from the date being calculated, never
another contract of the same root (whose price describes a different period) and never today's.
"""

import logging
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.application.services.data.entities.factor.factor_value_resolution_service import FactorValueResolutionService
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.future.bond_future_repository import (
    BondFutureRepository,
)
from tests.misbuffet.sqlite_portfolio import SqlitePortfolio

logging.getLogger("sqlite_portfolio").setLevel(logging.CRITICAL)


@pytest.mark.parametrize("day, symbol", [
    (date(2025, 11, 3), "SR3Z5"),
    (date(2026, 1, 5), "SR3H6"),
    (date(2026, 3, 20), "SR3H6"),       # March contract until (approx.) the 21st
    (date(2026, 3, 21), "SR3M6"),
    (date(2026, 4, 10), "SR3M6"),
    (date(2026, 9, 30), "SR3Z6"),
    (date(2026, 12, 22), "SR3H7"),      # rolls into next year's March
])
def test_front_month_symbol_follows_the_date(day, symbol):
    assert BondFutureRepository.front_month_symbol("SR3", day) == symbol


@pytest.fixture
def book():
    p = SqlitePortfolio(cash=100_000.0, shares=())          # registers the USD currency tree
    yield p
    p.close()


def usd(p):
    return p.factory.get_local_repository("Currency").get_by_symbol("USD") if hasattr(
        p.factory.get_local_repository("Currency"), "get_by_symbol") else _usd_by_query(p)


def _usd_by_query(p):
    from src.infrastructure.models.finance.financial_assets.currency import CurrencyModel
    row = p.session.query(CurrencyModel).filter(CurrencyModel.symbol == "USD").first()
    return p.factory.get_local_repository("Currency").get_by_id(row.id)


def store(p, *symbols):
    """Contracts as the IBKR repository stores them (start_date set; BondFutureRepository._create_or_get
    cannot create one locally because it never sets the NOT NULL start_date)."""
    from src.domain.entities.finance.financial_assets.derivatives.future.bond_future import BondFuture
    repo = p.factory.get_local_repository("BondFuture")
    ids = {}
    for s in symbols:
        added = repo.add(BondFuture(id=None, name=f"{s} Bond Future", symbol=s, start_date=date(2026, 1, 1),
                                    currency_id=usd(p).id, exchange_id=1, underlying_asset_id=usd(p).id))
        assert added is not None, s
        ids[s] = added.id
    return ids


def related(p, target_date, ibkr_repo=None):
    currency = usd(p)
    with patch.object(p.factory, "get_ibkr_repository", return_value=ibkr_repo, create=True):
        return p.factory.get_local_repository("Currency").get_related_entities(currency.id, target_date=target_date)


class TestContractOfTheDate:

    @pytest.mark.parametrize("when, symbol", [
        (datetime(2026, 1, 5, 16), "SR3H6"),
        (datetime(2026, 4, 10, 16), "SR3M6"),
        (date(2026, 10, 1), "SR3Z6"),
        ("2026-04-10 16:00:00", "SR3M6"),
    ])
    def test_each_date_gets_its_own_contract(self, book, when, symbol):
        ids = store(book, "SR3H6", "SR3M6", "SR3Z6")
        [future] = related(book, when)
        assert (future.symbol, future.id) == (symbol, ids[symbol])

    def test_another_contract_of_the_root_is_never_used(self, book):
        """Regression: get_by_root_symbol fell back to any stored SR3 contract (e.g. SR3Z6 from a
        project config) when the date's contract was not stored locally."""
        store(book, "SR3Z6")
        ibkr = MagicMock()
        ibkr._create_or_get.side_effect = lambda symbol: MagicMock(symbol=symbol)
        [future] = related(book, datetime(2026, 1, 5, 16), ibkr_repo=ibkr)
        assert future.symbol == "SR3H6"
        ibkr._create_or_get.assert_called_once_with("SR3H6")

    def test_missing_contract_without_ibkr_gives_nothing(self, book):
        store(book, "SR3Z6")
        assert related(book, datetime(2026, 1, 5, 16), ibkr_repo=None) == []

    def test_no_date_selects_no_contract(self, book):
        """Regression: without a date the contract of *today* was used, also for historical dates."""
        store(book, "SR3H6", "SR3M6", "SR3Z6")
        ibkr = MagicMock()
        assert related(book, None, ibkr_repo=ibkr) == []
        ibkr._create_or_get.assert_not_called()

    def test_root_lookup_requires_a_date(self, book):
        store(book, "SR3H6")
        with pytest.raises(ValueError):
            book.factory.get_local_repository("BondFuture").get_by_root_symbol("SR3", None)


class TestResolverForwardsTheCalculationDate:

    def test_related_entities_of_a_currency_follow_the_calculation_date(self, book):
        store(book, "SR3H6", "SR3M6")
        service = FactorValueResolutionService(factory=book.factory, logger=logging.getLogger("x"))
        currency = usd(book)
        with patch.object(book.factory, "get_ibkr_repository", return_value=None, create=True):
            jan = service._get_related_entities(currency, "local", target_date=datetime(2026, 1, 5, 16))
            apr = service._get_related_entities(currency, "local", target_date=datetime(2026, 4, 10, 16))
        assert [f.symbol for f in jan] == ["SR3H6"]
        assert [f.symbol for f in apr] == ["SR3M6"]

    def test_aggregated_resolution_passes_its_date(self, book):
        service = FactorValueResolutionService(factory=book.factory, logger=logging.getLogger("x"))
        seen = []
        with patch.object(service, "_get_related_entities",
                          side_effect=lambda entity, repo_type, target_date=None: seen.append(target_date) or []):
            service.resolve_aggregated_factor_value(MagicMock(), usd(book), datetime(2026, 4, 10, 16))
        assert seen == [datetime(2026, 4, 10, 16)]
