# Commodity Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/commodity.py

import logging
from typing import Optional
from domain.ports.finance.financial_assets.commodity_port import CommodityPort
from infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models.finance.financial_assets.commodity import CommodityModel as CommodityModel
from src.domain.entities.finance.financial_assets.commodity import Commodity as CommodityEntity
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class CommodityRepository(FinancialAssetRepository, CommodityPort):
    """Local repository for commodity model"""
    
    def __init__(self, session: Session, factory):
        """Initialize CommodityRepository with database session."""
        super().__init__(session)
        self.factory = factory
        self.data_store = []
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Commodity."""
        return CommodityModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Commodity."""
        return CommodityEntity
    
    def save(self, commodity):
        """Save commodity to local storage"""
        self.data_store.append(commodity)
        
    def find_by_id(self, commodity_id):
        """Find commodity by ID"""
        for commodity in self.data_store:
            if getattr(commodity, 'id', None) == commodity_id:
                return commodity
        return None
        
    def find_all(self):
        """Find all commodities"""
        return self.data_store.copy()
    
    def get_or_create(self, ticker: str = None, name: str = None, symbol: str = None,
                      currency_code: str = "USD", commodity_type: str = "Physical") -> Optional[CommodityEntity]:
        """
        Get or create a commodity with dependency resolution.
        
        Args:
            ticker: Commodity ticker symbol
            name: Commodity name 
            symbol: Commodity symbol
            currency_code: Currency ISO code (default: USD)
            commodity_type: Type of commodity (Physical, Financial, etc.)
            
        Returns:
            Commodity entity or None if creation failed
        """
        try:
            # First try to get existing commodity by ticker
            if ticker:
                existing = self.get_by_ticker(ticker)
                if existing:
                    return existing
            
            # Get or create currency dependency
            currency_local_repo = self.factory.currency_local_repo
            currency = currency_local_repo.get_or_create(iso_code=currency_code)
            
            # Create new commodity
            new_commodity = CommodityEntity(
                ticker=ticker or f"COMM_{symbol or name}",
                name=name or f"Commodity {ticker or symbol}",
                symbol=symbol or ticker
            )
            
            # Set currency_id if the entity supports it
            if hasattr(new_commodity, 'currency_id') and currency:
                new_commodity.currency_id = currency.asset_id
            
            # Add to data store (simple implementation)
            self.save(new_commodity)
            return new_commodity
            
        except Exception as e:
            logger.error(f"Error in get_or_create for commodity {ticker or symbol or name}: {e}")
            return None