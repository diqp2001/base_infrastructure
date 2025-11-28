"""
src/domain/entities/factor/share_target_factor.py

ShareTargetFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
from typing import Optional
from .share_factor import ShareFactor


class ShareTargetFactor(ShareFactor):
    """Domain entity representing a share target variable factor for model training."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,


        target_type: Optional[str] = None,
        forecast_horizon: Optional[int] = None,
        is_scaled: Optional[bool] = None,
        scaling_method: Optional[str] = None,
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
        self.target_type = target_type or "return"  # e.g., "return", "price", "direction", "volatility"
        self.forecast_horizon = forecast_horizon or 1  # Days ahead to predict
        self.is_scaled = is_scaled or False  # Whether target is normalized/scaled
        self.scaling_method = scaling_method  # e.g., "z_score", "min_max", "robust"

    def calculate_future_return(self, current_price: float, future_price: float) -> Optional[float]:
        """Calculate the future return target variable."""
        if current_price <= 0 or future_price <= 0:
            return None
        
        return (future_price / current_price) - 1

    def calculate_price_direction(self, current_price: float, future_price: float) -> Optional[int]:
        """Calculate the price direction target variable (1 for up, 0 for down)."""
        if current_price <= 0 or future_price <= 0:
            return None
        
        return 1 if future_price > current_price else 0

    def is_return_target(self) -> bool:
        """Check if this is a return-based target variable."""
        return self.target_type.lower() == "return"

    def is_classification_target(self) -> bool:
        """Check if this is a classification target (direction, category)."""
        classification_types = ["direction", "category", "binary", "class"]
        return any(t in self.target_type.lower() for t in classification_types)

    def is_short_term_target(self) -> bool:
        """Check if this is a short-term prediction target."""
        return self.forecast_horizon <= 5

    def is_medium_term_target(self) -> bool:
        """Check if this is a medium-term prediction target."""
        return 5 < self.forecast_horizon <= 30

    def is_long_term_target(self) -> bool:
        """Check if this is a long-term prediction target."""
        return self.forecast_horizon > 30

    def calculate_target(self, prices: list, forecast_horizon: int = None, is_scaled: bool = None) -> list:
        """
        Calculate target values based on price data.
        
        Args:
            prices: List of price values
            forecast_horizon: Number of periods ahead to predict (uses instance default if None)
            is_scaled: Whether to return scaled values (uses instance default if None)
            
        Returns:
            List of target values (returns or price directions)
        """
        if not prices or len(prices) < 2:
            return []
        
        horizon = forecast_horizon if forecast_horizon is not None else self.forecast_horizon
        scaled = is_scaled if is_scaled is not None else self.is_scaled
        
        target_values = []
        
        # Calculate target values based on target_type
        if self.target_type.lower() == "return":
            # Calculate future returns
            for i in range(len(prices) - horizon):
                current_price = prices[i]
                future_price = prices[i + horizon]
                
                if current_price > 0 and future_price > 0:
                    return_value = (future_price / current_price) - 1
                    target_values.append(return_value)
                else:
                    target_values.append(0.0)  # Default to 0 for invalid prices
                    
        elif "direction" in self.target_type.lower() or "binary" in self.target_type.lower():
            # Calculate price direction (1 for up, 0 for down)
            for i in range(len(prices) - horizon):
                current_price = prices[i]
                future_price = prices[i + horizon]
                
                if current_price > 0 and future_price > 0:
                    direction = 1 if future_price > current_price else 0
                    target_values.append(direction)
                else:
                    target_values.append(0)  # Default to 0 for invalid prices
        else:
            # Default to return calculation
            for i in range(len(prices) - horizon):
                current_price = prices[i]
                future_price = prices[i + horizon]
                
                if current_price > 0 and future_price > 0:
                    return_value = (future_price / current_price) - 1
                    target_values.append(return_value)
                else:
                    target_values.append(0.0)
        
        # Apply scaling if requested
        if scaled and target_values and self.scaling_method:
            target_values = self._apply_scaling(target_values)
        
        return target_values
    
    def _apply_scaling(self, values: list) -> list:
        """Apply scaling to target values based on scaling_method."""
        if not values or self.scaling_method is None:
            return values
            
        import numpy as np
        from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
        
        values_array = np.array(values).reshape(-1, 1)
        
        if self.scaling_method.lower() == 'z_score' or self.scaling_method.lower() == 'standard':
            scaler = StandardScaler()
        elif self.scaling_method.lower() == 'min_max' or self.scaling_method.lower() == 'minmax':
            scaler = MinMaxScaler()
        elif self.scaling_method.lower() == 'robust':
            scaler = RobustScaler()
        else:
            # Default to standard scaling
            scaler = StandardScaler()
        
        try:
            scaled_values = scaler.fit_transform(values_array)
            return scaled_values.flatten().tolist()
        except Exception:
            # Return original values if scaling fails
            return values