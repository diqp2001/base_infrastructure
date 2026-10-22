"""
Local repositories for all 51 CompanyShare technical/momentum factors.
Each class follows the CompanyShareValueFactorRepository pattern.
"""
from typing import Optional
from sqlalchemy.orm import Session

from src.domain.entities.factor.factor_dependency import FactorDependency
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.share.company_share.company_share_technical_momentum_factor_mappers import (
    CompanyShareReturn1DFactorMapper, CompanyShareReturn5DFactorMapper,
    CompanyShareReturn10DFactorMapper, CompanyShareReturn20DFactorMapper,
    CompanyShareReturn1MFactorMapper, CompanyShareReturn2MFactorMapper,
    CompanyShareReturn3MFactorMapper, CompanyShareReturn4MFactorMapper,
    CompanyShareReturn5MFactorMapper, CompanyShareReturnYTDFactorMapper,
    CompanySharePriceVsMA5FactorMapper, CompanySharePriceVsMA10FactorMapper,
    CompanySharePriceVsMA20FactorMapper, CompanySharePriceVsMA50FactorMapper,
    CompanySharePriceVsMA100FactorMapper, CompanyShareMA5VsMA10FactorMapper,
    CompanyShareMA10VsMA20FactorMapper, CompanyShareMA20VsMA50FactorMapper,
    CompanyShareMA50VsMA100FactorMapper,
    CompanyShareTrendSlope5DFactorMapper, CompanyShareTrendSlope10DFactorMapper,
    CompanyShareTrendSlope20DFactorMapper, CompanyShareTrendSlope50DFactorMapper,
    CompanyShareTrendSlope100DFactorMapper, CompanyShareMomentumSlope10DFactorMapper,
    CompanyShareMomentumSlope20DFactorMapper, CompanyShareMomentumSlope50DFactorMapper,
    CompanyShareMomentumAcceleration5D10DFactorMapper, CompanyShareMomentumAcceleration10D20DFactorMapper,
    CompanyShareMomentumAcceleration20D50DFactorMapper, CompanyShareReturnChange5DFactorMapper,
    CompanyShareReturnChange10DFactorMapper, CompanyShareReturnChange20DFactorMapper,
    CompanyShareSharpe10DFactorMapper, CompanyShareSharpe20DFactorMapper,
    CompanyShareSharpe50DFactorMapper, CompanyShareSharpe100DFactorMapper,
    CompanyShareSortino20DFactorMapper, CompanyShareSortino50DFactorMapper,
    CompanyShareSortino100DFactorMapper,
    CompanyShareDistanceFrom5MHighFactorMapper, CompanyShareDistanceFrom5MLowFactorMapper,
    CompanyShareDrawdownFrom5MHighFactorMapper, CompanyShareDaysSince5MHighFactorMapper,
    CompanyShareDaysSince5MLowFactorMapper,
    CompanyShareShortTermMomentumFactorMapper, CompanyShareMediumTermMomentumFactorMapper,
    CompanyShareShortVsMediumMomentumFactorMapper, CompanyShareMomentumZScore20DFactorMapper,
    CompanyShareMomentumZScore50DFactorMapper, CompanyShareMomentumZScore100DFactorMapper,
)
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

from src.infrastructure.repositories.mappers.factor.finance.financial_assets.share.company_share.company_share_technical_momentum_factor_mappers import (
    CompanyShareAvgTurnover1mFactorMapper, CompanyShareAvgTurnover2mFactorMapper,
    CompanyShareAvgTurnover3mFactorMapper, CompanyShareAvgTurnover4mFactorMapper,
    CompanyShareAvgTurnover5mFactorMapper, CompanyShareTurnoverFactorMapper,
    CompanyShareVpt16w20dLagFactorMapper, CompanyShareMaxDailyReturn6mFactorMapper,
    CompanyShareMinReturn120dFactorMapper,
)
from src.domain.ports.factor.finance.financial_assets.share_factor.company_share.company_share_technical_momentum_factor_ports import (
    CompanyShareAvgTurnover1mFactorPort, CompanyShareAvgTurnover2mFactorPort,
    CompanyShareAvgTurnover3mFactorPort, CompanyShareAvgTurnover4mFactorPort,
    CompanyShareAvgTurnover5mFactorPort, CompanyShareTurnoverFactorPort, CompanyShareVpt16w20dLagFactorPort,
    CompanyShareMaxDailyReturn6mFactorPort, CompanyShareMinReturn120dFactorPort,
)

from src.infrastructure.repositories.mappers.factor.finance.financial_assets.share.company_share.company_share_technical_momentum_factor_mappers import (
    CompanyShareRelativeReturnVsSpy1DFactorMapper, CompanyShareRelativeReturnVsSpy5DFactorMapper,
    CompanyShareRelativeReturnVsSpy20DFactorMapper, CompanyShareRelativeReturnVsSpy3MFactorMapper,
    CompanyShareRelativeReturnVsSpy6MFactorMapper,
)
from src.domain.ports.factor.finance.financial_assets.share_factor.company_share.company_share_technical_momentum_factor_ports import (
    CompanyShareRelativeReturnVsSpy1DFactorPort, CompanyShareRelativeReturnVsSpy5DFactorPort,
    CompanyShareRelativeReturnVsSpy20DFactorPort, CompanyShareRelativeReturnVsSpy3MFactorPort,
    CompanyShareRelativeReturnVsSpy6MFactorPort,
)


class _BaseTechMomentumFactorRepository(BaseFactorRepository):
    """
    Shared implementation for all technical/momentum CompanyShare factor repositories.
    Concrete subclasses supply `_default_group`, `_default_subgroup`, `_default_frequency`,
    `_default_factor_type`, and the mapper instance.
    """

    _default_group: str = 'momentum'
    _default_subgroup: str = 'daily'
    _default_frequency: str = '1d'
    _default_factor_type: str = ''

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper_value = FactorValueMapper()

    @property
    def entity_class(self):
        return self.get_factor_entity()

    @property
    def model_class(self):
        return self.mapper.model_class

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        try:
            existing = self.get_by_all(
                name=primary_key,
                group=kwargs.get('group', self._default_group),
                frequency=kwargs.get('frequency'),
                factor_type=kwargs.get('factor_type', self._default_factor_type),
            )
            if existing:
                return self._to_entity(existing)

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group', self._default_group),
                subgroup=kwargs.get('subgroup', self._default_subgroup),
                frequency=kwargs.get('frequency', self._default_frequency),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'calculated'),
                definition=kwargs.get('definition', f'CompanyShare factor: {primary_key}'),
            )
            orm_factor = self._to_model(domain_factor)
            self.session.add(orm_factor)

            if kwargs.get('dependencies'):
                for dep_name, dep_config in kwargs['dependencies'].items():
                    entity_class = dep_config.get('class')
                    repo = self.factory.get_local_repository(entity_class)
                    dependency_entity = repo._create_or_get(
                        entity_class,
                        primary_key=dep_config.get('name'),
                        group=dep_config.get('group'),
                        subgroup=dep_config.get('subgroup'),
                        frequency=dep_config.get('frequency', '1d'),
                        data_type=dep_config.get('data_type'),
                        factor_type=dep_config.get('factor_type'),
                        source=dep_config.get('source'),
                        definition=dep_config.get('definition'),
                    )
                    repo_dep = self.factory.get_local_repository(FactorDependency)
                    lag = dep_config.get('parameters', {}).get('lag')
                    repo_dep._create_or_get(
                        independent_factor=dependency_entity,
                        dependent_factor=self._to_entity(orm_factor),
                        lag=lag,
                        dependency_name=dep_name,
                    )

            self.session.commit()
            return self._to_entity(orm_factor)
        except Exception as e:
            print(f"Error in _create_or_get {self.__class__.__name__} '{primary_key}': {e}")
            return None

    def get_by_all(self, name: str, group: str, factor_type: Optional[str] = None,
                   subgroup: Optional[str] = None, frequency: Optional[str] = None,
                   data_type: Optional[str] = None, source: Optional[str] = None):
        try:
            FM = self.get_factor_model()
            query = self.session.query(FM).filter(FM.name == name, FM.group == group)
            if factor_type is not None:
                query = query.filter(FM.factor_type == factor_type)
            if subgroup is not None:
                query = query.filter(FM.subgroup == subgroup)
            if frequency is not None:
                query = query.filter(FM.frequency == frequency)
            if data_type is not None:
                query = query.filter(FM.data_type == data_type)
            if source is not None:
                query = query.filter(FM.source == source)
            return query.first()
        except Exception as e:
            print(f"Error in get_by_all {self.__class__.__name__}: {e}")
            return None

    def get_by_id(self, id: int):
        return self._to_entity(
            self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none()
        )

    def get_by_name(self, name: str):
        orm = self.session.query(self.model_class).filter(self.model_class.name == name).first()
        return self._to_entity(orm) if orm else None

    def get_factor_model(self):
        return self.mapper.get_factor_model()

    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    def get_factor_value_model(self):
        return self.mapper_value.get_factor_value_model()

    def get_factor_value_entity(self):
        return self.mapper_value.get_factor_value_entity()

    def _to_entity(self, infra_obj):
        return self.mapper.to_domain(infra_obj)

    def _to_model(self, entity):
        return self.mapper.to_orm(entity)


# ─────────────────────────────────────────────────────────────────────────────
# Return factor repositories
# ─────────────────────────────────────────────────────────────────────────────

class CompanyShareReturn1DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareReturn1DFactorPort):
    _default_group = 'return'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_return_1d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareReturn1DFactorMapper()


class CompanyShareReturn5DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareReturn5DFactorPort):
    _default_group = 'return'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_return_5d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareReturn5DFactorMapper()


class CompanyShareReturn10DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareReturn10DFactorPort):
    _default_group = 'return'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_return_10d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareReturn10DFactorMapper()


class CompanyShareReturn20DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareReturn20DFactorPort):
    _default_group = 'return'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_return_20d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareReturn20DFactorMapper()


class CompanyShareReturn1MFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareReturn1MFactorPort):
    _default_group = 'return'; _default_subgroup = 'monthly'; _default_frequency = '1mth'
    _default_factor_type = 'company_share_return_1m_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareReturn1MFactorMapper()


class CompanyShareReturn2MFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareReturn2MFactorPort):
    _default_group = 'return'; _default_subgroup = 'monthly'; _default_frequency = '1mth'
    _default_factor_type = 'company_share_return_2m_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareReturn2MFactorMapper()


class CompanyShareReturn3MFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareReturn3MFactorPort):
    _default_group = 'return'; _default_subgroup = 'monthly'; _default_frequency = '1mth'
    _default_factor_type = 'company_share_return_3m_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareReturn3MFactorMapper()


class CompanyShareReturn4MFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareReturn4MFactorPort):
    _default_group = 'return'; _default_subgroup = 'monthly'; _default_frequency = '1mth'
    _default_factor_type = 'company_share_return_4m_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareReturn4MFactorMapper()


class CompanyShareReturn5MFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareReturn5MFactorPort):
    _default_group = 'return'; _default_subgroup = 'monthly'; _default_frequency = '1mth'
    _default_factor_type = 'company_share_return_5m_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareReturn5MFactorMapper()


class CompanyShareReturnYTDFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareReturnYTDFactorPort):
    _default_group = 'return'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_return_ytd_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareReturnYTDFactorMapper()


# ─────────────────────────────────────────────────────────────────────────────
# MA factor repositories
# ─────────────────────────────────────────────────────────────────────────────

class CompanySharePriceVsMA5FactorRepository(_BaseTechMomentumFactorRepository, CompanySharePriceVsMA5FactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_price_vs_ma_5_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanySharePriceVsMA5FactorMapper()


class CompanySharePriceVsMA10FactorRepository(_BaseTechMomentumFactorRepository, CompanySharePriceVsMA10FactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_price_vs_ma_10_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanySharePriceVsMA10FactorMapper()


class CompanySharePriceVsMA20FactorRepository(_BaseTechMomentumFactorRepository, CompanySharePriceVsMA20FactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_price_vs_ma_20_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanySharePriceVsMA20FactorMapper()


class CompanySharePriceVsMA50FactorRepository(_BaseTechMomentumFactorRepository, CompanySharePriceVsMA50FactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_price_vs_ma_50_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanySharePriceVsMA50FactorMapper()


class CompanySharePriceVsMA100FactorRepository(_BaseTechMomentumFactorRepository, CompanySharePriceVsMA100FactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_price_vs_ma_100_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanySharePriceVsMA100FactorMapper()


class CompanyShareMA5VsMA10FactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMA5VsMA10FactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_ma_5_vs_ma_10_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMA5VsMA10FactorMapper()


class CompanyShareMA10VsMA20FactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMA10VsMA20FactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_ma_10_vs_ma_20_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMA10VsMA20FactorMapper()


class CompanyShareMA20VsMA50FactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMA20VsMA50FactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_ma_20_vs_ma_50_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMA20VsMA50FactorMapper()


class CompanyShareMA50VsMA100FactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMA50VsMA100FactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_ma_50_vs_ma_100_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMA50VsMA100FactorMapper()


# ─────────────────────────────────────────────────────────────────────────────
# Trend / Slope factor repositories
# ─────────────────────────────────────────────────────────────────────────────

class CompanyShareTrendSlope5DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareTrendSlope5DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_trend_slope_5d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareTrendSlope5DFactorMapper()


class CompanyShareTrendSlope10DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareTrendSlope10DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_trend_slope_10d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareTrendSlope10DFactorMapper()


class CompanyShareTrendSlope20DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareTrendSlope20DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_trend_slope_20d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareTrendSlope20DFactorMapper()


class CompanyShareTrendSlope50DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareTrendSlope50DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_trend_slope_50d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareTrendSlope50DFactorMapper()


class CompanyShareTrendSlope100DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareTrendSlope100DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_trend_slope_100d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareTrendSlope100DFactorMapper()


class CompanyShareMomentumSlope10DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMomentumSlope10DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_momentum_slope_10d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMomentumSlope10DFactorMapper()


class CompanyShareMomentumSlope20DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMomentumSlope20DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_momentum_slope_20d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMomentumSlope20DFactorMapper()


class CompanyShareMomentumSlope50DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMomentumSlope50DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_momentum_slope_50d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMomentumSlope50DFactorMapper()


# ─────────────────────────────────────────────────────────────────────────────
# Momentum change / acceleration repositories
# ─────────────────────────────────────────────────────────────────────────────

class CompanyShareMomentumAcceleration5D10DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMomentumAcceleration5D10DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_momentum_accel_5d_10d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMomentumAcceleration5D10DFactorMapper()


class CompanyShareMomentumAcceleration10D20DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMomentumAcceleration10D20DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_momentum_accel_10d_20d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMomentumAcceleration10D20DFactorMapper()


class CompanyShareMomentumAcceleration20D50DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMomentumAcceleration20D50DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_momentum_accel_20d_50d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMomentumAcceleration20D50DFactorMapper()


class CompanyShareReturnChange5DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareReturnChange5DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_return_change_5d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareReturnChange5DFactorMapper()


class CompanyShareReturnChange10DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareReturnChange10DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_return_change_10d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareReturnChange10DFactorMapper()


class CompanyShareReturnChange20DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareReturnChange20DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_return_change_20d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareReturnChange20DFactorMapper()


# ─────────────────────────────────────────────────────────────────────────────
# Risk factor repositories
# ─────────────────────────────────────────────────────────────────────────────

class CompanyShareSharpe10DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareSharpe10DFactorPort):
    _default_group = 'risk'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_sharpe_10d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareSharpe10DFactorMapper()


class CompanyShareSharpe20DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareSharpe20DFactorPort):
    _default_group = 'risk'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_sharpe_20d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareSharpe20DFactorMapper()


class CompanyShareSharpe50DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareSharpe50DFactorPort):
    _default_group = 'risk'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_sharpe_50d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareSharpe50DFactorMapper()


class CompanyShareSharpe100DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareSharpe100DFactorPort):
    _default_group = 'risk'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_sharpe_100d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareSharpe100DFactorMapper()


class CompanyShareSortino20DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareSortino20DFactorPort):
    _default_group = 'risk'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_sortino_20d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareSortino20DFactorMapper()


class CompanyShareSortino50DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareSortino50DFactorPort):
    _default_group = 'risk'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_sortino_50d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareSortino50DFactorMapper()


class CompanyShareSortino100DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareSortino100DFactorPort):
    _default_group = 'risk'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_sortino_100d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareSortino100DFactorMapper()


# ─────────────────────────────────────────────────────────────────────────────
# Drawdown / Distance factor repositories
# ─────────────────────────────────────────────────────────────────────────────

class CompanyShareDistanceFrom5MHighFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareDistanceFrom5MHighFactorPort):
    _default_group = 'technical'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_distance_from_5m_high_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareDistanceFrom5MHighFactorMapper()


class CompanyShareDistanceFrom5MLowFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareDistanceFrom5MLowFactorPort):
    _default_group = 'technical'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_distance_from_5m_low_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareDistanceFrom5MLowFactorMapper()


class CompanyShareDrawdownFrom5MHighFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareDrawdownFrom5MHighFactorPort):
    _default_group = 'risk'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_drawdown_from_5m_high_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareDrawdownFrom5MHighFactorMapper()


class CompanyShareDaysSince5MHighFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareDaysSince5MHighFactorPort):
    _default_group = 'technical'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_days_since_5m_high_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareDaysSince5MHighFactorMapper()


class CompanyShareDaysSince5MLowFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareDaysSince5MLowFactorPort):
    _default_group = 'technical'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_days_since_5m_low_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareDaysSince5MLowFactorMapper()


# ─────────────────────────────────────────────────────────────────────────────
# Composite momentum repositories
# ─────────────────────────────────────────────────────────────────────────────

class CompanyShareShortTermMomentumFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareShortTermMomentumFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_short_term_momentum_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareShortTermMomentumFactorMapper()


class CompanyShareMediumTermMomentumFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMediumTermMomentumFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_medium_term_momentum_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMediumTermMomentumFactorMapper()


class CompanyShareShortVsMediumMomentumFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareShortVsMediumMomentumFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_short_vs_medium_momentum_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareShortVsMediumMomentumFactorMapper()


class CompanyShareMomentumZScore20DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMomentumZScore20DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_momentum_zscore_20d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMomentumZScore20DFactorMapper()


class CompanyShareMomentumZScore50DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMomentumZScore50DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_momentum_zscore_50d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMomentumZScore50DFactorMapper()


class CompanyShareMomentumZScore100DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMomentumZScore100DFactorPort):
    _default_group = 'momentum'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_momentum_zscore_100d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMomentumZScore100DFactorMapper()


# ── Liquidity, volume-trend and return-extreme factor repositories ───────────


class CompanyShareAvgTurnover1mFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareAvgTurnover1mFactorPort):
    _default_group = 'volume'; _default_subgroup = 'turnover'; _default_frequency = '1d'
    _default_factor_type = 'company_share_avg_turnover_1m_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareAvgTurnover1mFactorMapper()


class CompanyShareAvgTurnover2mFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareAvgTurnover2mFactorPort):
    _default_group = 'volume'; _default_subgroup = 'turnover'; _default_frequency = '1d'
    _default_factor_type = 'company_share_avg_turnover_2m_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareAvgTurnover2mFactorMapper()


class CompanyShareAvgTurnover3mFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareAvgTurnover3mFactorPort):
    _default_group = 'volume'; _default_subgroup = 'turnover'; _default_frequency = '1d'
    _default_factor_type = 'company_share_avg_turnover_3m_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareAvgTurnover3mFactorMapper()


class CompanyShareAvgTurnover4mFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareAvgTurnover4mFactorPort):
    _default_group = 'volume'; _default_subgroup = 'turnover'; _default_frequency = '1d'
    _default_factor_type = 'company_share_avg_turnover_4m_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareAvgTurnover4mFactorMapper()


class CompanyShareAvgTurnover5mFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareAvgTurnover5mFactorPort):
    _default_group = 'volume'; _default_subgroup = 'turnover'; _default_frequency = '1d'
    _default_factor_type = 'company_share_avg_turnover_5m_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareAvgTurnover5mFactorMapper()


class CompanyShareTurnoverFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareTurnoverFactorPort):
    _default_group = 'volume'; _default_subgroup = 'turnover'; _default_frequency = '1d'
    _default_factor_type = 'company_share_turnover_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareTurnoverFactorMapper()


class CompanyShareVpt16w20dLagFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareVpt16w20dLagFactorPort):
    _default_group = 'volume'; _default_subgroup = 'trend'; _default_frequency = '1d'
    _default_factor_type = 'company_share_vpt_16w_20d_lag_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareVpt16w20dLagFactorMapper()


class CompanyShareMaxDailyReturn6mFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMaxDailyReturn6mFactorPort):
    _default_group = 'return'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_max_daily_return_6m_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMaxDailyReturn6mFactorMapper()


class CompanyShareMinReturn120dFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareMinReturn120dFactorPort):
    _default_group = 'return'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_min_return_120d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareMinReturn120dFactorMapper()


# ── Relative performance versus SPY factor repositories ───────────


class CompanyShareRelativeReturnVsSpy1DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareRelativeReturnVsSpy1DFactorPort):
    _default_group = 'return'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_relative_return_vs_spy_1d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareRelativeReturnVsSpy1DFactorMapper()


class CompanyShareRelativeReturnVsSpy5DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareRelativeReturnVsSpy5DFactorPort):
    _default_group = 'return'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_relative_return_vs_spy_5d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareRelativeReturnVsSpy5DFactorMapper()


class CompanyShareRelativeReturnVsSpy20DFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareRelativeReturnVsSpy20DFactorPort):
    _default_group = 'return'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_relative_return_vs_spy_20d_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareRelativeReturnVsSpy20DFactorMapper()


class CompanyShareRelativeReturnVsSpy3MFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareRelativeReturnVsSpy3MFactorPort):
    _default_group = 'return'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_relative_return_vs_spy_3m_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareRelativeReturnVsSpy3MFactorMapper()


class CompanyShareRelativeReturnVsSpy6MFactorRepository(_BaseTechMomentumFactorRepository, CompanyShareRelativeReturnVsSpy6MFactorPort):
    _default_group = 'return'; _default_subgroup = 'daily'; _default_frequency = '1d'
    _default_factor_type = 'company_share_relative_return_vs_spy_6m_factor'
    def __init__(self, session, factory=None):
        super().__init__(session, factory); self.mapper = CompanyShareRelativeReturnVsSpy6MFactorMapper()
