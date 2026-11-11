"""
ETF option dispersion factor values in the factor value table, produced the way CompanyShare factors are: the raw
inputs stored as factor values on their own entities, the ETF's holdings as UniverseConstituent rows (point in time),
then every calculated value resolved through FactorValueResolutionService and stored by it.

    ETFShareRealizedDispersionFactor   inputs: the daily closes (ETFShare / CompanyShare `close`, TRADES, 1d)
    ETFShareImpliedDispersionFactor    inputs: the ATM option series of each underlying (atm_<right>_<field>_<m>m)

Steps (the paper gateway is reachable from Docker only; base_infra is the Windows SQL Server):

    prices <date>  (Docker, IBKR read-only, client id 80): 13 months of daily closes into the price cache
    quotes <date>  (Docker, IBKR read-only, client id 80, market hours): the ATM call and put of every ETF and
                   constituent for the expiries closest to 1..6 months -> results/<date>/atm_options/<time>.json
    load <date> [--tickers DIA,XLE] [--measures dispersion] [--every 1] [--no-realized] [--no-implied]
                   (Windows, base_infra; files only, no broker)
    strategies <date> [--tickers DIA] [--sources screen,puts,maturities] [--all-scenario-measures]
                   (Windows, base_infra; files only): the screen's strategies as ETF option factor values
                   (dispersion_strategy_factors.py)

    python -m src.application.managers.project_managers.etf_dispersion_screener_project.dispersion_factors <step> ...

Holdings: each archived holdings snapshot (results/<d>/universe.json, d <= the date) is a UniverseConstituent row set
from its own date to the next snapshot; before the first snapshot the first one is back-cast to the start of the
price history - written in the universe's description and printed: those values use the later membership.
Realized values: each trading day d of the last WINDOW_MONTHS months, stored at d + 1 day 00:00 (the daily bar of d
is stamped at its start and closed then: no look-ahead). Implied values: at each quote run's time (New York).
"""

import argparse
import glob
import json
import os
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

from src.application.managers.project_managers.etf_dispersion_screener_project import config as project_config
from src.application.managers.project_managers.etf_dispersion_screener_project.realized_history import (
    snapshots_by_etf,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_dispersion_factor import (
    MONTHS, RIGHTS, dispersion_factor_name, months_before,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_implied_dispersion_factor import (
    ETFShareImpliedDispersionFactor, atm_option_series_name,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_realized_dispersion_factor import (
    ETFShareRealizedDispersionFactor,
)
from src.domain.ports.finance.dispersion.option_data import Underlying
from src.domain.ports.finance.dispersion.option_market_data_port import MarketDataUnavailable
from src.domain.ports.finance.dispersion.price_history_port import PriceHistoryPort

LOOKBACK_MONTHS = 13        # a 6-month holding period needs 6 months of closes before the first of 6 months of values
WINDOW_MONTHS = 6           # realized values are produced for the last 6 months
DAYS_PER_MONTH = 365.25 / 12
MAX_ATM_DEVIATION = 0.05    # an "ATM" option's strike is within 5 % of the spot
NEW_YORK = ZoneInfo("America/New_York")
FACTORS = {"realized": ("ETFShareRealizedDispersionFactor", ETFShareRealizedDispersionFactor),
           "implied": ("ETFShareImpliedDispersionFactor", ETFShareImpliedDispersionFactor)}


def history_start(as_of: date) -> date:
    return months_before(as_of, LOOKBACK_MONTHS) - timedelta(days=7)


def _symbols(snapshots) -> List[str]:
    return sorted({s for snap in snapshots for s in snap.weights})


def atm_dir(results_dir: str, day: str) -> str:
    return os.path.join(results_dir, day, "atm_options")


# ---- step 1: prices (Docker, IBKR) -----------------------------------------------------------------------------------

def fetch_prices(day: str, tickers: Optional[Sequence[str]] = None, config=None) -> Dict[str, str]:
    """Fill the daily-close cache from history_start to the date for every eligible ETF and its constituents.
    Returns {symbol: problem} for the symbols without a price history."""
    from src.application.managers.project_managers.etf_dispersion_screener_project.realized_history import (
        _connect as connect_history,
    )
    config = config or project_config.get_config()
    snapshots = snapshots_by_etf(config["results_dir"], day)
    etfs = [t for t in snapshots if not tickers or t in tickers]
    prices, resolver, client = connect_history(config, config["results_dir"], day)
    start, end = history_start(date.fromisoformat(day)), date.fromisoformat(day)
    problems = {}
    try:
        for i, etf in enumerate(etfs, 1):
            print(f"{etf} ({i} of {len(etfs)})", flush=True)
            for symbol in [etf] + _symbols(snapshots[etf]):
                if symbol in problems:
                    continue
                try:
                    u = resolver([symbol], end)[symbol]
                    if u is None:
                        problems[symbol] = "not a US-listed share at the broker"
                    elif not prices.daily_closes(u, start, end):
                        problems[symbol] = "no daily history"
                except MarketDataUnavailable as e:
                    problems[symbol] = f"market data unavailable: {e}"[:120]
    finally:
        client.disconnect()
    print(f"done: {len(problems)} symbols without prices", flush=True)
    return problems


# ---- step 2: quotes (Docker, IBKR) -----------------------------------------------------------------------------------

def fetch_atm_options(day: str, tickers: Optional[Sequence[str]] = None, config=None, market_data=None,
                      now=lambda: datetime.now(NEW_YORK)) -> str:
    """The ATM call and put of every ETF (with prices for all its constituents) and of each constituent, for the
    expiries closest to 1..6 months, in one file per run. Returns the file's path."""
    from src.application.services.dispersion.dispersion_screening_service import DispersionScreeningService
    config = config or project_config.get_config()
    snapshots = snapshots_by_etf(config["results_dir"], day)
    etfs = [t for t in snapshots if (not tickers or t in tickers) and covered(config, t, snapshots[t], day)]
    symbols = sorted(set(etfs) | {s for t in etfs for s in _symbols(snapshots[t])})
    client = None
    if market_data is None:
        from src.application.managers.project_managers.etf_dispersion_screener_project.maturities import (
            _connect as connect_quotes,
        )
        ib = dict(config["ibkr"])
        ib["maturities_client_id"] = ib["history_client_id"]
        market_data, client = connect_quotes({**config, "ibkr": ib})
    started = now()
    quote_day = started.date()
    rows = []
    folder = atm_dir(config["results_dir"], day)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, started.strftime("%Y%m%dT%H%M%S") + ".json")

    def save():                                   # after every maturity: a later failure keeps what was quoted
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"run_at": started.isoformat(), "quote_day": str(quote_day), "etfs": etfs, "options": rows}, f,
                      indent=1)
    try:
        lookups = os.path.join(config["results_dir"], day, "lookups.json")
        for right in ("C", "P"):
            service = DispersionScreeningService(market_data, project_config.SCREEN, now=now, right=right)
            if os.path.exists(lookups):
                with open(lookups, encoding="utf-8") as f:
                    service.import_lookups({**json.load(f), "screening_date": quote_day.isoformat()}, quote_day)
            for m in MONTHS:
                print(f"{right} {m}m: {len(symbols)} underlyings", flush=True)
                found = service.atm_options(symbols, round(m * DAYS_PER_MONTH), quote_day, MAX_ATM_DEVIATION)
                for a in found.values():
                    rows.append({"symbol": a.symbol, "right": "call" if right == "C" else "put", "months": m,
                                 "spot": a.spot, "expiry": str(a.expiry) if a.expiry else None, "strike": a.strike,
                                 "bid": a.bid, "ask": a.ask, "iv": a.iv, "problem": a.problem,
                                 "quoted_at": a.quoted_at.isoformat() if a.quoted_at else None})
                save()
    finally:
        if client is not None:
            client.disconnect()
    ok = sum(1 for r in rows if r["problem"] is None)
    print(f"done: {ok} of {len(rows)} ATM options quoted -> {path}", flush=True)
    return path


def atm_series(row: dict) -> Dict[str, float]:
    """The leaf series values of one ATM option row (premium / bid / ask per unit of the spot); {} when unusable."""
    if row.get("problem") or not row.get("spot") or not row.get("bid") or not row.get("ask"):
        return {}
    spot, bid, ask = float(row["spot"]), float(row["bid"]), float(row["ask"])
    quoted = datetime.fromisoformat(row["quoted_at"]).astimezone(NEW_YORK).date()
    out = {"premium": (bid + ask) / 2.0 / spot, "bid": bid / spot, "ask": ask / spot, "strike": float(row["strike"]),
           "moneyness": float(row["strike"]) / spot - 1.0,
           "dte": float((date.fromisoformat(row["expiry"]) - quoted).days)}
    if row.get("iv") is not None:
        out["iv"] = float(row["iv"])
    return out


# ---- step 3: load (base_infra) ---------------------------------------------------------------------------------------

class CacheOnly(PriceHistoryPort):
    """The daily-close cache, never the broker (a missing file is no data)."""

    def daily_closes(self, underlying, start, end):
        raise MarketDataUnavailable(f"{underlying.symbol}: not in the price cache")


def _cached_closes(folder: str, symbol: str, start: date, end: date) -> Dict[date, float]:
    from src.infrastructure.repositories.ibkr_repo.finance.dispersion.cached_price_history import CachedPriceHistory
    try:
        return CachedPriceHistory(CacheOnly(), folder).daily_closes(Underlying(symbol, 0, "STK", "USD"), start, end)
    except MarketDataUnavailable:
        return {}


def covered(config, ticker: str, snapshots, day: str) -> bool:
    """Every price of the ETF and its constituents is in the cache over the lookback."""
    as_of = date.fromisoformat(day)
    return all(_cached_closes(config["price_history_dir"], s, history_start(as_of), as_of)
               for s in [ticker] + _symbols(snapshots))


class DispersionFactorLoader:

    def __init__(self, factory, service, price_dir: str, logger=print):
        self.f = factory
        self.service = service
        self.price_dir = price_dir
        self.log = logger
        self._raw = {}

    # -- raw inputs as factor values on their own entities --
    def _raw_factor(self, entity_type: str, name: str, subgroup: str, definition: str):
        key = (entity_type, name, subgroup)
        if key not in self._raw:
            from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
                CompanyShareFactor,
            )
            from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_factor import (
                ETFShareFactor,
            )
            cls = ETFShareFactor if entity_type == "ETFShare" else CompanyShareFactor
            self._raw[key] = self.f.get_local_repository(f"{entity_type}Factor")._create_or_get(
                cls, name, group="price", subgroup=subgroup, frequency="1d", data_type="numeric", source="ibkr",
                definition=definition)
        return self._raw[key]

    def _store(self, entity, entity_type: str, factor, points: Dict[datetime, float]) -> int:
        from src.domain.entities.factor.factor_value import FactorValue
        rows = [FactorValue(id=None, factor_id=factor.id, entity=None, entity_id=entity.id, entity_type=entity_type,
                            date=when, value=repr(float(v))) for when, v in sorted(points.items())]
        return self.f.get_local_repository("FactorValue").add_bulk(rows)

    def store_closes(self, entity, entity_type: str, closes: Dict[date, float]) -> int:
        factor = self._raw_factor(entity_type, "close", "TRADES", "daily close (IBKR TRADES bars)")
        return self._store(entity, entity_type, factor, {datetime(d.year, d.month, d.day): c for d, c in closes.items()})

    def store_atm(self, entity, entity_type: str, row: dict, when: datetime) -> int:
        n = 0
        for field_name, value in atm_series(row).items():
            name = atm_option_series_name(row["right"], field_name, row["months"])
            factor = self._raw_factor(entity_type, name, "implied",
                                      f"ATM {row['right']} expiring closest to {row['months']} month(s): {field_name}")
            n += self._store(entity, entity_type, factor, {when: value})
        return n

    # -- entities and holdings --
    def etf_entity(self, ticker: str, name: str = None):
        repo = self.f.get_local_repository("ETFShare")
        return repo.get_by_symbol(ticker) or repo._create_or_get(ticker, name=name, asset_class="equity")

    def share_entity(self, symbol: str):
        repo = self.f.get_local_repository("CompanyShare")
        return repo.get_by_symbol(symbol) or repo._create_or_get(symbol)

    def store_holdings(self, etf, snapshots, backcast_from: date, members: Dict[str, object]) -> str:
        """UniverseConstituent rows: each snapshot from its date to the next one; the first back-cast to
        backcast_from. Rows already stored (same constituent and start) are kept. Returns the membership note."""
        from src.domain.entities.universe.universe import Universe
        from src.domain.entities.universe.universe_constituent import UniverseConstituent
        first = snapshots[0].as_of
        note = (f"constituents before {first} back-cast from the {first} holdings file (that day's membership and "
                f"weights, not the historical ones)") if backcast_from < first else "point in time"
        name = self.f.get_local_repository("ETFShare").holdings_universe_name(etf.symbol)
        universes = self.f.get_local_repository("InvestmentUniverse")
        universe = universes._create_or_get(Universe, name, entity_type="CompanyShare", currency_id=etf.currency_id,
                                            description=f"{etf.symbol} holdings (issuer files); {note}")
        rows = self.f.get_local_repository("UniverseConstituent")
        stored = {(r.entity_id, r.start_date) for r in rows.get_by_universe(universe.id)}
        for k, snap in enumerate(snapshots):
            start = backcast_from if k == 0 and backcast_from < first else snap.as_of
            end = snapshots[k + 1].as_of if k + 1 < len(snapshots) else None
            for symbol, weight in snap.weights.items():
                share = members.get(symbol)
                if share is None or (share.id, start) in stored:
                    continue
                rows.add(UniverseConstituent(universe_id=universe.id, entity_id=share.id, entity_type="CompanyShare",
                                             start_date=start, end_date=end, weight=float(weight)))
        return note

    # -- calculated values --
    def definitions(self, kind: str, rights=RIGHTS, measures=("dispersion",), months=MONTHS):
        key, cls = FACTORS[kind]
        repo = self.f.get_local_repository(key)
        return [repo._create_or_get(cls, dispersion_factor_name(kind, r, m_, n), group="dispersion", subgroup=kind,
                                    frequency="1d", data_type="numeric", source="calculated")
                for r in rights for m_ in measures if m_ in cls.MEASURES for n in months]

    def resolve(self, etf, definitions, times: Sequence[datetime]) -> int:
        n = 0
        for when in times:
            for definition in definitions:
                fv = self.service.resolve_factor_value(definition, etf, when)
                n += fv is not None and fv.value is not None
        return n

    def prepare_etf(self, ticker: str, snapshots, as_of: date):
        """The ETF's entities, holdings and closes; (etf, members, closes, note) or a skip reason."""
        start = history_start(as_of)
        symbols = _symbols(snapshots)
        closes = {s: _cached_closes(self.price_dir, s, start, as_of) for s in [ticker] + symbols}
        missing = [s for s, c in closes.items() if not c]
        if missing:
            return f"no price history for {', '.join(missing[:5])}{' ...' if len(missing) > 5 else ''} ({len(missing)})"
        etf = self.etf_entity(ticker)
        if etf is None:
            return "ETF share could not be created"
        members = {s: self.share_entity(s) for s in symbols}
        failed = [s for s, e in members.items() if e is None]
        if failed:
            return f"shares not created: {', '.join(failed[:5])}"
        note = self.store_holdings(etf, snapshots, start, members)
        return etf, members, closes, note

    def load_etf(self, ticker: str, snapshots, as_of: date, realized_defs, implied_defs, atm_runs,
                 every: int = 1) -> Dict[str, object]:
        prepared = self.prepare_etf(ticker, snapshots, as_of)
        if isinstance(prepared, str):
            return {"etf": ticker, "skipped": prepared}
        etf, members, closes, note = prepared
        out = {"etf": ticker, "membership": note}
        stored = self.store_closes(etf, "ETFShare", closes[ticker])
        for s, share in members.items():
            stored += self.store_closes(share, "CompanyShare", closes[s])
        out["closes_stored"] = stored
        t0 = time.monotonic()
        if realized_defs:
            window = months_before(as_of, WINDOW_MONTHS)
            days = sorted(d for d in closes[ticker] if window < d <= as_of)[::-1][::every][::-1]
            out["realized_days"] = len(days)
            out["realized_values"] = self.resolve(etf, realized_defs, [datetime(d.year, d.month, d.day)
                                                                       + timedelta(days=1) for d in days])
        if implied_defs and atm_runs:
            entities = {ticker: (etf, "ETFShare"), **{s: (e, "CompanyShare") for s, e in members.items()}}
            times = []
            for run in atm_runs:
                when = datetime.fromisoformat(run["run_at"]).astimezone(NEW_YORK).replace(tzinfo=None, microsecond=0)
                rows = [r for r in run["options"] if r["symbol"] in entities]
                if not any(r["symbol"] == ticker for r in rows):
                    continue
                for r in rows:
                    self.store_atm(*entities[r["symbol"]], r, when)
                times.append(when)
            out["implied_times"] = len(times)
            out["implied_values"] = self.resolve(etf, implied_defs, times)
        out["seconds"] = round(time.monotonic() - t0, 1)
        return out


def load(day: str, tickers: Optional[Sequence[str]] = None, measures=("dispersion",), every: int = 1,
         realized: bool = True, implied: bool = True, factory=None, config=None) -> List[Dict[str, object]]:
    import logging
    from src.application.services.data.entities.factor.factor_value_resolution_service import (
        FactorValueResolutionService,
    )
    config = config or project_config.get_config()
    if factory is None:
        from src.application.services.database_service.database_service import DatabaseService
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        db = DatabaseService("sql_server")
        db.set_ext_db()
        factory = RepositoryFactory(db.session)
    quiet = logging.getLogger("etf_dispersion_factors")
    quiet.setLevel(logging.ERROR)
    loader = DispersionFactorLoader(factory, FactorValueResolutionService(factory=factory, logger=quiet),
                                    config["price_history_dir"])
    realized_defs = loader.definitions("realized", measures=measures) if realized else []
    implied_defs = loader.definitions("implied", measures=measures) if implied else []
    runs = []
    for path in sorted(glob.glob(os.path.join(atm_dir(config["results_dir"], day), "*.json"))):
        with open(path, encoding="utf-8") as f:
            runs.append(json.load(f))
    snapshots = snapshots_by_etf(config["results_dir"], day)
    out = []
    for ticker in [t for t in snapshots if not tickers or t in tickers]:
        result = loader.load_etf(ticker, snapshots[ticker], date.fromisoformat(day), realized_defs, implied_defs,
                                 runs, every)
        print(json.dumps(result), flush=True)
        out.append(result)
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("step", choices=["prices", "quotes", "load", "strategies"])
    p.add_argument("day")
    p.add_argument("--tickers", default="")
    p.add_argument("--measures", default="dispersion", help="comma list, e.g. dispersion,etf,basket,weight_coverage")
    p.add_argument("--every", type=int, default=1, help="realized: one value every N trading days")
    p.add_argument("--no-realized", action="store_true")
    p.add_argument("--no-implied", action="store_true")
    p.add_argument("--sources", default="", help="strategies: comma list of screen, puts, maturities")
    p.add_argument("--all-scenario-measures", action="store_true",
                   help="strategies: every scenario measure (default: the scenarios' P&L)")
    a = p.parse_args()
    chosen = [t for t in a.tickers.split(",") if t] or None
    if a.step == "prices":
        fetch_prices(a.day, chosen)
    elif a.step == "quotes":
        fetch_atm_options(a.day, chosen)
    elif a.step == "strategies":
        from src.application.managers.project_managers.etf_dispersion_screener_project.dispersion_strategy_factors import (
            load_strategies,
        )
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_scenario_payoff_factor import (
            SCENARIO_MEASURES,
        )
        load_strategies(a.day, chosen, [s for s in a.sources.split(",") if s] or None,
                        SCENARIO_MEASURES if a.all_scenario_measures else ("pnl",))
    else:
        load(a.day, chosen, tuple(m for m in a.measures.split(",") if m), a.every, not a.no_realized,
             not a.no_implied)
