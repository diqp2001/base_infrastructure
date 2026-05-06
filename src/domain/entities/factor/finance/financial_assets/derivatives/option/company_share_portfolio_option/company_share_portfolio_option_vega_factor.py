import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor


class CompanySharePortfolioOptionVegaFactor(CompanySharePortfolioOptionFactor):
    """Vega factor associated with company share portfolio options."""

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
        Calculate vega for company share portfolio options using Black-Scholes model.
        
        Vega measures the rate of change of the option value with respect to changes in implied volatility.
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
        
        exp_minus_qT = math.exp(-dividend_yield * time_to_expiry)
        sqrt_T = math.sqrt(time_to_expiry)

        # Vega is the same for both calls and puts
        vega = adjusted_stock * exp_minus_qT * phi_d1 * sqrt_T

        return vega * multiplier / 100  # Convert to percentage point change

    def calculate_portfolio_vega(
        self,
        portfolio_weights: dict,
        individual_vegas: dict,
        correlation_matrix: dict = None,
    ) -> Optional[float]:
        """
        Calculate portfolio-level vega for options on a portfolio of company shares.
        
        Args:
            portfolio_weights: Dictionary of weights for each portfolio component
            individual_vegas: Dictionary of vega values for each portfolio component
            correlation_matrix: Volatility correlations between portfolio components
            
        Returns:
            Portfolio-weighted vega
        """
        if not portfolio_weights or not individual_vegas:
            return None
            
        # Simple weighted vega
        portfolio_vega = sum(
            weight * individual_vegas.get(asset, 0) 
            for asset, weight in portfolio_weights.items()
            if asset in individual_vegas
        )
        
        # Note: In reality, portfolio vega would include correlation effects
        # between volatilities of different assets in the portfolio
        
        return portfolio_vega

    def calculate_vega_pnl(
        self,
        vega: float,
        volatility_change: float,  # Change in implied volatility (in percentage points)
    ) -> Optional[float]:
        """
        Calculate P&L from vega exposure given a volatility change.
        
        Vega P&L = Vega * Volatility Change
        """
        if vega is None:
            return None
            
        return vega * volatility_change

    def calculate_volga(
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
        Calculate volga (vomma) - the second derivative of option value with respect to volatility.
        
        Volga measures the rate of change of vega with respect to volatility changes.
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
        
        exp_minus_qT = math.exp(-dividend_yield * time_to_expiry)
        sqrt_T = math.sqrt(time_to_expiry)

        # Volga calculation
        volga = adjusted_stock * exp_minus_qT * phi_d1 * sqrt_T * d1 * d2 / volatility

        return volga * multiplier / 10000  # Convert to 0.01% point change

    def calculate_vanna(
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
        Calculate vanna - the sensitivity of delta to volatility changes.
        
        Vanna measures the rate of change of delta with respect to volatility changes.
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
        
        exp_minus_qT = math.exp(-dividend_yield * time_to_expiry)

        # Vanna calculation
        vanna = -exp_minus_qT * phi_d1 * d2 / volatility

        return vanna * multiplier / 100

    def calculate_term_structure_vega(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        term_structure_shift: float,  # Parallel shift in volatility term structure
        dividend_yield: float = 0.0,
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate vega for parallel shifts in volatility term structure.
        
        This accounts for the fact that volatilities across different expiries
        often move together.
        """
        base_vega = self.calculate(
            stock_price, strike_price, risk_free_rate, volatility,
            time_to_expiry, dividend_yield, multiplier
        )
        
        if base_vega is None:
            return None
            
        # For term structure shifts, vega is adjusted by the size of the shift
        # and the time to expiry
        term_adjustment = 1.0 + term_structure_shift * math.sqrt(time_to_expiry)
        return base_vega * term_adjustment

    def calculate_skew_vega(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        skew_shift: float,  # Change in volatility skew
        dividend_yield: float = 0.0,
        multiplier: int = 100,
    ) -> Optional[float]:
        """
        Calculate vega sensitivity to volatility skew changes.
        
        This measures how the option value changes when the volatility
        skew (different volatilities for different strikes) changes.
        """
        base_vega = self.calculate(
            stock_price, strike_price, risk_free_rate, volatility,
            time_to_expiry, dividend_yield, multiplier
        )
        
        if base_vega is None:
            return None
        
        # Calculate moneyness to determine skew sensitivity
        moneyness = stock_price / strike_price if strike_price > 0 else 1.0
        
        # Out-of-the-money puts and in-the-money calls are more sensitive to skew
        if moneyness < 0.95:  # OTM puts
            skew_sensitivity = 1.5
        elif moneyness > 1.05:  # ITM calls
            skew_sensitivity = 1.2
        else:  # ATM options
            skew_sensitivity = 0.8
            
        return base_vega * skew_shift * skew_sensitivity

    def calculate_vega_hedging_requirement(
        self,
        current_vega: float,
        target_vega: float,
        hedge_instrument_vega: float,
    ) -> Optional[float]:
        """
        Calculate the quantity of hedge instrument needed to achieve target vega.
        
        Args:
            current_vega: Current portfolio vega exposure
            target_vega: Desired vega exposure (often 0 for vega-neutral)
            hedge_instrument_vega: Vega of the hedging instrument per unit
            
        Returns:
            Number of hedge instrument units needed
        """
        if hedge_instrument_vega == 0:
            return None
            
        vega_difference = target_vega - current_vega
        hedge_quantity = vega_difference / hedge_instrument_vega
        
        return hedge_quantity

    def calculate_correlation_adjusted_vega(
        self,
        individual_vegas: list,
        correlation_matrix: list,
        portfolio_weights: list,
    ) -> Optional[float]:
        """
        Calculate portfolio vega accounting for correlations between asset volatilities.
        
        This provides a more accurate measure of portfolio vega when
        volatilities of different assets are correlated.
        """
        if not individual_vegas or not portfolio_weights:
            return None
            
        n_assets = len(individual_vegas)
        if len(portfolio_weights) != n_assets:
            return None
            
        # Simple portfolio vega (no correlation)
        simple_vega = sum(w * v for w, v in zip(portfolio_weights, individual_vegas))
        
        if not correlation_matrix or len(correlation_matrix) != n_assets:
            return simple_vega
            
        # Correlation-adjusted vega (simplified calculation)
        correlation_adjustment = 0.0
        for i in range(n_assets):
            for j in range(n_assets):
                if i != j and j < len(correlation_matrix[i]):
                    correlation_adjustment += (
                        portfolio_weights[i] * portfolio_weights[j] *
                        individual_vegas[i] * individual_vegas[j] *
                        correlation_matrix[i][j]
                    )
        
        # This is a simplified approach; full calculation would be more complex
        return simple_vega + correlation_adjustment * 0.1