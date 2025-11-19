"""
Mapper for converting between Factor domain entities and ORM models.
"""

from abc import abstractmethod
from typing import Optional
from infrastructure.models.factor.factor_model import (
    FactorModel, ContinentFactor, CountryFactor, FinancialAssetFactor,
    SecurityFactor, EquityFactor, ShareFactor, ShareMomentumFactor,
    ShareTechnicalFactor, ShareTargetFactor, ShareVolatilityFactor
)
from domain.entities.factor.factor import Factor as FactorEntity
from domain.entities.factor.continent_factor import ContinentFactor as ContinentFactorEntity
from domain.entities.factor.country_factor import CountryFactor as CountryFactorEntity
from domain.entities.factor.finance.financial_assets.financial_asset_factor import FinancialAssetFactor as FinancialAssetFactorEntity
from domain.entities.factor.finance.financial_assets.security_factor import SecurityFactor as SecurityFactorEntity
from domain.entities.factor.finance.financial_assets.equity_factor import EquityFactor as EquityFactorEntity
from domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor as ShareFactorEntity
from domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor as ShareMomentumFactorEntity
from domain.entities.factor.finance.financial_assets.share_factor.share_technical_factor import ShareTechnicalFactor as ShareTechnicalFactorEntity
from domain.entities.factor.finance.financial_assets.share_factor.share_target_factor import ShareTargetFactor as ShareTargetFactorEntity
from domain.entities.factor.finance.financial_assets.share_factor.share_volatility_factor import ShareVolatilityFactor as ShareVolatilityFactorEntity



class FactorMapper:
    """Mapper for Factor domain entity and ORM model conversion."""
    @abstractmethod
    def get_factor_model(self):
        return FactorModel
    
    @abstractmethod
    def get_factor_entity(self):
        return FactorEntity

    
    @staticmethod
    def to_domain(orm_model: Optional[FactorModel]) -> Optional[FactorEntity]:
        """Convert ORM model to domain entity based on factor_type discriminator."""
        if not orm_model:
            return None
        
        # Map based on discriminator type
        factor_type = orm_model.factor_type
        base_args = {
            'name': orm_model.name,
            'group': orm_model.group,
            'subgroup': orm_model.subgroup,
            'data_type': orm_model.data_type,
            'source': orm_model.source,
            'definition': orm_model.definition,
            'factor_id': orm_model.id,
        }
        
        if factor_type == 'continent':
            return ContinentFactorEntity(
                **base_args,
                continent_code=orm_model.continent_code,
                geographic_zone=orm_model.geographic_zone,
            )
        elif factor_type == 'country':
            return CountryFactorEntity(
                **base_args,
                country_code=orm_model.country_code,
                currency=orm_model.currency,
                is_developed=orm_model.is_developed == 'true' if orm_model.is_developed else None,
            )
        elif factor_type == 'financial_asset':
            return FinancialAssetFactorEntity(
                **base_args,
                asset_class=orm_model.asset_class,
                currency=orm_model.currency,
                market=orm_model.market,
            )
        elif factor_type == 'security':
            return SecurityFactorEntity(
                **base_args,
                asset_class=orm_model.asset_class,
                currency=orm_model.currency,
                market=orm_model.market,
                security_type=orm_model.security_type,
                isin=orm_model.isin,
                cusip=orm_model.cusip,
            )
        elif factor_type == 'equity':
            return EquityFactorEntity(
                **base_args,
                asset_class=orm_model.asset_class,
                currency=orm_model.currency,
                market=orm_model.market,
                security_type=orm_model.security_type,
                isin=orm_model.isin,
                cusip=orm_model.cusip,
                sector=orm_model.sector,
                industry=orm_model.industry,
                market_cap_category=orm_model.market_cap_category,
            )
        elif factor_type == 'share':
            return ShareFactorEntity(
                **base_args,
                asset_class=orm_model.asset_class,
                currency=orm_model.currency,
                market=orm_model.market,
                security_type=orm_model.security_type,
                isin=orm_model.isin,
                cusip=orm_model.cusip,
                sector=orm_model.sector,
                industry=orm_model.industry,
                market_cap_category=orm_model.market_cap_category,
                ticker_symbol=orm_model.ticker_symbol,
                share_class=orm_model.share_class,
                exchange=orm_model.exchange,
            )
        elif factor_type == 'share_momentum':
            return ShareMomentumFactorEntity(
                **base_args,
                asset_class=orm_model.asset_class,
                currency=orm_model.currency,
                market=orm_model.market,
                security_type=orm_model.security_type,
                isin=orm_model.isin,
                cusip=orm_model.cusip,
                sector=orm_model.sector,
                industry=orm_model.industry,
                market_cap_category=orm_model.market_cap_category,
                ticker_symbol=orm_model.ticker_symbol,
                share_class=orm_model.share_class,
                exchange=orm_model.exchange,
                period=orm_model.period,
                momentum_type=orm_model.momentum_type,
            )
        elif factor_type == 'share_technical':
            return ShareTechnicalFactorEntity(
                **base_args,
                asset_class=orm_model.asset_class,
                currency=orm_model.currency,
                market=orm_model.market,
                security_type=orm_model.security_type,
                isin=orm_model.isin,
                cusip=orm_model.cusip,
                sector=orm_model.sector,
                industry=orm_model.industry,
                market_cap_category=orm_model.market_cap_category,
                ticker_symbol=orm_model.ticker_symbol,
                share_class=orm_model.share_class,
                exchange=orm_model.exchange,
                indicator_type=orm_model.indicator_type,
                period=orm_model.period,
                smoothing_factor=orm_model.smoothing_factor,
            )
        elif factor_type == 'share_target':
            return ShareTargetFactorEntity(
                **base_args,
                asset_class=orm_model.asset_class,
                currency=orm_model.currency,
                market=orm_model.market,
                security_type=orm_model.security_type,
                isin=orm_model.isin,
                cusip=orm_model.cusip,
                sector=orm_model.sector,
                industry=orm_model.industry,
                market_cap_category=orm_model.market_cap_category,
                ticker_symbol=orm_model.ticker_symbol,
                share_class=orm_model.share_class,
                exchange=orm_model.exchange,
                target_type=orm_model.target_type,
                forecast_horizon=orm_model.forecast_horizon,
                is_scaled=orm_model.is_scaled == 'true' if orm_model.is_scaled else None,
                scaling_method=orm_model.scaling_method,
            )
        elif factor_type == 'share_volatility':
            return ShareVolatilityFactorEntity(
                **base_args,
                asset_class=orm_model.asset_class,
                currency=orm_model.currency,
                market=orm_model.market,
                security_type=orm_model.security_type,
                isin=orm_model.isin,
                cusip=orm_model.cusip,
                sector=orm_model.sector,
                industry=orm_model.industry,
                market_cap_category=orm_model.market_cap_category,
                ticker_symbol=orm_model.ticker_symbol,
                share_class=orm_model.share_class,
                exchange=orm_model.exchange,
                volatility_type=orm_model.volatility_type,
                period=orm_model.period,
                annualization_factor=orm_model.annualization_factor,
            )
        else:
            # Default to base Factor for unknown types
            # Since Factor is abstract, create a concrete implementation
            class GenericFactor(FactorEntity):
                pass
            
            return GenericFactor(**base_args)

    @staticmethod
    def to_orm(domain_entity: FactorEntity) -> FactorModel:
        """Convert domain entity to ORM model based on entity type."""
        base_data = {
            'id': domain_entity.id,
            'name': domain_entity.name,
            'group': domain_entity.group,
            'subgroup': domain_entity.subgroup,
            'data_type': domain_entity.data_type,
            'source': domain_entity.source,
            'definition': domain_entity.definition,
        }
        
        # Determine the appropriate ORM model and set specialized fields
        if isinstance(domain_entity, ContinentFactorEntity):
            return ContinentFactor(
                **base_data,
                continent_code=domain_entity.continent_code,
                geographic_zone=domain_entity.geographic_zone,
            )
        elif isinstance(domain_entity, CountryFactorEntity):
            return CountryFactor(
                **base_data,
                country_code=domain_entity.country_code,
                currency=domain_entity.currency,
                is_developed='true' if domain_entity.is_developed else 'false' if domain_entity.is_developed is False else None,
            )
        elif isinstance(domain_entity, ShareVolatilityFactorEntity):
            return ShareVolatilityFactor(
                **base_data,
                asset_class=getattr(domain_entity, 'asset_class', None),
                currency=getattr(domain_entity, 'currency', None),
                market=getattr(domain_entity, 'market', None),
                security_type=getattr(domain_entity, 'security_type', None),
                isin=getattr(domain_entity, 'isin', None),
                cusip=getattr(domain_entity, 'cusip', None),
                sector=getattr(domain_entity, 'sector', None),
                industry=getattr(domain_entity, 'industry', None),
                market_cap_category=getattr(domain_entity, 'market_cap_category', None),
                ticker_symbol=getattr(domain_entity, 'ticker_symbol', None),
                share_class=getattr(domain_entity, 'share_class', None),
                exchange=getattr(domain_entity, 'exchange', None),
                volatility_type=domain_entity.volatility_type,
                period=domain_entity.period,
                annualization_factor=domain_entity.annualization_factor,
            )
        elif isinstance(domain_entity, ShareTargetFactorEntity):
            return ShareTargetFactor(
                **base_data,
                asset_class=getattr(domain_entity, 'asset_class', None),
                currency=getattr(domain_entity, 'currency', None),
                market=getattr(domain_entity, 'market', None),
                security_type=getattr(domain_entity, 'security_type', None),
                isin=getattr(domain_entity, 'isin', None),
                cusip=getattr(domain_entity, 'cusip', None),
                sector=getattr(domain_entity, 'sector', None),
                industry=getattr(domain_entity, 'industry', None),
                market_cap_category=getattr(domain_entity, 'market_cap_category', None),
                ticker_symbol=getattr(domain_entity, 'ticker_symbol', None),
                share_class=getattr(domain_entity, 'share_class', None),
                exchange=getattr(domain_entity, 'exchange', None),
                target_type=domain_entity.target_type,
                forecast_horizon=domain_entity.forecast_horizon,
                is_scaled='true' if domain_entity.is_scaled else 'false' if domain_entity.is_scaled is False else None,
                scaling_method=domain_entity.scaling_method,
            )
        elif isinstance(domain_entity, ShareTechnicalFactorEntity):
            return ShareTechnicalFactor(
                **base_data,
                asset_class=getattr(domain_entity, 'asset_class', None),
                currency=getattr(domain_entity, 'currency', None),
                market=getattr(domain_entity, 'market', None),
                security_type=getattr(domain_entity, 'security_type', None),
                isin=getattr(domain_entity, 'isin', None),
                cusip=getattr(domain_entity, 'cusip', None),
                sector=getattr(domain_entity, 'sector', None),
                industry=getattr(domain_entity, 'industry', None),
                market_cap_category=getattr(domain_entity, 'market_cap_category', None),
                ticker_symbol=getattr(domain_entity, 'ticker_symbol', None),
                share_class=getattr(domain_entity, 'share_class', None),
                exchange=getattr(domain_entity, 'exchange', None),
                indicator_type=domain_entity.indicator_type,
                period=domain_entity.period,
                smoothing_factor=domain_entity.smoothing_factor,
            )
        elif isinstance(domain_entity, ShareMomentumFactorEntity):
            return ShareMomentumFactor(
                **base_data,
                asset_class=getattr(domain_entity, 'asset_class', None),
                currency=getattr(domain_entity, 'currency', None),
                market=getattr(domain_entity, 'market', None),
                security_type=getattr(domain_entity, 'security_type', None),
                isin=getattr(domain_entity, 'isin', None),
                cusip=getattr(domain_entity, 'cusip', None),
                sector=getattr(domain_entity, 'sector', None),
                industry=getattr(domain_entity, 'industry', None),
                market_cap_category=getattr(domain_entity, 'market_cap_category', None),
                ticker_symbol=getattr(domain_entity, 'ticker_symbol', None),
                share_class=getattr(domain_entity, 'share_class', None),
                exchange=getattr(domain_entity, 'exchange', None),
                period=domain_entity.period,
                momentum_type=domain_entity.momentum_type,
            )
        elif isinstance(domain_entity, ShareFactorEntity):
            return ShareFactor(
                **base_data,
                asset_class=getattr(domain_entity, 'asset_class', None),
                currency=getattr(domain_entity, 'currency', None),
                market=getattr(domain_entity, 'market', None),
                security_type=getattr(domain_entity, 'security_type', None),
                isin=getattr(domain_entity, 'isin', None),
                cusip=getattr(domain_entity, 'cusip', None),
                sector=getattr(domain_entity, 'sector', None),
                industry=getattr(domain_entity, 'industry', None),
                market_cap_category=getattr(domain_entity, 'market_cap_category', None),
                ticker_symbol=domain_entity.ticker_symbol,
                share_class=domain_entity.share_class,
                exchange=domain_entity.exchange,
            )
        elif isinstance(domain_entity, EquityFactorEntity):
            return EquityFactor(
                **base_data,
                asset_class=getattr(domain_entity, 'asset_class', None),
                currency=getattr(domain_entity, 'currency', None),
                market=getattr(domain_entity, 'market', None),
                security_type=getattr(domain_entity, 'security_type', None),
                isin=getattr(domain_entity, 'isin', None),
                cusip=getattr(domain_entity, 'cusip', None),
                sector=domain_entity.sector,
                industry=domain_entity.industry,
                market_cap_category=domain_entity.market_cap_category,
            )
        elif isinstance(domain_entity, SecurityFactorEntity):
            return SecurityFactor(
                **base_data,
                asset_class=getattr(domain_entity, 'asset_class', None),
                currency=getattr(domain_entity, 'currency', None),
                market=getattr(domain_entity, 'market', None),
                security_type=domain_entity.security_type,
                isin=domain_entity.isin,
                cusip=domain_entity.cusip,
            )
        elif isinstance(domain_entity, FinancialAssetFactorEntity):
            return FinancialAssetFactor(
                **base_data,
                asset_class=domain_entity.asset_class,
                currency=domain_entity.currency,
                market=domain_entity.market,
            )
        else:
            # Default to base FactorModel
            return FactorModel(**base_data)
    