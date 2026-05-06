import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor


class CompanySharePortfolioOptionRhoFactor(CompanySharePortfolioOptionFactor):
    """Rho factor associated with company share portfolio options."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
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
            **kwargs,
        )

    def calculate(
        self,
        stock_price: float,        # current stock price
        strike_price: float,       # strike price
        risk_free_rate: float,     # risk-free rate
        volatility: float,         # implied volatility
        time_to_expiry: float,     # time to expiration in years
        option_type: str = "call",
        dividend_yield: float = 0.0,  # dividend yield of underlying stock
        multiplier: int = 100,        # contract multiplier
    ) -> Optional[float]:
        """
        Calculate rho for company share portfolio options using Black-Scholes model.
        
        Rho measures the rate of change of the option value with respect to changes in the risk-free interest rate.
        """
        if stock_price <= 0 or strike_price <= 0 or volatility <= 0 or time_to_expiry <= 0:
            return None

        # Adjust for dividend yield
        adjusted_stock = stock_price * math.exp(-dividend_yield * time_to_expiry)
        
        d1, d2 = self._d1_d2(adjusted_stock, strike_price, risk_free_rate, volatility, time_to_expiry)
        if d1 is None:
            return None

        if option_type.lower() == "call":
            rho = strike_price * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * self._norm_cdf(d2)
        else:  # put
            rho = -strike_price * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * self._norm_cdf(-d2)

        return rho * multiplier / 100  # Convert to percentage point change

    def calculate_portfolio_rho(
        self,
        portfolio_weights: dict,
        individual_rhos: dict,
    ) -> Optional[float]:
        """
        Calculate portfolio-level rho for options on a portfolio of company shares.
        
        Args:
            portfolio_weights: Dictionary of weights for each portfolio component
            individual_rhos: Dictionary of rho values for each portfolio component
            
        Returns:
            Portfolio-weighted rho
        """
        if not portfolio_weights or not individual_rhos:
            return None
            
        portfolio_rho = sum(
            weight * individual_rhos.get(asset, 0) 
            for asset, weight in portfolio_weights.items()
            if asset in individual_rhos
        )
        
        return portfolio_rho

    def calculate_duration_adjusted_rho(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        portfolio_duration: float,  # Duration of the underlying portfolio
        option_type: str = "call",
        dividend_yield: float = 0.0,
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate duration-adjusted rho for portfolio options with bond components.
        
        This accounts for the fact that portfolio options may include bond components
        that have different interest rate sensitivities.
        """
        base_rho = self.calculate(
            stock_price, strike_price, risk_free_rate, volatility,
            time_to_expiry, option_type, dividend_yield, multiplier
        )
        
        if base_rho is None or portfolio_duration <= 0:
            return base_rho
            
        # Adjust rho by portfolio duration
        duration_adjustment = 1 + (portfolio_duration - 1) * 0.1  # Simplified adjustment
        return base_rho * duration_adjustment

    def calculate_rho_pnl(
        self,
        rho: float,
        rate_change: float,  # Change in interest rate (in percentage points)
    ) -> Optional[float]:
        """
        Calculate P&L from rho exposure given an interest rate change.
        
        Rho P&L = Rho * Rate Change
        """
        if rho is None:
            return None
            
        return rho * rate_change

    def calculate_rho_hedging_requirement(
        self,
        current_rho: float,
        target_rho: float,
        hedge_instrument_rho: float,
    ) -> Optional[float]:
        """
        Calculate the quantity of hedge instrument needed to achieve target rho.
        
        Args:
            current_rho: Current portfolio rho exposure
            target_rho: Desired rho exposure (often 0 for rho-neutral)
            hedge_instrument_rho: Rho of the hedging instrument per unit
            
        Returns:
            Number of hedge instrument units needed
        """
        if hedge_instrument_rho == 0:
            return None
            
        rho_difference = target_rho - current_rho
        hedge_quantity = rho_difference / hedge_instrument_rho
        
        return hedge_quantity

    def calculate_convexity_adjusted_rho(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        rate_change: float,
        option_type: str = "call",
        dividend_yield: float = 0.0,
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate convexity-adjusted rho for large rate changes.
        
        This accounts for the non-linear relationship between option price and interest rates.
        """
        if abs(rate_change) < 0.001:  # For small changes, regular rho is sufficient
            return self.calculate(
                stock_price, strike_price, risk_free_rate, volatility,
                time_to_expiry, option_type, dividend_yield, multiplier
            )
        
        # Calculate option price at current rate
        base_price = self._calculate_option_price(
            stock_price, strike_price, risk_free_rate, volatility,
            time_to_expiry, option_type, dividend_yield, multiplier
        )
        
        # Calculate option price at new rate
        new_price = self._calculate_option_price(
            stock_price, strike_price, risk_free_rate + rate_change, volatility,
            time_to_expiry, option_type, dividend_yield, multiplier
        )
        
        if base_price is None or new_price is None:
            return None
            
        # Convexity-adjusted rho
        return (new_price - base_price) / rate_change

    def _calculate_option_price(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        option_type: str,
        dividend_yield: float,
        multiplier: int,
    ) -> Optional[float]:
        """Helper method to calculate option price using Black-Scholes."""
        if stock_price <= 0 or strike_price <= 0 or volatility <= 0 or time_to_expiry <= 0:
            return None
        
        try:
            adjusted_stock = stock_price * math.exp(-dividend_yield * time_to_expiry)
            d1, d2 = self._d1_d2(adjusted_stock, strike_price, risk_free_rate, volatility, time_to_expiry)
            
            if d1 is None:
                return None
            
            if option_type.lower() == "call":
                price = (adjusted_stock * self._norm_cdf(d1) - 
                        strike_price * math.exp(-risk_free_rate * time_to_expiry) * self._norm_cdf(d2))
            else:  # put
                price = (strike_price * math.exp(-risk_free_rate * time_to_expiry) * self._norm_cdf(-d2) - 
                        adjusted_stock * self._norm_cdf(-d1))
            
            return price * multiplier
            
        except (ValueError, ZeroDivisionError, OverflowError):
            return None