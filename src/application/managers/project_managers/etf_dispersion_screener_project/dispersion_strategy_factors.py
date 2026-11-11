"""
The dispersion screen's strategies as factor values (owner's option A, 2026-11-10): the Docker screen writes its
results to files; this Windows step stores them in base_infra and resolves the strategy factors through
FactorValueResolutionService, like the CompanyShare factors:

    entities   the ETF option (ETFShareOption on the ETFShare) and each constituent option (CompanyShareOption)
    legs       the constituent options that replicate the ETF option's holdings, as the Universe "<option> legs"
               (UniverseConstituent rows, weights renormalized over the legs, in force on the screen's day)
    quotes     each option's quote fields (QUOTE_FIELDS: bid / ask / volatilities / greeks / underlying price / strike /
               multiplier) as raw series (ETFShareOptionFactor / CompanyShareOptionFactor, subgroup 'quote') at the
               strategy's quote time T (the latest quote of its legs, New York, to the second)
    values     ETFShareOptionNetPremiumFactor, ...ReversePremiumFactor, ...ImpliedCorrelationFactor and
               ...ScenarioPayoffFactor resolved on the ETF option at T

Sources (results/<date>/): candidates.json (the screen: calls), puts/<ETF>.json (the put strategy), maturities/<ETF>.json
(calls at each maturity). Only priced strategies (an ETF option strike and legs with contracts) are stored.

    python -m src.application.managers.project_managers.etf_dispersion_screener_project.dispersion_factors strategies <date>
"""

from __future__ import annotations

import glob
import json
import os
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from src.application.services.data.entities.factor.factor_library.finance.financial_assets.etf_share_option_library import (
    STRATEGY_FACTORS,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (
    CALL, PUT, QUOTE_FIELDS, QUOTE_SUBGROUP,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_scenario_payoff_factor import (
    ETFShareOptionScenarioPayoffFactor,
)

NEW_YORK = ZoneInfo("America/New_York")

# every measure, except the scenarios' P&L only (the other scenario measures on request: --all-scenario-measures)
DEFAULT_SCENARIO_MEASURES = ("pnl",)


def option_symbol(underlying: str, expiry: date, right: str, strike: float) -> str:
    """OCC-style option symbol: root padded to 6, YYMMDD, C / P, strike x 1000 on 8 digits."""
    return f"{underlying:<6}{expiry:%y%m%d}{right}{int(round(strike * 1000)):08d}"


def strategy_rows(results_dir: str, day: str) -> Iterable[Tuple[str, dict]]:
    """(source, row) of every strategy the screen priced on `day`: the calls screen, the puts, the maturities."""
    folder = os.path.join(results_dir, day)
    path = os.path.join(folder, "candidates.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for row in json.load(f):
                yield "screen", {**row, "right": row.get("right") or CALL}
    for path in sorted(glob.glob(os.path.join(folder, "puts", "*.json"))):
        with open(path, encoding="utf-8") as f:
            trade = json.load(f).get("trade")
        if trade:
            yield "puts", {**trade, "right": trade.get("right") or PUT}
    for path in sorted(glob.glob(os.path.join(folder, "maturities", "*.json"))):
        with open(path, encoding="utf-8") as f:
            for row in json.load(f).get("maturities") or []:
                yield "maturities", {**row, "right": row.get("right") or CALL}


def _f(x) -> Optional[float]:
    return None if x is None else float(x)


def _new_york(text: Optional[str]) -> Optional[datetime]:
    if not text:
        return None
    t = datetime.fromisoformat(text)
    return (t.astimezone(NEW_YORK) if t.tzinfo else t).replace(tzinfo=None, microsecond=0)


def etf_quote(row: dict) -> Dict[str, Optional[float]]:
    """The ETF option's quote fields from a screen row (older rows: multiplier and greeks from the strategy totals)."""
    n, spot = _f(row.get("etf_contracts")) or 1.0, _f(row.get("etf_spot"))
    multiplier = _f(row.get("etf_multiplier"))
    if multiplier is None and row.get("notional") and spot:
        multiplier = round(float(row["notional"]) / (n * spot), 6)
    size = n * multiplier if multiplier else None

    def per_contract(total):
        return None if total is None or not size else float(total) / size

    delta = _f(row.get("etf_delta"))
    if delta is None and row.get("etf_dollar_delta") is not None and size and spot:
        delta = abs(float(row["etf_dollar_delta"])) / (size * spot) * (1.0 if row["right"] == CALL else -1.0)
    return {"bid": _f(row.get("etf_call_bid")), "ask": _f(row.get("etf_call_ask")), "iv": _f(row.get("etf_iv")),
            "bid_iv": _f(row.get("etf_bid_iv")), "ask_iv": _f(row.get("etf_ask_iv")), "delta": delta,
            "gamma": _f(row.get("etf_gamma")) if "etf_gamma" in row else per_contract(row.get("gamma_etf")),
            "vega": _f(row.get("etf_vega")) if "etf_vega" in row else per_contract(row.get("vega_etf")),
            "theta": _f(row.get("etf_theta")) if "etf_theta" in row else per_contract(row.get("theta_etf")),
            "underlying_price": spot, "strike": _f(row.get("etf_strike")), "multiplier": multiplier}


def leg_quote(leg: dict) -> Dict[str, Optional[float]]:
    return {"bid": _f(leg.get("call_bid")), "ask": _f(leg.get("call_ask")), "iv": _f(leg.get("iv")),
            "bid_iv": _f(leg.get("bid_iv")), "ask_iv": _f(leg.get("ask_iv")), "delta": _f(leg.get("delta")),
            "gamma": _f(leg.get("gamma")), "vega": _f(leg.get("vega")), "theta": _f(leg.get("theta")),
            "underlying_price": _f(leg.get("price")), "strike": _f(leg.get("strike")),
            "multiplier": _f(leg.get("multiplier"))}


def priced_legs(row: dict) -> List[dict]:
    """The legs the screen sized (usable constituents), with their weights renormalized over them."""
    legs = [leg for leg in row.get("constituent_legs") or []
            if leg.get("status") == "ok" and leg.get("contracts") is not None and leg.get("expiry")
            and leg.get("strike") is not None and leg.get("weight")]
    total = sum(float(leg["weight"]) for leg in legs)
    return [{**leg, "weight": float(leg["weight"]) / total} for leg in legs] if total > 0 else []


class StrategyFactorLoader:
    """Stores the screen's strategies and resolves their factors (see the module docstring)."""

    def __init__(self, factory, service, scenario_measures: Sequence[str] = DEFAULT_SCENARIO_MEASURES):
        self.f = factory
        self.service = service
        self._raw = {}
        self.definitions = self._definitions(scenario_measures)

    def _definitions(self, scenario_measures) -> list:
        out = []
        for cls in STRATEGY_FACTORS:
            repo = self.f.get_local_repository(cls.__name__)
            for measure in cls.MEASURES:
                if cls is ETFShareOptionScenarioPayoffFactor and not measure.endswith(tuple(scenario_measures)):
                    continue
                out.append(repo._create_or_get(cls, cls.factor_name(measure), group="dispersion", subgroup=cls.KIND,
                                               frequency="1d", data_type="numeric", source="calculated"))
        return [d for d in out if d is not None]

    def _quote_factor(self, entity_type: str, field: str):
        key = (entity_type, field)
        if key not in self._raw:
            if entity_type == "ETFShareOption":
                from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (
                    ETFShareOptionFactor as cls,
                )
            else:
                from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import (
                    CompanyShareOptionFactor as cls,
                )
            self._raw[key] = self.f.get_local_repository(f"{entity_type}Factor")._create_or_get(
                cls, field, group="price", subgroup=QUOTE_SUBGROUP, frequency="1d", data_type="numeric",
                source="ibkr", definition=f"option quote at the dispersion screen's time: {field.replace('_', ' ')}")
        return self._raw[key]

    def store_quote(self, entity, entity_type: str, quote: Dict[str, Optional[float]], when: datetime) -> int:
        """The quote's fields at `when` (a value already stored is kept: add_bulk skips duplicates)."""
        from src.domain.entities.factor.factor_value import FactorValue
        rows = []
        for field in QUOTE_FIELDS:
            value, factor = quote.get(field), self._quote_factor(entity_type, field)
            if value is not None and factor is not None:
                rows.append(FactorValue(id=None, factor_id=factor.id, entity=None, entity_id=entity.id,
                                        entity_type=entity_type, date=when, value=repr(float(value))))
        return self.f.get_local_repository("FactorValue").add_bulk(rows) if rows else 0

    def etf_entity(self, ticker: str, name: str = None):
        repo = self.f.get_local_repository("ETFShare")
        return repo.get_by_symbol(ticker) or repo._create_or_get(ticker, name=name, asset_class="equity")

    def share_entity(self, symbol: str):
        repo = self.f.get_local_repository("CompanyShare")
        return repo.get_by_symbol(symbol) or repo._create_or_get(symbol)

    def option_entity(self, key: str, underlying, symbol: str, expiry: date, right: str, strike: float,
                      multiplier: float, day: date):
        repo = self.f.get_local_repository(key)
        occ = option_symbol(symbol, expiry, right, strike)
        return repo.get_by_symbol(occ) or repo._create_or_get(
            symbol=occ, name=f"{symbol} {expiry} {right} {strike:g}", option_type="call" if right == CALL else "put",
            underlying_asset_id=underlying.id, strike_price=strike, expiry=expiry.strftime("%Y%m%d"),
            multiplier=multiplier, start_date=day)

    def store_legs(self, option, legs: List[Tuple[object, float]], day: date) -> int:
        """The legs universe rows in force on `day` (start day, end the next day); rows already stored are kept."""
        from src.domain.entities.universe.universe import Universe
        from src.domain.entities.universe.universe_constituent import UniverseConstituent
        name = self.f.get_local_repository("ETFShareOption").legs_universe_name(option.symbol)
        universe = self.f.get_local_repository("InvestmentUniverse")._create_or_get(
            Universe, name, entity_type="CompanyShareOption", currency_id=option.currency_id,
            description=f"{option.symbol} dispersion legs: the constituent options replicating its holdings")
        rows = self.f.get_local_repository("UniverseConstituent")
        stored = {(r.entity_id, r.start_date) for r in rows.get_by_universe(universe.id)}
        n = 0
        for entity, weight in legs:
            if (entity.id, day) in stored:
                continue
            rows.add(UniverseConstituent(universe_id=universe.id, entity_id=entity.id, entity_type="CompanyShareOption",
                                         start_date=day, end_date=day + timedelta(days=1), weight=float(weight)))
            n += 1
        return n

    def load_strategy(self, source: str, row: dict) -> Dict[str, object]:
        out = {"etf": row.get("etf"), "source": source, "right": row["right"], "expiry": row.get("expiry")}
        legs = priced_legs(row)
        quote = etf_quote(row)
        when = max(t for t in [_new_york(row.get("etf_quote_time")) or _new_york(row.get("screened_at"))]
                   + [_new_york(leg.get("quote_time")) for leg in legs] if t is not None) if legs else None
        if not legs or not row.get("expiry") or quote["strike"] is None or not quote["multiplier"] or when is None:
            out["skipped"] = "not priced (no ETF option or no sized legs)"
            return out
        day = when.date()
        etf = self.etf_entity(row["etf"], row.get("name"))
        if etf is None:
            out["skipped"] = "ETF share could not be created"
            return out
        option = self.option_entity("ETFShareOption", etf, row["etf"], date.fromisoformat(row["expiry"]), row["right"],
                                    quote["strike"], quote["multiplier"], day)
        if option is None:
            out["skipped"] = "ETF option could not be created"
            return out
        stored = self.store_quote(option, "ETFShareOption", quote, when)
        members = []
        for leg in legs:
            share = self.share_entity(leg["ticker"])
            leg_option = share and self.option_entity(
                "CompanyShareOption", share, leg["ticker"], date.fromisoformat(leg["expiry"]), row["right"],
                float(leg["strike"]), float(leg.get("multiplier") or 100.0), day)
            if leg_option is None:
                out["skipped"] = f"option on {leg['ticker']} could not be created"
                return out
            stored += self.store_quote(leg_option, "CompanyShareOption", leg_quote(leg), when)
            members.append((leg_option, leg["weight"]))
        out.update(option=option.symbol, at=str(when), legs=len(members),
                   legs_stored=self.store_legs(option, members, day), quotes_stored=stored)
        values = {}
        for definition in self.definitions:
            fv = self.service.resolve_factor_value(definition, option, when)
            if fv is not None and fv.value is not None:
                values[definition.name] = round(float(fv.value), 6)
        out["values"] = values
        return out


def load_strategies(day: str, tickers: Optional[Sequence[str]] = None, sources: Optional[Sequence[str]] = None,
                    scenario_measures: Sequence[str] = DEFAULT_SCENARIO_MEASURES, factory=None,
                    config=None) -> List[Dict[str, object]]:
    import logging
    from src.application.managers.project_managers.etf_dispersion_screener_project import config as project_config
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
    quiet = logging.getLogger("etf_dispersion_strategy_factors")
    quiet.setLevel(logging.ERROR)
    service = FactorValueResolutionService(factory=factory, logger=quiet)
    loader = StrategyFactorLoader(factory, service, scenario_measures)
    out = []
    for source, row in strategy_rows(config["results_dir"], day):
        if (tickers and row.get("etf") not in tickers) or (sources and source not in sources):
            continue
        result = loader.load_strategy(source, row)
        print(json.dumps(result), flush=True)
        out.append(result)
    return out
