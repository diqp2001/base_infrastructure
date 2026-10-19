"""
CompanyShare Momentum Acceleration and Return Change Factors.
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


def _momentum_accel(dependencies: dict, short: int) -> Optional[float]:
    """Return over the last `short` days minus the return over the rest of the window before it."""
    prices = _get_prices(dependencies)
    n = len(prices)
    if n < short + 2:
        return None
    pivot = prices[-1 - short]
    if pivot == 0 or prices[0] == 0:
        return None
    return (prices[-1] - pivot) / pivot - (pivot - prices[0]) / prices[0]


def _return_change(dependencies: dict, period: int) -> Optional[float]:
    """N-day return minus the N-day return before it (second derivative over N days)."""
    prices = _get_prices(dependencies)
    if len(prices) < 2 * period + 1:
        return None
    p_now, p_mid, p_old = prices[-1], prices[-1 - period], prices[-1 - 2 * period]
    if p_mid == 0 or p_old == 0:
        return None
    return (p_now - p_mid) / p_mid - (p_mid - p_old) / p_old


class CompanyShareMomentumAcceleration5D10DFactor(CompanyShareFactor):
    def __init__(self, name='momentum_accel_5d_10d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='5-day vs 10-day momentum acceleration', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=11)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _momentum_accel(dependencies, 5)


class CompanyShareMomentumAcceleration10D20DFactor(CompanyShareFactor):
    def __init__(self, name='momentum_accel_10d_20d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='10-day vs 20-day momentum acceleration', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=21)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _momentum_accel(dependencies, 10)


class CompanyShareMomentumAcceleration20D50DFactor(CompanyShareFactor):
    def __init__(self, name='momentum_accel_20d_50d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='20-day vs 50-day momentum acceleration', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=51)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _momentum_accel(dependencies, 20)


class CompanyShareReturnChange5DFactor(CompanyShareFactor):
    def __init__(self, name='return_change_5d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='5-day return change (second derivative)', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=11)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_change(dependencies, 5)


class CompanyShareReturnChange10DFactor(CompanyShareFactor):
    def __init__(self, name='return_change_10d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='10-day return change (second derivative)', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=21)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_change(dependencies, 10)


class CompanyShareReturnChange20DFactor(CompanyShareFactor):
    def __init__(self, name='return_change_20d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='20-day return change (second derivative)', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=41)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_change(dependencies, 20)
