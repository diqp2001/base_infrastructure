# Factor Local Repository
# Mirrors src/infrastructure/models/factor/factor.py

from typing import Optional, List
from sqlalchemy.orm import Session

from infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.domain.entities.factor.factor import Factor
from src.infrastructure.models.factor.factor import FactorModel as FactorModel
from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
from src.domain.ports.factor.factor_port import FactorPort


class FactorRepository(BaseFactorRepository, FactorPort):

    def __init__(self, session: Session, factory, mapper: FactorMapper = None,entity_factor_class_input = None):
        """Initialize FactorRepository with database session."""
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or FactorMapper()
        

    # ----------------------------
    # Required by BaseLocalRepository
    # ----------------------------
    def redef_entity_class(self,entity_factor_class_input = None):
        self.entity_class_input =entity_factor_class_input
    @property
    def model_class(self):
        return FactorModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Factor."""
        if self.entity_class_input== None:
            return Factor
        
        return self.entity_class_input

    def _to_entity(self, model: FactorModel) -> Optional[Factor]:
        if not model:
            return None
        return self.mapper.to_domain(model)

    def _to_model(self, entity: Factor) -> FactorModel:
        if not entity:
            return None
        return self.mapper.to_orm(entity)

    def _create_or_get(self, name: str, group: str, subgroup: str) -> Factor:
        existing = self.session.query(FactorModel).filter(
            FactorModel.name == name,
            FactorModel.group == group,
            FactorModel.subgroup == subgroup
        ).first()

        if existing:
            return self._to_entity(existing)

        entity = self.entity_class(
            id=self._get_next_available_id(),
            name=name,
            group=group,
            subgroup=subgroup
        )

        return self.create(entity)

    # ----------------------------
    # Required by FactorPort
    # ----------------------------

    def get_by_id(self, factor_id: int) -> Optional[Factor]:
        model = self.session.query(FactorModel).filter(
            FactorModel.id == factor_id
        ).first()
        return self._to_entity(model)

    def get_by_name(self, name: str) -> Optional[Factor]:
        model = self.session.query(FactorModel).filter(
            FactorModel.name == name
        ).first()
        return self._to_entity(model)

    def get_by_group(self, group: str) -> List[Factor]:
        models = self.session.query(FactorModel).filter(
            FactorModel.group == group
        ).all()
        return [self._to_entity(m) for m in models]

    def get_by_subgroup(self, subgroup: str) -> List[Factor]:
        models = self.session.query(FactorModel).filter(
            FactorModel.subgroup == subgroup
        ).all()
        return [self._to_entity(m) for m in models]

    def get_or_create(self, primary_key: str, **kwargs) -> Optional[Factor]:
        """
        Get or create a factor with dependency resolution.
        
        Args:
            primary_key: Factor name identifier
            **kwargs: Additional parameters for factor creation
            
        Returns:
            Factor entity or None if creation failed
        """
        try:
            # Check existing by primary identifier (factor name)
            existing = self.get_by_name(primary_key)
            if existing:
                return existing
            
            # Create new factor using base _create_or_get method
            return self._create_or_get(
                name=primary_key,
                group=kwargs.get('group', 'general'),
                subgroup=kwargs.get('subgroup', 'default')
            )
            
        except Exception as e:
            print(f"Error in get_or_create for factor {primary_key}: {e}")
            return None
