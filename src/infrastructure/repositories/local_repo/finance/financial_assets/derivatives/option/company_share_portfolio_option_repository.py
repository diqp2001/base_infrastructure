"""
Repository for portfolio company share option entities
"""
from typing import List, Optional
from datetime import date, datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging

from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_portfolio_option import CompanySharePortfolioOptionModel
from src.domain.ports.finance.financial_assets.derivatives.option.company_share_portfolio_option_port import CompanySharePortfolioOptionPort
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.infrastructure.repositories.mappers.finance.financial_assets.derivatives.option.company_share_portfolio_option_mapper import CompanySharePortfolioOptionMapper
from src.domain.entities.finance.financial_assets.derivatives.option.company_share_portfolio_option import CompanySharePortfolioOption as CompanySharePortfolioOptionEntity


class CompanySharePortfolioOptionRepository(FinancialAssetRepository, CompanySharePortfolioOptionPort):
    """Repository for portfolio company share option entities with basic CRUD operations"""
    
    def __init__(self, session: Session, factory=None):
        super().__init__(session, factory=factory)
        self.mapper = CompanySharePortfolioOptionMapper()
    
    @property
    def entity_class(self):
        return self.mapper.entity_class
    @property
    def model_class(self):
        return self.mapper.model_class
    # -------------------------
    # CREATE OR GET
    # -------------------------
    def _create_or_get(self, name: str, **kwargs) -> Optional[CompanySharePortfolioOptionEntity]:
        """Create or get an existing company share portfolio option by name"""
        try:
            existing = self.get_by_name(name)
            if existing:
                return existing

            # Resolve currency_id from currency_code if not provided
            currency_id = kwargs.get("currency_id")
            if currency_id is None:
                currency_code = kwargs.get("currency_code", "USD")
                currency_local_repo = self.factory.currency_local_repo
                currency = currency_local_repo.get_or_create(iso_code=currency_code)
                currency_id = currency.asset_id if currency else 1  # Default to 1 if currency service fails
            
            # Set default underlying_asset_id if not provided (SPX index for SPX options)
            underlying_asset_id = kwargs.get("underlying_asset_id")
            if underlying_asset_id is None:
                # For SPX options, try to get SPX index as underlying
                if "SPX" in name.upper():
                    try:
                        from src.infrastructure.repositories.local_repo.finance.financial_assets.index_repository import IndexRepository
                        index_repo = IndexRepository(self.session, self.factory)
                        spx_index = index_repo.get_by_symbol("SPX")
                        if spx_index:
                            underlying_asset_id = spx_index.id
                        else:
                            underlying_asset_id = 1  # Default fallback
                    except Exception as idx_e:
                        logging.warning(f"Could not resolve SPX index as underlying: {idx_e}")
                        underlying_asset_id = 1  # Default fallback
                else:
                    underlying_asset_id = 1  # Default fallback for non-SPX options

            # Create entity with proper fields based on domain entity constructor
            entity = self.entity_class(
                id=None,
                name=name,
                symbol=kwargs.get("symbol", name),
                currency_id=currency_id,
                underlying_asset_id=underlying_asset_id,
                option_type=kwargs.get("option_type", "CALL"),
                start_date=kwargs.get("start_date", datetime.now().date()),
                end_date=kwargs.get("end_date"),
            )

            orm_obj = self.mapper.to_orm(entity)

            self.session.add(orm_obj)
            self.session.commit()

            return self.mapper.to_domain(orm_obj)

        except Exception as e:
            self.session.rollback()
            logging.error(f"Error creating portfolio company share option {name}: {e}")
            return None
    def add(self, option):
        """
        Add a single option to the database.
        
        :param option: Domain option entity to add
        :return: The saved option entity with assigned ID
        :raises: IntegrityError if option already exists
        """
        try:
            # Convert domain entity to ORM model
            orm_option = self.mapper.to_orm(option)
            
            # Add to session and flush to get the ID
            self.session.add(orm_option)
            self.session.flush()
            
            self.session.commit()
            
            
            
            return self.mapper.to_domain(orm_option)
            
        except IntegrityError as e:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise
    # -------------------------
    # STANDARD METHODS
    # -------------------------
    
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionEntity]:
        """Retrieve a portfolio by name."""
        model = self.session.query(CompanySharePortfolioOptionModel).filter(
            CompanySharePortfolioOptionModel.name == name
        ).first()
        return self.mapper.to_domain(model)  if model else None
    def get_by_id(self, option_id: int) -> Optional[CompanySharePortfolioOptionEntity]:
        """Get an option by ID"""
        model = self.session.query(CompanySharePortfolioOptionModel).filter_by(id=option_id).first()
        return self.mapper.to_domain(model) if model else None

    def get_all(self) -> List[CompanySharePortfolioOptionEntity]:
        """Get all options"""
        models = self.session.query(CompanySharePortfolioOptionModel).all()
        return [self.mapper.to_domain(model) for model in models]

    def get_by_underlying_id(self, underlying_id: int) -> List[CompanySharePortfolioOptionEntity]:
        """Get all options for a specific underlying asset"""
        models = self.session.query(CompanySharePortfolioOptionModel).filter_by(underlying_id=underlying_id).all()
        return [self.mapper.to_domain(model) for model in models]

    def get_by_company_id(self, company_id: int) -> List[CompanySharePortfolioOptionEntity]:
        """Get all options for a specific company"""
        models = self.session.query(CompanySharePortfolioOptionModel).filter_by(company_id=company_id).all()
        return [self.mapper.to_domain(model) for model in models]

    def get_by_expiration_date(self, expiration_date: date) -> List[CompanySharePortfolioOptionEntity]:
        """Get all options expiring on a specific date"""
        models = self.session.query(CompanySharePortfolioOptionModel).filter_by(expiration_date=expiration_date).all()
        return [self.mapper.to_domain(model) for model in models]

    def get_active_options(self, company_id: int = None) -> List[CompanySharePortfolioOptionEntity]:
        """Get active options (no end_date or end_date in future)"""
        from datetime import datetime
        query = self.session.query(CompanySharePortfolioOptionModel).filter(
            (CompanySharePortfolioOptionModel.end_date.is_(None)) | 
            (CompanySharePortfolioOptionModel.end_date > date.today())
        )
        if company_id:
            query = query.filter_by(company_id=company_id)
        
        models = query.all()
        return [self.mapper.to_domain(model) for model in models]

    def get_by_option_type(self, option_type: str) -> List[CompanySharePortfolioOptionEntity]:
        """Get options by type (CALL or PUT)"""
        models = self.session.query(CompanySharePortfolioOptionModel).filter_by(option_type=option_type).all()
        return [self.mapper.to_domain(model) for model in models]

    def save(self, option: CompanySharePortfolioOptionEntity) -> CompanySharePortfolioOptionEntity:
        """Save or update an option"""
        model = self.mapper.to_orm(option)
        self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.to_domain(model)

    def delete(self, option_id: int) -> bool:
        """Delete an option by ID"""
        model = self.session.query(CompanySharePortfolioOptionModel).filter_by(id=option_id).first()
        if model:
            self.session.delete(model)
            self.session.commit()
            return True
        return False

    