"""
CompanyShare Composite Momentum Factors — blended and z-score signals.
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


def _short_momentum(prices) -> Optional[float]:
    if len(prices) < 2:
        return None
    p0, p1 = prices[-2], prices[-1]
    return (p1 - p0) / p0 if p0 != 0 else None


def _medium_momentum(prices) -> Optional[float]:
    if len(prices) < 2:
        return None
    p0, p1 = prices[0], prices[-1]
    return (p1 - p0) / p0 if p0 != 0 else None


def _zscore(prices) -> Optional[float]:
    if len(prices) < 2:
        return None
    mean = sum(prices) / len(prices)
    variance = sum((p - mean) ** 2 for p in prices) / len(prices)
    std = variance ** 0.5
    if std == 0:
        return None
    return (prices[-1] - mean) / std


class CompanyShareShortTermMomentumFactor(CompanyShareFactor):
    def __init__(self, name='short_term_momentum', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='Short-term momentum (recent 2-period return)', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=2)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        prices = _get_prices(dependencies)
        return _short_momentum(prices)


class CompanyShareMediumTermMomentumFactor(CompanyShareFactor):
    def __init__(self, name='medium_term_momentum', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='Medium-term momentum (full window return)', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=22)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        prices = _get_prices(dependencies)
        return _medium_momentum(prices)


class CompanyShareShortVsMediumMomentumFactor(CompanyShareFactor):
    def __init__(self, name='short_vs_medium_momentum', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='Short-term minus medium-term momentum', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=22)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        prices = _get_prices(dependencies)
        short = _short_momentum(prices)
        medium = _medium_momentum(prices)
        if short is None or medium is None:
            return None
        return short - medium


class CompanyShareMomentumZScore20DFactor(CompanyShareFactor):
    def __init__(self, name='momentum_zscore_20d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='20-day momentum z-score', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=20)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        prices = _get_prices(dependencies)
        return _zscore(prices)


class CompanyShareMomentumZScore50DFactor(CompanyShareFactor):
    def __init__(self, name='momentum_zscore_50d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='50-day momentum z-score', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=50)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        prices = _get_prices(dependencies)
        return _zscore(prices)


class CompanyShareMomentumZScore100DFactor(CompanyShareFactor):
    def __init__(self, name='momentum_zscore_100d', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='100-day momentum z-score', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=100)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        prices = _get_prices(dependencies)
        return _zscore(prices)
