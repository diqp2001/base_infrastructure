"""
IBKR repositories for all 51 CompanyShare technical/momentum factors.
All operations delegate to the corresponding local repository.
"""
from typing import Optional, List

from src.domain.ports.factor.finance.financial_assets.share_factor.company_share.company_share_technical_momentum_factor_ports import (
    CompanyShareReturn1DFactorPort, CompanyShareReturn5DFactorPort,
    CompanyShareReturn10DFactorPort, CompanyShareReturn20DFactorPort,
    CompanyShareReturn1MFactorPort, CompanyShareReturn2MFactorPort,
    CompanyShareReturn3MFactorPort, CompanyShareReturn4MFactorPort,
    CompanyShareReturn5MFactorPort, CompanyShareReturnYTDFactorPort,
    CompanySharePriceVsMA5FactorPort, CompanySharePriceVsMA10FactorPort,
    CompanySharePriceVsMA20FactorPort, CompanySharePriceVsMA50FactorPort,
    CompanySharePriceVsMA100FactorPort, CompanyShareMA5VsMA10FactorPort,
    CompanyShareMA10VsMA20FactorPort, CompanyShareMA20VsMA50FactorPort,
    CompanyShareMA50VsMA100FactorPort,
    CompanyShareTrendSlope5DFactorPort, CompanyShareTrendSlope10DFactorPort,
    CompanyShareTrendSlope20DFactorPort, CompanyShareTrendSlope50DFactorPort,
    CompanyShareTrendSlope100DFactorPort, CompanyShareMomentumSlope10DFactorPort,
    CompanyShareMomentumSlope20DFactorPort, CompanyShareMomentumSlope50DFactorPort,
    CompanyShareMomentumAcceleration5D10DFactorPort, CompanyShareMomentumAcceleration10D20DFactorPort,
    CompanyShareMomentumAcceleration20D50DFactorPort, CompanyShareReturnChange5DFactorPort,
    CompanyShareReturnChange10DFactorPort, CompanyShareReturnChange20DFactorPort,
    CompanyShareSharpe10DFactorPort, CompanyShareSharpe20DFactorPort,
    CompanyShareSharpe50DFactorPort, CompanyShareSharpe100DFactorPort,
    CompanyShareSortino20DFactorPort, CompanyShareSortino50DFactorPort,
    CompanyShareSortino100DFactorPort,
    CompanyShareDistanceFrom5MHighFactorPort, CompanyShareDistanceFrom5MLowFactorPort,
    CompanyShareDrawdownFrom5MHighFactorPort, CompanyShareDaysSince5MHighFactorPort,
    CompanyShareDaysSince5MLowFactorPort,
    CompanyShareShortTermMomentumFactorPort, CompanyShareMediumTermMomentumFactorPort,
    CompanyShareShortVsMediumMomentumFactorPort, CompanyShareMomentumZScore20DFactorPort,
    CompanyShareMomentumZScore50DFactorPort, CompanyShareMomentumZScore100DFactorPort,
)

from src.domain.ports.factor.finance.financial_assets.share_factor.company_share.company_share_technical_momentum_factor_ports import (
    CompanyShareAvgTurnover1mFactorPort, CompanyShareAvgTurnover2mFactorPort,
    CompanyShareAvgTurnover3mFactorPort, CompanyShareAvgTurnover4mFactorPort,
    CompanyShareAvgTurnover5mFactorPort, CompanyShareTurnoverFactorPort, CompanyShareVpt16w20dLagFactorPort,
    CompanyShareMaxDailyReturn6mFactorPort, CompanyShareMinReturn120dFactorPort,
)

from src.domain.ports.factor.finance.financial_assets.share_factor.company_share.company_share_technical_momentum_factor_ports import (
    CompanyShareRelativeReturnVsSpy1DFactorPort, CompanyShareRelativeReturnVsSpy5DFactorPort,
    CompanyShareRelativeReturnVsSpy20DFactorPort, CompanyShareRelativeReturnVsSpy3MFactorPort,
    CompanyShareRelativeReturnVsSpy6MFactorPort,
)

from src.domain.ports.factor.finance.financial_assets.share_factor.company_share.company_share_technical_momentum_factor_ports import (
    CompanyShareZakamoulineDeltaCeilingFactorPort, CompanyShareZakamoulineDeltaFloorFactorPort,
    CompanyShareWhalleyWilmottDeltaCeilingFactorPort, CompanyShareWhalleyWilmottDeltaFloorFactorPort,
    CompanyShareZakamoulineCeilingDistanceFactorPort, CompanyShareZakamoulineFloorDistanceFactorPort,
    CompanyShareWhalleyWilmottCeilingDistanceFactorPort, CompanyShareWhalleyWilmottFloorDistanceFactorPort,
)


class _BaseIBKRTechMomentumRepo:
    """Mixin: all operations delegate to the matched local repo."""

    _local_repo_key: str = ''

    def __init__(self, ibkr_client, factory=None):
        self.ibkr_client = ibkr_client
        self.factory = factory
        self.local_repo = factory._local_repositories.get(self._local_repo_key) if factory else None

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        return self.local_repo._create_or_get(entity_cls, primary_key, **kwargs) if self.local_repo else None

    def get_by_id(self, id: int):
        return self.local_repo.get_by_id(id) if self.local_repo else None

    def get_by_name(self, name: str):
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_all(self) -> List:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity):
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity):
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, id: int) -> bool:
        return self.local_repo.delete(id) if self.local_repo else False


# ─────────────────────────────────────────────────────────────────────────────
# Return factor IBKR repos
# ─────────────────────────────────────────────────────────────────────────────

class IBKRCompanyShareReturn1DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareReturn1DFactorPort):
    _local_repo_key = 'CompanyShareReturn1DFactor'


class IBKRCompanyShareReturn5DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareReturn5DFactorPort):
    _local_repo_key = 'CompanyShareReturn5DFactor'


class IBKRCompanyShareReturn10DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareReturn10DFactorPort):
    _local_repo_key = 'CompanyShareReturn10DFactor'


class IBKRCompanyShareReturn20DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareReturn20DFactorPort):
    _local_repo_key = 'CompanyShareReturn20DFactor'


class IBKRCompanyShareReturn1MFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareReturn1MFactorPort):
    _local_repo_key = 'CompanyShareReturn1MFactor'


class IBKRCompanyShareReturn2MFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareReturn2MFactorPort):
    _local_repo_key = 'CompanyShareReturn2MFactor'


class IBKRCompanyShareReturn3MFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareReturn3MFactorPort):
    _local_repo_key = 'CompanyShareReturn3MFactor'


class IBKRCompanyShareReturn4MFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareReturn4MFactorPort):
    _local_repo_key = 'CompanyShareReturn4MFactor'


class IBKRCompanyShareReturn5MFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareReturn5MFactorPort):
    _local_repo_key = 'CompanyShareReturn5MFactor'


class IBKRCompanyShareReturnYTDFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareReturnYTDFactorPort):
    _local_repo_key = 'CompanyShareReturnYTDFactor'


# ─────────────────────────────────────────────────────────────────────────────
# MA factor IBKR repos
# ─────────────────────────────────────────────────────────────────────────────

class IBKRCompanySharePriceVsMA5FactorRepository(_BaseIBKRTechMomentumRepo, CompanySharePriceVsMA5FactorPort):
    _local_repo_key = 'CompanySharePriceVsMA5Factor'


class IBKRCompanySharePriceVsMA10FactorRepository(_BaseIBKRTechMomentumRepo, CompanySharePriceVsMA10FactorPort):
    _local_repo_key = 'CompanySharePriceVsMA10Factor'


class IBKRCompanySharePriceVsMA20FactorRepository(_BaseIBKRTechMomentumRepo, CompanySharePriceVsMA20FactorPort):
    _local_repo_key = 'CompanySharePriceVsMA20Factor'


class IBKRCompanySharePriceVsMA50FactorRepository(_BaseIBKRTechMomentumRepo, CompanySharePriceVsMA50FactorPort):
    _local_repo_key = 'CompanySharePriceVsMA50Factor'


class IBKRCompanySharePriceVsMA100FactorRepository(_BaseIBKRTechMomentumRepo, CompanySharePriceVsMA100FactorPort):
    _local_repo_key = 'CompanySharePriceVsMA100Factor'


class IBKRCompanyShareMA5VsMA10FactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMA5VsMA10FactorPort):
    _local_repo_key = 'CompanyShareMA5VsMA10Factor'


class IBKRCompanyShareMA10VsMA20FactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMA10VsMA20FactorPort):
    _local_repo_key = 'CompanyShareMA10VsMA20Factor'


class IBKRCompanyShareMA20VsMA50FactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMA20VsMA50FactorPort):
    _local_repo_key = 'CompanyShareMA20VsMA50Factor'


class IBKRCompanyShareMA50VsMA100FactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMA50VsMA100FactorPort):
    _local_repo_key = 'CompanyShareMA50VsMA100Factor'


# ─────────────────────────────────────────────────────────────────────────────
# Trend / Slope IBKR repos
# ─────────────────────────────────────────────────────────────────────────────

class IBKRCompanyShareTrendSlope5DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareTrendSlope5DFactorPort):
    _local_repo_key = 'CompanyShareTrendSlope5DFactor'


class IBKRCompanyShareTrendSlope10DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareTrendSlope10DFactorPort):
    _local_repo_key = 'CompanyShareTrendSlope10DFactor'


class IBKRCompanyShareTrendSlope20DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareTrendSlope20DFactorPort):
    _local_repo_key = 'CompanyShareTrendSlope20DFactor'


class IBKRCompanyShareTrendSlope50DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareTrendSlope50DFactorPort):
    _local_repo_key = 'CompanyShareTrendSlope50DFactor'


class IBKRCompanyShareTrendSlope100DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareTrendSlope100DFactorPort):
    _local_repo_key = 'CompanyShareTrendSlope100DFactor'


class IBKRCompanyShareMomentumSlope10DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMomentumSlope10DFactorPort):
    _local_repo_key = 'CompanyShareMomentumSlope10DFactor'


class IBKRCompanyShareMomentumSlope20DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMomentumSlope20DFactorPort):
    _local_repo_key = 'CompanyShareMomentumSlope20DFactor'


class IBKRCompanyShareMomentumSlope50DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMomentumSlope50DFactorPort):
    _local_repo_key = 'CompanyShareMomentumSlope50DFactor'


# ─────────────────────────────────────────────────────────────────────────────
# Momentum change IBKR repos
# ─────────────────────────────────────────────────────────────────────────────

class IBKRCompanyShareMomentumAcceleration5D10DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMomentumAcceleration5D10DFactorPort):
    _local_repo_key = 'CompanyShareMomentumAcceleration5D10DFactor'


class IBKRCompanyShareMomentumAcceleration10D20DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMomentumAcceleration10D20DFactorPort):
    _local_repo_key = 'CompanyShareMomentumAcceleration10D20DFactor'


class IBKRCompanyShareMomentumAcceleration20D50DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMomentumAcceleration20D50DFactorPort):
    _local_repo_key = 'CompanyShareMomentumAcceleration20D50DFactor'


class IBKRCompanyShareReturnChange5DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareReturnChange5DFactorPort):
    _local_repo_key = 'CompanyShareReturnChange5DFactor'


class IBKRCompanyShareReturnChange10DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareReturnChange10DFactorPort):
    _local_repo_key = 'CompanyShareReturnChange10DFactor'


class IBKRCompanyShareReturnChange20DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareReturnChange20DFactorPort):
    _local_repo_key = 'CompanyShareReturnChange20DFactor'


# ─────────────────────────────────────────────────────────────────────────────
# Risk factor IBKR repos
# ─────────────────────────────────────────────────────────────────────────────

class IBKRCompanyShareSharpe10DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareSharpe10DFactorPort):
    _local_repo_key = 'CompanyShareSharpe10DFactor'


class IBKRCompanyShareSharpe20DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareSharpe20DFactorPort):
    _local_repo_key = 'CompanyShareSharpe20DFactor'


class IBKRCompanyShareSharpe50DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareSharpe50DFactorPort):
    _local_repo_key = 'CompanyShareSharpe50DFactor'


class IBKRCompanyShareSharpe100DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareSharpe100DFactorPort):
    _local_repo_key = 'CompanyShareSharpe100DFactor'


class IBKRCompanyShareSortino20DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareSortino20DFactorPort):
    _local_repo_key = 'CompanyShareSortino20DFactor'


class IBKRCompanyShareSortino50DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareSortino50DFactorPort):
    _local_repo_key = 'CompanyShareSortino50DFactor'


class IBKRCompanyShareSortino100DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareSortino100DFactorPort):
    _local_repo_key = 'CompanyShareSortino100DFactor'


# ─────────────────────────────────────────────────────────────────────────────
# Drawdown / Distance IBKR repos
# ─────────────────────────────────────────────────────────────────────────────

class IBKRCompanyShareDistanceFrom5MHighFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareDistanceFrom5MHighFactorPort):
    _local_repo_key = 'CompanyShareDistanceFrom5MHighFactor'


class IBKRCompanyShareDistanceFrom5MLowFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareDistanceFrom5MLowFactorPort):
    _local_repo_key = 'CompanyShareDistanceFrom5MLowFactor'


class IBKRCompanyShareDrawdownFrom5MHighFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareDrawdownFrom5MHighFactorPort):
    _local_repo_key = 'CompanyShareDrawdownFrom5MHighFactor'


class IBKRCompanyShareDaysSince5MHighFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareDaysSince5MHighFactorPort):
    _local_repo_key = 'CompanyShareDaysSince5MHighFactor'


class IBKRCompanyShareDaysSince5MLowFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareDaysSince5MLowFactorPort):
    _local_repo_key = 'CompanyShareDaysSince5MLowFactor'


# ─────────────────────────────────────────────────────────────────────────────
# Composite momentum IBKR repos
# ─────────────────────────────────────────────────────────────────────────────

class IBKRCompanyShareShortTermMomentumFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareShortTermMomentumFactorPort):
    _local_repo_key = 'CompanyShareShortTermMomentumFactor'


class IBKRCompanyShareMediumTermMomentumFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMediumTermMomentumFactorPort):
    _local_repo_key = 'CompanyShareMediumTermMomentumFactor'


class IBKRCompanyShareShortVsMediumMomentumFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareShortVsMediumMomentumFactorPort):
    _local_repo_key = 'CompanyShareShortVsMediumMomentumFactor'


class IBKRCompanyShareMomentumZScore20DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMomentumZScore20DFactorPort):
    _local_repo_key = 'CompanyShareMomentumZScore20DFactor'


class IBKRCompanyShareMomentumZScore50DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMomentumZScore50DFactorPort):
    _local_repo_key = 'CompanyShareMomentumZScore50DFactor'


class IBKRCompanyShareMomentumZScore100DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMomentumZScore100DFactorPort):
    _local_repo_key = 'CompanyShareMomentumZScore100DFactor'


# ── Liquidity, volume-trend and return-extreme factor repositories ───────────


class IBKRCompanyShareAvgTurnover1mFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareAvgTurnover1mFactorPort):
    _local_repo_key = 'CompanyShareAvgTurnover1mFactor'


class IBKRCompanyShareAvgTurnover2mFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareAvgTurnover2mFactorPort):
    _local_repo_key = 'CompanyShareAvgTurnover2mFactor'


class IBKRCompanyShareAvgTurnover3mFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareAvgTurnover3mFactorPort):
    _local_repo_key = 'CompanyShareAvgTurnover3mFactor'


class IBKRCompanyShareAvgTurnover4mFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareAvgTurnover4mFactorPort):
    _local_repo_key = 'CompanyShareAvgTurnover4mFactor'


class IBKRCompanyShareAvgTurnover5mFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareAvgTurnover5mFactorPort):
    _local_repo_key = 'CompanyShareAvgTurnover5mFactor'


class IBKRCompanyShareTurnoverFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareTurnoverFactorPort):
    _local_repo_key = 'CompanyShareTurnoverFactor'


class IBKRCompanyShareVpt16w20dLagFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareVpt16w20dLagFactorPort):
    _local_repo_key = 'CompanyShareVpt16w20dLagFactor'


class IBKRCompanyShareMaxDailyReturn6mFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMaxDailyReturn6mFactorPort):
    _local_repo_key = 'CompanyShareMaxDailyReturn6mFactor'


class IBKRCompanyShareMinReturn120dFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareMinReturn120dFactorPort):
    _local_repo_key = 'CompanyShareMinReturn120dFactor'


# ── Relative performance versus SPY factor repositories ───────────


class IBKRCompanyShareRelativeReturnVsSpy1DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareRelativeReturnVsSpy1DFactorPort):
    _local_repo_key = 'CompanyShareRelativeReturnVsSpy1DFactor'


class IBKRCompanyShareRelativeReturnVsSpy5DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareRelativeReturnVsSpy5DFactorPort):
    _local_repo_key = 'CompanyShareRelativeReturnVsSpy5DFactor'


class IBKRCompanyShareRelativeReturnVsSpy20DFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareRelativeReturnVsSpy20DFactorPort):
    _local_repo_key = 'CompanyShareRelativeReturnVsSpy20DFactor'


class IBKRCompanyShareRelativeReturnVsSpy3MFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareRelativeReturnVsSpy3MFactorPort):
    _local_repo_key = 'CompanyShareRelativeReturnVsSpy3MFactor'


class IBKRCompanyShareRelativeReturnVsSpy6MFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareRelativeReturnVsSpy6MFactorPort):
    _local_repo_key = 'CompanyShareRelativeReturnVsSpy6MFactor'


# ── Delta-hedging band (reference call) factor repositories ───────────


class IBKRCompanyShareZakamoulineDeltaCeilingFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareZakamoulineDeltaCeilingFactorPort):
    _local_repo_key = 'CompanyShareZakamoulineDeltaCeilingFactor'


class IBKRCompanyShareZakamoulineDeltaFloorFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareZakamoulineDeltaFloorFactorPort):
    _local_repo_key = 'CompanyShareZakamoulineDeltaFloorFactor'


class IBKRCompanyShareWhalleyWilmottDeltaCeilingFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareWhalleyWilmottDeltaCeilingFactorPort):
    _local_repo_key = 'CompanyShareWhalleyWilmottDeltaCeilingFactor'


class IBKRCompanyShareWhalleyWilmottDeltaFloorFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareWhalleyWilmottDeltaFloorFactorPort):
    _local_repo_key = 'CompanyShareWhalleyWilmottDeltaFloorFactor'


class IBKRCompanyShareZakamoulineCeilingDistanceFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareZakamoulineCeilingDistanceFactorPort):
    _local_repo_key = 'CompanyShareZakamoulineCeilingDistanceFactor'


class IBKRCompanyShareZakamoulineFloorDistanceFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareZakamoulineFloorDistanceFactorPort):
    _local_repo_key = 'CompanyShareZakamoulineFloorDistanceFactor'


class IBKRCompanyShareWhalleyWilmottCeilingDistanceFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareWhalleyWilmottCeilingDistanceFactorPort):
    _local_repo_key = 'CompanyShareWhalleyWilmottCeilingDistanceFactor'


class IBKRCompanyShareWhalleyWilmottFloorDistanceFactorRepository(_BaseIBKRTechMomentumRepo, CompanyShareWhalleyWilmottFloorDistanceFactorPort):
    _local_repo_key = 'CompanyShareWhalleyWilmottFloorDistanceFactor'
