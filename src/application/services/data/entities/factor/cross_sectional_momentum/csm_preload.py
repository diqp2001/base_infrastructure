"""
The bar series a cross-sectional momentum run reads, derived from its candidate features — the single list used by
the data updater (live imports) and by the backtest data preload (BacktestDataPreloadService):

    every universe share   TRADES                       (close / open / high / low / volume)
    every universe share   each named series the candidates read, e.g. OPTION_IMPLIED_VOLATILITY (delta bands)
    every benchmark        TRADES, of its entity class  (SPY: CompanyShare for the relative returns,
                                                         IRX: Index for the rate of the delta bands)
"""

from __future__ import annotations

from typing import List, NamedTuple, Tuple

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMConfiguration,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import (
    benchmark_entity_types,
    required_series,
)


class SeriesSpec(NamedTuple):
    """One series to load; the fields of backtest_preload.PreloadSeries (the preload service reads them by name)."""
    entity_class: type
    symbol: str
    what_to_show: str = "TRADES"
    bar_size_setting: str = "1 day"


def _entity_class(entity_type):
    if entity_type == "Index":
        from src.domain.entities.finance.financial_assets.index.index import Index
        return Index
    from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
    return CompanyShare


def extra_series(config: CSMConfiguration) -> List[Tuple[type, str, str]]:
    """[(entity class, symbol, whatToShow)] besides the shares' TRADES bars: benchmarks and named share series."""
    from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
    tickers = list(config.universe.tickers or [])
    out = [(_entity_class(etype), sym, "TRADES") for sym, etype in benchmark_entity_types(config.features).items()
           if sym not in tickers]
    subgroups = sorted({sub for _, (field, sub, sym, _) in required_series(config.features).items() if sub and not sym})
    out += [(CompanyShare, t, sub) for sub in subgroups for t in tickers]
    return out


def preload_series(config: CSMConfiguration, bar_size_setting: str = "1 day") -> List[SeriesSpec]:
    """Every series of the run (shares' TRADES first, then extra_series), for BacktestDataPreloadService.preload."""
    from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
    series = [SeriesSpec(CompanyShare, t, "TRADES", bar_size_setting) for t in config.universe.tickers or []]
    series += [SeriesSpec(cls, sym, wts, bar_size_setting) for cls, sym, wts in extra_series(config)]
    return series
