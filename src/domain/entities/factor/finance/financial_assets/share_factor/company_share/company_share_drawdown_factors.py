"""
CompanyShare Distance and Drawdown Factors.
"""
from __future__ import annotations
from typing import Dict, Any, Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor


def _get_prices(dependencies: dict):
    raw = dependencies.get('CompanyShareFactor')
    if raw is None:
        return []
    prices = raw if isinstance(raw, list) else [raw]
    return [float(p) for p in prices if p is not None]


class CompanyShareDistanceFrom5MHighFactor(CompanyShareFactor):
    def __init__(self, name='distance_from_5m_high', group='technical', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='Distance of current price from 5-month high', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=105)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        prices = _get_prices(dependencies)
        if not prices:
            return None
        high = max(prices)
        if high == 0:
            return None
        return (high - prices[-1]) / high


class CompanyShareDistanceFrom5MLowFactor(CompanyShareFactor):
    def __init__(self, name='distance_from_5m_low', group='technical', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='Distance of current price from 5-month low', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=105)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        prices = _get_prices(dependencies)
        if not prices:
            return None
        low = min(prices)
        if low == 0:
            return None
        return (prices[-1] - low) / low


class CompanyShareDrawdownFrom5MHighFactor(CompanyShareFactor):
    def __init__(self, name='drawdown_from_5m_high', group='risk', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='Drawdown from 5-month high', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=105)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        prices = _get_prices(dependencies)
        if not prices:
            return None
        high = max(prices)
        if high == 0:
            return None
        return (high - prices[-1]) / high


class CompanyShareDaysSince5MHighFactor(CompanyShareFactor):
    def __init__(self, name='days_since_5m_high', group='technical', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='Approximate days since 5-month high', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=105)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        prices = _get_prices(dependencies)
        if not prices:
            return None
        high = max(prices)
        try:
            idx = prices.index(high)
        except ValueError:
            return None
        return float(len(prices) - idx - 1)


class CompanyShareDaysSince5MLowFactor(CompanyShareFactor):
    def __init__(self, name='days_since_5m_low', group='technical', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='Approximate days since 5-month low', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=105)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        prices = _get_prices(dependencies)
        if not prices:
            return None
        low = min(prices)
        try:
            idx = prices.index(low)
        except ValueError:
            return None
        return float(len(prices) - idx - 1)
