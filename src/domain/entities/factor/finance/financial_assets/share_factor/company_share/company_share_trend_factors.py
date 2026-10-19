"""
CompanyShare Trend and Momentum Slope Factors.
"""
from __future__ import annotations
from typing import Dict, Any, Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor


def _linear_slope(dependencies: dict) -> Optional[float]:
    """Compute linear regression slope (or simple first-last approximation)."""
    raw = dependencies.get('CompanyShareFactor')
    if raw is None:
        return None
    prices = raw if isinstance(raw, list) else [raw]
    prices = [float(p) for p in prices if p is not None]
    n = len(prices)
    if n < 2:
        return None
    try:
        import numpy as np
        x = np.arange(n, dtype=float)
        slope = float(np.polyfit(x, prices, 1)[0])
        return slope
    except Exception:
        return (prices[-1] - prices[0]) / (n - 1)


class CompanyShareTrendSlope5DFactor(CompanyShareFactor):
    def __init__(self, name='trend_slope_5d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='5-day price trend slope', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=5)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _linear_slope(dependencies)


class CompanyShareTrendSlope10DFactor(CompanyShareFactor):
    def __init__(self, name='trend_slope_10d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='10-day price trend slope', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=10)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _linear_slope(dependencies)


class CompanyShareTrendSlope20DFactor(CompanyShareFactor):
    def __init__(self, name='trend_slope_20d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='20-day price trend slope', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=20)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _linear_slope(dependencies)


class CompanyShareTrendSlope50DFactor(CompanyShareFactor):
    def __init__(self, name='trend_slope_50d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='50-day price trend slope', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=50)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _linear_slope(dependencies)


class CompanyShareTrendSlope100DFactor(CompanyShareFactor):
    def __init__(self, name='trend_slope_100d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='100-day price trend slope', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=100)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _linear_slope(dependencies)


class CompanyShareMomentumSlope10DFactor(CompanyShareFactor):
    def __init__(self, name='momentum_slope_10d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='10-day momentum slope', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=10)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _linear_slope(dependencies)


class CompanyShareMomentumSlope20DFactor(CompanyShareFactor):
    def __init__(self, name='momentum_slope_20d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='20-day momentum slope', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=20)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _linear_slope(dependencies)


class CompanyShareMomentumSlope50DFactor(CompanyShareFactor):
    def __init__(self, name='momentum_slope_50d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='50-day momentum slope', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=50)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _linear_slope(dependencies)
