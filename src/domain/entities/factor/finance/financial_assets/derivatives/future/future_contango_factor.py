"""
Example factor implementation using the new discriminator-based dependency system.
This demonstrates the structure described in the GitHub issue.
"""

from __future__ import annotations
from typing import Optional
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor
import math


class FutureContangoFactor(FutureFactor):
    """
    Future contango factor demonstrating discriminator-based dependencies.
    
    Contango occurs when future price > spot price, indicating normal market conditions.
    This factor requires dependencies on other factors stored in the database.
    """
    
    # Class-level dependencies using discriminator format as specified in the issue
    dependencies = {
        "spot_price": {
            "factor": {
                "discriminator": {
                    "code": "MARKET_SPOT_PRICE",
                    "version": "v1",
                },
                "name": "Spot Price",
                "group": "Market Price",
                "subgroup": "Spot",
                "source": "IBKR",
            },
            "required": True,
        },
        "future_price": {
            "factor": {
                "discriminator": {
                    "code": "MARKET_FUTURE_PRICE",
                    "version": "v1",
                },
                "name": "Future Price",
                "group": "Market Price",
                "subgroup": "Future",
                "source": "IBKR",
            },
            "required": True,
        },
        "T": {
            "factor": {
                "discriminator": {
                    "code": "FUTURE_TIME_TO_MATURITY",
                    "version": "v1",
                },
                "name": "Time To Maturity",
                "group": "Future Factor",
                "subgroup": "Contract",
                "source": "model",
            },
            "required": True,
        },
    }
    
    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            name="Future Contango",
            group="Future Factor",
            subgroup="Market Structure",
            data_type="float",
            source="model",
            definition="Measures contango/backwardation in futures market. Positive values indicate contango (future > spot), negative values indicate backwardation (future < spot).",
            factor_id=factor_id,
            **kwargs
        )
    
    def calculate(
        self,
        spot_price: float,
        future_price: float,
        T: float
    ) -> Optional[float]:
        """
        Calculate contango factor.
        
        Formula: (Future Price - Spot Price) / (Spot Price * T)
        
        Args:
            spot_price: Current spot price (resolved from database)
            future_price: Current future price (resolved from database)
            T: Time to maturity in years (resolved from database)
            
        Returns:
            Contango factor value or None if calculation not possible
        """
        if spot_price <= 0 or T <= 0:
            return None
        
        # Calculate annualized contango rate
        raw_contango = (future_price - spot_price) / spot_price
        annualized_contango = raw_contango / T
        
        return annualized_contango
    
    def calculate_backwardation_strength(
        self,
        spot_price: float,
        future_price: float,
        T: float
    ) -> Optional[str]:
        """
        Alternative calculation method that returns market structure classification.
        
        This demonstrates how factors can have multiple calculation methods.
        """
        contango_value = self.calculate(spot_price, future_price, T)
        
        if contango_value is None:
            return None
        elif contango_value > 0.05:  # > 5% annualized
            return "Strong Contango"
        elif contango_value > 0:
            return "Mild Contango"  
        elif contango_value > -0.05:
            return "Mild Backwardation"
        else:
            return "Strong Backwardation"