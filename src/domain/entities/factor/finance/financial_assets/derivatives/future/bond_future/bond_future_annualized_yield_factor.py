from __future__ import annotations
from decimal import Decimal
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_factor import BondFutureFactor


class BondFutureAnnualizedYieldFactor(BondFutureFactor):
    """Implied annualized SOFR rate from a 3-month SOFR (SR3) futures price.

    SR3 price convention:  F = 100 - R  →  R = (100 - F) / 100

    Example: F = 96.00  →  R = 4.00% annualized (= 0.04 in decimal form).

    The 3-month reference period is already embedded in the SR3 quotation;
    no maturity adjustment is needed.

    Dependency: 'price' → BondFutureFactor close.
    """

    def __init__(self, name: str = "Annualized Yield", factor_id: Optional[int] = None, **kwargs):
        kwargs.setdefault('subgroup', 'yield')
        kwargs.setdefault('group', 'return')
        kwargs.setdefault('frequency', "5m")
        kwargs.setdefault('data_type', 'decimal')
        kwargs.setdefault('source', 'calculated')
        super().__init__(name=name, factor_id=factor_id, **kwargs)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        # Only the raw close price. The frequency is not inherited: the raw
        # bar frequency follows bar_size_setting (e.g. '8h') while this
        # calculated yield is published at its own frequency (e.g. '1d').
        # Inheriting it made the spec match nothing, so the resolver created
        # a placeholder 'BondFutureFactor' that IBKR bars can never fill.
        return [
            DependencySpec(
                factor_type=BondFutureFactor,
                group="price",
                name_in=["close"],
                source_not_in=["calculated"],
            )
        ]

    def calculate(self, dependencies: dict) -> Optional[Decimal]:
        raw = dependencies.get("BondFutureFactor")
        if raw is None:
            return None
        values = raw if isinstance(raw, list) else [raw]
        prices = [float(v) for v in values if v is not None and float(v) > 0]
        if not prices:
            return None
        price_f = sum(prices) / len(prices)
        return Decimal(str((100.0 - price_f) / 100.0))
