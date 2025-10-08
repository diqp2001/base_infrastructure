from domain.entities.factor.finance.financial_assets.financial_asset_factor import FactorFinancialAsset

from __future__ import annotations

from decimal import Decimal
from typing import Optional



class FactorSecurity(FactorFinancialAsset):

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = "numeric",
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[str] = None,
    ):
        super().__init__(name, group, subgroup, data_type, source, definition, factor_id)

    def calculate(self, *args, **kwargs) -> Decimal:
        """Stub calculation logic for equity factor (to be implemented)."""
        raise NotImplementedError("FactorEquity must implement calculate() method.")