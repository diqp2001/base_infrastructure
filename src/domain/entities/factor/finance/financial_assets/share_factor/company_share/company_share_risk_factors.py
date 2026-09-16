"""
CompanyShare Risk-Adjusted Factors — Sharpe and Sortino ratios.
"""
from __future__ import annotations
from typing import Dict, Any, Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor


def _get_returns(dependencies: dict):
    """Compute sequential price returns from the price list."""
    raw = dependencies.get('CompanyShareFactor')
    if raw is None:
        return []
    prices = raw if isinstance(raw, list) else [raw]
    prices = [float(p) for p in prices if p is not None]
    if len(prices) < 2:
        return []
    returns = [(prices[i] - prices[i - 1]) / prices[i - 1]
               for i in range(1, len(prices)) if prices[i - 1] != 0]
    return returns


def _sharpe(dependencies: dict) -> Optional[float]:
    returns = _get_returns(dependencies)
    n = len(returns)
    if n < 2:
        return None
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    std = variance ** 0.5
    if std == 0:
        return None
    return mean / std


def _sortino(dependencies: dict) -> Optional[float]:
    returns = _get_returns(dependencies)
    n = len(returns)
    if n < 2:
        return None
    mean = sum(returns) / n
    downside = [r for r in returns if r < 0]
    if not downside:
        return None
    downside_variance = sum(r ** 2 for r in downside) / len(downside)
    downside_std = downside_variance ** 0.5
    if downside_std == 0:
        return None
    return mean / downside_std


class CompanyShareSharpe10DFactor(CompanyShareFactor):
    def __init__(self, name='sharpe_10d', group='risk', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='10-day Sharpe ratio approximation', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _sharpe(dependencies)


class CompanyShareSharpe20DFactor(CompanyShareFactor):
    def __init__(self, name='sharpe_20d', group='risk', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='20-day Sharpe ratio approximation', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _sharpe(dependencies)


class CompanyShareSharpe50DFactor(CompanyShareFactor):
    def __init__(self, name='sharpe_50d', group='risk', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='50-day Sharpe ratio approximation', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _sharpe(dependencies)


class CompanyShareSharpe100DFactor(CompanyShareFactor):
    def __init__(self, name='sharpe_100d', group='risk', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='100-day Sharpe ratio approximation', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _sharpe(dependencies)


class CompanyShareSortino20DFactor(CompanyShareFactor):
    def __init__(self, name='sortino_20d', group='risk', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='20-day Sortino ratio approximation', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _sortino(dependencies)


class CompanyShareSortino50DFactor(CompanyShareFactor):
    def __init__(self, name='sortino_50d', group='risk', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='50-day Sortino ratio approximation', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _sortino(dependencies)


class CompanyShareSortino100DFactor(CompanyShareFactor):
    def __init__(self, name='sortino_100d', group='risk', subgroup='daily',
                 frequency='1d', data_type='numeric', source='calculated',
                 definition='100-day Sortino ratio approximation', factor_id=None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, definition=definition, factor_id=factor_id)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        return [DependencySpec(factor_type=CompanyShareFactor, group='price')]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        return _sortino(dependencies)
