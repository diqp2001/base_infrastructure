import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionPriceReturnFactor(CompanyShareOptionFactor):
    """Price return factor associated with company share options."""

    def __init__(
        self,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name="Company Share Option Price Return",
            group="Company Share Option Factor",
            subgroup="Price Return",
            data_type="float",
            source="calculated",
            definition="Price return of company share option calculated as percentage change in option value.",
            factor_id=factor_id,
            **kwargs,
        )

    def calculate_price_return(
        self,
        current_price: float,
        previous_price: float,
    ) -> Optional[float]:
        """
        Calculate the price return as percentage change.
        
        Args:
            current_price: Current option price
            previous_price: Previous option price
            
        Returns:
            Price return as decimal (e.g., 0.05 for 5% return)
        """
        if previous_price <= 0:
            return None
            
        return (current_price - previous_price) / previous_price

    def calculate_log_return(
        self,
        current_price: float,
        previous_price: float,
    ) -> Optional[float]:
        """
        Calculate the logarithmic return.
        
        Args:
            current_price: Current option price
            previous_price: Previous option price
            
        Returns:
            Log return as decimal
        """
        if current_price <= 0 or previous_price <= 0:
            return None
            
        return math.log(current_price / previous_price)

    def calculate_volatility_adjusted_return(
        self,
        current_price: float,
        previous_price: float,
        volatility: float,
        time_period: float = 1.0,
    ) -> Optional[float]:
        """
        Calculate volatility-adjusted return (return per unit of volatility).
        
        Args:
            current_price: Current option price
            previous_price: Previous option price
            volatility: Option's implied volatility
            time_period: Time period for the return (in years)
            
        Returns:
            Volatility-adjusted return
        """
        if volatility <= 0 or previous_price <= 0:
            return None
            
        price_return = self.calculate_price_return(current_price, previous_price)
        if price_return is None:
            return None
            
        # Adjust for time period and volatility
        annualized_return = price_return / time_period
        return annualized_return / volatility

    def calculate_sharpe_ratio(
        self,
        option_return: float,
        risk_free_rate: float,
        return_volatility: float,
    ) -> Optional[float]:
        """
        Calculate Sharpe ratio for the option returns.
        
        Args:
            option_return: Option return
            risk_free_rate: Risk-free rate
            return_volatility: Volatility of option returns
            
        Returns:
            Sharpe ratio
        """
        if return_volatility <= 0:
            return None
            
        excess_return = option_return - risk_free_rate
        return excess_return / return_volatility

    def calculate_underlying_correlation_return(
        self,
        option_return: float,
        underlying_stock_return: float,
    ) -> Optional[float]:
        """
        Calculate return adjusted for correlation with underlying company share.
        
        Args:
            option_return: Option return
            underlying_stock_return: Return of underlying company share
            
        Returns:
            Correlation-adjusted return measure
        """
        if underlying_stock_return == 0:
            return None
            
        # Beta-like measure of option sensitivity to underlying stock moves
        return option_return / underlying_stock_return

    def calculate_delta_adjusted_return(
        self,
        option_return: float,
        option_delta: float,
        underlying_return: float,
    ) -> Optional[float]:
        """
        Calculate delta-adjusted return to isolate non-directional components.
        
        Args:
            option_return: Option return
            option_delta: Option delta (sensitivity to underlying)
            underlying_return: Return of underlying stock
            
        Returns:
            Delta-adjusted return
        """
        if option_delta == 0:
            return option_return
            
        # Remove the expected return from delta exposure
        expected_delta_return = option_delta * underlying_return
        return option_return - expected_delta_return