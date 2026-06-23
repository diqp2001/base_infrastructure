"""
Mapper for converting between portfolio company share option domain entities and infrastructure models
"""
from datetime import datetime
from typing import Optional

from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_portfolio_option import CompanySharePortfolioOptionModel
from src.domain.entities.finance.financial_assets.derivatives.option.company_share_portfolio_option import CompanySharePortfolioOption



class CompanySharePortfolioOptionMapper:
    """Mapper for converting between option entities and models"""

    @property
    def discriminator(self):
        return "CompanySharePortfolioOption"
    @property
    def entity_class(self):
        return CompanySharePortfolioOption
    @property
    def model_class(self):
        return CompanySharePortfolioOptionModel

    
    
    @staticmethod
    def to_domain(orm_obj: CompanySharePortfolioOptionModel) -> CompanySharePortfolioOption:
        """Convert ORM model to domain entity."""
        domain_entity = CompanySharePortfolioOption(
            id=orm_obj.id,
            name=getattr(orm_obj, 'name', None),
            symbol=getattr(orm_obj, 'symbol', None),
            currency_id=getattr(orm_obj, 'currency_id', None),
            underlying_asset_id=getattr(orm_obj, 'underlying_asset_id', None),
            option_type=getattr(orm_obj, 'option_type', None),
            start_date=getattr(orm_obj, 'start_date', None),
            end_date=getattr(orm_obj, 'end_date', None),
            strike_price=getattr(orm_obj, 'strike_price', None),
            multiplier=getattr(orm_obj, 'multiplier', None)
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: CompanySharePortfolioOption, orm_obj: Optional[CompanySharePortfolioOptionModel] = None) -> CompanySharePortfolioOptionModel:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = CompanySharePortfolioOptionModel()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        
        # Map company share option specific fields
        if hasattr(domain_obj, 'option_type'):
            orm_obj.option_type = domain_obj.option_type
        if hasattr(domain_obj, 'currency_id'):
            orm_obj.currency_id = domain_obj.currency_id
        if hasattr(domain_obj, 'underlying_asset_id'):
            orm_obj.underlying_asset_id = domain_obj.underlying_asset_id
 
        if hasattr(domain_obj, 'strike_price'):
            orm_obj.strike_price = domain_obj.strike_price
        if hasattr(domain_obj, 'multiplier'):
            orm_obj.multiplier = domain_obj.multiplier

        # Map optional financial asset attributes
        if hasattr(domain_obj, 'name'):
            orm_obj.name = domain_obj.name
        if hasattr(domain_obj, 'symbol'):
            orm_obj.symbol = domain_obj.symbol
        if hasattr(domain_obj, 'start_date'):
            orm_obj.start_date = domain_obj.start_date
        if hasattr(domain_obj, 'end_date'):
            orm_obj.end_date = domain_obj.end_date
        
        
        return orm_obj