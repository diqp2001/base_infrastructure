"""
Infrastructure service for resolving entity relationships using local database queries.

This service implements the EntityRelationshipResolver protocol to provide
concrete relationship resolution for the factor value dependency resolver.
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session

from src.domain.services.factor_value_dependency_resolver import EntityRelationshipResolver
from src.infrastructure.models.finance.holding.holding import HoldingModel
from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldingsModel
from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_option import CompanyShareOptionModel


class LocalEntityRelationshipResolver(EntityRelationshipResolver):
    """
    Concrete implementation of EntityRelationshipResolver using local database queries.
    
    This resolver handles the specific relationship mappings described in the issue:
    - Portfolio → Holdings (indirect relationship via holdings table)
    - Option → Underlying Asset (direct relationship via underlying_asset_id)
    - Future → Underlying Asset (direct relationship)
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_related_entities(self, entity_id: int, entity_type: str, relationship_type: str) -> List[int]:
        """
        Get related entity IDs for a given entity and relationship type.
        
        Args:
            entity_id: ID of the source entity
            entity_type: Type of the source entity ('portfolio', 'option', etc.)
            relationship_type: Type of relationship ('holdings', 'underlying_asset', etc.)
            
        Returns:
            List of related entity IDs
        """
        try:
            if entity_type == 'portfolio' and relationship_type == 'holdings':
                return self._get_portfolio_holdings(entity_id)
            elif entity_type == 'option' and relationship_type == 'underlying_asset':
                return self._get_option_underlying_asset(entity_id)
            elif entity_type == 'future' and relationship_type == 'underlying_asset':
                return self._get_future_underlying_asset(entity_id)
            else:
                # Unknown relationship type
                return []
        except Exception as e:
            print(f"Error resolving relationship {entity_type} -> {relationship_type} for entity {entity_id}: {e}")
            return []
    
    def _get_portfolio_holdings(self, portfolio_id: int) -> List[int]:
        """
        Get all holding IDs for a given portfolio.
        
        This handles the indirect relationship case where portfolios don't contain
        holding IDs directly, but holdings contain the portfolio_id.
        """
        try:
            # Query for all holdings that belong to this portfolio
            holding_ids = (
                self.session.query(PortfolioHoldingsModel.id)
                .filter(PortfolioHoldingsModel.portfolio_id == portfolio_id)
                .all()
            )
            return [holding_id[0] for holding_id in holding_ids]
        except Exception as e:
            print(f"Error getting holdings for portfolio {portfolio_id}: {e}")
            return []
    
    def _get_option_underlying_asset(self, option_id: int) -> List[int]:
        """
        Get the underlying asset ID for a given option.
        
        This handles the direct relationship case where the option entity
        contains the underlying_asset_id field.
        """
        try:
            # Query for the option to get its underlying asset ID
            option = (
                self.session.query(CompanyShareOptionModel)
                .filter(CompanyShareOptionModel.id == option_id)
                .first()
            )
            
            if option and hasattr(option, 'underlying_asset_id') and option.underlying_asset_id:
                return [option.underlying_asset_id]
            else:
                return []
        except Exception as e:
            print(f"Error getting underlying asset for option {option_id}: {e}")
            return []
    
    def _get_future_underlying_asset(self, future_id: int) -> List[int]:
        """
        Get the underlying asset ID for a given future contract.
        
        Similar to options, futures typically have an underlying asset reference.
        """
        try:
            # This would need to be implemented based on the actual future model structure
            # For now, return empty list as placeholder
            return []
        except Exception as e:
            print(f"Error getting underlying asset for future {future_id}: {e}")
            return []
    
    def get_entity_attribute(self, entity_id: int, entity_type: str, attribute_name: str) -> Any:
        """
        Get a specific attribute value from an entity.
        
        This is useful for the direct relationship case where we need to extract
        the related entity ID from an attribute (e.g., underlying_asset_id from option).
        """
        try:
            if entity_type == 'option':
                option = (
                    self.session.query(CompanyShareOptionModel)
                    .filter(CompanyShareOptionModel.id == entity_id)
                    .first()
                )
                return getattr(option, attribute_name, None) if option else None
            
            # Add more entity types as needed
            return None
            
        except Exception as e:
            print(f"Error getting attribute {attribute_name} for {entity_type} {entity_id}: {e}")
            return None