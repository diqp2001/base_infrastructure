"""
CurrencyRateFactor — the exchange rate (mid price) of a Currency asset.

Calculates the true mid exchange rate by aggregating multiple data sources,
filtering outliers, and returning a statistically robust rate. This is the
currency equivalent of CompanyShareMidPriceFactor.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
import statistics
from decimal import Decimal

from src.domain.entities.factor.finance.financial_assets.currency.currency_factor import CurrencyFactor


class CurrencyRateFactor(CurrencyFactor):
    """
    Domain entity representing a currency exchange rate (mid price) factor.

    Calculates the true mid rate by:
    1. Collecting rates from multiple data sources
    2. Filtering same group and subgroup sources
    3. Removing outliers using statistical methods
    4. Averaging or medianing the remaining valid rates
    """

    def __init__(
        self,
        name: str = "mid_price",
        group: str = "price",
        subgroup: Optional[str] = "mid_price_true",
        frequency: Optional[str] = None,
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "multiple",
        definition: Optional[str] = "True mid exchange rate calculated from multiple data sources with outlier filtering",
        factor_id: Optional[int] = None,
        outlier_threshold: float = 2.0,
        min_sources: int = 2,
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
        )
        self.frequency = frequency
        self.outlier_threshold = outlier_threshold
        self.min_sources = min_sources

    def calculate(self, source_prices: List[Dict[str, Any]]) -> Optional[Decimal]:
        """
        Calculate true mid exchange rate from multiple data sources.

        Args:
            source_prices: List of rate dictionaries with keys:
                - 'source': str (data provider name)
                - 'price': Decimal (mid rate)
                - 'timestamp': datetime
                - 'group': str
                - 'subgroup': str

        Returns:
            Optional[Decimal]: Calculated true mid rate or None if insufficient data
        """
        if not source_prices or len(source_prices) < self.min_sources:
            return None

        filtered = self._filter_same_group_subgroup(source_prices)

        if len(filtered) < self.min_sources:
            return None
        if len(filtered) == self.min_sources:
            valid = self._remove_outliers(filtered)
            if not valid:
                return None
            return self._calculate_average_price(valid)
        else:
            valid = self._remove_outliers(filtered)
            if not valid:
                return None
            return self._calculate_median_price(valid)

    def _filter_same_group_subgroup(self, source_prices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            p for p in source_prices
            if p.get('group') == self.group and p.get('subgroup') == self.subgroup
        ]

    def _remove_outliers(self, prices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(prices) <= 2:
            return prices
        price_values = [float(p['price']) for p in prices]
        try:
            median = statistics.median(price_values)
            mad = statistics.median([abs(x - median) for x in price_values])
            if mad == 0:
                return prices
            valid = []
            for i, p in enumerate(prices):
                modified_z = abs(price_values[i] - median) / (1.4826 * mad)
                if modified_z <= self.outlier_threshold:
                    valid.append(p)
            return valid if valid else prices[:1]
        except (ValueError, ZeroDivisionError):
            return prices

    def _calculate_average_price(self, prices: List[Dict[str, Any]]) -> Decimal:
        total = sum(p['price'] for p in prices)
        return total / len(prices)

    def _calculate_median_price(self, prices: List[Dict[str, Any]]) -> Decimal:
        sorted_prices = sorted(p['price'] for p in prices)
        n = len(sorted_prices)
        mid = n // 2
        if n % 2 == 1:
            return sorted_prices[mid]
        return (sorted_prices[mid - 1] + sorted_prices[mid]) / Decimal(2)

    def get_dependency_requirements(self):
        from src.application.services.data.entities.factor.dynamic_dependency_requirements import DependencyRequirements
        return DependencyRequirements(
            required_groups=["price"],
            required_subgroups=["mid_price", "close", "last"],
            min_sources=self.min_sources,
            max_sources=5,
            max_age_days=1,
            preferred_sources=["ibkr", "fmp", "yahoo", "alpha_vantage", "quandl"],
            fallback_strategies=[
                "use_close_if_no_mid",
                "single_source_ok",
                "use_older_data",
            ],
            allow_single_source=True,
            allow_older_data=True,
            frequency_compatibility=["1m", "5m", "15m", "1h", "1d"],
        )

    def get_dependencies(self) -> List[str]:
        return [
            f"currency_rate_{source}"
            for source in ["ibkr", "fmp", "yahoo", "alpha_vantage", "quandl"]
        ]

    def __repr__(self):
        return f"CurrencyRateFactor(name={self.name}, group={self.group}, subgroup={self.subgroup})"
