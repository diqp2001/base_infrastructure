import math
from typing import Optional

from domain.entities.factor.finance.portfolio.derivatives.option.company_share_option_portfolio.company_share_option_portfolio_factor import CompanyShareOptionPortfolioFactor


class CompanyShareOptionPortfolioDeltaFactor(CompanyShareOptionPortfolioFactor):
    """Delta factor associated with portfolio company share options."""

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
        Calculate delta for portfolio company share options using Black-Scholes model.
        """
        if stock_price <= 0 or strike_price <= 0 or volatility <= 0 or time_to_expiry <= 0:
            return None

        # Adjust for dividend yield
        adjusted_stock = stock_price * math.exp(-dividend_yield * time_to_expiry)
        
        d1, d2 = self._d1_d2(adjusted_stock, strike_price, risk_free_rate, volatility, time_to_expiry)
        if d1 is None:
            return None

        dividend_discount = math.exp(-dividend_yield * time_to_expiry)

        if option_type.lower() == "call":
            delta = dividend_discount * self._norm_cdf(d1)
        else:  # put
            delta = dividend_discount * (self._norm_cdf(d1) - 1)

        return delta * multiplier

    def calculate_dollar_delta(
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
        Calculate dollar delta (delta * stock price * multiplier).
        Represents the dollar change in option value for a 1 point move in the stock.
        """
        delta = self.calculate_delta(
            stock_price, strike_price, risk_free_rate, volatility,
            time_to_expiry, option_type, dividend_yield, multiplier
        )
        if delta is None:
            return None
            
        return delta * stock_price

    def calculate_hedge_ratio(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        option_type: str = "call",
        dividend_yield: float = 0.0,
        multiplier: int = 100,
        hedge_instrument_multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate hedge ratio for hedging option position with underlying stock.
        
        Args:
            hedge_instrument_multiplier: Multiplier of the hedging instrument
            
        Returns:
            Number of hedge instrument shares needed per option contract
        """
        delta = self.calculate_delta(
            stock_price, strike_price, risk_free_rate, volatility,
            time_to_expiry, option_type, dividend_yield, multiplier
        )
        if delta is None:
            return None
            
        return (delta * multiplier) / hedge_instrument_multiplier

    def calculate_portfolio_delta(
        self,
        portfolio_weights: dict,
        individual_deltas: dict,
    ) -> Optional[float]:
        """
        Calculate portfolio-level delta for options on a portfolio of company shares.
        
        Args:
            portfolio_weights: Dictionary of weights for each portfolio component
            individual_deltas: Dictionary of delta values for each portfolio component
            
        Returns:
            Portfolio-weighted delta
        """
        if not portfolio_weights or not individual_deltas:
            return None
            
        portfolio_delta = sum(
            weight * individual_deltas.get(asset, 0) 
            for asset, weight in portfolio_weights.items()
            if asset in individual_deltas
        )
        
        return portfolio_delta

    def calculate_gamma(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        dividend_yield: float = 0.0,
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate gamma (second derivative of option value with respect to underlying price).
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
        
        dividend_discount = math.exp(-dividend_yield * time_to_expiry)
        gamma = (dividend_discount * phi_d1) / (adjusted_stock * volatility * math.sqrt(time_to_expiry))
        
        return gamma * multiplier

    def calculate_delta_sensitivity_to_portfolio_composition(
        self,
        current_delta: float,
        portfolio_weight_change: float,
        asset_correlation: float = 1.0,
    ) -> Optional[float]:
        """
        Calculate how delta changes with portfolio composition changes.
        
        Args:
            current_delta: Current delta value
            portfolio_weight_change: Change in portfolio weight for specific asset
            asset_correlation: Correlation of the asset with the overall portfolio
            
        Returns:
            Change in delta due to portfolio rebalancing
        """
        if current_delta == 0:
            return None
            
        # Delta sensitivity to portfolio composition
        delta_sensitivity = current_delta * portfolio_weight_change * asset_correlation
        return delta_sensitivity