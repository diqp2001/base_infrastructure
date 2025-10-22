from __future__ import annotations
from domain.entities.factor.finance.financial_assets.security_factor import FactorSecurity



from decimal import Decimal
from typing import Optional



class FactorEquity(FactorSecurity):
    """Specialized factor for equity instruments."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = "numeric",
        source: Optional[str] = None,
        definition: Optional[str] = None,
        equity_specific: Optional[str] = None,
        factor_id: Optional[int] = None,
    ):
        super().__init__(name, group, subgroup, data_type, source, definition, factor_id)
        self.equity_specific = equity_specific  # e.g. "return", "volatility"

    