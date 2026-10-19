"""
DataReport — what data was missing during an SPX v2 run, and why, written to ``data_report.txt``.

Sections:
  1. checks at the start of the run (universe entities, SOFR contracts the backtest window needs,
     greek factor definitions);
  2. greeks that did not resolve, grouped by option / greek / root cause: first and last bar, count,
     and the dependency tree (values found, values missing and why) of the first occurrence;
  3. bars where the hedge was decided with a position missing greeks (counted as delta / gamma 0).
"""

import os
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

REPORT_FILE = "data_report.txt"


@dataclass
class _Miss:
    symbol: str
    greek: str
    cause: str
    first: datetime
    last: datetime
    count: int = 1
    tree: str = ""


@dataclass
class DataReport:
    project: str = ""
    period: tuple = ("", "")
    checks: List[tuple] = field(default_factory=list)                 # (ok, title, detail)
    misses: "OrderedDict[tuple, _Miss]" = field(default_factory=OrderedDict)
    hedges_without_greeks: List[tuple] = field(default_factory=list)  # (time, symbols, book delta)
    bars: int = 0

    # ------------------------------------------------------------------ checks
    def check(self, ok: bool, title: str, detail: str = "") -> None:
        self.checks.append((bool(ok), title, detail))

    def check_sofr_contracts(self, start: date, end: date, registered: Iterable[str], root: str = "SR3") -> None:
        from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.future.bond_future_repository import (
            BondFutureRepository,
        )
        needed = {}
        for d in range((end - start).days + 1):
            day = start + timedelta(days=d)
            needed.setdefault(BondFutureRepository.front_month_symbol(root, day), []).append(day)
        registered = set(registered or [])
        missing = {s: days for s, days in needed.items() if s not in registered}
        detail = "; ".join(f"{s} needed {days[0]} .. {days[-1]}" for s, days in missing.items())
        self.check(not missing, f"{root} contract of every backtest date in the universe "
                                f"(needed {sorted(needed)}, registered {sorted(registered)})",
                   detail and f"missing — fetched from IBKR at run time or the risk-free rate fails: {detail}")

    # ------------------------------------------------------------------ during the run
    def greek_missing(self, time: datetime, symbol: str, greek: str, cause: str, tree: str = "") -> None:
        key = (symbol, greek, cause)
        miss = self.misses.get(key)
        if miss is None:
            self.misses[key] = _Miss(symbol, greek, cause, time, time, 1, tree)
        else:
            miss.count += 1
            miss.first, miss.last = min(miss.first, time), max(miss.last, time)

    def hedge_decided_without_greeks(self, time: datetime, symbols: List[str], book_delta: Any) -> None:
        self.hedges_without_greeks.append((time, symbols, book_delta))

    # ------------------------------------------------------------------ output
    def render(self) -> str:
        out = [f"DATA REPORT — {self.project}", f"period {self.period[0]} .. {self.period[1]}   bars {self.bars}",
               f"written {datetime.now().isoformat(timespec='seconds')}", ""]
        failed = [c for c in self.checks if not c[0]]
        out.append(f"1. CHECKS AT START  ({len(self.checks) - len(failed)} ok, {len(failed)} failed)")
        for ok, title, detail in self.checks:
            out.append(f"  [{'ok' if ok else 'MISSING'}] {title}")
            if detail:
                out.append(f"        {detail}")
        out.append("")
        out.append(f"2. GREEKS THAT DID NOT RESOLVE  ({len(self.misses)} distinct, "
                   f"{sum(m.count for m in self.misses.values())} occurrences)")
        if not self.misses:
            out.append("  none")
        for m in self.misses.values():
            out.append(f"  - {m.symbol}  {m.greek}: {m.count} bar(s), {m.first} .. {m.last}")
            out.append(f"    root cause: {m.cause}")
            if m.tree:
                out.append("    dependency tree (first occurrence):")
                out.extend("      " + line for line in m.tree.splitlines())
        out.append("")
        out.append(f"3. HEDGE DECIDED WITH POSITIONS MISSING GREEKS  ({len(self.hedges_without_greeks)} bar(s); "
                   f"those positions count as delta / gamma 0)")
        for time, symbols, delta in self.hedges_without_greeks[:200]:
            out.append(f"  {time}  {', '.join(symbols)}  book delta used: {delta}")
        if not self.hedges_without_greeks:
            out.append("  none")
        return "\n".join(out) + "\n"

    def write(self, directory: str) -> str:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, REPORT_FILE)
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(self.render())
        os.replace(tmp, path)
        return path


def run_start_checks(report: DataReport, config: Dict[str, Any], factory, entities: List[Any]) -> None:
    """Section 1: universe entities, SOFR contracts of the window, greek factor definitions."""
    from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.data.position_book import (
        FACTOR_REPO_KEYS,
    )
    from src.domain.entities.finance.financial_assets.derivatives.future.bond_future import BondFuture

    universe = config.get('universe', {}) or {}
    wanted = [t for tickers in universe.values() if isinstance(tickers, list) for t in tickers if isinstance(t, str)]
    found = {getattr(e, 'symbol', None) for e in entities or []}
    absent = [t for t in wanted if t not in found]
    report.check(not absent, f"universe entities created ({len(wanted) - len(absent)}/{len(wanted)})",
                 absent and f"not created: {absent}")
    try:
        start = datetime.strptime(str(config['backtest_start']), "%Y-%m-%d %H:%M:%S").date()
        end = datetime.strptime(str(config['backtest_end']), "%Y-%m-%d %H:%M:%S").date()
        report.check_sofr_contracts(start, end, universe.get(BondFuture, []))
    except Exception as e:
        report.check(False, "SOFR contracts of the backtest window", f"could not be checked: {e}")
    for key, repo_key in FACTOR_REPO_KEYS.items():
        try:
            repo = factory.get_local_repository(repo_key)
            stored = repo.get_all() if repo else []
        except Exception:
            stored = []
        report.check(bool(stored), f"factor definition for '{key}' ({repo_key})",
                     "" if stored else "not stored: this greek is never resolved")
