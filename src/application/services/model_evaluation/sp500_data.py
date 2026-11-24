"""
S&P 500 data for the monthly classifier backtest: point-in-time members (sp500_membership, Wikipedia) and daily OHLCV
bars (Eulerpool, split-adjusted, not dividend-adjusted) cached as files in results/sp500/price_history/eulerpool_ohlcv
(never in the database).

    python -m src.application.services.model_evaluation.sp500_data fetch      # one request per symbol, cached
    python -m src.application.services.model_evaluation.sp500_data coverage   # members with bars, month by month

Coverage: Eulerpool serves today's listings; companies delisted since (acquired, bankrupt) often have no bars, so the
member-months without bars are reported (a survivorship gap of the source, not filled).
"""

from __future__ import annotations

import argparse
import time
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
BARS_DIR = ROOT / "results" / "sp500" / "price_history" / "eulerpool_ohlcv"
HISTORY_START = date(2006, 6, 1)
FIELDS = ("open", "high", "low", "close", "volume")


def bar_cache(client=None, folder: Path = BARS_DIR):
    from src.infrastructure.repositories.eulerpool_repo.prices.eulerpool_price_history import CachedDailyBars
    return CachedDailyBars(client, str(folder))


def fetch(symbols: List[str], end: Optional[date] = None, folder: Path = BARS_DIR, log=print) -> Dict[str, int]:
    """Fetch (or read from the cache) every symbol's bars from HISTORY_START; {symbol: bars}."""
    from src.infrastructure.repositories.eulerpool_repo.eulerpool_client import EulerpoolClient
    client = EulerpoolClient.from_environment()
    if client is None:
        raise RuntimeError("no Eulerpool key (EULERPOOL_API_KEY or EULERPOOL_CREDENTIALS_FILE)")
    cache = bar_cache(client, folder)
    end = end or date.today()
    out = {}
    for i, s in enumerate(symbols, 1):
        t0 = time.time()
        try:
            out[s] = len(cache.bars(s, HISTORY_START, end))
        except Exception as e:                                   # one symbol never stops the others
            out[s] = -1
            log(f"  {s}: {e!r}"[:200])
        if i % 25 == 0 or i == len(symbols):
            log(f"  {i}/{len(symbols)} symbols ({sum(1 for v in out.values() if v > 0)} with bars), "
                f"last {s} {time.time() - t0:.1f}s")
    return out


STATEMENTS_DIR = ROOT / "results" / "sp500" / "statements" / "eulerpool"


def statement_sources(folder: Path = STATEMENTS_DIR):
    """({statement: Eulerpool source behind a file cache}, request errors). The provider is built on an in-memory
    SQLite factory: only its statement sources are used, nothing is stored in a database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from src.infrastructure.repositories.fundamental_provider.statement_file_cache import FileCachedStatementSource
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    factory = RepositoryFactory(Session(create_engine("sqlite://")))
    provider = factory.enable_provider_family("eulerpool")
    if provider is None:
        raise RuntimeError("no Eulerpool key (EULERPOOL_API_KEY or EULERPOOL_CREDENTIALS_FILE)")
    sources = {name: FileCachedStatementSource(src, str(folder)) for name, src in provider.statements.items()}
    return sources, tuple(getattr(provider, "errors", ()))


def prefetch_statements(symbols: List[str], folder: Path = STATEMENTS_DIR, log=print) -> Dict[str, int]:
    """Every statement x frequency of every symbol into the file cache; {symbol: records}."""
    sources, errors = statement_sources(folder)
    out = {}
    for i, s in enumerate(symbols, 1):
        n = 0
        for source in sources.values():
            for frequency in source.FREQUENCIES:
                try:
                    n += len(source.fetch(s, frequency))
                except errors as e:
                    log(f"  {s} {source.STATEMENT} {frequency}: {e!r}"[:200])
                except Exception as e:                         # never stop the batch on one symbol
                    log(f"  {s} {source.STATEMENT} {frequency}: unexpected {e!r}"[:200])
        out[s] = n
        if i % 25 == 0 or i == len(symbols):
            log(f"  {i}/{len(symbols)} symbols ({sum(1 for v in out.values() if v > 0)} with statements)")
    return out


def load_panels(symbols: List[str], folder: Path = BARS_DIR) -> Dict[str, pd.DataFrame]:
    """{field: DataFrame (dates x symbols)} from the cache only (no request)."""
    cache = bar_cache(None, folder)
    per_field: Dict[str, Dict[str, pd.Series]] = {f: {} for f in FIELDS}
    for s in symbols:
        hit = cache.cached(s)
        if not hit or not hit.get("bars"):
            continue
        frame = pd.DataFrame.from_dict(hit["bars"], orient="index")
        frame.index = pd.DatetimeIndex(pd.to_datetime(frame.index))
        for f in FIELDS:
            if f in frame:
                per_field[f][s] = frame[f].astype(float)
    return {f: pd.DataFrame(series).sort_index() for f, series in per_field.items()}


def coverage(membership, closes: pd.DataFrame, month_ends: pd.DatetimeIndex) -> pd.DataFrame:
    """Per month end: members, members with a close that day, share."""
    rows = []
    for t in month_ends:
        if t.date() < membership.base_date:
            continue
        members = membership.members_at(t.date())
        have = [s for s in members if s in closes.columns and pd.notna(closes.at[t, s])] if t in closes.index else []
        rows.append({"date": t, "members": len(members), "with_bars": len(have),
                     "share": len(have) / len(members) if members else float("nan")})
    return pd.DataFrame(rows).set_index("date")


def main(argv=None) -> int:
    from src.application.services.universe import sp500_membership as spm
    p = argparse.ArgumentParser(description="S&P 500 bars for the monthly classifier backtest")
    p.add_argument("command", choices=["fetch", "statements", "coverage"])
    a = p.parse_args(argv)
    snapshot = spm.load_snapshot()
    symbols = spm.all_symbols(snapshot)
    if a.command == "statements":                   # only the symbols with bars (the others are never evaluated)
        with_bars = [s for s in symbols if bar_cache(None).cached(s) and bar_cache(None).cached(s).get("bars")]
        got = prefetch_statements(with_bars)
        print(f"{sum(1 for v in got.values() if v > 0)}/{len(with_bars)} symbols with statements")
        return 0
    if a.command == "fetch":
        got = fetch(symbols)
        print(f"{sum(1 for v in got.values() if v > 0)}/{len(symbols)} symbols with bars; "
              f"no bars: {sorted(s for s, v in got.items() if v == 0)[:60]}")
        return 0
    panels = load_panels(symbols)
    closes = panels["close"]
    days = closes.index[closes.notna().any(axis=1)]
    month_ends = pd.DatetimeIndex(days.to_series().groupby(days.to_period("M")).max().to_numpy())
    cov = coverage(snapshot.membership(), closes, month_ends)
    yearly = cov.groupby(cov.index.year)[["members", "with_bars", "share"]].mean().round(3)
    print(yearly.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
