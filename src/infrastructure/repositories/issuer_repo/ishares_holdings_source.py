"""
iShares (BlackRock) US: fund list from the product-screener JSON, holdings from each product page's
latest-holdings.csv (the older .ajax download links now return the HTML page). The UK site's CSV layout (no fund
name line, other date format, 'Shares' column) is parsed too.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from typing import List

from src.domain.entities.finance.dispersion.etf_holdings import EQUITY, EtfHoldingsSnapshot, EtfListing, HoldingLine
from src.infrastructure.repositories.issuer_repo.issuer_holdings_source import IssuerHoldingsSource, clean_text, number

BASE_URL = "https://www.ishares.com"
SCREENER_URL = (BASE_URL + "/us/product-screener/product-screener-v3.1.jsn?dcrPath=/templatedata/config/"
                "product-screener-v3/data/en/us-ishares/ishares-product-screener-backend-config"
                "&siteEntryPassthrough=true")
AS_OF_FORMATS = ("%b %d, %Y", "%d/%b/%Y")
ASSET_CLASSES = {"equity": EQUITY, "cash": "cash", "cash collateral and margins": "cash", "fx": "fx",
                 "futures": "future", "money market": "money_market"}


class ISharesHoldingsSource(IssuerHoldingsSource):
    ISSUER = "ishares"
    FILE_EXT = ".csv"

    def fetch_listings(self) -> List[EtfListing]:
        return parse_screener(self.fetch(SCREENER_URL))

    def holdings_url(self, listing: EtfListing) -> str:
        return BASE_URL + listing.product_ref.rstrip("/") + "/latest-holdings.csv"

    def parse_holdings(self, raw: bytes, listing: EtfListing, source: str,
                       retrieved_at: datetime) -> EtfHoldingsSnapshot:
        return parse_holdings_csv(raw, listing.ticker, source, retrieved_at)


def parse_screener(raw: bytes) -> List[EtfListing]:
    products = json.loads(raw.decode("utf-8"))
    listings = []
    for p in products.values():
        if "etf" not in (p.get("productView") or []) or not p.get("localExchangeTicker") or not p.get("productPageUrl"):
            continue
        tna = p.get("totalNetAssets")
        listings.append(EtfListing(
            ticker=p["localExchangeTicker"].strip().upper(), name=clean_text(p.get("fundName")), issuer="iShares",
            asset_class=p.get("aladdinAssetClass"), sub_asset_class=p.get("aladdinSubAssetClass"),
            country=p.get("aladdinCountry"), product_ref=p["productPageUrl"],
            total_net_assets=tna.get("r") if isinstance(tna, dict) else None))
    return sorted(listings, key=lambda l: l.ticker)


def _as_of(value: str) -> date:
    for fmt in AS_OF_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unknown holdings date {value!r}")


def parse_holdings_csv(raw: bytes, etf_ticker: str, source: str, retrieved_at: datetime) -> EtfHoldingsSnapshot:
    text = raw.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    as_of, fund_name, header_at = None, None, None
    for i, row in enumerate(rows):
        if not row:
            continue
        if row[0].strip() == "Fund Holdings as of" and len(row) > 1:
            as_of = _as_of(row[1])
        elif row[0].strip() == "Ticker":
            header_at = i
            break
        elif i == 0 and len(row) == 1:
            fund_name = clean_text(row[0])
    if as_of is None or header_at is None:
        raise ValueError("not an iShares holdings file (no 'Fund Holdings as of' line or no header)")
    header = [h.strip() for h in rows[header_at]]
    lines = []
    for row in rows[header_at + 1:]:
        if len(row) < len(header) or not any(cell.strip() for cell in row):
            break                                          # end of the table (a footer, if any, follows)
        r = dict(zip(header, (cell.strip() for cell in row)))
        weight = number(r.get("Weight (%)"))
        lines.append(HoldingLine(
            ticker=r.get("Ticker", "").upper(), name=clean_text(r.get("Name")),
            weight=None if weight is None else weight / 100.0,
            asset_class=ASSET_CLASSES.get(r.get("Asset Class", "").lower(), "other"),
            sector=r.get("Sector") or None, exchange=r.get("Exchange") or None,
            currency=r.get("Market Currency") or r.get("Currency") or None,
            market_value=number(r.get("Market Value")), quantity=number(r.get("Quantity") or r.get("Shares"))))
    return EtfHoldingsSnapshot(etf_ticker=etf_ticker, issuer="iShares", as_of=as_of, lines=tuple(lines),
                               source=source, retrieved_at=retrieved_at, fund_name=fund_name)
