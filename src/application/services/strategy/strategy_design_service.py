"""
StrategyDesignService — browse strategies and design new ones from an existing strategy (what /strategies calls).

derive              a new DRAFT from any strategy (a project-registered or a web-configured one): its definition,
                    sections and universe are copied; the copy gets its OWN universe, so editing it never touches
                    the source. ``name`` given -> a new strategy (version 1, parent = source); else the next version
                    of the source's name.
update_definition   typed definition: bar frequency / size (trading frequency), model type, training window,
                    retraining every N days, prediction horizon
set_financial_assets  the financial-asset universe from symbols ("CompanyShare: JPM, BAC" lines or plain symbols),
                    resolved to stored financial assets; unknown symbols are reported, never stored
set_factors         the factor universe (factor ids)
set_section         one parameter section as JSON (strategies without a project schema)
validate            web-configured types: their schema + project checks; project-registered types: the strategy
                    must apply onto the project's config (model available, sections / universe writable)

Only draft / validated strategies change (StrategyLocked otherwise); a universe another strategy also references is
copied before it changes (copy-on-write), so a locked strategy's universe never moves.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.domain.entities.strategy.configuration_schema import ERROR
from src.domain.entities.strategy.strategy import DEFINITION_FIELDS, Strategy, StrategyLocked
from src.domain.entities.universe.universe import Universe

DEFAULT_ASSET_TYPE = "CompanyShare"
_INT_FIELDS = ("training_window", "retrain_every_days", "prediction_horizon")


# factor_type prefixes -> the entity type the factor describes (longest first)
_FACTOR_ENTITIES = ("company_share_portfolio_portfolio_holding", "currency_portfolio_portfolio_holding",
                    "company_share_portfolio_holding", "currency_portfolio_holding", "company_share_portfolio",
                    "currency_portfolio", "company_share_option", "etf_share_option", "company_share", "etf_share",
                    "portfolio", "index", "currency", "future")


def factor_entity(factor_type: Optional[str]) -> str:
    """'company_share_option_factor' -> 'CompanyShareOption', 'index_factor' -> 'Index'; else 'Other'."""
    t = str(factor_type or "").lower()
    for prefix in _FACTOR_ENTITIES:
        if t == prefix or t.startswith(prefix + "_"):
            return "".join("ETF" if w == "etf" else w.capitalize() for w in prefix.split("_"))
    return "Other"


def parse_instruments(text: str, default_type: str = DEFAULT_ASSET_TYPE) -> Dict[str, List[str]]:
    """'CompanyShare: JPM, BAC' / 'ETFShare: DIA' lines, or bare symbols (-> default_type). Symbols are kept as
    typed (option symbols contain spaces: one per line or comma separated)."""
    out: Dict[str, List[str]] = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        asset_type, rest = default_type, line
        match = re.match(r"^([A-Za-z][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if match:
            asset_type, rest = match.group(1), match.group(2)
        for symbol in rest.split(","):
            symbol = symbol.strip()
            if symbol and symbol not in out.setdefault(asset_type, []):
                out[asset_type].append(symbol)
    return {k: v for k, v in out.items() if v}                      # order kept: it is the model's asset order


def format_instruments(instruments: Dict[str, List[str]]) -> str:
    return "\n".join(f"{t}: {', '.join(symbols)}" for t, symbols in sorted((instruments or {}).items()))


class StrategyDesignService:

    def __init__(self, factory, strategy_service=None, clock=datetime.utcnow):
        self.factory = factory
        self.strategies = factory.strategy_local_repo
        self.universes = factory.universe_local_repo
        self.universe_factors = factory.universe_factor_local_repo
        self.strategy_service = strategy_service
        self.clock = clock

    # -- reads ------------------------------------------------------------------------------------------------------
    def get(self, strategy_id: int) -> Strategy:
        strategy = self.strategies.get_by_id(strategy_id)
        if strategy is None:
            raise LookupError(f"strategy {strategy_id} does not exist")
        return strategy

    def universe_of(self, strategy: Strategy) -> Optional[Universe]:
        return self.universes.get_by_id(strategy.universe_id) if strategy.universe_id else None

    def overview(self) -> List[Dict[str, Any]]:
        """Every strategy version with its universe size, for the dashboard."""
        universes = {u.id: u for u in self.universes.get_all()}
        rows = []
        for s in sorted(self.strategies.get_all(), key=lambda x: (x.name, x.version)):
            u = universes.get(s.universe_id)
            rows.append({"strategy": s, "universe": u,
                         "assets": len(u.financial_asset_ids()) if u else 0,
                         "requested": sum(len(v) for v in (s.section("universe").get("instruments") or {}).values()),
                         "factors": len(u.factor_ids()) if u else 0})
        return rows

    def universe_detail(self, strategy: Strategy) -> Dict[str, Any]:
        """Members of the strategy's universe as symbols, the requested instruments and what is missing."""
        universe = self.universe_of(strategy)
        request = strategy.section("universe").get("instruments") or {}
        resolved = {}
        for asset_type, symbols in request.items():
            ids = self.universes.resolve_financial_assets(
                symbols, asset_type=None if asset_type == "FinancialAsset" else asset_type)
            resolved[asset_type] = ids
        member_ids = set(universe.financial_asset_ids()) if universe else set()
        missing = {t: [s for s in symbols if resolved.get(t, {}).get(s) not in member_ids]
                   for t, symbols in request.items()}
        catalog = {f["id"]: f for f in self.universe_factors.factor_catalog()}
        return {"universe": universe, "instruments": request, "instruments_text": format_instruments(request),
                "missing": {t: s for t, s in missing.items() if s},
                "factors": [catalog[i] for i in (universe.factor_ids() if universe else []) if i in catalog],
                "shared_with": [s for s in self.strategies.get_by_universe(universe.id) if s.id != strategy.id]
                if universe else []}

    def asset_choices(self, strategy: Strategy, registry=None) -> Dict[str, Any]:
        """What the financial-asset universe is ticked from:
        groups     [{type, symbols: [(symbol, chosen, stored, sector)], chosen}] one per asset type: every stored
                   type, the strategy's and its project's default types (a universe can mix types)
        sectors    the sectors company shares can be ticked by
        universes  [{id, label, members: ['Type:SYMBOL', ...]}] saved universes whose members can be ticked"""
        request = strategy.section("universe").get("instruments") or {}
        defaults: Dict[str, List[str]] = {}
        if registry is not None:
            try:
                defaults = registry.get(strategy.strategy_type).default_sections().get("universe", {}).get(
                    "instruments") or {}
            except Exception:
                defaults = {}
        stored = self.universes.stored_assets() if hasattr(self.universes, "stored_assets") else {}
        sectors = self._sectors()
        types = list(dict.fromkeys([*request, *defaults, *stored])) or [DEFAULT_ASSET_TYPE]
        types.sort(key=lambda t: (t not in request, t != DEFAULT_ASSET_TYPE, t))     # used types first
        groups = []
        for asset_type in types:
            chosen = set(request.get(asset_type) or [])
            in_store = set(stored.get(asset_type, []))
            symbols = sorted(in_store | chosen | set(defaults.get(asset_type) or []))
            rows = [(s, s in chosen, s in in_store, sectors.get(s, "") if asset_type == DEFAULT_ASSET_TYPE else "")
                    for s in symbols]
            groups.append({"type": asset_type, "chosen": len(chosen), "symbols": rows,
                           "has_sectors": any(r[3] for r in rows)})
        saved = self.universes.saved_universes() if hasattr(self.universes, "saved_universes") else []
        universes = [{"id": u["id"], "label": f"{u['name']} v{u['version']} "
                                              f"({sum(len(v) for v in u['assets'].values())})",
                      "members": [f"{t}:{s}" for t, symbols in u["assets"].items() for s in symbols]}
                     for u in saved if u["assets"]]
        return {"groups": groups, "sectors": sorted({v for v in sectors.values()}), "universes": universes}

    def factor_universes(self) -> List[Dict[str, Any]]:
        """Saved universes that list factors: [{id, label, factor_ids}] (the factor universe can load one)."""
        saved = self.universes.saved_universes() if hasattr(self.universes, "saved_universes") else []
        return [{"id": u["id"], "label": f"{u['name']} v{u['version']} ({len(u['factor_ids'])} factors)",
                 "factor_ids": u["factor_ids"]} for u in saved if u["factor_ids"]]

    def save_factor_universe(self, name: str, factor_ids: Iterable[Any]) -> Universe:
        """The ticked factors saved as a universe of their own (a new version when the name exists)."""
        name = (name or "").strip()
        if not name:
            raise ValueError("a factor universe needs a name")
        ids = sorted({int(i) for i in factor_ids})
        if not ids:
            raise ValueError("tick at least one factor to save a factor universe")
        universe = Universe(name=name, version=self.universes.latest_version_number(name) + 1,
                            description=f"factor universe ({len(ids)} factors)", created_at=self.clock())
        for factor_id in ids:
            universe.add_factor(factor_id)
        return self.universes.add(universe)

    def _sectors(self) -> Dict[str, str]:
        """{symbol: sector} of company shares: GICS of the Dow members, then the S&P 500 sector lists the STM
        projects use, then the sector stored with the company (through its industry)."""
        out: Dict[str, str] = {}
        if hasattr(self.universes, "company_share_sectors"):
            try:
                out.update(self.universes.company_share_sectors())
            except Exception:
                pass
        try:      # reference data kept with the STM project (GICS sector -> S&P 500 constituents), loaded as the
            import importlib       # project adapters load project folders (no static import of the managers)

            from src.application.services.strategy.project_adapters import PROJECTS_PACKAGE
            constituents = importlib.import_module(
                f"{PROJECTS_PACKAGE}.spatio_temporal_momentum_project.data.sector_constituents").SECTOR_CONSTITUENTS
            out.update({s: sector for sector, symbols in constituents.items() for s in symbols})
        except Exception:
            pass
        try:
            from src.application.services.universe.djia_membership import SECTORS
            out.update(SECTORS)
        except Exception:
            pass
        return out

    def factor_catalog(self) -> List[Dict[str, Any]]:
        """Every stored factor, with the entity type it describes ('company_share_option_factor' -> CompanyShareOption)."""
        return [{**f, "entity": factor_entity(f.get("factor_type"))} for f in self.universe_factors.factor_catalog()]

    # -- derive -----------------------------------------------------------------------------------------------------
    def derive(self, source_id: int, name: Optional[str] = None, description: Optional[str] = None) -> Strategy:
        source = self.get(source_id)
        name = (name or "").strip()
        if name and name != source.name:
            if self.strategies.latest_version_number(name):
                raise ValueError(f"a strategy named '{name}' already exists: derive from it to get a new version")
            draft = source.revise(new_version=1, name=name)
        else:
            draft = source.revise(new_version=self.strategies.latest_version_number(source.name) + 1)
        draft.created_at = self.clock()
        if description:
            draft.description = description
        draft.universe_id = self._copy_universe(self.universe_of(source), draft.name).id
        return self.strategies.add(draft)

    def _copy_universe(self, source: Optional[Universe], strategy_name: str) -> Universe:
        name = f"{strategy_name} universe"
        copy = Universe(name=name, version=self.universes.latest_version_number(name) + 1,
                        description=f"copied from universe #{source.id} ({source.name} v{source.version})"
                        if source else f"universe of strategy {strategy_name}")
        for member in (source.financial_assets if source else ()):
            copy.add_financial_asset(member.financial_asset_id, start_date=member.start_date,
                                     end_date=member.end_date)
        for factor_id in (source.factor_ids() if source else ()):
            copy.add_factor(factor_id)
        return self.universes.add(copy)

    def _own_universe(self, strategy: Strategy) -> Universe:
        """The strategy's universe, copied first when another strategy references it (copy-on-write)."""
        universe = self.universe_of(strategy)
        if universe is None or any(s.id != strategy.id for s in self.strategies.get_by_universe(universe.id)):
            universe = self._copy_universe(universe, strategy.name)
            strategy.assign_universe(universe.id)
            self.strategies.update(strategy)
        return universe

    # -- edits ------------------------------------------------------------------------------------------------------
    def _editable(self, strategy_id: int) -> Strategy:
        strategy = self.get(strategy_id)
        if not strategy.is_editable:
            raise StrategyLocked(f"strategy '{strategy.name}' v{strategy.version} is {strategy.status}: "
                                 f"create a new strategy from it to change it")
        return strategy

    def update_definition(self, strategy_id: int, values: Dict[str, Any],
                          description: Optional[str] = None) -> Strategy:
        strategy = self._editable(strategy_id)
        parsed = {}
        for key in DEFINITION_FIELDS:
            if key not in values:
                continue
            raw = values[key]
            raw = raw.strip() if isinstance(raw, str) else raw
            if raw in ("", None):
                parsed[key] = None
            elif key in _INT_FIELDS:
                try:
                    parsed[key] = int(raw)
                except (TypeError, ValueError):
                    raise ValueError(f"{key} must be a whole number, got {raw!r}")
            else:
                parsed[key] = str(raw)
        sections = None
        decision = values.get("decision_minutes")
        decision = decision.strip() if isinstance(decision, str) else decision
        if decision not in (None, ""):                     # trading decisions every N minutes (engine interval)
            try:
                minutes = int(decision)
            except (TypeError, ValueError):
                raise ValueError(f"decision interval must be whole minutes, got {decision!r}")
            if minutes < 1:
                raise ValueError("decision interval must be at least 1 minute")
            trading = strategy.section("trading")
            interval = dict(trading.get("config_interval") or {})
            interval["custom_interval_minutes"] = minutes
            sections = {"trading": {**trading, "config_interval": interval}}
        # the two schedules picked as category + count (strategy_schedule: stored where the project reads them)
        from src.application.services.strategy.strategy_schedule import schedule_changes
        from src.domain.entities.strategy.frequency import Frequency

        def picked(prefix):
            unit, count = values.get(f"{prefix}_unit"), values.get(f"{prefix}_count")
            return Frequency.of(unit, count) if unit not in (None, "") and count not in (None, "") else None
        schedule_sections, schedule_typed = schedule_changes(strategy, trading=picked("trading"),
                                                             training=picked("training"), horizon=picked("horizon"))
        if schedule_sections:
            sections = {**(sections or {}), **schedule_sections}
        parsed.update(schedule_typed)
        strategy.update(sections=sections, description=description, **parsed)
        return self.strategies.update(strategy)

    def set_financial_assets(self, strategy_id: int, text: str) -> Tuple[Strategy, Dict[str, List[str]]]:
        """Replace the financial-asset universe; returns (strategy, {asset type: symbols not stored})."""
        strategy = self._editable(strategy_id)
        instruments = parse_instruments(text)
        universe = self._own_universe(strategy)
        strategy = self.get(strategy_id)
        wanted, unknown = [], {}
        for asset_type, symbols in instruments.items():
            ids = self.universes.resolve_financial_assets(
                symbols, asset_type=None if asset_type == "FinancialAsset" else asset_type)
            for symbol in symbols:
                if symbol in ids:
                    wanted.append(ids[symbol])
                else:
                    unknown.setdefault(asset_type, []).append(symbol)
        for member in list(universe.financial_assets):                 # drop what is no longer listed
            if member.financial_asset_id not in wanted:
                universe.remove_financial_asset(member.financial_asset_id, start_date=member.start_date)
        present = set(universe.financial_asset_ids())
        for asset_id in wanted:
            if asset_id not in present:
                universe.add_financial_asset(asset_id)
                present.add(asset_id)
        self.universes.update(universe)
        universe_section = {**strategy.section("universe"), "instruments": instruments}
        strategy.update(sections={"universe": universe_section})
        return self.strategies.update(strategy), unknown

    def set_factors(self, strategy_id: int, factor_ids: List[int]) -> Strategy:
        strategy = self._editable(strategy_id)
        universe = self._own_universe(strategy)
        strategy = self.get(strategy_id)
        wanted = []
        for raw in factor_ids:
            value = int(raw)
            if value not in wanted:
                wanted.append(value)
        for factor_id in list(universe.factor_ids()):
            if factor_id not in wanted:
                universe.remove_factor(factor_id)
        for factor_id in wanted:
            if factor_id not in universe.factor_ids():
                universe.add_factor(factor_id)
        self.universes.update(universe)
        strategy.update()                                     # the definition changed: back to draft
        return self.strategies.update(strategy)

    def set_section(self, strategy_id: int, section: str, text: str) -> Strategy:
        strategy = self._editable(strategy_id)
        try:
            values = json.loads(text or "{}")
        except ValueError as e:
            raise ValueError(f"section '{section}' is not valid JSON: {e}")
        if not isinstance(values, dict):
            raise ValueError(f"section '{section}' must be a JSON object")
        strategy.update(sections={section: values})
        return self.strategies.update(strategy)

    def validate(self, strategy_id: int, registry=None):
        """(strategy, issues). Web-configured types: the project schema; project-registered types: stored as
        validated (the project checks its own config when it runs)."""
        self._editable(strategy_id)
        if self.strategy_service is not None:
            return self.strategy_service.validate(strategy_id)
        strategy = self.get(strategy_id)
        strategy.mark_validated(strategy.sections, self.clock())
        return self.strategies.update(strategy), []

    def model_choices(self, strategy: Strategy, registry=None) -> List[str]:
        """Models the strategy's project can train (the current one first when it is not in the list)."""
        from src.application.services.strategy.model_catalog import model_choices
        try:
            registry = registry or getattr(self.strategy_service, "registry", None)
            choices = model_choices(registry.get(strategy.strategy_type).base_config()) if registry else []
        except Exception:
            choices = []
        if strategy.model_type and strategy.model_type not in choices:
            choices = [strategy.model_type] + choices
        return choices

    def has_errors(self, issues) -> bool:
        return any(i.severity == ERROR for i in issues)
