"""
IBKR historical-data type (whatToShow) of a stored factor — driven by the domain source policy (BI-026,
src/domain/entities/factor/source_policy.py): one rule set for every IBKR fetch (IBKRFactorValueRepository and
MarketDataHistoryService).

  source_choice(factor, entity, use)   -> SourceChoice: data types in order of preference + fallback allowed
  resolve_what_to_show(...)            -> the preferred type as an IBKR whatToShow string

With the default policy, raw price bars read as marks are requested as MIDPOINT first and TRADES when IBKR has no
quote history (trades do not happen on every bar); volume is TRADES; implied / historical volatility use their
IBKR types. The instrument class comes from the entity (or the factor class), so a stored definition's subgroup
name no longer decides the data type.
"""

from typing import Any, Optional

from src.domain.entities.factor.source_policy import DEFAULT_SOURCE_POLICY, IntendedUse, SourceChoice, SourcePolicy

TRADES = "TRADES"
MIDPOINT = "MIDPOINT"


def _name_of(obj: Any) -> str:
    return type(obj).__name__ if obj is not None else ""


def is_option_factor(factor: Any) -> bool:
    factor_type = str(getattr(factor, "factor_type", "") or "")
    return "option" in factor_type.lower() or "Option" in _name_of(factor).removesuffix("Model")


def is_option_entity(entity: Any) -> bool:
    return "Option" in _name_of(entity).removesuffix("Model")


def instrument_class(factor: Any = None, entity: Optional[Any] = None) -> str:
    """'CompanyShareOption', 'CompanyShare', 'IndexFuture', ... from the entity, else from the factor class."""
    if entity is not None:
        return _name_of(entity).removesuffix("Model")
    name = _name_of(factor).removesuffix("Model").removesuffix("Factor")
    if not name and getattr(factor, "factor_type", None):
        name = "".join(part.title() for part in str(factor.factor_type).removesuffix("_factor").split("_"))
    return name


def source_choice(factor: Any = None, entity: Optional[Any] = None, *, group: Optional[str] = None,
                  subgroup: Optional[str] = None, name: Optional[str] = None,
                  use: IntendedUse = IntendedUse.VALUATION_MARK,
                  policy: SourcePolicy = DEFAULT_SOURCE_POLICY) -> SourceChoice:
    group = group if group is not None else getattr(factor, "group", None)
    subgroup = subgroup if subgroup is not None else getattr(factor, "subgroup", None)
    name = name if name is not None else getattr(factor, "name", None)
    from src.domain.entities.factor.source_policy import exact_choice, is_what_to_show
    if is_what_to_show(subgroup):                     # BI-036: the factor names its own series — exactly that type
        return exact_choice(subgroup)
    return policy.select(instrument_class(factor, entity), group, name, use=use, subgroup=subgroup)


def resolve_what_to_show(factor: Any = None, entity: Optional[Any] = None, *, group: Optional[str] = None,
                         subgroup: Optional[str] = None, name: Optional[str] = None,
                         use: IntendedUse = IntendedUse.VALUATION_MARK) -> str:
    """Preferred IBKR whatToShow for `factor` fetched for `entity` (see source_choice)."""
    return source_choice(factor, entity, group=group, subgroup=subgroup, name=name, use=use).preferred.value
