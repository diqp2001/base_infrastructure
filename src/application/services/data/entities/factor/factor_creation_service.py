"""
Factor Creation Service - handles creation and management of factor entities.
Provides a service layer for creating factor domain entities with proper configuration.
"""

from typing import Optional, Dict, Any, List
from datetime import date, datetime

from src.domain.entities.factor.factor import Factor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_technical_factor import ShareTechnicalFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_volatility_factor import ShareVolatilityFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_target_factor import ShareTargetFactor
from src.domain.entities.factor.country_factor import CountryFactor
from src.domain.entities.factor.continent_factor import ContinentFactor
from src.domain.entities.factor.finance.financial_assets.security_factor import SecurityFactor
from src.domain.entities.factor.finance.financial_assets.equity_factor import EquityFactor
from src.domain.entities.factor.finance.financial_assets.financial_asset_factor import FinancialAssetFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor

from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository


class FactorCreationService:
    """Service for creating and managing factor domain entities."""
    
    def __init__(self, db_type: str = 'sqlite'):
        """Initialize the service with a database type."""
        self.repository = BaseFactorRepository(db_type)
    
    def create_share_momentum_factor(
        self,
        name: str,
        group: str = "momentum",
        subgroup: str = "price",
        definition: str = None,
        momentum_type: str = "price_momentum",
        period: int = 20
    ) -> ShareMomentumFactor:
        """Create a ShareMomentumFactor entity."""
        return ShareMomentumFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"{period}-period {momentum_type} momentum factor",
            momentum_type=momentum_type,
            period=period
        )
    
    def create_share_technical_factor(
        self,
        name: str,
        indicator_type: str = "SMA",
        period: int = 20,
        group: str = "technical",
        subgroup: str = "trend",
        definition: str = None
    ) -> ShareTechnicalFactor:
        """Create a ShareTechnicalFactor entity."""
        return ShareTechnicalFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"{period}-period {indicator_type} technical indicator",
            indicator_type=indicator_type,
            period=period
        )
    
    def create_share_volatility_factor(
        self,
        name: str,
        volatility_type: str = "historical",
        period: int = 30,
        annualization_factor: float = 252.0,
        group: str = "volatility",
        subgroup: str = "risk",
        definition: str = None
    ) -> ShareVolatilityFactor:
        """Create a ShareVolatilityFactor entity."""
        return ShareVolatilityFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"{period}-period {volatility_type} volatility factor",
            volatility_type=volatility_type,
            period=period,
            annualization_factor=annualization_factor
        )
    
    def create_share_target_factor(
        self,
        name: str,
        target_type: str = "returns",
        forecast_horizon: int = 1,
        is_scaled: bool = False,
        group: str = "target",
        subgroup: str = "prediction",
        definition: str = None
    ) -> ShareTargetFactor:
        """Create a ShareTargetFactor entity."""
        return ShareTargetFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"{forecast_horizon}-period {target_type} target factor",
            target_type=target_type,
            forecast_horizon=forecast_horizon,
            is_scaled=is_scaled
        )
    
    def create_share_factor(
        self,
        name: str,
        group: str = "share",
        subgroup: str = "general",
        definition: str = None,
        equity_specific: str = None
    ) -> ShareFactor:
        """Create a ShareFactor entity."""
        return ShareFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"Share-specific factor: {name}",
            equity_specific=equity_specific
        )
    
    def create_country_factor(
        self,
        name: str,
        group: str = "geographic",
        subgroup: str = "country",
        definition: str = None
    ) -> CountryFactor:
        """Create a CountryFactor entity."""
        return CountryFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="external",
            definition=definition or f"Country-level factor: {name}"
        )
    
    def create_continent_factor(
        self,
        name: str,
        group: str = "geographic",
        subgroup: str = "continent",
        definition: str = None
    ) -> ContinentFactor:
        """Create a ContinentFactor entity."""
        return ContinentFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="external",
            definition=definition or f"Continent-level factor: {name}"
        )
    
    def create_security_factor(
        self,
        name: str,
        group: str = "security",
        subgroup: str = "general",
        definition: str = None
    ) -> SecurityFactor:
        """Create a SecurityFactor entity."""
        return SecurityFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"Security-level factor: {name}"
        )
    
    def create_equity_factor(
        self,
        name: str,
        group: str = "equity",
        subgroup: str = "general",
        definition: str = None
    ) -> EquityFactor:
        """Create an EquityFactor entity."""
        return EquityFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"Equity-level factor: {name}"
        )
    
    def create_financial_asset_factor(
        self,
        name: str,
        group: str = "financial_asset",
        subgroup: str = "general",
        definition: str = None
    ) -> FinancialAssetFactor:
        """Create a FinancialAssetFactor entity."""
        return FinancialAssetFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"Financial asset factor: {name}"
        )
    
    def create_base_factor(
        self,
        name: str,
        group: str,
        subgroup: str = None,
        data_type: str = "float",
        source: str = "calculated",
        definition: str = None
    ) -> Factor:
        """Create a base Factor entity."""
        return Factor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition or f"Base factor: {name}"
        )
    
    def create_factor_from_config(self, config: Dict[str, Any]) -> Factor:
        """
        Create a factor entity from a configuration dictionary.
        
        Args:
            config: Dictionary with factor configuration
                Required keys: 'factor_type', 'name'
                Optional keys: varies by factor type
                
        Returns:
            Factor entity instance
        """
        factor_type = config.get('factor_type', '').lower()
        
        if factor_type == 'share_momentum':
            return self.create_share_momentum_factor(
                name=config['name'],
                group=config.get('group', 'momentum'),
                subgroup=config.get('subgroup', 'price'),
                definition=config.get('definition'),
                momentum_type=config.get('momentum_type', 'price_momentum'),
                period=config.get('period', 20)
            )
        
        elif factor_type == 'share_technical':
            return self.create_share_technical_factor(
                name=config['name'],
                indicator_type=config.get('indicator_type', 'SMA'),
                period=config.get('period', 20),
                group=config.get('group', 'technical'),
                subgroup=config.get('subgroup', 'trend'),
                definition=config.get('definition')
            )
        
        elif factor_type == 'share_volatility':
            return self.create_share_volatility_factor(
                name=config['name'],
                volatility_type=config.get('volatility_type', 'historical'),
                period=config.get('period', 30),
                annualization_factor=config.get('annualization_factor', 252.0),
                group=config.get('group', 'volatility'),
                subgroup=config.get('subgroup', 'risk'),
                definition=config.get('definition')
            )
        
        elif factor_type == 'share_target':
            return self.create_share_target_factor(
                name=config['name'],
                target_type=config.get('target_type', 'returns'),
                forecast_horizon=config.get('forecast_horizon', 1),
                is_scaled=config.get('is_scaled', False),
                group=config.get('group', 'target'),
                subgroup=config.get('subgroup', 'prediction'),
                definition=config.get('definition')
            )
        
        elif factor_type == 'share':
            return self.create_share_factor(
                name=config['name'],
                group=config.get('group', 'share'),
                subgroup=config.get('subgroup', 'general'),
                definition=config.get('definition'),
                equity_specific=config.get('equity_specific')
            )
        
        elif factor_type == 'country':
            return self.create_country_factor(
                name=config['name'],
                group=config.get('group', 'geographic'),
                subgroup=config.get('subgroup', 'country'),
                definition=config.get('definition')
            )
        
        elif factor_type == 'continent':
            return self.create_continent_factor(
                name=config['name'],
                group=config.get('group', 'geographic'),
                subgroup=config.get('subgroup', 'continent'),
                definition=config.get('definition')
            )
        
        elif factor_type == 'security':
            return self.create_security_factor(
                name=config['name'],
                group=config.get('group', 'security'),
                subgroup=config.get('subgroup', 'general'),
                definition=config.get('definition')
            )
        
        elif factor_type == 'equity':
            return self.create_equity_factor(
                name=config['name'],
                group=config.get('group', 'equity'),
                subgroup=config.get('subgroup', 'general'),
                definition=config.get('definition')
            )
        
        elif factor_type == 'financial_asset':
            return self.create_financial_asset_factor(
                name=config['name'],
                group=config.get('group', 'financial_asset'),
                subgroup=config.get('subgroup', 'general'),
                definition=config.get('definition')
            )
        
        else:
            return self.create_base_factor(
                name=config['name'],
                group=config.get('group', 'general'),
                subgroup=config.get('subgroup'),
                data_type=config.get('data_type', 'float'),
                source=config.get('source', 'calculated'),
                definition=config.get('definition')
            )
    
    def persist_factor(self, factor: Factor) -> Optional[Factor]:
        """
        Persist a factor entity to the database.
        
        Args:
            factor: Factor entity to persist
            
        Returns:
            Persisted factor entity or None if failed
        """
        try:
            return self.repository.add_factor(factor)
        except Exception as e:
            # Log error in production
            print(f"Error persisting factor {factor.name}: {str(e)}")
            return None
    
    def create_and_persist_factor(self, config: Dict[str, Any]) -> Optional[Factor]:
        """
        Create and persist a factor entity from configuration.
        
        Args:
            config: Factor configuration dictionary
            
        Returns:
            Persisted factor entity or None if failed
        """
        factor = self.create_factor_from_config(config)
        return self.persist_factor(factor)
    
    # Pull Methods (Retrieve from database)
    def pull_factor_by_id(self, factor_id: int) -> Optional[Factor]:
        """Pull factor by ID from database."""
        try:
            return self.repository.get_by_id(factor_id)
        except Exception as e:
            print(f"Error pulling factor by ID {factor_id}: {str(e)}")
            return None
    
    def pull_factor_by_name(self, name: str) -> Optional[Factor]:
        """Pull factor by name from database."""
        try:
            return self.repository.get_by_name(name)
        except Exception as e:
            print(f"Error pulling factor by name {name}: {str(e)}")
            return None
    
    def pull_factor_values(self, factor_id: int, entity_id: int, start_date: date = None, end_date: date = None) -> List:
        """Pull factor values for a specific factor and entity."""
        try:
            return self.repository.get_factor_values(
                factor_id=factor_id,
                entity_id=entity_id,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            print(f"Error pulling factor values for factor {factor_id}, entity {entity_id}: {str(e)}")
            return []
    
    def pull_all_factors(self) -> List[Factor]:
        """Pull all factors from database."""
        try:
            return [self.repository.get_by_id(factor_id) for factor_id in range(1, 1000)]  # Simple approach
        except Exception as e:
            print(f"Error pulling all factors: {str(e)}")
            return []
    
    def pull_factors_by_group(self, group: str) -> List[Factor]:
        """Pull factors by group from database."""
        try:
            return self.repository.get_factors_by_groups([group])
        except Exception as e:
            print(f"Error pulling factors by group {group}: {str(e)}")
            return []