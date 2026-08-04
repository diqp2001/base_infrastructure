"""
src/domain/entities/factor/finance/financial_assets/share_factor/company_share/company_share_mid_price_factor.py

CompanyShare Mid Price Factor domain entity - calculates true mid price from multiple data sources.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
import statistics
from decimal import Decimal
from .company_share_factor import CompanyShareFactor


class CompanyShareMidPriceFactor(CompanyShareFactor):
    """
    Domain entity representing a company share mid price factor.
    
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
        frequency: Optional[str] = "1d",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
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

    def calculate(self, dependencies: dict) -> Optional[Decimal]:
        """
        Calculate true mid price from the resolved dependency values.

        dependencies['CompanyShareFactor'] is a list of float values, one per
        external-source CompanyShareFactor whose value was resolved for this
        entity.  The list is built by the resolution service via DependencySpec.
        """
        raw_values = dependencies.get("CompanyShareFactor", [])
        if isinstance(raw_values, (int, float)):
            raw_values = [raw_values]

        source_prices = [
            {
                "source": f"source_{i}",
                "price": Decimal(str(v)),
                "group": self.group,
                "subgroup": self.subgroup,
            }
            for i, v in enumerate(raw_values)
            if v is not None
        ]

        if len(source_prices) < self.min_sources:
            return None

        valid_prices = self._remove_outliers(source_prices)
        if not valid_prices:
            return None

        if len(source_prices) <= self.min_sources:
            return self._calculate_average_price(valid_prices)
        return self._calculate_median_price(valid_prices)
        
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

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor
        return [
            DependencySpec(
                factor_type=CompanyShareFactor,
                group="price",
                frequency=DependencySpec.SELF,
                source_not_in=["calculated"],
            )
        ]

    def __repr__(self):
        return f"CompanyShareMidPriceFactor(name={self.name}, group={self.group}, subgroup={self.subgroup})"