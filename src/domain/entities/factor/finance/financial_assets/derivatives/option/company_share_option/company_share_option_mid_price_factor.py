"""
src/domain/entities/factor/finance/financial_assets/derivatives/option/company_share_option/company_share_option_mid_price_factor.py

CompanyShare Option Mid Price Factor domain entity - calculates true mid price from multiple data sources.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
import statistics
from decimal import Decimal
from .company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionMidPriceFactor(CompanyShareOptionFactor):
    """
    Domain entity representing a company share option mid price factor.
    
    This factor calculates the true mid price by:
    1. Collecting mid prices from multiple data sources
    2. Filtering same group and subgroup sources  
    3. Removing outliers using statistical methods
    4. Averaging the remaining valid prices
    """

    def __init__(
        self,
        name: str = "mid_price",
        group: str = "price",
        subgroup: Optional[str] = "mid_price_true",
        frequency: Optional[str] = None,
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "multiple",
        definition: Optional[str] = "True mid price calculated from multiple data sources with outlier filtering",
        factor_id: Optional[int] = None,
        outlier_threshold: float = 2.0,
        min_sources: int = 2,
        **kwargs,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            frequency=frequency,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
            **kwargs,
        )
        
        self.outlier_threshold = outlier_threshold
        self.min_sources = min_sources

    def calculate(self, source_prices: List[Dict[str, Any]]) -> Optional[Decimal]:
        """
        Calculate true mid price from multiple data sources.
        
        Args:
            source_prices: List of price dictionaries with keys:
                - 'source': str (data provider name)
                - 'price': Decimal (mid price)
                - 'timestamp': datetime
                - 'group': str
                - 'subgroup': str
                - 'strike': Optional[Decimal] (for options)
                - 'expiry': Optional[date] (for options)
                
        Returns:
            Optional[Decimal]: Calculated true mid price or None if insufficient data
        """
        if not source_prices or len(source_prices) < self.min_sources:
            return None

        filtered_prices = self._filter_same_group_subgroup(source_prices)
        
        if len(filtered_prices) < self.min_sources:
            return None
        if len(filtered_prices) == self.min_sources:

            valid_prices = self._remove_outliers(filtered_prices)
            
            if not valid_prices:
                return None

            return self._calculate_average_price(valid_prices)
        
        elif len(filtered_prices) > self.min_sources:

            valid_prices = self._remove_outliers(filtered_prices)
            
            if not valid_prices:
                return None

            return self._calculate_median_price(valid_prices)

    def _filter_same_group_subgroup(self, source_prices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter prices that match the same group and subgroup."""
        return [
            price for price in source_prices
            if price.get('group') == self.group and price.get('subgroup') == self.subgroup
        ]

    def _remove_outliers(self, prices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove outlier prices using statistical methods.
        
        Uses modified Z-score to identify and remove outliers.
        For options, additional validation based on option greeks if available.
        """
        if len(prices) <= 2:
            return prices

        price_values = [float(price['price']) for price in prices]
        
        try:
            median = statistics.median(price_values)
            mad = statistics.median([abs(x - median) for x in price_values])
            
            if mad == 0:
                return prices
            
            valid_prices = []
            for i, price_dict in enumerate(prices):
                modified_z_score = abs(price_values[i] - median) / (1.4826 * mad)
                if modified_z_score <= self.outlier_threshold:
                    valid_prices.append(price_dict)
            
            return valid_prices if valid_prices else prices[:1]
            
        except (ValueError, ZeroDivisionError):
            return prices

    def _calculate_average_price(self, prices: List[Dict[str, Any]]) -> Decimal:
        """Calculate the average price from valid prices."""
        total = sum(price['price'] for price in prices)
        return total / len(prices)


    def _calculate_median_price(self, prices: List[Dict[str, Any]]) -> Decimal:
        """Calculate the median price from valid prices."""
        sorted_prices = sorted(price['price'] for price in prices)
        n = len(sorted_prices)
        
        if n == 0:
            raise ValueError("Cannot compute median of empty price list")
        
        mid = n // 2

        if n % 2 == 1:
            return sorted_prices[mid]
        else:
            return (sorted_prices[mid - 1] + sorted_prices[mid]) / Decimal(2)

    def get_dependencies(self) -> List[str]:
        """
        Return list of factor dependencies.
        
        This factor depends on multiple price sources for the same option contract.
        """
        return [
            f"company_share_option_price_{source}" 
            for source in ["ibkr", "fmp", "yahoo", "alpha_vantage", "quandl"]
        ]

    def __repr__(self):
        return f"CompanyShareOptionMidPriceFactor(name={self.name}, group={self.group}, subgroup={self.subgroup})"