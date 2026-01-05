"""
Company Repository - handles CRUD operations for Company entities.

Follows the standardized repository pattern with _create_or_get_* methods
consistent with other repositories in the codebase.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session

from src.infrastructure.models.finance.company import Company as CompanyModel
from src.domain.entities.finance.company import Company as CompanyEntity
from src.infrastructure.repositories.base_repository import BaseRepository


class CompanyRepository(BaseRepository):
    """Repository for managing Company entities."""
    
    def __init__(self, session: Session):
        super().__init__(session)
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Company."""
        return CompanyModel
    
    def _to_entity(self, model: CompanyModel) -> CompanyEntity:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        
        return CompanyEntity(
            id=model.id,
            name=model.name,
            legal_name=model.legal_name,
            country_id=model.country_id,
            industry_id=model.industry_id,
            start_date=model.start_date,
            end_date=model.end_date
        )
    
    def _to_model(self, entity: CompanyEntity) -> CompanyModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        
        return CompanyModel(
            name=entity.name,
            legal_name=entity.legal_name,
            country_id=entity.country_id,
            industry_id=entity.industry_id,
            start_date=entity.start_date,
            end_date=entity.end_date
        )
    
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