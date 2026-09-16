"""
CompanyShare Return Factors — daily and monthly price return signals.
"""
from __future__ import annotations
from typing import Dict, Any, Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor


def _return_from_prices(dependencies: dict) -> Optional[float]:
    """Compute simple return (last - first) / first from the price list."""
    raw = dependencies.get('CompanyShareFactor')
    if raw is None:
        return None
    prices = raw if isinstance(raw, list) else [raw]
    prices = [float(p) for p in prices if p is not None]
    if len(prices) < 2:
        return None
    return (prices[-1] - prices[0]) / prices[0] if prices[0] != 0 else None


class CompanyShareReturn1DFactor(CompanyShareFactor):
    def __init__(self, name='return_1d', group='return', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='1-day price return', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_from_prices(dependencies)


class CompanyShareReturn5DFactor(CompanyShareFactor):
    def __init__(self, name='return_5d', group='return', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='5-day price return', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_from_prices(dependencies)


class CompanyShareReturn10DFactor(CompanyShareFactor):
    def __init__(self, name='return_10d', group='return', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='10-day price return', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_from_prices(dependencies)


class CompanyShareReturn20DFactor(CompanyShareFactor):
    def __init__(self, name='return_20d', group='return', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='20-day price return', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_from_prices(dependencies)


class CompanyShareReturn1MFactor(CompanyShareFactor):
    def __init__(self, name='return_1m', group='return', subgroup='monthly',
                 frequency='1mth', data_type='numeric', source='calculated',
                 definition='1-month price return', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_from_prices(dependencies)


class CompanyShareReturn2MFactor(CompanyShareFactor):
    def __init__(self, name='return_2m', group='return', subgroup='monthly',
                 frequency='1mth', data_type='numeric', source='calculated',
                 definition='2-month price return', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_from_prices(dependencies)


class CompanyShareReturn3MFactor(CompanyShareFactor):
    def __init__(self, name='return_3m', group='return', subgroup='monthly',
                 frequency='1mth', data_type='numeric', source='calculated',
                 definition='3-month price return', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_from_prices(dependencies)


class CompanyShareReturn4MFactor(CompanyShareFactor):
    def __init__(self, name='return_4m', group='return', subgroup='monthly',
                 frequency='1mth', data_type='numeric', source='calculated',
                 definition='4-month price return', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_from_prices(dependencies)


class CompanyShareReturn5MFactor(CompanyShareFactor):
    def __init__(self, name='return_5m', group='return', subgroup='monthly',
                 frequency='1mth', data_type='numeric', source='calculated',
                 definition='5-month price return', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_from_prices(dependencies)


class CompanyShareReturnYTDFactor(CompanyShareFactor):
    def __init__(self, name='return_ytd', group='return', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='Year-to-date price return', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _return_from_prices(dependencies)
