"""
CompanyShare Moving Average Factors — price vs MA and MA vs MA signals.
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


def _price_vs_ma(dependencies: dict) -> Optional[float]:
    prices = _get_prices(dependencies)
    if not prices:
        return None
    avg = sum(prices) / len(prices)
    if avg == 0:
        return None
    return prices[-1] / avg - 1


def _ma_short_vs_ma_long(dependencies: dict, short: int) -> Optional[float]:
    """Moving average of the last `short` closes vs the moving average of the whole window - 1."""
    prices = _get_prices(dependencies)
    if len(prices) < short or short < 1:
        return None
    short_avg = sum(prices[-short:]) / short
    long_avg = sum(prices) / len(prices)
    if long_avg == 0:
        return None
    return short_avg / long_avg - 1


class CompanySharePriceVsMA5Factor(CompanyShareFactor):
    def __init__(self, name='price_vs_ma_5', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='Price vs 5-day moving average', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=5)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _price_vs_ma(dependencies)


class CompanySharePriceVsMA10Factor(CompanyShareFactor):
    def __init__(self, name='price_vs_ma_10', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='Price vs 10-day moving average', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=10)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _price_vs_ma(dependencies)


class CompanySharePriceVsMA20Factor(CompanyShareFactor):
    def __init__(self, name='price_vs_ma_20', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='Price vs 20-day moving average', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=20)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _price_vs_ma(dependencies)


class CompanySharePriceVsMA50Factor(CompanyShareFactor):
    def __init__(self, name='price_vs_ma_50', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='Price vs 50-day moving average', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=50)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _price_vs_ma(dependencies)


class CompanySharePriceVsMA100Factor(CompanyShareFactor):
    def __init__(self, name='price_vs_ma_100', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='Price vs 100-day moving average', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=100)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _price_vs_ma(dependencies)


class CompanyShareMA5VsMA10Factor(CompanyShareFactor):
    def __init__(self, name='ma_5_vs_ma_10', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='5-day MA vs 10-day MA', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=10)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _ma_short_vs_ma_long(dependencies, 5)


class CompanyShareMA10VsMA20Factor(CompanyShareFactor):
    def __init__(self, name='ma_10_vs_ma_20', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='10-day MA vs 20-day MA', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=20)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _ma_short_vs_ma_long(dependencies, 10)


class CompanyShareMA20VsMA50Factor(CompanyShareFactor):
    def __init__(self, name='ma_20_vs_ma_50', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='20-day MA vs 50-day MA', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=50)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _ma_short_vs_ma_long(dependencies, 20)


class CompanyShareMA50VsMA100Factor(CompanyShareFactor):
    def __init__(self, name='ma_50_vs_ma_100', group='momentum', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='50-day MA vs 100-day MA', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price', name_in=['close'], lookback=100)]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _ma_short_vs_ma_long(dependencies, 50)
