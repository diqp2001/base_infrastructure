"""
Repository for portfolio company share option entities
"""
from typing import List, Optional
from datetime import date

from sqlalchemy.orm import Session

from src.domain.ports.finance.financial_assets.derivatives.option.portfolio_company_share_option_port import PortfolioCompanyShareOptionPort
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models.finance.portfolio.portfolio_company_share_option import PortfolioCompanyShareOptionModel as PortfolioCompanyShareOptionModel
from src.infrastructure.repositories.mappers.finance.portfolio_company_share_option_mapper import PortfolioCompanyShareOptionMapper
from src.domain.entities.finance.financial_assets.derivatives.option.portfolio_company_share_option import PortfolioCompanyShareOption as PortfolioCompanyShareOptionEntity


class PortfolioCompanyShareOptionRepository(FinancialAssetRepository, PortfolioCompanyShareOptionPort):
    """Repository for portfolio company share option entities with basic CRUD operations"""
    
    def __init__(self, session: Session):
        super().__init__(session)
        self.mapper = PortfolioCompanyShareOptionMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for PortfolioCompanyShareOption."""
        return PortfolioCompanyShareOptionModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for PortfolioCompanyShareOption."""
        return PortfolioCompanyShareOptionEntity

    def get_by_id(self, option_id: int) -> Optional[PortfolioCompanyShareOptionEntity]:
        """Get an option by ID"""
        model = self.session.query(PortfolioCompanyShareOptionModel).filter_by(id=option_id).first()
        return self.mapper.to_entity(model) if model else None

    def get_all(self) -> List[PortfolioCompanyShareOptionEntity]:
        """Get all options"""
        models = self.session.query(PortfolioCompanyShareOptionModel).all()
        return [self.mapper.to_entity(model) for model in models]

    def get_by_underlying_id(self, underlying_id: int) -> List[PortfolioCompanyShareOptionEntity]:
        """Get all options for a specific underlying asset"""
        models = self.session.query(PortfolioCompanyShareOptionModel).filter_by(underlying_id=underlying_id).all()
        return [self.mapper.to_entity(model) for model in models]

    def get_by_company_id(self, company_id: int) -> List[PortfolioCompanyShareOptionEntity]:
        """Get all options for a specific company"""
        models = self.session.query(PortfolioCompanyShareOptionModel).filter_by(company_id=company_id).all()
        return [self.mapper.to_entity(model) for model in models]

    def get_by_expiration_date(self, expiration_date: date) -> List[PortfolioCompanyShareOptionEntity]:
        """Get all options expiring on a specific date"""
        models = self.session.query(PortfolioCompanyShareOptionModel).filter_by(expiration_date=expiration_date).all()
        return [self.mapper.to_entity(model) for model in models]

    def get_active_options(self, company_id: int = None) -> List[PortfolioCompanyShareOptionEntity]:
        """Get active options (no end_date or end_date in future)"""
        from datetime import datetime
        query = self.session.query(PortfolioCompanyShareOptionModel).filter(
            (PortfolioCompanyShareOptionModel.end_date.is_(None)) | 
            (PortfolioCompanyShareOptionModel.end_date > date.today())
        )
        if company_id:
            query = query.filter_by(company_id=company_id)
        
        models = query.all()
        return [self.mapper.to_entity(model) for model in models]

    def get_by_option_type(self, option_type: str) -> List[PortfolioCompanyShareOptionEntity]:
        """Get options by type (CALL or PUT)"""
        models = self.session.query(PortfolioCompanyShareOptionModel).filter_by(option_type=option_type).all()
        return [self.mapper.to_entity(model) for model in models]

    def save(self, option: PortfolioCompanyShareOptionEntity) -> PortfolioCompanyShareOptionEntity:
        """Save or update an option"""
        model = self.mapper.to_model(option)
        self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.to_entity(model)

    def delete(self, option_id: int) -> bool:
        """Delete an option by ID"""
        model = self.session.query(PortfolioCompanyShareOptionModel).filter_by(id=option_id).first()
        if model:
            self.session.delete(model)
            self.session.commit()
            return True
        return False

    def get_or_create(self, name: str, symbol: Optional[str] = None, currency_id: Optional[int] = None, 
                      underlying_asset_id: Optional[int] = None, option_type: Optional[str] = None) -> Optional[PortfolioCompanyShareOptionEntity]:
        """
        Get or create a portfolio company share option with dependency resolution.
        
        Args:
            name: Option name (primary identifier)
            symbol: Option symbol (optional)
            currency_id: Currency ID (optional, will use default USD if not provided)
            underlying_asset_id: Underlying asset ID (optional)
            option_type: Option type ('CALL' or 'PUT', optional)
            
        Returns:
            Domain option entity or None if creation failed
        """
        try:
            # First try to get existing option by name
            existing = self.session.query(PortfolioCompanyShareOptionModel).filter(
                PortfolioCompanyShareOptionModel.name == name
            ).first()
            
            if existing:
                return self.mapper.to_entity(existing)
            
            # Resolve dependencies
            # Get or create currency dependency if not provided
            if not currency_id:
                currency_local_repo = self.factory.currency_local_repo
                default_currency = currency_local_repo.get_or_create("USD", "United States Dollar")
                currency_id = default_currency.id if default_currency else 1
            
            # Get or create underlying asset dependency if not provided
            if not underlying_asset_id:
                company_share_local_repo = self.factory.company_share_local_repo
                default_share = company_share_local_repo.get_or_create("DEFAULT_SHARE", "DEFAULT")
                underlying_asset_id = default_share.id if default_share else 1
            
            # Set defaults
            from src.domain.entities.finance.financial_assets.derivatives.option.option_type import OptionType
            from datetime import datetime
            
            option_type_enum = OptionType.CALL if option_type == 'CALL' else OptionType.PUT
            
            # Create new option entity
            new_option = PortfolioCompanyShareOptionEntity(
                id=None,
                name=name,
                symbol=symbol or name,
                currency_id=currency_id,
                underlying_asset_id=underlying_asset_id,
                option_type=option_type_enum,
                start_date=datetime.now().date(),
                end_date=None
            )
            
            # Save the option
            return self.save(new_option)
            
        except Exception as e:
            print(f"Error in get_or_create for portfolio company share option {name}: {e}")
            return None