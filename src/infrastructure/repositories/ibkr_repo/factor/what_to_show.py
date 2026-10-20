"""
IBKR historical-data type (whatToShow) of a stored factor — one rule for every IBKR fetch
(IBKRFactorValueRepository and MarketDataHistoryService).

  implied volatility  (group volatility, subgroup implied)     -> OPTION_IMPLIED_VOLATILITY
  historical vol      (group volatility, subgroup historical)  -> HISTORICAL_VOLATILITY
  option price bars   (group price, an option factor or an option entity; not volume) -> MIDPOINT
  anything else                                                -> TRADES

Option prices are recognised by the factor type / the entity, not by the definition's subgroup: the raw
option OHLC definitions are stored with subgroup 'ohlc' (CompanyShareOptionFactorRepository default,
BaseModelTrainer), so a subgroup rule ('option') never applied and illiquid options (e.g. long-dated
calls) were fetched as TRADES — no bars on days without a trade (IBKR error 162).
"""

from typing import Any, Optional

TRADES = "TRADES"
MIDPOINT = "MIDPOINT"

_VOLATILITY = {"implied": "OPTION_IMPLIED_VOLATILITY", "historical": "HISTORICAL_VOLATILITY"}


def _name_of(obj: Any) -> str:
    return type(obj).__name__ if obj is not None else ""


def is_option_factor(factor: Any) -> bool:
    factor_type = str(getattr(factor, "factor_type", "") or "")
    return "option" in factor_type.lower() or "Option" in _name_of(factor).removesuffix("Model")


def is_option_entity(entity: Any) -> bool:
    return "Option" in _name_of(entity).removesuffix("Model")


def resolve_what_to_show(factor: Any = None, entity: Optional[Any] = None, *, group: Optional[str] = None,
                         subgroup: Optional[str] = None, name: Optional[str] = None) -> str:
    """whatToShow for `factor` (or explicit group / subgroup / name) fetched for `entity`."""
    group = group if group is not None else getattr(factor, "group", None)
    subgroup = subgroup if subgroup is not None else getattr(factor, "subgroup", None)
    name = name if name is not None else getattr(factor, "name", None)
    if group == "volatility" and subgroup in _VOLATILITY:
        return _VOLATILITY[subgroup]
    if group == "price" and (str(name).lower() != "volume") and (
            subgroup == "option" or is_option_entity(entity) or (factor is not None and is_option_factor(factor))):
        return MIDPOINT
    return TRADES
