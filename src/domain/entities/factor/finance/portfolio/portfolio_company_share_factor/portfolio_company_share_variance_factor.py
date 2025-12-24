from __future__ import annotations
from typing import Optional, List
from decimal import Decimal
import math

from domain.entities.factor.finance.portfolio.portfolio_company_share_factor.portfolio_company_share_factor import (
    PortfolioCompanyShareFactor
)
from domain.entities.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding


class PortfolioCompanyShareVarianceFactor(PortfolioCompanyShareFactor):
    """
    Factor representing the variance of company share returns within a portfolio.

    This factor computes the portfolio variance using the full
    variance–covariance matrix formulation:

    Portfolio Variance =
        Σᵢ Σⱼ wᵢ wⱼ σᵢ σⱼ ρᵢⱼ

    where:
        wᵢ   = value weight of holding i
        σᵢ   = volatility of holding i
        ρᵢⱼ = correlation between holdings i and j
    """

    def __init__(
        self,
        name: str = "Portfolio Company Share Variance",
        group: str = "portfolio",
        subgroup: Optional[str] = "variance",
        data_type: Optional[str] = "float",
        source: Optional[str] = "risk_management",
        definition: Optional[str] = "Variance of portfolio company share returns",
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

    def calculate_portfolio_variance(
        self,
        holdings: List[PortfolioCompanyShareHolding],
        quantities: List[Decimal],
        return_series: List[List[Decimal]],
    ) -> Optional[float]:
        """
        Calculate the portfolio variance of company share returns.

        Args:
            holdings: List of portfolio company share holdings
            quantities: Quantities held for each holding
            return_series: Return time series for each holding

        Returns:
            Portfolio variance (float)
            Returns None if variance cannot be computed

        Raises:
            ValueError: If input dimensions are inconsistent
        """
        n = len(holdings)

        if not (len(quantities) == len(return_series) == n):
            raise ValueError("Holdings, quantities, and return series must have the same length")

        if n < 1:
            return None

        series_length = len(return_series[0])
        if series_length < 2:
            return None

        for series in return_series:
            if len(series) != series_length:
                raise ValueError("All return series must have the same length")

        # ---- Helpers --------------------------------------------------------

        def mean(x: List[Decimal]) -> Decimal:
            return sum(x) / Decimal(len(x))

        def variance(x: List[Decimal]) -> Decimal:
            mu = mean(x)
            return sum((xi - mu) ** 2 for xi in x) / Decimal(len(x) - 1)

        def covariance(x: List[Decimal], y: List[Decimal]) -> Decimal:
            mu_x = mean(x)
            mu_y = mean(y)
            return sum(
                (xi - mu_x) * (yi - mu_y) for xi, yi in zip(x, y)
            ) / Decimal(len(x) - 1)

        # ---- Compute weights ------------------------------------------------

        holding_values: List[Decimal] = []
        total_value = Decimal("0")

        for holding, quantity in zip(holdings, quantities):
            if holding.asset.price is None:
                raise ValueError(f"Holding {holding.id} has no price information")

            price = Decimal(str(holding.asset.price))
            value = quantity * price

            holding_values.append(value)
            total_value += value

        if total_value == 0:
            return None

        weights = [value / total_value for value in holding_values]

        # ---- Compute portfolio variance ------------------------------------

        portfolio_variance = Decimal("0")

        for i in range(n):
            var_i = variance(return_series[i])
            portfolio_variance += weights[i] ** 2 * var_i

            for j in range(i + 1, n):
                cov_ij = covariance(return_series[i], return_series[j])
                portfolio_variance += Decimal("2") * weights[i] * weights[j] * cov_ij

        return float(portfolio_variance)
