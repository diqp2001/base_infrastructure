from __future__ import annotations
from typing import Optional, List
from decimal import Decimal

from .portfolio_factor import PortfolioFactor
from domain.entities.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding


class PortfolioCompanyShareReturnFactor(PortfolioFactor):
    """
    Factor representing the total return of all company share holdings in a portfolio.

    This factor computes the portfolio return as a value-weighted aggregation
    of individual company share returns.

    Portfolio Return = Σ (Weight_i × Return_i)
    where:
        Weight_i = Holding Value_i / Total Portfolio Value

    This definition aligns with standard portfolio theory and performance measurement.
    """

    def __init__(
        self,
        name: str = "Portfolio Company Share Return",
        group: str = "portfolio",
        subgroup: Optional[str] = "return",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "portfolio_management",
        definition: Optional[str] = "Value-weighted return of all company share holdings in portfolio",
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

    def calculate_portfolio_return(
        self,
        holdings: List[PortfolioCompanyShareHolding],
        quantities: List[Decimal],
        returns: List[Decimal],
    ) -> Decimal:
        """
        Calculate the value-weighted portfolio return.

        Args:
            holdings: List of portfolio company share holdings
            quantities: List of quantities held for each holding
            returns: List of returns for each holding (as decimals, e.g. 0.05 for 5%)

        Returns:
            Portfolio return as a Decimal

        Raises:
            ValueError: If input lists have different lengths
                        or if price/return data is missing
        """
        if not (len(holdings) == len(quantities) == len(returns)):
            raise ValueError("Holdings, quantities, and returns lists must have the same length")

        total_portfolio_value = Decimal("0")
        holding_values: List[Decimal] = []

        # First pass: compute holding values and total portfolio value
        for holding, quantity in zip(holdings, quantities):
            if holding.asset.price is None:
                raise ValueError(f"Holding {holding.id} has no price information")

            if quantity < 0:
                raise ValueError(f"Quantity for holding {holding.id} cannot be negative")

            price = Decimal(str(holding.asset.price))
            value = quantity * price

            holding_values.append(value)
            total_portfolio_value += value

        if total_portfolio_value == 0:
            raise ValueError("Total portfolio value is zero; cannot compute return")

        # Second pass: compute weighted return
        portfolio_return = Decimal("0")

        for value, holding_return in zip(holding_values, returns):
            weight = value / total_portfolio_value
            portfolio_return += weight * holding_return

        return portfolio_return
