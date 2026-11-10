"""
State Street (SPDR) US: fund list from the fund-finder JSON, holdings from the daily XLSX
(holdings-daily-us-en-<ticker>.xlsx). The XLSX has no asset-class column: cash, money market and futures lines are
recognised by their ticker / name (ticker '-', 'US DOLLAR', 'MONEY MARKET', a futures month code).
"""

from __future__ import annotations

import io
import json
import re
from datetime import datetime
from typing import List

from src.domain.ports.finance.dispersion.etf_holdings import EQUITY, EtfHoldingsSnapshot, EtfListing, HoldingLine
from src.infrastructure.repositories.issuer_repo.issuer_holdings_source import IssuerHoldingsSource, clean_text, number

FUND_LIST_URL = ("https://www.ssga.com/bin/v1/ssmp/fund/fundfinder?country=us&language=en&role=intermediary"
                 "&product=etfs&ui=fund-finder")
HOLDINGS_URL = "https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-{}.xlsx"
FUTURE_NAME = re.compile(r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\d{2}\b")
# the fund list has no asset-class field; each fund's "keywords" carries it ("..., XLU, Equity, XLU US, ...")
ASSET_CLASS_KEYWORDS = ("Equity", "Fixed Income", "Alternative", "Multi-Asset", "Cash")


class SSGAHoldingsSource(IssuerHoldingsSource):
    ISSUER = "ssga"
    FILE_EXT = ".xlsx"

    def fetch_listings(self) -> List[EtfListing]:
        return parse_fund_list(self.fetch(FUND_LIST_URL))

    def holdings_url(self, listing: EtfListing) -> str:
        return HOLDINGS_URL.format(listing.ticker.lower())

    def parse_holdings(self, raw: bytes, listing: EtfListing, source: str,
                       retrieved_at: datetime) -> EtfHoldingsSnapshot:
        return parse_holdings_xlsx(raw, listing.ticker, source, retrieved_at)


def parse_fund_list(raw: bytes) -> List[EtfListing]:
    funds = json.loads(raw.decode("utf-8"))["data"]["funds"]["etfs"]["datas"]
    listings = []
    for f in funds:
        ticker = re.sub(r"[^A-Z0-9.]", "", str(f.get("fundTicker", "")).upper())
        if not ticker:
            continue
        keywords = [k.strip() for k in str(f.get("keywords", "")).split(",")]
        asset_class = next((k for k in keywords if k in ASSET_CLASS_KEYWORDS), None)
        listings.append(EtfListing(ticker=ticker, name=clean_text(f.get("fundName")), issuer="SPDR",
                                   asset_class=asset_class, exchange=f.get("primaryExchange"),
                                   product_ref=f.get("fundUri")))
    return sorted(listings, key=lambda l: l.ticker)


def _asset_class(ticker: str, name: str) -> str:
    upper = name.upper()
    if FUTURE_NAME.search(upper):
        return "future"
    if "MONEY MARKET" in upper:
        return "money_market"
    if ticker in ("", "-") or upper in ("US DOLLAR", "CASH") or upper.endswith(" CASH"):
        return "cash"
    return EQUITY


def parse_holdings_xlsx(raw: bytes, etf_ticker: str, source: str, retrieved_at: datetime) -> EtfHoldingsSnapshot:
    import openpyxl
    sheet = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True).active
    rows = [tuple(r) for r in sheet.iter_rows(values_only=True)]
    fund_name, as_of, header_at = None, None, None
    for i, row in enumerate(rows):
        first = str(row[0] or "").strip() if row else ""
        if first == "Fund Name:":
            fund_name = clean_text(row[1])
        elif first == "Holdings:":
            as_of = datetime.strptime(str(row[1]).replace("As of", "").strip(), "%d-%b-%Y").date()
        elif first == "Name" and len(row) > 1 and str(row[1] or "").strip() == "Ticker":
            header_at = i
            break
    if as_of is None or header_at is None:
        raise ValueError("not an SPDR holdings file (no 'Holdings:' date or no header)")
    header = [str(h or "").strip() for h in rows[header_at]]
    lines = []
    for row in rows[header_at + 1:]:
        if not row or all(cell in (None, "") for cell in row):
            break                                          # blank row: the disclaimer follows
        r = dict(zip(header, row))
        ticker = str(r.get("Ticker") or "").strip().upper()
        name = clean_text(r.get("Name"))
        weight = number(r.get("Weight"))
        identifier = str(r.get("Identifier") or "").strip()
        lines.append(HoldingLine(
            ticker=ticker, name=name, weight=None if weight is None else weight / 100.0,
            asset_class=_asset_class(ticker, name), sector=None if r.get("Sector") in (None, "-") else r.get("Sector"),
            currency=r.get("Local Currency"), quantity=number(r.get("Shares Held")),
            identifier=identifier if identifier not in ("", "-") else None))
    return EtfHoldingsSnapshot(etf_ticker=etf_ticker, issuer="SPDR", as_of=as_of, lines=tuple(lines),
                               source=source, retrieved_at=retrieved_at, fund_name=fund_name)
