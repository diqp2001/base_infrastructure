"""
Company Repository - handles CRUD operations for Company entities.

Follows the standardized repository pattern with _create_or_get_* methods
consistent with other repositories in the codebase.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session

from src.infrastructure.models.finance.company import CompanyModel as CompanyModel
from src.domain.entities.finance.company import Company as CompanyEntity
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.finance.company_mapper import CompanyMapper
from src.domain.ports.finance.company_port import CompanyPort

logger = logging.getLogger(__name__)


class CompanyRepository(BaseLocalRepository, CompanyPort):
    """Repository for managing Company entities."""
    
    def __init__(self, session: Session, factory, mapper: CompanyMapper = None):
        """Initialize CompanyRepository with database session and mapper."""
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or CompanyMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Company."""
        return CompanyModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Company."""
        return CompanyEntity
    
    def _to_entity(self, model: CompanyModel) -> CompanyEntity:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        return self.mapper.to_domain(model)
    
    def _to_model(self, entity: CompanyEntity) -> CompanyModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)
    
    def get_all(self) -> List[CompanyEntity]:
        """Retrieve all Company records."""
        models = self.session.query(CompanyModel).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, company_id: int) -> Optional[CompanyEntity]:
        """Retrieve a Company by its ID."""
        model = self.session.query(CompanyModel).filter(
            CompanyModel.id == company_id
        ).first()
        return self._to_entity(model)
    
    def get_by_name(self, name: str) -> List[CompanyEntity]:
        """Retrieve companies by name."""
        models = self.session.query(CompanyModel).filter(
            CompanyModel.name == name
        ).all()
        return [self._to_entity(model) for model in models]
    
    def exists_by_name(self, name: str) -> bool:
        """Check if a Company exists by name."""
        return self.session.query(CompanyModel).filter(
            CompanyModel.name == name
        ).first() is not None
    
    def add(self, entity: CompanyEntity) -> CompanyEntity:
        """Add a new Company entity to the database."""
        # Check for existing company with same name
        if self.exists_by_name(entity.name):
            existing = self.get_by_name(entity.name)[0]
            return existing
        
        model = self._to_model(entity)
        self.session.add(model)
        self.session.commit()
        
        return self._to_entity(model)
    
    def update(self, company_id: int, **kwargs) -> Optional[CompanyEntity]:
        """Update an existing Company record."""
        model = self.session.query(CompanyModel).filter(
            CompanyModel.id == company_id
        ).first()
        
        if not model:
            return None
        
        for attr, value in kwargs.items():
            if hasattr(model, attr):
                setattr(model, attr, value)
        
        self.session.commit()
        return self._to_entity(model)
    
    def delete(self, company_id: int) -> bool:
        """Delete a Company record by ID."""
        model = self.session.query(CompanyModel).filter(
            CompanyModel.id == company_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        self.session.commit()
        return True
    
    def get_or_create(self, name: str, legal_name: Optional[str] = None, country_id: Optional[int] = None, 
                      industry_id: Optional[int] = None) -> Optional[CompanyEntity]:
        """
        Get or create a company with dependency resolution.
        Integrates the functionality from to_orm_with_dependencies.
        
        Args:
            name: Company name
            legal_name: Legal name (optional, will default to name if not provided)
            country_id: Country ID (optional, will use default if not provided)
            industry_id: Industry ID (optional)
            
        Returns:
            Domain company entity or None if creation failed
        """
        try:
            # First try to get existing company
            existing = self.get_by_name(name)
            if existing:
                return existing[0]
            
            # Get or create country dependency if not provided
            if not country_id:
                country_local_repo = self.factory.country_local_repo
                default_country = country_local_repo._create_or_get(name="Global", iso_code="GL")
                country_id = default_country.id if default_country else 1
            
            # Set default legal name
            if not legal_name:
                legal_name = name
            
            # Create new company
            new_company = CompanyEntity(
                name=name,
                legal_name=legal_name,
                country_id=country_id,
                industry_id=industry_id,
                start_date=datetime.now().date()
            )
            
            return self.add(new_company)
            
        except Exception as e:
            logger.error(f"Error in get_or_create for company {name}: {e}")
            return None

    def _get_next_available_company_id(self) -> int:
        """
        Get the next available ID for company creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            max_id_result = self.session.query(CompanyModel.id).order_by(CompanyModel.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available company ID: {str(e)}")
            return 1  # Default to 1 if query fails
    
    def _create_or_get(self, name: str, legal_name: Optional[str] = None,
                              country_id: int = 1, industry_id: int = 1,
                              start_date: Optional[date] = None) -> CompanyEntity:
        """
        Create company entity if it doesn't exist, otherwise return existing.
        Follows the same pattern as BaseFactorRepository._create_or_get_factor().
        
        Args:
            name: Company name (unique identifier)
            legal_name: Legal name (defaults to name if not provided)
            country_id: Country ID (defaults to 1 - USA)
            industry_id: Industry ID (defaults to 1 - Technology)
            start_date: Start date (defaults to current date)
            
        Returns:
            CompanyEntity: Created or existing company
        """
        # Check if entity already exists by name (unique identifier)
        if self.exists_by_name(name):
            existing_companies = self.get_by_name(name)
            return existing_companies[0] if existing_companies else None
        
        try:
            # Get next available ID
            next_id = self._get_next_available_company_id()
            
            # Create new company entity
            company = CompanyEntity(
                id=next_id,
                name=name,
                legal_name=legal_name or name,
                country_id=country_id,
                industry_id=industry_id,
                start_date=start_date or date.today(),
                end_date=None
            )
            
            # Add to database
            return self.add(company)
            
        except Exception as e:
            print(f"Error creating company {name}: {str(e)}")
            return None
    
    # Standard CRUD interface
    def create(self, entity: CompanyEntity) -> CompanyEntity:
        """Create new company entity in database (standard CRUD interface)."""
        return self.add(entity)