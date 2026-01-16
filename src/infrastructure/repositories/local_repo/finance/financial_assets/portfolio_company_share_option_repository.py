"""
Repository for portfolio company share option entities
"""
from typing import List, Optional
from datetime import date

from sqlalchemy.orm import Session

from domain.ports.finance.financial_assets.derivatives.option.portfolio_company_share_option_port import PortfolioCompanyShareOptionPort
from infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models.finance.financial_assets.portfolio_company_share_option import PortfolioCompanyShareOption as PortfolioCompanyShareOptionModel
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

    def get_by_underlying_id(self, underlying_id: int) -> List[PortfolioCompanyShareOption]:
        """Get all options for a specific underlying asset"""
        models = self.session.query(PortfolioCompanyShareOption).filter_by(underlying_id=underlying_id).all()
        return [self.mapper.to_entity(model) for model in models]

    def get_by_company_id(self, company_id: int) -> List[PortfolioCompanyShareOption]:
        """Get all options for a specific company"""
        models = self.session.query(PortfolioCompanyShareOption).filter_by(company_id=company_id).all()
        return [self.mapper.to_entity(model) for model in models]

    def get_by_expiration_date(self, expiration_date: date) -> List[PortfolioCompanyShareOption]:
        """Get all options expiring on a specific date"""
        models = self.session.query(PortfolioCompanyShareOption).filter_by(expiration_date=expiration_date).all()
        return [self.mapper.to_entity(model) for model in models]

    def get_active_options(self, company_id: int = None) -> List[PortfolioCompanyShareOption]:
        """Get active options (no end_date or end_date in future)"""
        from datetime import datetime
        query = self.session.query(PortfolioCompanyShareOption).filter(
            (PortfolioCompanyShareOption.end_date.is_(None)) | 
            (PortfolioCompanyShareOption.end_date > date.today())
        )
        if company_id:
            query = query.filter_by(company_id=company_id)
        
        models = query.all()
        return [self.mapper.to_entity(model) for model in models]

    def get_by_option_type(self, option_type: str) -> List[PortfolioCompanyShareOption]:
        """Get options by type (CALL or PUT)"""
        models = self.session.query(PortfolioCompanyShareOption).filter_by(option_type=option_type).all()
        return [self.mapper.to_entity(model) for model in models]

    def save(self, option: PortfolioCompanyShareOption) -> PortfolioCompanyShareOption:
        """Save or update an option"""
        model = self.mapper.to_model(option)
        self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.to_entity(model)

    def delete(self, option_id: int) -> bool:
        """Delete an option by ID"""
        model = self.session.query(PortfolioCompanyShareOption).filter_by(id=option_id).first()
        if model:
            self.session.delete(model)
            self.session.commit()
            return True
        return False