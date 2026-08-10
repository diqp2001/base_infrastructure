import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionVolFactor(CompanyShareOptionFactor):
    """Realized volatility of a company share option price series, computed from IBKR price data.

    Resolution branch: A — depends on CompanyShareOptionFactor for the option market price
    fetched directly from IBKR.  Annualised realised vol = std(log_returns) * sqrt(252).
    """

    def __init__(
        self,
        name: str = "vol",
        group: str = "volatility",
        subgroup: Optional[str] = "realized",
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
        return ["CompanyShareOptionFactor"]

    def calculate(self, dependencies: dict) -> Optional[float]:
        """Compute annualised realised volatility from a series of option prices from IBKR."""
        raw = dependencies.get("CompanyShareOptionFactor")
        if raw is None:
            return None
        prices = [float(v) for v in (raw if isinstance(raw, list) else [raw]) if v is not None and float(v) > 0]
        if len(prices) < 2:
            return None
        log_returns = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]
        n = len(log_returns)
        mean = sum(log_returns) / n
        variance = sum((r - mean) ** 2 for r in log_returns) / (n - 1)
        return math.sqrt(variance) * math.sqrt(252)
