from decimal import Decimal
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionRFYieldFactor(CompanyShareOptionFactor):
    """Risk-free yield applicable to a company share option.

    Value equals CurrencyYieldFactor of the option's settlement currency
    (e.g. SOFR for USD-denominated options, CORRA for CAD).

    Resolution path:
      1. FactorDependency record links this factor → CurrencyYieldFactor.
      2. _handle_missing_dependency calls get_related_entities(option_id).
      3. get_related_entities reads option.currency_id → returns [Currency].
      4. resolve_factor_value recurses into CurrencyYieldFactor for that
         Currency and passes the result as {'CurrencyYieldFactor': <rate>}
         to calculate().
    """

    def __init__(
        self,
        name: str = "rf_yield",
        group: str = "fundamental",
        subgroup: Optional[str] = "yield",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = (
            "Risk-free overnight repo yield derived from the option currency's "
            "CurrencyYieldFactor (SOFR for USD, CORRA for CAD, etc.)"
        ),
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

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.currency.currency_yield_factor import CurrencyYieldFactor
        return [
            DependencySpec(
                factor_type=CurrencyYieldFactor,
                group="fundamental",
                frequency=DependencySpec.SELF,
                source_in=["calculated"],
            )
        ]