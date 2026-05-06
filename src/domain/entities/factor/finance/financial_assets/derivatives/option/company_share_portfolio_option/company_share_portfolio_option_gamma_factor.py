import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor


class CompanySharePortfolioOptionGammaFactor(CompanySharePortfolioOptionFactor):
    """Gamma factor associated with company share portfolio options."""

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
        dividend_yield: float = 0.0,  # dividend yield of underlying stock
        multiplier: int = 100,        # contract multiplier
    ) -> Optional[float]:
        """
        Calculate gamma for company share portfolio options using Black-Scholes model.
        
        Gamma measures the rate of change of delta with respect to changes in the underlying price.
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

    def calculate_dollar_gamma(
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
        Calculate dollar gamma (gamma * stock price^2 / 100).
        Represents the dollar change in delta for a 1% move in the stock price.
        """
        gamma = self.calculate(
            stock_price, strike_price, risk_free_rate, volatility,
            time_to_expiry, dividend_yield, multiplier
        )
        if gamma is None:
            return None
            
        return gamma * stock_price * stock_price / 100

    def calculate_gamma_percentage(
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
        Calculate percentage gamma (gamma * stock price / 100).
        Represents the percentage change in delta for a 1% move in the stock price.
        """
        gamma = self.calculate(
            stock_price, strike_price, risk_free_rate, volatility,
            time_to_expiry, dividend_yield, multiplier
        )
        if gamma is None:
            return None
            
        return gamma * stock_price / 100

    def calculate_portfolio_gamma(
        self,
        portfolio_weights: dict,
        individual_gammas: dict,
        correlation_matrix: dict = None,
    ) -> Optional[float]:
        """
        Calculate portfolio-level gamma for options on a portfolio of company shares.
        
        Args:
            portfolio_weights: Dictionary of weights for each portfolio component
            individual_gammas: Dictionary of gamma values for each portfolio component
            correlation_matrix: Cross-gamma correlation effects (simplified as None for now)
            
        Returns:
            Portfolio-weighted gamma
        """
        if not portfolio_weights or not individual_gammas:
            return None
            
        portfolio_gamma = sum(
            weight * individual_gammas.get(asset, 0) 
            for asset, weight in portfolio_weights.items()
            if asset in individual_gammas
        )
        
        # Note: This is a simplified calculation
        # In reality, portfolio gamma would include cross-gamma terms
        # involving correlations between underlying assets
        
        return portfolio_gamma

    def calculate_cross_gamma(
        self,
        stock_price_1: float,
        stock_price_2: float,
        correlation: float,
        portfolio_weight_1: float,
        portfolio_weight_2: float,
        gamma_1: float,
        gamma_2: float,
    ) -> Optional[float]:
        """
        Calculate cross-gamma between two assets in the portfolio.
        
        Cross-gamma measures how the gamma of one asset affects another
        through portfolio correlations.
        """
        if correlation == 0 or portfolio_weight_1 == 0 or portfolio_weight_2 == 0:
            return 0.0
            
        # Simplified cross-gamma calculation
        cross_gamma = correlation * math.sqrt(gamma_1 * gamma_2) * portfolio_weight_1 * portfolio_weight_2
        
        return cross_gamma

    def calculate_gamma_pnl(
        self,
        gamma: float,
        price_change: float,
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate P&L from gamma exposure given a price change.
        
        Gamma P&L = 0.5 * Gamma * (Price Change)^2
        """
        if gamma is None:
            return None
            
        gamma_pnl = 0.5 * gamma * price_change * price_change
        return gamma_pnl

    def calculate_gamma_hedging_requirement(
        self,
        current_gamma: float,
        target_gamma: float,
        hedge_instrument_gamma: float,
    ) -> Optional[float]:
        """
        Calculate the quantity of hedge instrument needed to achieve target gamma.
        
        Args:
            current_gamma: Current portfolio gamma exposure
            target_gamma: Desired gamma exposure (often 0 for gamma-neutral)
            hedge_instrument_gamma: Gamma of the hedging instrument per unit
            
        Returns:
            Number of hedge instrument units needed
        """
        if hedge_instrument_gamma == 0:
            return None
            
        gamma_difference = target_gamma - current_gamma
        hedge_quantity = gamma_difference / hedge_instrument_gamma
        
        return hedge_quantity

    def calculate_gamma_decay(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        time_step: float = 1/365,  # Daily decay by default
        dividend_yield: float = 0.0,
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate gamma decay over a time step (theta effect on gamma).
        """
        if time_to_expiry <= time_step:
            return None
            
        current_gamma = self.calculate(
            stock_price, strike_price, risk_free_rate, volatility,
            time_to_expiry, dividend_yield, multiplier
        )
        
        future_gamma = self.calculate(
            stock_price, strike_price, risk_free_rate, volatility,
            time_to_expiry - time_step, dividend_yield, multiplier
        )
        
        if current_gamma is None or future_gamma is None:
            return None
            
        return future_gamma - current_gamma