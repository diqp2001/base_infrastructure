"""Dispersion screener P.02: issuer holdings parsing (iShares CSV US / UK, SPDR XLSX), the archive that gives
history, and the constituent rules (spec test 5: 49 constituents eligible, 50 rejected). Files are small inline
copies of the issuers' layouts; nothing is downloaded and nothing touches a database."""

import io
import json
from datetime import date, datetime

import openpyxl
import pytest

from src.domain.entities.finance.dispersion.etf_holdings import (
    EQUITY, EtfHoldingsSnapshot, EtfListing, HoldingLine, listing_rejections, prepare_constituents,
)
from src.domain.entities.finance.dispersion.screen_config import DispersionScreenConfig
from src.infrastructure.repositories.issuer_repo.ishares_holdings_source import (
    ISharesHoldingsSource, parse_holdings_csv, parse_screener,
)
from src.infrastructure.repositories.issuer_repo.ssga_holdings_source import parse_fund_list, parse_holdings_xlsx

CONFIG = DispersionScreenConfig()
NOW = datetime(2026, 11, 5, 9, 0)

ISHARES_US = (
    'iShares MSCI Brazil ETF\n'
    'Fund Holdings as of,"Nov 04, 2026"\n'
    'Inception Date,"Jul 10, 2000"\n'
    'Shares Outstanding,"291,800,000.00"\n'
    'Stock,"-"\n'
    '\n'
    'Ticker,Name,Sector,Asset Class,Market Value,Weight (%),Notional Value,Quantity,Price,Location,Exchange,'
    'Currency,FX Rate,Market Currency,Accrual Date\n'
    '"NU","NU HOLDINGS CLASS A","Financials","Equity","823,589,227.23","60.00","823,589,227.23","68,689,677.00",'
    '"11.99","Brazil","NYSE","USD","1.00","USD","-"\n'
    '"VALE3","CIA VALE DO RIO DOCE SH","Materials","Equity","808,866,384.80","38.00","808,866,384.80",'
    '"71,239,269.00","11.35","Brazil","XBSP","USD","5.49","BRL","-"\n'
    '"BRL","BRL CASH","Cash and/or Derivatives","Cash","282,557,515.09","3.04","282,557,515.09",'
    '"1,551,622,210.00","18.21","Brazil","-","USD","5.49","BRL","-"\n'
    '"USD","USD CASH","Cash and/or Derivatives","Cash","-1,000.00","-1.04","-1,000.00","-1,000.00","1.00",'
    '"United States","-","USD","1.00","USD","-"\n'
    '"XBZ6","MINI BOVESPA DEC 26","Cash and/or Derivatives","Futures","0.00","0.00","5,000.00","10.00","1.00",'
    '"Brazil","-","USD","1.00","BRL","-"\n'
).encode("utf-8")

ISHARES_UK = (
    'Fund Holdings as of,"04/Nov/2026"\n'
    '\n'
    'Ticker,Name,Sector,Asset Class,Market Value,Weight (%),Notional Value,Shares,Price,Location,Exchange,'
    'Market Currency\n'
    '"JPM","JPMORGAN CHASE & CO","Financials","Equity","82,665,568.92","50.00","82,665,568.92","234,772.00",'
    '"352.11","United States","New York Stock Exchange Inc.","USD"\n'
    '"BAC","BANK OF AMERICA CORP","Financials","Equity","82,000,000.00","50.00","82,000,000.00","1,000.00",'
    '"52.00","United States","New York Stock Exchange Inc.","USD"\n'
).encode("utf-8")


def spdr_xlsx(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "holdings"
    for row in [("Fund Name:", "State Street� Utilities Select Sector SPDR� ETF"), ("Ticker Symbol:", "XLU"),
                ("Holdings:", "As of 04-Nov-2026"), (),
                ("Name", "Ticker", "Identifier", "SEDOL", "Weight", "Sector", "Shares Held", "Local Currency")]:
        ws.append(row)
    for row in rows:
        ws.append(row)
    ws.append(())
    ws.append(("State Street Global Advisors (SSGA) is now State Street Investment Management.",))
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


XLU = spdr_xlsx([
    ("NEXTERA ENERGY INC", "NEE", "65339F101", "2328915", 60.0, "-", 36623512, "USD"),
    ("SOUTHERN CO/THE", "SO", "842587107", "2829601", 39.0, "-", 20196886, "USD"),
    ("SSI US GOV MONEY MARKET CLASS", "-", "924QSGII3", "-", 0.5, "-", 1000, "USD"),
    ("XAU UTILITIES     DEC26", "IXSZ6", "ADI393HZ6", "-", 0.0, "-", 50000, "USD"),
    ("US DOLLAR", "-", "999USDZ92", "-", 0.5, "-", 1486090.24, "USD"),
])


def snapshot(n, as_of=date(2026, 11, 4), weight=None, extra=()):
    w = weight if weight is not None else 1.0 / n
    lines = tuple(HoldingLine(ticker=f"T{i}", name=f"Stock {i}", weight=w, asset_class=EQUITY) for i in range(n))
    return EtfHoldingsSnapshot("ETF", "iShares", as_of, lines + tuple(extra), "test", NOW)


class TestParsers:

    def test_ishares_us_file(self):
        snap = parse_holdings_csv(ISHARES_US, "EWZ", "url", NOW)
        assert (snap.fund_name, snap.as_of, len(snap.lines)) == ("iShares MSCI Brazil ETF", date(2026, 11, 4), 5)
        assert [l.asset_class for l in snap.lines] == [EQUITY, EQUITY, "cash", "cash", "future"]
        nu = snap.lines[0]
        assert (nu.weight, nu.market_value, nu.quantity, nu.exchange) == (0.60, 823589227.23, 68689677.0, "NYSE")
        assert snap.lines[3].weight == pytest.approx(-0.0104)

    def test_ishares_uk_file(self):
        snap = parse_holdings_csv(ISHARES_UK, "BNKS", "url", NOW)
        assert (snap.fund_name, snap.as_of) == (None, date(2026, 11, 4))
        assert [(l.ticker, l.quantity) for l in snap.lines] == [("JPM", 234772.0), ("BAC", 1000.0)]

    def test_an_html_page_is_not_a_holdings_file(self):
        with pytest.raises(ValueError):
            parse_holdings_csv(b"<html><body>iShares</body></html>", "EWZ", "url", NOW)

    def test_spdr_file(self):
        snap = parse_holdings_xlsx(XLU, "XLU", "url", NOW)
        assert (snap.fund_name, snap.as_of) == ("State Street Utilities Select Sector SPDR ETF", date(2026, 11, 4))
        assert [l.asset_class for l in snap.lines] == [EQUITY, EQUITY, "money_market", "future", "cash"]
        assert snap.lines[0].weight == pytest.approx(0.60) and snap.lines[0].identifier == "65339F101"

    def test_fund_lists(self):
        screener = {"1": {"localExchangeTicker": "XLU1", "fundName": "iShares A ETF", "productView": ["etf"],
                          "productPageUrl": "/us/products/1/a", "aladdinAssetClass": "Equity",
                          "totalNetAssets": {"d": "1", "r": 1.5}},
                    "2": {"localExchangeTicker": "MF", "fundName": "Mutual", "productView": ["mutualfund"],
                          "productPageUrl": "/us/products/2/b"}}
        listings = parse_screener(json.dumps(screener).encode())
        assert [(l.ticker, l.asset_class, l.total_net_assets) for l in listings] == [("XLU1", "Equity", 1.5)]
        finder = {"data": {"funds": {"etfs": {"datas": [{"fundTicker": "XLU�", "fundName": "Utilities SPDR�",
                                                         "primaryExchange": "NYSE ARCA", "fundUri": "/x",
                                                         "keywords": "Utilities SPDR, XLU, Equity, XLU US, US81369Y8865"},
                                                        {"fundTicker": "BIL", "fundName": "T-Bill", "fundUri": "/y",
                                                         "keywords": "T-Bill, BIL, Fixed Income, BIL US"}]}}}}
        assert [(l.ticker, l.name, l.asset_class) for l in parse_fund_list(json.dumps(finder).encode())] == [
            ("BIL", "T-Bill", "Fixed Income"), ("XLU", "Utilities SPDR", "Equity")]


class TestConstituentRules:

    def test_49_constituents_eligible_50_rejected(self):          # specification test 5
        ok = prepare_constituents(snapshot(49), CONFIG, date(2026, 11, 5))
        assert ok.ok and ok.count == 49 and sum(ok.weights.values()) == pytest.approx(1.0)
        too_many = prepare_constituents(snapshot(50), CONFIG, date(2026, 11, 5))
        assert not too_many.ok and "50 equity constituents (max 49)" in too_many.reasons

    def test_weights_normalised_without_cash_and_derivatives(self):
        snap = parse_holdings_csv(ISHARES_US, "EWZ", "url", NOW)
        cw = prepare_constituents(snap, CONFIG, date(2026, 11, 5))
        assert cw.ok and cw.equity_share == pytest.approx(0.98)
        assert cw.weights == pytest.approx({"NU": 0.60 / 0.98, "VALE3": 0.38 / 0.98})

    def test_rejections(self):
        day = date(2026, 11, 5)
        assert "1 equity constituent(s) (min 2)" in prepare_constituents(snapshot(1), CONFIG, day).reasons
        stale = prepare_constituents(snapshot(10, as_of=date(2026, 10, 1)), CONFIG, day)
        assert any("days old" in r for r in stale.reasons)
        future = prepare_constituents(snapshot(10, as_of=date(2026, 11, 6)), CONFIG, day)
        assert any("after the screening date" in r for r in future.reasons)
        swaps = snapshot(10, weight=0.05, extra=(HoldingLine("SWAP", "TRS", 0.5, "other"),))
        assert any("derivatives" in r for r in prepare_constituents(swaps, CONFIG, day).reasons)
        no_weight = snapshot(3, extra=(HoldingLine("X", "X", None, EQUITY),))
        assert any("no weight" in r for r in prepare_constituents(no_weight, CONFIG, day).reasons)

    def test_listing_rejections(self):
        plain = EtfListing("XLU", "Utilities Select Sector SPDR", "SPDR")
        assert listing_rejections(plain, CONFIG) == []
        assert listing_rejections(EtfListing("AGG", "Core Bond", "iShares", asset_class="Fixed Income"), CONFIG)
        assert listing_rejections(EtfListing("SSO", "ProShares Ultra S&P500", "X"), CONFIG)
        assert "inverse" in listing_rejections(EtfListing("SH", "Short S&P", "X", leverage_factor=-1), CONFIG)
        assert listing_rejections(EtfListing("S", "Swap fund", "X", replication="synthetic"), CONFIG)


class TestProjectManager:

    def test_a_run_writes_the_universe_and_its_manifest(self, tmp_path):
        from src.application.managers.project_managers.etf_dispersion_screener_project.project_manager import (
            EtfDispersionScreenerProjectManager,
        )
        source = ISharesHoldingsSource(str(tmp_path / "archive"), today=lambda: date(2026, 11, 5),
                                       min_interval_seconds=0, fetch=lambda url: ISHARES_US)
        source.fetch_listings = lambda: [
            EtfListing("EWZ", "iShares MSCI Brazil ETF", "iShares", asset_class="Equity", product_ref="/us/products/1/a"),
            EtfListing("AGG", "iShares Core US Aggregate Bond ETF", "iShares", asset_class="Fixed Income",
                       product_ref="/us/products/2/b")]
        manager = EtfDispersionScreenerProjectManager(
            config={"results_dir": str(tmp_path / "results"), "issuers": [], "holdings_archive_dir": "",
                    "download_interval_seconds": 0}, sources=[(source, source)])
        result = manager.run(date(2026, 11, 5))
        assert result.counts() == {"eligible": 1, "listing rejected": 1}
        out = tmp_path / "results" / "2026-11-05"
        universe = json.loads((out / "universe.json").read_text(encoding="utf-8"))
        ewz = next(e for e in universe["etfs"] if e["ticker"] == "EWZ")
        assert ewz["constituents"] == 2 and ewz["weights"]["NU"] == pytest.approx(0.60 / 0.98)
        assert json.loads((out / "run_manifest.json").read_text())["outcome"] == "completed"
        assert (out / "universe.csv").read_text(encoding="utf-8").startswith("ticker,name,issuer")


class TestArchive:

    def test_today_downloads_and_archives_a_past_date_reads_the_archive(self, tmp_path):
        calls = []
        today = {"d": date(2026, 11, 5)}
        source = ISharesHoldingsSource(str(tmp_path), fetch=lambda url: calls.append(url) or ISHARES_US,
                                       today=lambda: today["d"], min_interval_seconds=0)
        listing = EtfListing("EWZ", "iShares MSCI Brazil ETF", "iShares", asset_class="Equity",
                             product_ref="/us/products/239612/ishares-msci-brazil-etf")
        snap = source.get_holdings(listing, date(2026, 11, 5))
        assert snap.as_of == date(2026, 11, 4)
        assert calls == ["https://www.ishares.com/us/products/239612/ishares-msci-brazil-etf/latest-holdings.csv"]
        assert (tmp_path / "ishares" / "EWZ" / "2026-11-04.csv").read_bytes() == ISHARES_US

        today["d"] = date(2026, 12, 1)                          # a month later: history from the archive
        old = source.get_holdings(listing, date(2026, 11, 4))
        assert old.as_of == date(2026, 11, 4) and old.source.endswith("2026-11-04.csv") and len(calls) == 1
        assert source.get_holdings(listing, date(2026, 11, 3)) is None    # nothing known that early

    def test_a_failed_download_is_none_not_an_exception(self, tmp_path):
        def boom(url):
            raise ConnectionError("down")
        source = ISharesHoldingsSource(str(tmp_path), fetch=boom, today=lambda: date(2026, 11, 5),
                                       min_interval_seconds=0)
        listing = EtfListing("EWZ", "x", "iShares", product_ref="/us/products/1/x")
        assert source.get_holdings(listing, date(2026, 11, 5)) is None
