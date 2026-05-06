import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor


class CompanySharePortfolioOptionThetaFactor(CompanySharePortfolioOptionFactor):
    """Theta factor associated with company share portfolio options."""

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
        Calculate theta for company share portfolio options using Black-Scholes model.
        
        Theta measures the rate of change of the option value with respect to the passage of time.
        """
        if stock_price <= 0 or strike_price <= 0 or volatility <= 0 or time_to_expiry <= 0:
            return None

        # Adjust for dividend yield
        adjusted_stock = stock_price * math.exp(-dividend_yield * time_to_expiry)
        
        d1, d2 = self._d1_d2(adjusted_stock, strike_price, risk_free_rate, volatility, time_to_expiry)
        if d1 is None:
            return None

        # Standard normal probability density function
        phi_d1 = (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * d1 * d1)
        
        sqrt_T = math.sqrt(time_to_expiry)
        exp_minus_rT = math.exp(-risk_free_rate * time_to_expiry)
        exp_minus_qT = math.exp(-dividend_yield * time_to_expiry)

        if option_type.lower() == "call":
            theta = (
                (-adjusted_stock * phi_d1 * volatility * exp_minus_qT) / (2 * sqrt_T) -
                risk_free_rate * strike_price * exp_minus_rT * self._norm_cdf(d2) +
                dividend_yield * adjusted_stock * exp_minus_qT * self._norm_cdf(d1)
            )
        else:  # put
            theta = (
                (-adjusted_stock * phi_d1 * volatility * exp_minus_qT) / (2 * sqrt_T) +
                risk_free_rate * strike_price * exp_minus_rT * self._norm_cdf(-d2) -
                dividend_yield * adjusted_stock * exp_minus_qT * self._norm_cdf(-d1)
            )

        return theta * multiplier / 365  # Convert to daily theta

    def calculate_portfolio_theta(
        self,
        portfolio_weights: dict,
        individual_thetas: dict,
    ) -> Optional[float]:
        """
        Calculate portfolio-level theta for options on a portfolio of company shares.
        
        Args:
            portfolio_weights: Dictionary of weights for each portfolio component
            individual_thetas: Dictionary of theta values for each portfolio component
            
        Returns:
            Portfolio-weighted theta
        """
        if not portfolio_weights or not individual_thetas:
            return None
            
        portfolio_theta = sum(
            weight * individual_thetas.get(asset, 0) 
            for asset, weight in portfolio_weights.items()
            if asset in individual_thetas
        )
        
        return portfolio_theta

    def calculate_theta_pnl(
        self,
        theta: float,
        time_passage: float = 1.0,  # Time passage in days
    ) -> Optional[float]:
        """
        Calculate P&L from theta exposure given the passage of time.
        
        Theta P&L = Theta * Time Passage
        """
        if theta is None:
            return None
            
        return theta * time_passage

    def calculate_weekend_theta(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        option_type: str = "call",
        dividend_yield: float = 0.0,
        multiplier: int = 100,
        weekend_days: float = 2.0,
    ) -> Optional[float]:
        """
        Calculate theta for weekend time decay (when markets are closed).
        
        This accounts for the fact that time decay continues over weekends
        even though markets are closed.
        """
        base_theta = self.calculate(
            stock_price, strike_price, risk_free_rate, volatility,
            time_to_expiry, option_type, dividend_yield, multiplier
        )
        
        if base_theta is None:
            return None
            
        # Weekend theta is typically higher due to accelerated time decay
        weekend_multiplier = 1.0 + (weekend_days - 1) * 0.1  # Simplified calculation
        return base_theta * weekend_multiplier

    def calculate_theta_decay_profile(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        initial_time_to_expiry: float,
        option_type: str = "call",
        dividend_yield: float = 0.0,
        multiplier: int = 100,
        days_to_track: int = 30,
    ) -> list:
        """
        Calculate theta decay profile over time until expiration.
        
        Returns a list of theta values as the option approaches expiration.
        """
        theta_profile = []
        
        for day in range(days_to_track):
            days_remaining = max(initial_time_to_expiry * 365 - day, 1)
            time_remaining = days_remaining / 365
            
            theta = self.calculate(
                stock_price, strike_price, risk_free_rate, volatility,
                time_remaining, option_type, dividend_yield, multiplier
            )
            
            theta_profile.append({
                'day': day,
                'days_remaining': days_remaining,
                'theta': theta
            })
        
        return theta_profile

    def calculate_moneyness_adjusted_theta(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        option_type: str = "call",
        dividend_yield: float = 0.0,
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate theta adjusted for option moneyness.
        
        At-the-money options typically have the highest theta,
        while deep in-the-money and out-of-the-money options have lower theta.
        """
        base_theta = self.calculate(
            stock_price, strike_price, risk_free_rate, volatility,
            time_to_expiry, option_type, dividend_yield, multiplier
        )
        
        if base_theta is None:
            return None
        
        # Calculate moneyness
        moneyness = stock_price / strike_price if strike_price > 0 else 0
        
        # Adjustment factor based on moneyness
        if 0.95 <= moneyness <= 1.05:  # At-the-money
            adjustment = 1.0
        elif 0.85 <= moneyness < 0.95 or 1.05 < moneyness <= 1.15:  # Slightly out-of-the-money
            adjustment = 0.8
        else:  # Deep in/out-of-the-money
            adjustment = 0.5
            
        return base_theta * adjustment

    def calculate_implied_volatility_theta(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        vol_change: float,  # Change in implied volatility
        option_type: str = "call",
        dividend_yield: float = 0.0,
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate theta when implied volatility is also changing.
        
        This accounts for the interaction between time decay and volatility changes.
        """
        # Base theta at current volatility
        base_theta = self.calculate(
            stock_price, strike_price, risk_free_rate, volatility,
            time_to_expiry, option_type, dividend_yield, multiplier
        )
        
        # Theta at new volatility
        new_theta = self.calculate(
            stock_price, strike_price, risk_free_rate, volatility + vol_change,
            time_to_expiry, option_type, dividend_yield, multiplier
        )
        
        if base_theta is None or new_theta is None:
            return base_theta
            
        # Volatility-adjusted theta
        return new_theta + (new_theta - base_theta) * 0.5  # Simplified interaction effect