"""BI-036: the MarketDataService import requests TRADES bars, so its price factors are the TRADES series — not the
repository default (MIDPOINT), which IBKR refuses for stocks without a quote subscription. No IBKR, no DB."""

from datetime import datetime
from types import SimpleNamespace

from src.application.services.misbuffet.data.market_data_service import MarketDataService
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare


def test_the_import_creates_its_price_factors_in_the_trades_series():
    calls = []

    def create_or_get_batch_ibkr(data, cls, **kwargs):
        calls.append((list(data), kwargs))
        return []                                                      # no factor: the import stops there

    client = SimpleNamespace(ib_connection=SimpleNamespace(connected_flag=True))
    entity_service = SimpleNamespace(repository_factory=SimpleNamespace(ibkr_client=client),
                                     create_or_get_batch_ibkr=create_or_get_batch_ibkr)
    service = MarketDataService(entity_service)
    share = CompanyShare.__new__(CompanyShare)
    share._id = 7
    service._get_entity_by_ticker = lambda ticker, cls: share
    service._get_point_in_time_data("MSFT", CompanyShare, datetime(2026, 10, 21), "10 mins", "1 W")
    factors, kwargs = calls[0]
    assert kwargs["what_to_show"] == "TRADES"
    assert {f["entity_symbol"]: f["subgroup"] for f in factors} == {
        n: "TRADES" for n in ("high", "open", "low", "close", "volume")}
