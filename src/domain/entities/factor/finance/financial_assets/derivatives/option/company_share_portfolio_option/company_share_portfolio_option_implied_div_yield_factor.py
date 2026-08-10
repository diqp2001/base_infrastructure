from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor


class CompanySharePortfolioOptionImpliedDivYieldFactor(CompanySharePortfolioOptionFactor):
    """Equal-weight average implied dividend yield across all component share options in the portfolio."""

    def __init__(
        self,
        name: str = "implied_div_yield",
        group: str = "fundamental",
        subgroup: Optional[str] = "daily",
        data_type: Optional[str] = "numeric",
        source: Optional[str] = "calculated",
        definition: Optional[str] = None,
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
        return ["CompanyShareOptionImpliedDivYieldFactor"]

    def calculate(self, dependencies: dict) -> Optional[float]:
        raw = dependencies.get("CompanyShareOptionImpliedDivYieldFactor")
        if raw is None:
            return None
        values: List[float] = [v for v in (raw if isinstance(raw, list) else [raw]) if v is not None]
        if not values:
            return None
        return sum(values) / len(values)
