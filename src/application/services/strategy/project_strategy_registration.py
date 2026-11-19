"""
ProjectStrategyRegistrar — every project registers its Strategy (and the Strategy's Universe) when it runs.

A project under ``src/application/managers/project_managers/<folder>`` runs from its own config dict. At the start of
a run the registrar makes sure a Strategy describes that config:

* strategy name / strategy_type = the project folder (unique; two projects may share a ``project_name``);
* typed definition (bar frequency / size, model type, training window, retraining, horizon) read from the config
  (``project_adapters.strategy_definition``);
* sections = the strategy-defining parameters of the config, grouped (universe, factors, model, training, portfolio,
  trading, risk, data_policy, strategy = anything else). NOT part of it: the run (backtest window, capital, run
  name, results folder) and the deployment (``live``: account / host / port / client id ..., supervisor, web
  interface, MLflow, data folders);
* universe = a Universe '<folder> universe' whose UniverseFinancialAsset members are the config's
  ``universe`` instruments ({Class: [symbols]} or [symbols]) found among the stored financial assets.
  Instruments a run creates later are added by ``sync_universe`` (called again after setup / at the end).

"If not already created": the version whose definition (sections + typed definition, universe excluded) equals the
config's is reused; a changed config gets a NEW version (parent = the latest) - an earlier run keeps pointing at
what it ran. Registered versions are locked (they are what a run used). A run launched from /strategies
(``strategy_experiment_id`` in its config) already has its strategy: only its universe members are synchronised.

Never fatal for a run: callers catch and log failures (``register_project_strategy``).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.application.services.backtest_registry.run_identity import _jsonable, _redact
from src.application.services.strategy.project_adapters import strategy_definition
from src.domain.entities.strategy.strategy import Strategy, content_hash
from src.domain.entities.universe.universe import Universe

logger = logging.getLogger(__name__)

PROJECT_PACKAGE = "src.application.managers.project_managers."

# config keys that describe a RUN or a DEPLOYMENT, never the strategy
RUN_KEYS = frozenset({
    "backtest_start", "backtest_end", "price_history_start", "initial_capital", "results_dir", "run_name",
    "run_registry", "strategy_experiment_id", "project_name", "version", "description", "register_strategy",
    # deployment / infrastructure
    "live", "supervisor", "enable_web_interface", "web_interface_port", "mlflow_experiment_name",
    "mlflow_tracking_uri", "price_history_dir", "holdings_archive_dir", "job_launcher", "job_script", "ibkr",
    "download_interval_seconds", "DATABASE", "WEB", "LOGGING",
    "BACKTEST",                                         # test_base_project: its run window / capital
})
SECTION_OF = {
    "universe": "universe",
    "factors": "factors", "FACTORS": "factors", "target_factor": "factors",
    "model_type": "model", "volatility_model": "model", "csm": "model", "SPATIOTEMPORAL": "model",
    "training_window": "training", "retrain_every_days": "training", "test_split": "training",
    "validation_split": "training", "pretrain_before_first_decision": "training", "missing_asset_patience": "training",
    "Portfolio": "portfolio", "PORTFOLIO": "portfolio", "gross_exposure_cap": "portfolio", "rebalance": "portfolio",
    "deciles": "portfolio", "option_entry_weight": "portfolio",
    "config_interval": "trading", "bar_size_setting": "trading", "execution_costs": "trading",
    "trading_hours": "trading", "commission_per_contract": "trading", "spread_type": "trading",
    "split_guard": "risk", "max_daily_loss": "risk", "max_gamma_exposure": "risk", "max_position_size": "risk",
    "max_spread_width": "risk",
    "duration_str": "data_policy", "max_import_ibkr": "data_policy", "preload_data": "data_policy",
    "file_price_sources": "data_policy", "fundamentals_source": "data_policy", "history_calendar_days": "data_policy",
    "historical_data_duration": "data_policy", "option_data_duration": "data_policy", "DATA": "data_policy",
}
# inside the Portfolio dict: the book's name / cash are the run's (each run has its own portfolio)
PORTFOLIO_RUN_KEYS = frozenset({"name", "initial_cash"})


def project_key_of(obj) -> Optional[str]:
    """The project folder of an object (or module name) defined under project_managers, else None."""
    module = obj if isinstance(obj, str) else type(obj).__module__
    if not module.startswith(PROJECT_PACKAGE):
        return None
    return module[len(PROJECT_PACKAGE):].split(".")[0] or None


def _factor_entry(entry: Any) -> Any:
    """A factor config dict -> its identifying fields (the class as a name, no nested dependency objects)."""
    if isinstance(entry, dict):
        keep = {k: entry.get(k) for k in ("name", "group", "subgroup", "frequency", "source") if entry.get(k)}
        cls = entry.get("class") or entry.get("entity_cls")
        if cls is not None:
            keep["class"] = getattr(cls, "__name__", str(cls))
        return keep or _jsonable(entry)
    return _jsonable(entry)


def universe_request(config: Dict[str, Any]) -> Dict[str, List[str]]:
    """{asset class name: sorted symbols} the config's ``universe`` asks for ([symbols] -> 'FinancialAsset')."""
    universe = config.get("universe")
    if isinstance(universe, dict):
        out = {}
        for cls, symbols in universe.items():
            if isinstance(symbols, (list, tuple, set)):
                out[getattr(cls, "__name__", str(cls))] = sorted({str(s) for s in symbols if s})
        return {k: v for k, v in out.items() if v}
    if isinstance(universe, (list, tuple, set)):
        symbols = sorted({str(s) for s in universe if s})
        return {"FinancialAsset": symbols} if symbols else {}
    return {}


def strategy_sections(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """The config's strategy-defining parameters, grouped by section (JSON values, credentials redacted)."""
    sections: Dict[str, Dict[str, Any]] = {}

    def put(section: str, key: str, value: Any) -> None:
        sections.setdefault(section, {})[key] = value

    for key, value in config.items():
        if key in RUN_KEYS:
            continue
        if key == "universe":
            request = universe_request(config)
            if request:
                put("universe", "instruments", request)
        elif key in ("factors", "FACTORS") and isinstance(value, (list, tuple)):
            put("factors", key.lower(), [_factor_entry(v) for v in value])
        elif key == "stm" and isinstance(value, dict):
            for sub, sub_value in value.items():
                target = {"universe": "universe", "features": "factors", "training": "training",
                          "artifact_dir": None}.get(sub, "model")
                if target:
                    put(target, f"stm.{sub}", _jsonable(sub_value))
        elif key in ("Portfolio", "PORTFOLIO") and isinstance(value, dict):
            put("portfolio", key, _jsonable({k: v for k, v in value.items() if k not in PORTFOLIO_RUN_KEYS}))
        else:
            put(SECTION_OF.get(key, "strategy"), key, _jsonable(value))
    return _redact(sections)


def _without_universe(definition: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in definition.items() if k != "universe_id"}


class ProjectStrategyRegistrar:

    def __init__(self, factory, clock=datetime.utcnow):
        self.factory = factory
        self.strategies = factory.strategy_local_repo
        self.universes = factory.universe_local_repo
        self.clock = clock

    # -- strategy ---------------------------------------------------------------------------------------------------
    def ensure(self, project_key: str, config: Dict[str, Any], description: Optional[str] = None) -> Strategy:
        """The Strategy describing ``config`` (created / new version when missing), its universe synchronised."""
        experiment_id = config.get("strategy_experiment_id")
        if experiment_id:                                       # launched from /strategies: the strategy exists
            experiment = self.factory.strategy_experiment_local_repo.get_by_id(int(experiment_id))
            strategy = self.strategies.get_by_id(experiment.strategy_id) if experiment else None
            if strategy is not None:
                self.sync_universe(strategy)
                return strategy
        sections = strategy_sections(config)
        definition = {k: v for k, v in strategy_definition(config).items() if v is not None}
        fingerprint = content_hash(project_key, sections, definition)
        versions = self.strategies.get_versions(project_key)
        for existing in versions:
            if content_hash(existing.strategy_type, existing.sections,
                            _without_universe(existing.definition)) == fingerprint:
                self.sync_universe(existing)
                return existing
        latest = versions[-1] if versions else None
        now = self.clock()
        strategy = Strategy(
            name=project_key, strategy_type=project_key, sections=sections,
            description=description or config.get("description")
            or f"Registered from project {project_key} (config version {config.get('version', '-')})",
            version=(latest.version + 1) if latest else 1, parent_id=latest.id if latest else None,
            universe_id=self._universe_for(project_key, sections, versions), created_at=now, **definition)
        strategy.mark_validated(strategy.sections, now)
        strategy.lock(now)                                      # what a run used never changes
        strategy = self.strategies.add(strategy)
        logger.info(f"strategy '{strategy.name}' v{strategy.version} registered (id {strategy.id}, "
                    f"universe {strategy.universe_id})")
        self.sync_universe(strategy)
        return strategy

    # -- universe ---------------------------------------------------------------------------------------------------
    def _universe_for(self, project_key: str, sections: Dict[str, Any], versions: List[Strategy]) -> Optional[int]:
        """Same instruments as an earlier version -> its universe; otherwise a new universe version."""
        request = sections.get("universe", {}).get("instruments")
        if not request:
            return None
        for existing in reversed(versions):
            if existing.universe_id and existing.section("universe").get("instruments") == request:
                return existing.universe_id
        name = f"{project_key} universe"
        count = sum(len(v) for v in request.values())
        universe = self.universes.add(Universe(
            name=name, version=self.universes.latest_version_number(name) + 1,
            description=f"Instruments of project {project_key}: {count} "
                        f"({', '.join(f'{k} {len(v)}' for k, v in request.items())})"))
        return universe.id

    def sync_universe(self, strategy: Strategy) -> Optional[Universe]:
        """Add the requested instruments now stored as financial assets (never removes: the request is fixed per
        strategy version). Returns the universe (None when the strategy has none)."""
        if not strategy.universe_id:
            return None
        universe = self.universes.get_by_id(strategy.universe_id)
        request = strategy.section("universe").get("instruments") or {}
        if universe is None or not request:
            return universe
        present = set(universe.financial_asset_ids())
        added = 0
        for asset_type, symbols in request.items():
            ids = self.universes.resolve_financial_assets(
                symbols, asset_type=None if asset_type == "FinancialAsset" else asset_type)
            for symbol in symbols:
                asset_id = ids.get(symbol)
                if asset_id is not None and asset_id not in present:
                    universe.add_financial_asset(asset_id)
                    present.add(asset_id)
                    added += 1
        if added:
            universe = self.universes.update(universe)
            logger.info(f"universe '{universe.name}' v{universe.version}: {added} instrument(s) added "
                        f"({len(present)} of {sum(len(v) for v in request.values())})")
        return universe


def register_project_strategy(factory, owner, config: Dict[str, Any], log=None) -> Optional[Strategy]:
    """Best effort: the Strategy of the project ``owner`` belongs to (a runner / manager object or a project key).
    Returns None (and logs why) when it cannot be registered; a run never fails because of it."""
    log = log or logger
    if config.get("register_strategy", True) is False:
        return None
    project_key = owner if isinstance(owner, str) else project_key_of(owner)
    if not project_key:
        return None
    try:
        return ProjectStrategyRegistrar(factory).ensure(project_key, config)
    except Exception as e:
        try:
            factory.session.rollback()
        except Exception:
            pass
        log.warning(f"strategy of project {project_key} not registered: {e}")
        return None


def sync_project_universe(factory, strategy: Optional[Strategy], log=None) -> None:
    """Best effort: add the instruments the run created to the strategy's universe."""
    if strategy is None:
        return
    try:
        ProjectStrategyRegistrar(factory).sync_universe(strategy)
    except Exception as e:
        try:
            factory.session.rollback()
        except Exception:
            pass
        (log or logger).warning(f"universe of strategy {strategy.name} not synchronised: {e}")


def factory_for(database_service):
    """A repository factory on its OWN session of the project's database (registry commits never touch the run's
    pending work)."""
    from sqlalchemy.orm import sessionmaker

    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    return RepositoryFactory(sessionmaker(bind=database_service.session.get_bind())())


def register_with_database(database_service, owner, config: Dict[str, Any], log=None):
    """register_project_strategy on the project's database service; returns (strategy, factory) - (None, None)
    when there is no database."""
    log = log or logger
    if database_service is None or getattr(database_service, "session", None) is None:
        return None, None
    try:
        factory = factory_for(database_service)
    except Exception as e:
        log.warning(f"strategy registration unavailable: {e}")
        return None, None
    return register_project_strategy(factory, owner, config, log=log), factory
