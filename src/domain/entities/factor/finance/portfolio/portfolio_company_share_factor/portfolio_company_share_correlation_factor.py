from __future__ import annotations
from typing import Optional, List
from decimal import Decimal
import math

from .portfolio_factor import PortfolioFactor
from domain.entities.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding


class PortfolioCompanyShareCorrelationFactor(PortfolioFactor):
    """
    Factor representing the average pairwise correlation of company share returns
    within a portfolio.

    This factor measures the internal diversification of the portfolio by
    computing the average correlation across all unique pairs of holdings.

    Portfolio Correlation =
        (2 / (N × (N - 1))) × Σ ρ(i, j)  for all i < j

    where ρ(i, j) is the correlation between returns of holding i and j.
    """

    def __init__(
        self,
        name: str = "Portfolio Company Share Correlation",
        group: str = "portfolio",
        subgroup: Optional[str] = "correlation",
        data_type: Optional[str] = "float",
        source: Optional[str] = "risk_management",
        definition: Optional[str] = "Average pairwise correlation of company share returns in portfolio",
        factor_id: Optional[int] = None,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
        )

    def calculate_portfolio_correlation(
        self,
        holdings: List[PortfolioCompanyShareHolding],
        return_series: List[List[Decimal]],
    ) -> Optional[float]:
        """
        Calculate the average pairwise correlation between all company share holdings.

        Args:
            holdings: List of portfolio company share holdings
            return_series: List of return time series, one per holding.
                           Each inner list must have the same length.

        Returns:
            Average pairwise correlation (float)
            Returns None if correlation cannot be computed.

        Raises:
            ValueError: If input lengths mismatch or time series are invalid
        """
        n = len(holdings)

        if n < 2:
            return None

        if len(return_series) != n:
            raise ValueError("Each holding must have a corresponding return time series")

        series_length = len(return_series[0])
        if series_length < 2:
            return None

        for series in return_series:
            if len(series) != series_length:
                raise ValueError("All return series must have the same length")

        def mean(x: List[Decimal]) -> Decimal:
            return sum(x) / Decimal(len(x))

        def std_dev(x: List[Decimal], mu: Decimal) -> Decimal:
            variance = sum((xi - mu) ** 2 for xi in x) / Decimal(len(x) - 1)
            return Decimal(math.sqrt(float(variance)))

        def correlation(x: List[Decimal], y: List[Decimal]) -> float:
            mu_x = mean(x)
            mu_y = mean(y)

            cov = sum((xi - mu_x) * (yi - mu_y) for xi, yi in zip(x, y)) / Decimal(len(x) - 1)

            std_x = std_dev(x, mu_x)
            std_y = std_dev(y, mu_y)

            if std_x == 0 or std_y == 0:
                return 0.0

            return float(cov / (std_x * std_y))

        total_corr = 0.0
        pair_count = 0

        for i in range(n):
            for j in range(i + 1, n):
                total_corr += correlation(return_series[i], return_series[j])
