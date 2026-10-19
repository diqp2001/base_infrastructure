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


def _momentum_accel(dependencies: dict) -> Optional[float]:
    """Approximate momentum acceleration: return of recent half vs older half."""
    prices = _get_prices(dependencies)
    n = len(prices)
    if n < 3:
        return None
    half = n // 2
    recent = prices[half:]
    older = prices[:half]
    if not recent or not older:
        return None
    r_recent = (recent[-1] - recent[0]) / recent[0] if recent[0] != 0 else None
    r_older = (older[-1] - older[0]) / older[0] if older[0] != 0 else None
    if r_recent is None or r_older is None:
        return None
    return r_recent - r_older


def _return_change(dependencies: dict) -> Optional[float]:
    """Second derivative of price — acceleration of returns."""
    prices = _get_prices(dependencies)
    n = len(prices)
    if n < 3:
        return None
    if n >= 3:
        r1 = (prices[-1] - prices[-2]) / prices[-2] if prices[-2] != 0 else None
        r2 = (prices[-2] - prices[-3]) / prices[-3] if prices[-3] != 0 else None
        if r1 is None or r2 is None:
            return None
        return r1 - r2
    return None


class CompanyShareMomentumAcceleration5D10DFactor(CompanyShareFactor):
    def __init__(self, name='momentum_accel_5d_10d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='5-day vs 10-day momentum acceleration', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'])]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _momentum_accel(dependencies)


class CompanyShareMomentumAcceleration10D20DFactor(CompanyShareFactor):
    def __init__(self, name='momentum_accel_10d_20d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='10-day vs 20-day momentum acceleration', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'])]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _momentum_accel(dependencies)


class CompanyShareMomentumAcceleration20D50DFactor(CompanyShareFactor):
    def __init__(self, name='momentum_accel_20d_50d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='20-day vs 50-day momentum acceleration', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'])]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _momentum_accel(dependencies)


class CompanyShareReturnChange5DFactor(CompanyShareFactor):
    def __init__(self, name='return_change_5d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='5-day return change (second derivative)', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'])]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_change(dependencies)


class CompanyShareReturnChange10DFactor(CompanyShareFactor):
    def __init__(self, name='return_change_10d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='10-day return change (second derivative)', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'])]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_change(dependencies)


class CompanyShareReturnChange20DFactor(CompanyShareFactor):
    def __init__(self, name='return_change_20d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='20-day return change (second derivative)', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'])]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_change(dependencies)
