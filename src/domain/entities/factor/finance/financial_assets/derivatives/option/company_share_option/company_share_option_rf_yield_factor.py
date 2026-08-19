from decimal import Decimal
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionRFYieldFactor(CompanyShareOptionFactor):
    """Risk-free yield applicable to a company share option.

    Derives its value from the CurrencyYieldFactor of the option's settlement currency
    (e.g. SOFR for USD-denominated options, ESTR for EUR, SONIA for GBP).
    """

    def __init__(
        self,
        name: str = "rf_yield",
        group: str = "fundamental",
        subgroup: Optional[str] = "yield",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Risk-free overnight repo yield derived from the option currency's CurrencyYieldFactor (SOFR, ESTR, SONIA, etc.)",
        factor_id: Optional[int] = None,
        frequency: Optional[str] = "1d",
        **kwargs,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
            frequency=frequency,
            **kwargs,
        )

    @property
    def calculate_dependencies(self) -> list:
        return ["CurrencyYieldFactor"]

    def calculate(self, dependencies: dict) -> Optional[Decimal]:
        """Return the CurrencyYieldFactor value of the option's settlement currency."""
        raw = dependencies.get("CurrencyYieldFactor")
        if raw is None:
            return None
        values = raw if isinstance(raw, list) else [raw]
        valid = [Decimal(str(v)) for v in values if v is not None]
        if not valid:
            return None
        return sum(valid) / len(valid)
