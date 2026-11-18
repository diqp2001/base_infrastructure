"""
ETFShareOptionValueFactor - the value of an option on an ETF share, the asset value its holding is valued with:
    the market price when the option has one - the last closed IBKR MIDPOINT close of the option ('market');
    else its model price (ETFShareOptionModelPriceFactor: Black-Scholes on the ETF's close, IBKR implied vol, IRX).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (
    ETFShareOptionFactor,
)

MARKET, MODEL = "market", "ETFShareOptionModelPriceFactor"


def _last(raw) -> Optional[float]:
    if raw is None:
        return None
    values = [float(v) for v in (raw if isinstance(raw, list) else [raw]) if v is not None]
    return values[-1] if values else None


class ETFShareOptionValueFactor(ETFShareOptionFactor):

    def __init__(self, name: str = "etf_share_option_value", group: str = "value", subgroup: Optional[str] = "asset",
                 frequency: Optional[str] = "1d", data_type: Optional[str] = "decimal",
                 source: Optional[str] = "calculated",
                 definition: Optional[str] = "Value of an ETF share option: IBKR mid price, else its model price",
                 factor_id: Optional[int] = None, **kwargs):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency, data_type=data_type,
                         source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_model_price_factor import (
            ETFShareOptionModelPriceFactor,
        )
        return [
            DependencySpec(factor_type=ETFShareOptionFactor, group="price", name_in=["close"],
                           subgroup="MIDPOINT", source_not_in=["calculated"], lookback=1, key=MARKET),
            DependencySpec(factor_type=ETFShareOptionModelPriceFactor, group="price_model", subgroup="black_scholes",
                           source_in=["calculated"]),
        ]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[Decimal]:
        market = _last(dependencies.get(MARKET))
        if market is not None and market > 0:
            return Decimal(str(market))
        model = _last(dependencies.get(MODEL))
        return Decimal(str(model)) if model is not None and model >= 0 else None
