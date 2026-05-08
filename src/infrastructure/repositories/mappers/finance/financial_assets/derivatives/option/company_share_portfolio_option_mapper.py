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
        return "company_share_portfolio_option"
    @property
    def entity_class(self):
        return CompanySharePortfolioOption
    @property
    def model_class(self):
        return CompanySharePortfolioOptionModel

    def to_entity(self, model: Optional[CompanySharePortfolioOptionModel]) -> Optional[CompanySharePortfolioOption]:
        """Convert PortfolioCompanyShareOptionDerivativeModel to PortfolioCompanyShareOption entity"""
        if not model:
            return None

        # Create placeholder underlying - in real implementation you'd load from repository
        from src.domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio
        
        underlying = CompanySharePortfolio(
            id=model.underlying_id,
            start_date=model.start_date,
            end_date=model.end_date
        )

        # Convert string to OptionType enum
        option_type = model.option_type

        return CompanySharePortfolioOption(
            id=model.id,
            underlying=underlying,
            expiration_date=model.expiration_date,
            option_type=option_type,
            start_date=model.start_date,
            end_date=model.end_date
        )

    def to_model(self, entity: CompanySharePortfolioOption) -> CompanySharePortfolioOptionModel:
        """Convert PortfolioCompanyShareOption entity to PortfolioCompanyShareOptionDerivativeModel"""
        return CompanySharePortfolioOptionModel(
            id=entity.id,
            underlying_id=entity.underlying.id,
            company_id=1,  # Default - not tracked at entity level
            expiration_date=entity.expiration_date,
            option_type=entity.option_type.value,  # Convert enum to string
            exercise_style='American',  # Default - not tracked at entity level
            strike_id=None,  # Default - not tracked at entity level
            start_date=entity.start_date,
            end_date=entity.end_date
        )
    
    @staticmethod
    def to_domain(orm_obj: CompanySharePortfolioOptionModel) -> CompanySharePortfolioOption:
        """Convert ORM model to domain entity."""
        domain_entity = CompanySharePortfolioOption(
            id=orm_obj.id,
            name=getattr(orm_obj, 'name', None),
            symbol=getattr(orm_obj, 'symbol', None),
            currency_id=getattr(orm_obj, 'currency_id', None),
            underlying_asset_id=getattr(orm_obj, 'underlying_asset_id', None),
            exchange_id=getattr(orm_obj, 'exchange_id', None),
            option_type=getattr(orm_obj, 'option_type', None),
            start_date=getattr(orm_obj, 'start_date', None),
            end_date=getattr(orm_obj, 'end_date', None),
            strike_price=getattr(orm_obj, 'strike_price', None),
            multiplier=getattr(orm_obj, 'multiplier', None),
            expiry=getattr(orm_obj, 'expiry', None)
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
        if hasattr(domain_obj, 'exchange_id'):
            orm_obj.exchange_id = domain_obj.exchange_id
        if hasattr(domain_obj, 'strike_price'):
            orm_obj.strike_price = domain_obj.strike_price
        if hasattr(domain_obj, 'multiplier'):
            orm_obj.multiplier = domain_obj.multiplier
        if hasattr(domain_obj, 'expiry'):
            orm_obj.expiry = domain_obj.expiry
        # Map optional financial asset attributes
        if hasattr(domain_obj, 'name'):
            orm_obj.name = domain_obj.name
        if hasattr(domain_obj, 'symbol'):
            orm_obj.symbol = domain_obj.symbol
        if hasattr(domain_obj, 'start_date'):
            orm_obj.start_date = domain_obj.start_date
        if hasattr(domain_obj, 'end_date'):
            orm_obj.end_date = domain_obj.end_date
        
        # Set timestamps if they exist on the model
        if hasattr(orm_obj, 'created_at') and not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        if hasattr(orm_obj, 'updated_at'):
            orm_obj.updated_at = datetime.now()
        
        return orm_obj