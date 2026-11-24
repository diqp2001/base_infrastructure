"""
Point-in-time S&P 500 constituents, built from Wikipedia (owner's choice, 2026-11-23):

    "List of S&P 500 companies"              today's constituents (table id="constituents")
    "Historical components of the S&P 500"   every dated change: effective date, added ticker, removed ticker

Today's members are rolled back change by change to BASE_DATE (a member added after a date was not in the index then;
one removed after it was), then IndexMembership applies the changes forward, so ``members_at(day)`` = the members in
force on that day (a change is effective before the open of its date), exactly as for the DJIA (djia_membership).

Tickers: Wikipedia's current list uses today's tickers, the change history the ticker at the time. TICKER_ALIASES maps
a historical ticker to today's when the same company renamed its symbol, so one company is one member. Changes that
do not fit (a ticker added twice, removed while absent ...) are kept in ``anomalies``, never silently dropped.

The parsed snapshot is cached as JSON (results/sp500/membership.json: the two pages' text is not re-read). Fetching is
SP500WikipediaSource (infrastructure); everything here is pure parsing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from src.application.services.dispersion.index_membership import IndexMembership, MembershipChange

ETF = "SPY"
BASE_DATE = date(2007, 1, 2)
ROOT = Path(__file__).resolve().parents[4]
CACHE = ROOT / "results" / "sp500" / "membership.json"

# historical ticker -> today's ticker of the same company (symbol renames while in the index)
TICKER_ALIASES: Dict[str, str] = {
    "FB": "META", "ANTM": "ELV", "COG": "CTRA", "FLT": "CPAY", "PKI": "RVTY", "TMK": "GL", "WLTW": "WTW",
    "HFC": "DINO", "ABC": "COR", "FISV": "FI", "RE": "EG", "BLL": "BALL", "DISCA": "WBD", "CTL": "LUMN",
    "PEAK": "DOC", "ADS": "BFH", "FBHS": "FBIN", "GPS": "GAP", "PCLN": "BKNG", "HRS": "LHX", "JEC": "J",
    "LUK": "JEF", "KORS": "CPRI", "DLPH": "APTV", "CDAY": "DAY", "UA.C": "UA", "TSO": "ANDV", "JOYG": "JOY",
}

_SYMBOL = re.compile(r"\{\{\s*(?:[A-Za-z ]*Symbol|nyse|nasdaq|NYSE|NASDAQ|BZX link|[A-Za-z]+ link)\s*\|\s*"
                     r"([A-Za-z0-9.\-]+)")


def _clean(cell: str) -> str:
    cell = re.sub(r"<!--.*?-->", "", cell, flags=re.S)
    cell = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", cell, flags=re.S)
    m = _SYMBOL.search(cell)
    if m:
        return m.group(1).strip().upper()
    cell = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", cell)
    cell = re.sub(r"\{\{[^}]*\}\}", "", cell)
    return cell.strip().strip("|").strip()


def _rows(wikitext: str, table_id: str) -> List[List[Tuple[str, Dict[str, int]]]]:
    """Rows of the wikitable with ``id``: each a list of (cell text, {'rowspan': n}) — header rows excluded."""
    start = wikitext.index(f'id="{table_id}"')
    body = wikitext[start:wikitext.index("\n|}", start)]
    rows = []
    for chunk in body.split("\n|-")[1:]:
        cells = []
        for line in chunk.strip("\n").split("\n"):
            if not line.startswith("|") or line.startswith("|+"):
                continue
            for raw in re.split(r"\|\|", line.lstrip("|")):
                attrs = {}
                m = re.match(r'\s*((?:[a-z\-]+="[^"]*"\s*)+)\|(?!\|)(.*)$', raw)
                if m:
                    for key, val in re.findall(r'([a-z\-]+)="([^"]*)"', m.group(1)):
                        if key == "rowspan" and val.isdigit():
                            attrs["rowspan"] = int(val)
                    raw = m.group(2)
                cells.append((_clean(raw), attrs))
        if cells:
            rows.append(cells)
    return rows


def parse_current(wikitext: str) -> List[str]:
    """Today's constituents (tickers) of 'List of S&P 500 companies'."""
    return sorted(parse_current_added(wikitext))


def parse_current_added(wikitext: str) -> Dict[str, Optional[date]]:
    """{today's constituent: its 'Date added'} (None when the cell is not a date)."""
    out: Dict[str, Optional[date]] = {}
    for cells in _rows(wikitext, "constituents"):
        if cells and cells[0][0]:
            texts = [c[0] for c in cells]
            out[cells[0][0]] = _date(texts[5]) if len(texts) > 5 else None
    return out


def _date(text: str) -> Optional[date]:
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%d %B %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


@dataclass(frozen=True)
class Change:
    effective: date
    added: Optional[str]
    removed: Optional[str]


def parse_changes(wikitext: str) -> List[Change]:
    """Every row of 'Historical components of the S&P 500' (table id="changes"): (date, added, removed). A date cell
    spanning several rows (rowspan) applies to the following rows."""
    out, carry, left = [], None, 0
    for cells in _rows(wikitext, "changes"):
        texts = [c[0] for c in cells]
        d = _date(texts[0]) if texts else None
        if d is not None:
            carry, left = d, cells[0][1].get("rowspan", 1) - 1
            texts = texts[1:]
        elif left > 0 and carry is not None:
            left -= 1
        else:
            continue
        if len(texts) < 4:
            texts = texts + [""] * (4 - len(texts))
        added, removed = texts[0] or None, texts[2] or None
        if added or removed:
            out.append(Change(carry, _alias(added), _alias(removed)))
    return out


def _alias(ticker: Optional[str]) -> Optional[str]:
    if not ticker:
        return None
    t = ticker.strip().upper()
    return TICKER_ALIASES.get(t, t)


@dataclass
class SP500Snapshot:
    current: List[str]
    changes: List[Change]
    fetched_at: str
    base_date: date = BASE_DATE
    base_members: List[str] = field(default_factory=list)
    anomalies: List[str] = field(default_factory=list)

    def membership(self) -> IndexMembership:
        later = [c for c in self.changes if c.effective > self.base_date]
        grouped: Dict[date, Tuple[Set[str], Set[str]]] = {}
        for c in later:
            add, rem = grouped.setdefault(c.effective, (set(), set()))
            if c.added:
                add.add(c.added)
            if c.removed:
                rem.add(c.removed)
        changes = [MembershipChange(d, tuple(sorted(a - r)), tuple(sorted(r - a)))
                   for d, (a, r) in sorted(grouped.items())]
        return _ForgivingMembership(ETF, self.base_date, self.base_members, changes,
                                    universe_name="S&P 500 point-in-time constituents")

    def to_json(self) -> dict:
        return {"current": self.current, "fetched_at": self.fetched_at, "base_date": self.base_date.isoformat(),
                "base_members": self.base_members, "anomalies": self.anomalies,
                "changes": [[c.effective.isoformat(), c.added, c.removed] for c in self.changes]}

    @classmethod
    def from_json(cls, d: dict) -> "SP500Snapshot":
        return cls(current=list(d["current"]), fetched_at=d["fetched_at"],
                   changes=[Change(date.fromisoformat(e), a, r) for e, a, r in d["changes"]],
                   base_date=date.fromisoformat(d["base_date"]), base_members=list(d["base_members"]),
                   anomalies=list(d.get("anomalies", [])))


class _ForgivingMembership(IndexMembership):
    """IndexMembership whose changes may remove a ticker that is not open (an inconsistency of the source): it is
    ignored instead of raising (the snapshot's anomalies list them)."""

    def __init__(self, etf, base_date, base_members, changes=(), splits=(), universe_name=None):
        from src.application.services.dispersion import index_membership as im
        original = im.IndexMembership.__init__
        cleaned, open_now = [], set(base_members)
        for ch in sorted(changes, key=lambda c: c.effective):
            removed = tuple(s for s in ch.removed if s in open_now)
            added = tuple(s for s in ch.added if s not in open_now)
            open_now = (open_now - set(removed)) | set(added)
            cleaned.append(MembershipChange(ch.effective, added, removed))
        original(self, etf, base_date, base_members, cleaned, splits, universe_name)


def build_snapshot(current_wikitext: str, history_wikitext: str, base_date: date = BASE_DATE,
                   fetched_at: Optional[str] = None) -> SP500Snapshot:
    added_on = {_alias(k): v for k, v in parse_current_added(current_wikitext).items()}
    current = sorted(added_on)
    changes = parse_changes(history_wikitext)
    anomalies = []
    # a current member added after base_date whose addition the history does not record: its 'Date added'
    recorded = {c.added for c in changes if c.added and c.effective > base_date}
    for ticker, added in sorted(added_on.items()):
        if added is not None and added > base_date and ticker not in recorded:
            changes.append(Change(added, ticker, None))
            anomalies.append(f"{added}: added {ticker} taken from 'Date added' (no change recorded)")
    members: Set[str] = set(current)
    for c in sorted(changes, key=lambda c: c.effective, reverse=True):     # roll back to base_date
        if c.effective <= base_date:
            break
        if c.added:
            if c.added in members:
                members.discard(c.added)
            else:
                anomalies.append(f"{c.effective}: added {c.added} was not a member afterwards")
        if c.removed:
            if c.removed in members:
                anomalies.append(f"{c.effective}: removed {c.removed} was already a member before")
            members.add(c.removed)
    return SP500Snapshot(current=sorted(set(current)), changes=changes,
                         fetched_at=fetched_at or datetime.now().isoformat(timespec="seconds"),
                         base_date=base_date, base_members=sorted(members), anomalies=anomalies)


def load_snapshot(path: Path = CACHE) -> SP500Snapshot:
    return SP500Snapshot.from_json(json.loads(Path(path).read_text(encoding="utf-8")))


def save_snapshot(snapshot: SP500Snapshot, path: Path = CACHE) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot.to_json(), indent=1), encoding="utf-8")
    return path


def build_membership(path: Path = CACHE) -> IndexMembership:
    return load_snapshot(path).membership()


def all_symbols(snapshot: SP500Snapshot) -> List[str]:
    """Every ticker that was a member on or after the base date."""
    out: Set[str] = set(snapshot.base_members) | set(snapshot.current)
    for c in snapshot.changes:
        if c.effective > snapshot.base_date:
            out.update(t for t in (c.added, c.removed) if t)
    return sorted(out)


def monthly_counts(membership: IndexMembership, days: Sequence[date]) -> Dict[date, int]:
    return {d: len(membership.members_at(d)) for d in days}


def refresh(path: Path = CACHE) -> SP500Snapshot:
    """Fetch both Wikipedia pages, rebuild the snapshot and cache it (the only network access)."""
    from src.infrastructure.research.sp500_wikipedia_source import sp500_pages
    current, history = sp500_pages()
    snapshot = build_snapshot(current, history)
    save_snapshot(snapshot, path)
    return snapshot


if __name__ == "__main__":                       # python -m src.application.services.universe.sp500_membership
    s = refresh()
    m = s.membership()
    print(f"saved {CACHE}: {len(s.current)} current members, {len(s.changes)} changes, "
          f"{len(all_symbols(s))} symbols since {s.base_date}, {len(s.anomalies)} anomalies")
    for d in (date(2012, 1, 31), date(2020, 12, 31), date(2026, 10, 30)):
        print(f"  {d}: {len(m.members_at(d))} members")
