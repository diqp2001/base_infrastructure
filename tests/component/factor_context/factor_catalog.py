"""
Catalog of every factor class that defines calculate(), discovered from src/domain/entities/factor.

Used by the wiring and resolution tests so that a new factor is covered without editing them.
"""

import importlib
import inspect
import pathlib
from functools import lru_cache

FACTOR_ROOT = pathlib.Path(__file__).resolve().parents[3] / "src" / "domain" / "entities" / "factor"
# keys calculate() may read that the resolution service adds itself (not declared dependencies)
SERVICE_KEYS = {"entity", "target_date", "parameters"}
# string dependencies resolved from an attribute of a related entity (_resolve_entity_attr_dep)
ENTITY_ATTRIBUTE_DEPS = {"Position"}
# a module holds a calculating factor if it defines calculate() or uses a mixin that does
CALCULATE_MARKERS = ("def calculate(", "SeriesPriceReturn", "OptionModelPrice")


def _has_own_calculate(cls):
    """calculate() defined by the class itself or by a mixin it uses (not inherited from another factor)."""
    if "calculate" in cls.__dict__:
        return True
    from src.domain.entities.factor.factor import Factor
    return any("calculate" in base.__dict__ for base in cls.__mro__[1:] if not issubclass(base, Factor))


@lru_cache(maxsize=None)
def factor_classes():
    """[(class name, class)] for every class that defines calculate(), sorted by name."""
    from src.domain.entities.factor.factor import Factor
    found = {}
    for path in sorted(FACTOR_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if path.name.startswith("_") or not any(marker in text for marker in CALCULATE_MARKERS):
            continue
        module_name = ".".join(path.relative_to(FACTOR_ROOT.parents[3]).with_suffix("").parts)
        module = importlib.import_module(module_name)
        for name, cls in inspect.getmembers(module, inspect.isclass):
            # a leading underscore marks an abstract base (e.g. _AvgTurnoverFactor), never a stored factor
            if (cls.__module__ == module_name and issubclass(cls, Factor) and _has_own_calculate(cls)
                    and not name.startswith("_")):
                found[name] = cls
    return sorted(found.items())


def instantiate(cls):
    """The factor with its default parameters, or None when it needs arguments."""
    try:
        return cls()
    except TypeError:
        return None


def declared_dependencies(factor):
    """calculate_dependencies of an instance ([] when the property is missing)."""
    deps = getattr(factor, "calculate_dependencies", None)
    if deps is None:
        return []
    return deps if isinstance(deps, list) else [deps]


def dependency_name(dep):
    """Key under which calculate() receives the dependency."""
    return dep if isinstance(dep, str) else dep.result_key


def unfed_parameters(cls, dependency_names):
    """Required calculate() parameters the resolution service cannot fill.

    _call_factor_calculate_method passes the whole dict to a `dependencies` parameter; otherwise it
    matches each parameter by name against the resolved dependencies (+ entity / target_date)."""
    params = [p for name, p in inspect.signature(cls.calculate).parameters.items() if name != "self"]
    if any(p.name == "dependencies" for p in params):
        return []
    fed = set(dependency_names) | SERVICE_KEYS
    return [p.name for p in params
            if p.default is inspect.Parameter.empty
            and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            and p.name not in fed]


_PORTFOLIO_OPTION = ("option on a share portfolio (basket): no basket option contracts or prices are stored, "
                     "so there is nothing to price / value it from")
_OPTION_PORTFOLIO = ("portfolio-level model price / greek of an option portfolio: no aggregation over the "
                     "holdings is defined (the per-contract CompanyShareOption* factors are resolved instead)")
_GENERIC = ("generic model class with no instrument (no entity, no stored inputs); the instrument factors "
            "(CompanyShareOption*, BondFuture*, IndexFuture*) are the resolvable ones")

# Factor classes the resolution service is not meant to feed: kept as domain models (callable with explicit
# arguments), excluded from the wiring / end-to-end tests with the reason. Remove an entry once its inputs exist.
NOT_SERVICE_RESOLVABLE = {
    **{f"CompanySharePortfolioOption{m}Factor": _PORTFOLIO_OPTION for m in (
        "BatesPrice", "BlackScholesMertonPrice", "CoxRossRubinsteinPrice", "Delta", "DupireLocalVolatilityPrice",
        "Gamma", "HestonPrice", "HullWhitePrice", "Price", "PriceReturn", "Rho", "SABRPrice", "Theta", "Value",
        "Vega", "ImpliedDivYield", "ImpliedVol")},
    "CompanyShareOptionPortfolioBatesPriceFactor": _OPTION_PORTFOLIO,
    "CompanyShareOptionPortfolioDeltaFactor": _OPTION_PORTFOLIO,
    "CompanyShareOptionImpliedCorrFactor": "needs the basket (index / portfolio) option's implied vol and its "
                                           "constituents' — no basket options are stored",
    "CompanyShareOptionImpliedDivYieldFactor": "put-call parity needs a call and a put with the same strike and "
                                               "expiry; the option data holds single contracts, no pairing",
    **{name: _GENERIC for name in (
        "OptionDeltaFactor", "OptionGammaFactor", "OptionPriceFactor", "OptionRhoFactor", "OptionVegaFactor",
        "FutureAnnualizedPriceReturnFactor", "FutureAnnualizedRollYieldFactor", "FutureDiscountedValueFactor",
        "FutureForwardPriceFactor", "FuturePriceReturnFactor", "IndexFutureOptionDeltaFactor",
        "IndexFutureOptionPriceFactor", "SwapPriceFactor")},
    "BondFutureAnnualizedRollYieldFactor": "needs the deferred contract's close (next quarterly expiry): futures "
                                           "have no front -> deferred relation to resolve it on",
    "PortfolioHoldingValueFactor": "generic holding: values come from the typed holding factors "
                                   "(CompanySharePortfolioHoldingValueFactor, CurrencyPortfolioHoldingValueFactor, ...)",
    "CompanySharePositionValueFactor": "no order / transaction factor values are stored; a position's value is "
                                       "CompanySharePortfolioHoldingValueFactor (quantity rebuilt from fills x price)",
    "CompanyShareTransactionValueFactor": "no order quantity / price factor values are stored (orders and "
                                          "transactions are entities, not factor values)",
    "ConstituentScoreFactor": "scores are written by the ML pipelines; calculate() is not a resolution path",
    "CurrencyRateFactor": "an observed rate stored by the data import; calculate() aggregates provider quotes "
                          "(source_prices), it is not a derived factor",
}
