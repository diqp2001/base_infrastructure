# application/services/cash_flow_service.py
import math
from domain.entities.financial_statements.financial_statement_items.cash_flow import CashFlow
from domain.entities.financial_assets.currency import Currency

class CashFlowService:
    @staticmethod
    def calculate_var(cash_flow: CashFlow, currency: Currency, revenue_volatility: float, confidence_level: float, correlation: float) -> float:
        """
        Calculate Value at Risk (VaR) for a cash flow in a foreign currency.
        
        Args:
            cash_flow (CashFlow): The cash flow object containing amount and currency.
            currency (Currency): The currency object with exchange rate and volatility.
            revenue_volatility (float): Revenue volatility (daily) as a percentage.
            confidence_level (float): Confidence level as a decimal (e.g., 0.95 for 95%).
            correlation (float): Correlation between revenue and exchange rate volatility.
        
        Returns:
            float: Value at Risk (VaR) in base currency.
        """
        # Z-score for given confidence level (e.g., 1.645 for 95%)
        from scipy.stats import norm
        z = norm.ppf(confidence_level)

        # Convert cash flow to base currency
        cash_flow_base = cash_flow.amount * currency.exchange_rate

        # Calculate combined volatility
        revenue_volatility_base = revenue_volatility * currency.exchange_rate
        combined_volatility = math.sqrt(
            (cash_flow.amount * currency.volatility) ** 2 +
            revenue_volatility_base ** 2 +
            2 * correlation * (cash_flow.amount * currency.volatility) * revenue_volatility_base
        )

        # Calculate VaR
        var = z * combined_volatility
        return var
