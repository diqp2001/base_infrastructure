"""
Mappers for all 51 CompanyShare technical/momentum factor domain entities <-> ORM models.
"""
from typing import Optional

from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper

# Domain entity imports
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_return_factors import (
    CompanyShareReturn1DFactor, CompanyShareReturn5DFactor, CompanyShareReturn10DFactor,
    CompanyShareReturn20DFactor, CompanyShareReturn1MFactor, CompanyShareReturn2MFactor,
    CompanyShareReturn3MFactor, CompanyShareReturn4MFactor, CompanyShareReturn5MFactor,
    CompanyShareReturnYTDFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_ma_factors import (
    CompanySharePriceVsMA5Factor, CompanySharePriceVsMA10Factor, CompanySharePriceVsMA20Factor,
    CompanySharePriceVsMA50Factor, CompanySharePriceVsMA100Factor,
    CompanyShareMA5VsMA10Factor, CompanyShareMA10VsMA20Factor,
    CompanyShareMA20VsMA50Factor, CompanyShareMA50VsMA100Factor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_trend_factors import (
    CompanyShareTrendSlope5DFactor, CompanyShareTrendSlope10DFactor,
    CompanyShareTrendSlope20DFactor, CompanyShareTrendSlope50DFactor,
    CompanyShareTrendSlope100DFactor, CompanyShareMomentumSlope10DFactor,
    CompanyShareMomentumSlope20DFactor, CompanyShareMomentumSlope50DFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_momentum_change_factors import (
    CompanyShareMomentumAcceleration5D10DFactor, CompanyShareMomentumAcceleration10D20DFactor,
    CompanyShareMomentumAcceleration20D50DFactor, CompanyShareReturnChange5DFactor,
    CompanyShareReturnChange10DFactor, CompanyShareReturnChange20DFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_risk_factors import (
    CompanyShareSharpe10DFactor, CompanyShareSharpe20DFactor,
    CompanyShareSharpe50DFactor, CompanyShareSharpe100DFactor,
    CompanyShareSortino20DFactor, CompanyShareSortino50DFactor, CompanyShareSortino100DFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_drawdown_factors import (
    CompanyShareDistanceFrom5MHighFactor, CompanyShareDistanceFrom5MLowFactor,
    CompanyShareDrawdownFrom5MHighFactor, CompanyShareDaysSince5MHighFactor,
    CompanyShareDaysSince5MLowFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_composite_momentum_factors import (
    CompanyShareShortTermMomentumFactor, CompanyShareMediumTermMomentumFactor,
    CompanyShareShortVsMediumMomentumFactor, CompanyShareMomentumZScore20DFactor,
    CompanyShareMomentumZScore50DFactor, CompanyShareMomentumZScore100DFactor,
)

# ORM model imports
from src.infrastructure.models.factor.company_share_technical_momentum_factor_models import (
    CompanyShareReturn1DFactorModel, CompanyShareReturn5DFactorModel,
    CompanyShareReturn10DFactorModel, CompanyShareReturn20DFactorModel,
    CompanyShareReturn1MFactorModel, CompanyShareReturn2MFactorModel,
    CompanyShareReturn3MFactorModel, CompanyShareReturn4MFactorModel,
    CompanyShareReturn5MFactorModel, CompanyShareReturnYTDFactorModel,
    CompanySharePriceVsMA5FactorModel, CompanySharePriceVsMA10FactorModel,
    CompanySharePriceVsMA20FactorModel, CompanySharePriceVsMA50FactorModel,
    CompanySharePriceVsMA100FactorModel, CompanyShareMA5VsMA10FactorModel,
    CompanyShareMA10VsMA20FactorModel, CompanyShareMA20VsMA50FactorModel,
    CompanyShareMA50VsMA100FactorModel,
    CompanyShareTrendSlope5DFactorModel, CompanyShareTrendSlope10DFactorModel,
    CompanyShareTrendSlope20DFactorModel, CompanyShareTrendSlope50DFactorModel,
    CompanyShareTrendSlope100DFactorModel, CompanyShareMomentumSlope10DFactorModel,
    CompanyShareMomentumSlope20DFactorModel, CompanyShareMomentumSlope50DFactorModel,
    CompanyShareMomentumAcceleration5D10DFactorModel, CompanyShareMomentumAcceleration10D20DFactorModel,
    CompanyShareMomentumAcceleration20D50DFactorModel, CompanyShareReturnChange5DFactorModel,
    CompanyShareReturnChange10DFactorModel, CompanyShareReturnChange20DFactorModel,
    CompanyShareSharpe10DFactorModel, CompanyShareSharpe20DFactorModel,
    CompanyShareSharpe50DFactorModel, CompanyShareSharpe100DFactorModel,
    CompanyShareSortino20DFactorModel, CompanyShareSortino50DFactorModel,
    CompanyShareSortino100DFactorModel,
    CompanyShareDistanceFrom5MHighFactorModel, CompanyShareDistanceFrom5MLowFactorModel,
    CompanyShareDrawdownFrom5MHighFactorModel, CompanyShareDaysSince5MHighFactorModel,
    CompanyShareDaysSince5MLowFactorModel,
    CompanyShareShortTermMomentumFactorModel, CompanyShareMediumTermMomentumFactorModel,
    CompanyShareShortVsMediumMomentumFactorModel, CompanyShareMomentumZScore20DFactorModel,
    CompanyShareMomentumZScore50DFactorModel, CompanyShareMomentumZScore100DFactorModel,
)


def _to_domain(cls, orm_model):
    if not orm_model:
        return None
    return cls(
        factor_id=orm_model.id,
        name=orm_model.name,
        group=orm_model.group,
        subgroup=orm_model.subgroup,
        frequency=orm_model.frequency,
        data_type=orm_model.data_type,
        source=orm_model.source,
        definition=orm_model.definition,
    )


def _to_orm(model_cls, factor_type_str, domain_entity):
    return model_cls(
        name=domain_entity.name,
        group=domain_entity.group,
        subgroup=domain_entity.subgroup,
        frequency=domain_entity.frequency,
        data_type=domain_entity.data_type,
        source=domain_entity.source,
        definition=domain_entity.definition,
        factor_type=factor_type_str,
    )


# ── Return factor mappers ─────────────────────────────────────────────────────

class CompanyShareReturn1DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareReturn1DFactorModel
    def get_factor_model(self): return CompanyShareReturn1DFactorModel
    def get_factor_entity(self): return CompanyShareReturn1DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareReturn1DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareReturn1DFactorModel, 'company_share_return_1d_factor', e)


class CompanyShareReturn5DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareReturn5DFactorModel
    def get_factor_model(self): return CompanyShareReturn5DFactorModel
    def get_factor_entity(self): return CompanyShareReturn5DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareReturn5DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareReturn5DFactorModel, 'company_share_return_5d_factor', e)


class CompanyShareReturn10DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareReturn10DFactorModel
    def get_factor_model(self): return CompanyShareReturn10DFactorModel
    def get_factor_entity(self): return CompanyShareReturn10DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareReturn10DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareReturn10DFactorModel, 'company_share_return_10d_factor', e)


class CompanyShareReturn20DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareReturn20DFactorModel
    def get_factor_model(self): return CompanyShareReturn20DFactorModel
    def get_factor_entity(self): return CompanyShareReturn20DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareReturn20DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareReturn20DFactorModel, 'company_share_return_20d_factor', e)


class CompanyShareReturn1MFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareReturn1MFactorModel
    def get_factor_model(self): return CompanyShareReturn1MFactorModel
    def get_factor_entity(self): return CompanyShareReturn1MFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareReturn1MFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareReturn1MFactorModel, 'company_share_return_1m_factor', e)


class CompanyShareReturn2MFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareReturn2MFactorModel
    def get_factor_model(self): return CompanyShareReturn2MFactorModel
    def get_factor_entity(self): return CompanyShareReturn2MFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareReturn2MFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareReturn2MFactorModel, 'company_share_return_2m_factor', e)


class CompanyShareReturn3MFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareReturn3MFactorModel
    def get_factor_model(self): return CompanyShareReturn3MFactorModel
    def get_factor_entity(self): return CompanyShareReturn3MFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareReturn3MFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareReturn3MFactorModel, 'company_share_return_3m_factor', e)


class CompanyShareReturn4MFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareReturn4MFactorModel
    def get_factor_model(self): return CompanyShareReturn4MFactorModel
    def get_factor_entity(self): return CompanyShareReturn4MFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareReturn4MFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareReturn4MFactorModel, 'company_share_return_4m_factor', e)


class CompanyShareReturn5MFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareReturn5MFactorModel
    def get_factor_model(self): return CompanyShareReturn5MFactorModel
    def get_factor_entity(self): return CompanyShareReturn5MFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareReturn5MFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareReturn5MFactorModel, 'company_share_return_5m_factor', e)


class CompanyShareReturnYTDFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareReturnYTDFactorModel
    def get_factor_model(self): return CompanyShareReturnYTDFactorModel
    def get_factor_entity(self): return CompanyShareReturnYTDFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareReturnYTDFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareReturnYTDFactorModel, 'company_share_return_ytd_factor', e)


# ── MA factor mappers ─────────────────────────────────────────────────────────

class CompanySharePriceVsMA5FactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanySharePriceVsMA5FactorModel
    def get_factor_model(self): return CompanySharePriceVsMA5FactorModel
    def get_factor_entity(self): return CompanySharePriceVsMA5Factor
    def to_domain(self, orm_model): return _to_domain(CompanySharePriceVsMA5Factor, orm_model)
    def to_orm(self, e): return _to_orm(CompanySharePriceVsMA5FactorModel, 'company_share_price_vs_ma_5_factor', e)


class CompanySharePriceVsMA10FactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanySharePriceVsMA10FactorModel
    def get_factor_model(self): return CompanySharePriceVsMA10FactorModel
    def get_factor_entity(self): return CompanySharePriceVsMA10Factor
    def to_domain(self, orm_model): return _to_domain(CompanySharePriceVsMA10Factor, orm_model)
    def to_orm(self, e): return _to_orm(CompanySharePriceVsMA10FactorModel, 'company_share_price_vs_ma_10_factor', e)


class CompanySharePriceVsMA20FactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanySharePriceVsMA20FactorModel
    def get_factor_model(self): return CompanySharePriceVsMA20FactorModel
    def get_factor_entity(self): return CompanySharePriceVsMA20Factor
    def to_domain(self, orm_model): return _to_domain(CompanySharePriceVsMA20Factor, orm_model)
    def to_orm(self, e): return _to_orm(CompanySharePriceVsMA20FactorModel, 'company_share_price_vs_ma_20_factor', e)


class CompanySharePriceVsMA50FactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanySharePriceVsMA50FactorModel
    def get_factor_model(self): return CompanySharePriceVsMA50FactorModel
    def get_factor_entity(self): return CompanySharePriceVsMA50Factor
    def to_domain(self, orm_model): return _to_domain(CompanySharePriceVsMA50Factor, orm_model)
    def to_orm(self, e): return _to_orm(CompanySharePriceVsMA50FactorModel, 'company_share_price_vs_ma_50_factor', e)


class CompanySharePriceVsMA100FactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanySharePriceVsMA100FactorModel
    def get_factor_model(self): return CompanySharePriceVsMA100FactorModel
    def get_factor_entity(self): return CompanySharePriceVsMA100Factor
    def to_domain(self, orm_model): return _to_domain(CompanySharePriceVsMA100Factor, orm_model)
    def to_orm(self, e): return _to_orm(CompanySharePriceVsMA100FactorModel, 'company_share_price_vs_ma_100_factor', e)


class CompanyShareMA5VsMA10FactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareMA5VsMA10FactorModel
    def get_factor_model(self): return CompanyShareMA5VsMA10FactorModel
    def get_factor_entity(self): return CompanyShareMA5VsMA10Factor
    def to_domain(self, orm_model): return _to_domain(CompanyShareMA5VsMA10Factor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareMA5VsMA10FactorModel, 'company_share_ma_5_vs_ma_10_factor', e)


class CompanyShareMA10VsMA20FactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareMA10VsMA20FactorModel
    def get_factor_model(self): return CompanyShareMA10VsMA20FactorModel
    def get_factor_entity(self): return CompanyShareMA10VsMA20Factor
    def to_domain(self, orm_model): return _to_domain(CompanyShareMA10VsMA20Factor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareMA10VsMA20FactorModel, 'company_share_ma_10_vs_ma_20_factor', e)


class CompanyShareMA20VsMA50FactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareMA20VsMA50FactorModel
    def get_factor_model(self): return CompanyShareMA20VsMA50FactorModel
    def get_factor_entity(self): return CompanyShareMA20VsMA50Factor
    def to_domain(self, orm_model): return _to_domain(CompanyShareMA20VsMA50Factor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareMA20VsMA50FactorModel, 'company_share_ma_20_vs_ma_50_factor', e)


class CompanyShareMA50VsMA100FactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareMA50VsMA100FactorModel
    def get_factor_model(self): return CompanyShareMA50VsMA100FactorModel
    def get_factor_entity(self): return CompanyShareMA50VsMA100Factor
    def to_domain(self, orm_model): return _to_domain(CompanyShareMA50VsMA100Factor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareMA50VsMA100FactorModel, 'company_share_ma_50_vs_ma_100_factor', e)


# ── Trend / Slope factor mappers ──────────────────────────────────────────────

class CompanyShareTrendSlope5DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareTrendSlope5DFactorModel
    def get_factor_model(self): return CompanyShareTrendSlope5DFactorModel
    def get_factor_entity(self): return CompanyShareTrendSlope5DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareTrendSlope5DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareTrendSlope5DFactorModel, 'company_share_trend_slope_5d_factor', e)


class CompanyShareTrendSlope10DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareTrendSlope10DFactorModel
    def get_factor_model(self): return CompanyShareTrendSlope10DFactorModel
    def get_factor_entity(self): return CompanyShareTrendSlope10DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareTrendSlope10DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareTrendSlope10DFactorModel, 'company_share_trend_slope_10d_factor', e)


class CompanyShareTrendSlope20DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareTrendSlope20DFactorModel
    def get_factor_model(self): return CompanyShareTrendSlope20DFactorModel
    def get_factor_entity(self): return CompanyShareTrendSlope20DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareTrendSlope20DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareTrendSlope20DFactorModel, 'company_share_trend_slope_20d_factor', e)


class CompanyShareTrendSlope50DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareTrendSlope50DFactorModel
    def get_factor_model(self): return CompanyShareTrendSlope50DFactorModel
    def get_factor_entity(self): return CompanyShareTrendSlope50DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareTrendSlope50DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareTrendSlope50DFactorModel, 'company_share_trend_slope_50d_factor', e)


class CompanyShareTrendSlope100DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareTrendSlope100DFactorModel
    def get_factor_model(self): return CompanyShareTrendSlope100DFactorModel
    def get_factor_entity(self): return CompanyShareTrendSlope100DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareTrendSlope100DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareTrendSlope100DFactorModel, 'company_share_trend_slope_100d_factor', e)


class CompanyShareMomentumSlope10DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareMomentumSlope10DFactorModel
    def get_factor_model(self): return CompanyShareMomentumSlope10DFactorModel
    def get_factor_entity(self): return CompanyShareMomentumSlope10DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareMomentumSlope10DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareMomentumSlope10DFactorModel, 'company_share_momentum_slope_10d_factor', e)


class CompanyShareMomentumSlope20DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareMomentumSlope20DFactorModel
    def get_factor_model(self): return CompanyShareMomentumSlope20DFactorModel
    def get_factor_entity(self): return CompanyShareMomentumSlope20DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareMomentumSlope20DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareMomentumSlope20DFactorModel, 'company_share_momentum_slope_20d_factor', e)


class CompanyShareMomentumSlope50DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareMomentumSlope50DFactorModel
    def get_factor_model(self): return CompanyShareMomentumSlope50DFactorModel
    def get_factor_entity(self): return CompanyShareMomentumSlope50DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareMomentumSlope50DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareMomentumSlope50DFactorModel, 'company_share_momentum_slope_50d_factor', e)


# ── Momentum change / acceleration mappers ────────────────────────────────────

class CompanyShareMomentumAcceleration5D10DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareMomentumAcceleration5D10DFactorModel
    def get_factor_model(self): return CompanyShareMomentumAcceleration5D10DFactorModel
    def get_factor_entity(self): return CompanyShareMomentumAcceleration5D10DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareMomentumAcceleration5D10DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareMomentumAcceleration5D10DFactorModel, 'company_share_momentum_accel_5d_10d_factor', e)


class CompanyShareMomentumAcceleration10D20DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareMomentumAcceleration10D20DFactorModel
    def get_factor_model(self): return CompanyShareMomentumAcceleration10D20DFactorModel
    def get_factor_entity(self): return CompanyShareMomentumAcceleration10D20DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareMomentumAcceleration10D20DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareMomentumAcceleration10D20DFactorModel, 'company_share_momentum_accel_10d_20d_factor', e)


class CompanyShareMomentumAcceleration20D50DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareMomentumAcceleration20D50DFactorModel
    def get_factor_model(self): return CompanyShareMomentumAcceleration20D50DFactorModel
    def get_factor_entity(self): return CompanyShareMomentumAcceleration20D50DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareMomentumAcceleration20D50DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareMomentumAcceleration20D50DFactorModel, 'company_share_momentum_accel_20d_50d_factor', e)


class CompanyShareReturnChange5DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareReturnChange5DFactorModel
    def get_factor_model(self): return CompanyShareReturnChange5DFactorModel
    def get_factor_entity(self): return CompanyShareReturnChange5DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareReturnChange5DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareReturnChange5DFactorModel, 'company_share_return_change_5d_factor', e)


class CompanyShareReturnChange10DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareReturnChange10DFactorModel
    def get_factor_model(self): return CompanyShareReturnChange10DFactorModel
    def get_factor_entity(self): return CompanyShareReturnChange10DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareReturnChange10DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareReturnChange10DFactorModel, 'company_share_return_change_10d_factor', e)


class CompanyShareReturnChange20DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareReturnChange20DFactorModel
    def get_factor_model(self): return CompanyShareReturnChange20DFactorModel
    def get_factor_entity(self): return CompanyShareReturnChange20DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareReturnChange20DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareReturnChange20DFactorModel, 'company_share_return_change_20d_factor', e)


# ── Risk factor mappers ───────────────────────────────────────────────────────

class CompanyShareSharpe10DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareSharpe10DFactorModel
    def get_factor_model(self): return CompanyShareSharpe10DFactorModel
    def get_factor_entity(self): return CompanyShareSharpe10DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareSharpe10DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareSharpe10DFactorModel, 'company_share_sharpe_10d_factor', e)


class CompanyShareSharpe20DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareSharpe20DFactorModel
    def get_factor_model(self): return CompanyShareSharpe20DFactorModel
    def get_factor_entity(self): return CompanyShareSharpe20DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareSharpe20DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareSharpe20DFactorModel, 'company_share_sharpe_20d_factor', e)


class CompanyShareSharpe50DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareSharpe50DFactorModel
    def get_factor_model(self): return CompanyShareSharpe50DFactorModel
    def get_factor_entity(self): return CompanyShareSharpe50DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareSharpe50DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareSharpe50DFactorModel, 'company_share_sharpe_50d_factor', e)


class CompanyShareSharpe100DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareSharpe100DFactorModel
    def get_factor_model(self): return CompanyShareSharpe100DFactorModel
    def get_factor_entity(self): return CompanyShareSharpe100DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareSharpe100DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareSharpe100DFactorModel, 'company_share_sharpe_100d_factor', e)


class CompanyShareSortino20DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareSortino20DFactorModel
    def get_factor_model(self): return CompanyShareSortino20DFactorModel
    def get_factor_entity(self): return CompanyShareSortino20DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareSortino20DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareSortino20DFactorModel, 'company_share_sortino_20d_factor', e)


class CompanyShareSortino50DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareSortino50DFactorModel
    def get_factor_model(self): return CompanyShareSortino50DFactorModel
    def get_factor_entity(self): return CompanyShareSortino50DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareSortino50DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareSortino50DFactorModel, 'company_share_sortino_50d_factor', e)


class CompanyShareSortino100DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareSortino100DFactorModel
    def get_factor_model(self): return CompanyShareSortino100DFactorModel
    def get_factor_entity(self): return CompanyShareSortino100DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareSortino100DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareSortino100DFactorModel, 'company_share_sortino_100d_factor', e)


# ── Drawdown / Distance factor mappers ───────────────────────────────────────

class CompanyShareDistanceFrom5MHighFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareDistanceFrom5MHighFactorModel
    def get_factor_model(self): return CompanyShareDistanceFrom5MHighFactorModel
    def get_factor_entity(self): return CompanyShareDistanceFrom5MHighFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareDistanceFrom5MHighFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareDistanceFrom5MHighFactorModel, 'company_share_distance_from_5m_high_factor', e)


class CompanyShareDistanceFrom5MLowFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareDistanceFrom5MLowFactorModel
    def get_factor_model(self): return CompanyShareDistanceFrom5MLowFactorModel
    def get_factor_entity(self): return CompanyShareDistanceFrom5MLowFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareDistanceFrom5MLowFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareDistanceFrom5MLowFactorModel, 'company_share_distance_from_5m_low_factor', e)


class CompanyShareDrawdownFrom5MHighFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareDrawdownFrom5MHighFactorModel
    def get_factor_model(self): return CompanyShareDrawdownFrom5MHighFactorModel
    def get_factor_entity(self): return CompanyShareDrawdownFrom5MHighFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareDrawdownFrom5MHighFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareDrawdownFrom5MHighFactorModel, 'company_share_drawdown_from_5m_high_factor', e)


class CompanyShareDaysSince5MHighFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareDaysSince5MHighFactorModel
    def get_factor_model(self): return CompanyShareDaysSince5MHighFactorModel
    def get_factor_entity(self): return CompanyShareDaysSince5MHighFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareDaysSince5MHighFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareDaysSince5MHighFactorModel, 'company_share_days_since_5m_high_factor', e)


class CompanyShareDaysSince5MLowFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareDaysSince5MLowFactorModel
    def get_factor_model(self): return CompanyShareDaysSince5MLowFactorModel
    def get_factor_entity(self): return CompanyShareDaysSince5MLowFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareDaysSince5MLowFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareDaysSince5MLowFactorModel, 'company_share_days_since_5m_low_factor', e)


# ── Composite momentum mappers ────────────────────────────────────────────────

class CompanyShareShortTermMomentumFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareShortTermMomentumFactorModel
    def get_factor_model(self): return CompanyShareShortTermMomentumFactorModel
    def get_factor_entity(self): return CompanyShareShortTermMomentumFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareShortTermMomentumFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareShortTermMomentumFactorModel, 'company_share_short_term_momentum_factor', e)


class CompanyShareMediumTermMomentumFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareMediumTermMomentumFactorModel
    def get_factor_model(self): return CompanyShareMediumTermMomentumFactorModel
    def get_factor_entity(self): return CompanyShareMediumTermMomentumFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareMediumTermMomentumFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareMediumTermMomentumFactorModel, 'company_share_medium_term_momentum_factor', e)


class CompanyShareShortVsMediumMomentumFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareShortVsMediumMomentumFactorModel
    def get_factor_model(self): return CompanyShareShortVsMediumMomentumFactorModel
    def get_factor_entity(self): return CompanyShareShortVsMediumMomentumFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareShortVsMediumMomentumFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareShortVsMediumMomentumFactorModel, 'company_share_short_vs_medium_momentum_factor', e)


class CompanyShareMomentumZScore20DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareMomentumZScore20DFactorModel
    def get_factor_model(self): return CompanyShareMomentumZScore20DFactorModel
    def get_factor_entity(self): return CompanyShareMomentumZScore20DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareMomentumZScore20DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareMomentumZScore20DFactorModel, 'company_share_momentum_zscore_20d_factor', e)


class CompanyShareMomentumZScore50DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareMomentumZScore50DFactorModel
    def get_factor_model(self): return CompanyShareMomentumZScore50DFactorModel
    def get_factor_entity(self): return CompanyShareMomentumZScore50DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareMomentumZScore50DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareMomentumZScore50DFactorModel, 'company_share_momentum_zscore_50d_factor', e)


class CompanyShareMomentumZScore100DFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self): return 'CompanyShare'
    @property
    def model_class(self): return CompanyShareMomentumZScore100DFactorModel
    def get_factor_model(self): return CompanyShareMomentumZScore100DFactorModel
    def get_factor_entity(self): return CompanyShareMomentumZScore100DFactor
    def to_domain(self, orm_model): return _to_domain(CompanyShareMomentumZScore100DFactor, orm_model)
    def to_orm(self, e): return _to_orm(CompanyShareMomentumZScore100DFactorModel, 'company_share_momentum_zscore_100d_factor', e)
