"""
FutureCarryInputs — inputs of a bond-future carry formula, resolved by FactorValueResolutionService:

    price  <- BondFutureFactor 'close', the last closed bar of the future (lookback 1)
    r      <- CurrencyYieldFactor of the future's settlement currency (-> the dated SOFR / CORRA future)
    T      <- years from the target date to the future's expiry (end_date / expiration_date)

Any input missing (no close, no rate, no expiry or expired) -> no value.
"""

from datetime import date as _date
from typing import Optional

from src.domain.entities.factor.dependency_spec import DependencySpec


class FutureCarryInputs:

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.finance.financial_assets.currency.currency_yield_factor import (
            CurrencyYieldFactor,
        )
        from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_factor import (
            BondFutureFactor,
        )
        return [
            DependencySpec(factor_type=BondFutureFactor, group="price", name_in=["close"],
                           source_not_in=["calculated"], lookback=1, key="prices"),
            DependencySpec(factor_type=CurrencyYieldFactor, group="fundamental", frequency=DependencySpec.SELF,
                           source_in=["calculated"], key="rates"),
        ]

    @staticmethod
    def years_to_expiry(entity, target_date) -> Optional[float]:
        expiry = getattr(entity, "expiration_date", None) or getattr(entity, "end_date", None)
        if expiry is None:
            return None
        if hasattr(expiry, "date"):
            expiry = expiry.date()
        ref = target_date.date() if hasattr(target_date, "date") else (target_date or _date.today())
        days = (expiry - ref).days
        return days / 365.0 if days > 0 else None

    def carry_inputs(self, dependencies: dict) -> Optional[tuple]:
        """(price, r, T) or None if any is missing."""
        prices = [float(v) for v in (dependencies.get("prices") or []) if v is not None]
        rates = [float(v) for v in (dependencies.get("rates") or []) if v is not None]
        T = self.years_to_expiry(dependencies.get("entity"), dependencies.get("target_date"))
        if not prices or not rates or T is None:
            return None
        return prices[-1], sum(rates) / len(rates), T
