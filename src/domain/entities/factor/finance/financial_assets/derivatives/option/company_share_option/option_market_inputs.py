"""
OptionMarketInputs — the market inputs of an option model, resolved by FactorValueResolutionService.

Mixed into option factors whose value is a function of (S, K, r, sigma, T, call/put):

    S      <- CompanyShareValueFactor           (the underlying)
    sigma  <- CompanyShareOptionImpliedVolFactor (the option's implied vol)
    r      <- CompanyShareOptionRFYieldFactor    (-> CurrencyYieldFactor -> dated SOFR future)
    K, T, call/put <- the option the value is resolved for (strike, expiry at the target date)

`calculate(dependencies)` (the resolution service) and the explicit-argument call used by direct callers
both work: a dict first argument is the dependency path, anything else is passed to the model method.
"""

from datetime import date as _date, datetime as _dt
from typing import Optional, Tuple

from src.domain.entities.factor.dependency_spec import DependencySpec


class OptionMarketInputs:

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_factor import (
            CompanyShareOptionImpliedVolFactor,
        )
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rf_yield_factor import (
            CompanyShareOptionRFYieldFactor,
        )
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import (
            CompanyShareValueFactor,
        )
        return [
            DependencySpec(factor_type=CompanyShareValueFactor, group="value", source_in=["calculated"]),
            DependencySpec(factor_type=CompanyShareOptionImpliedVolFactor, group="volatility", source_in=["calculated"]),
            DependencySpec(factor_type=CompanyShareOptionRFYieldFactor, group="fundamental"),
        ]

    @staticmethod
    def _mean(raw, positive: bool = False) -> Optional[float]:
        if raw is None:
            return None
        values = [float(v) for v in (raw if isinstance(raw, list) else [raw]) if v is not None]
        if positive:
            values = [v for v in values if v > 0]
        return sum(values) / len(values) if values else None

    @staticmethod
    def contract_terms(entity, target_date) -> Optional[Tuple[float, float, str]]:
        """(strike, years to expiry at target_date, 'call' | 'put') of the option, or None if unknown / expired."""
        strike = getattr(entity, "strike_price", None)
        expiry = getattr(entity, "end_date", None)
        if expiry is None and getattr(entity, "expiry", None):
            expiry = _dt.strptime(str(entity.expiry), "%Y%m%d").date()
        if strike is None or expiry is None:
            return None
        if hasattr(expiry, "date"):
            expiry = expiry.date()
        ref = target_date.date() if hasattr(target_date, "date") else (target_date or _date.today())
        days = (expiry - ref).days
        if days <= 0:
            return None
        return float(strike), days / 365.0, (getattr(entity, "option_type", None) or "call").lower()

    def market_inputs(self, dependencies: dict) -> Optional[dict]:
        """{'S', 'K', 'r', 'sigma', 'T', 'option_type'} from the resolved dependencies, or None if any is missing."""
        S = self._mean(dependencies.get("CompanyShareValueFactor"), positive=True)
        sigma = self._mean(dependencies.get("CompanyShareOptionImpliedVolFactor"), positive=True)
        r = self._mean(dependencies.get("CompanyShareOptionRFYieldFactor"))
        entity = dependencies.get("entity")
        if S is None or sigma is None or r is None or entity is None:
            return None
        terms = self.contract_terms(entity, dependencies.get("target_date"))
        if terms is None:
            return None
        K, T, option_type = terms
        return {"S": S, "K": K, "r": r, "sigma": sigma, "T": T, "option_type": option_type}
