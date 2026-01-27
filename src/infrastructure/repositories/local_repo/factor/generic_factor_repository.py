"""
Generic Factor Repository - type-safe repository for any factor entity type.
This provides a clean implementation that works with a specific factor type.
"""

from typing import Optional, Type, TypeVar, Generic
from sqlalchemy.orm import Session

from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.domain.entities.factor.factor import Factor
from src.infrastructure.models.factor.factor import FactorModel
from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
from src.domain.ports.factor.factor_port import FactorPort

F = TypeVar('F', bound=Factor)


class GenericFactorRepository(BaseFactorRepository, FactorPort, Generic[F]):
    """
    Generic repository that works with a specific factor entity type.
    This is type-safe and follows DDD principles by being bound to a single entity type.
    """

    def __init__(self, session: Session, factory, factor_class: Type[F], mapper: FactorMapper = None):
        """
        Initialize GenericFactorRepository with a specific factor class.
        
        Args:
            session: Database session
            factory: Repository factory
            factor_class: The specific factor entity class this repository handles
            mapper: Optional factor mapper (uses default if not provided)
        """
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or FactorMapper()
        self._factor_class = factor_class

    # ----------------------------
    # Required by BaseLocalRepository
    # ----------------------------
    
    @property
    def model_class(self):
        return FactorModel
    
    @property
    def entity_class(self) -> Type[F]:
        """Return the specific factor entity class for this repository."""
        return self._factor_class

    def _to_entity(self, model: FactorModel) -> Optional[F]:
        """Convert ORM model to domain entity using the mapper."""
        if not model:
            return None
        return self.mapper.to_domain(model)

    def _to_model(self, entity: F) -> FactorModel:
        """Convert domain entity to ORM model using the mapper."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)

    def create_or_get_factor(self, name: str, group: str = "price", subgroup: str = "default", **kwargs) -> Optional[F]:
        """
        Create or get a factor of the specific type handled by this repository.
        
        Args:
            name: Factor name
            group: Factor group (default: "price")
            subgroup: Factor subgroup (default: "default")
            **kwargs: Additional arguments passed to factor constructor
            
        Returns:
            Factor instance of type F or None
        """
        # Check if factor already exists
        existing = self.session.query(FactorModel).filter(
            FactorModel.name == name,
            FactorModel.group == group,
            FactorModel.subgroup == subgroup
        ).first()

        if existing:
            return self._to_entity(existing)

        # Create new factor instance
        try:
            factor_kwargs = {
                'name': name,
                'group': group,
                'subgroup': subgroup,
                'factor_id': self._get_next_available_id(),
                **kwargs  # Allow additional arguments like data_type, source, definition
            }
            
            entity = self._factor_class(**factor_kwargs)
            return self.create(entity)
            
        except Exception as e:
            print(f"Error creating factor {name} of type {self._factor_class.__name__}: {e}")
            return None

    # ----------------------------
    # Required by FactorPort
    # ----------------------------

    def get_by_id(self, factor_id: int) -> Optional[F]:
        """Get factor by ID."""
        model = self.session.query(FactorModel).filter(
            FactorModel.id == factor_id
        ).first()
        return self._to_entity(model)

    def get_by_name(self, name: str) -> Optional[F]:
        """Get factor by name."""
        model = self.session.query(FactorModel).filter(
            FactorModel.name == name
        ).first()
        return self._to_entity(model)

    def get_by_group(self, group: str) -> list[F]:
        """Get all factors in a group."""
        models = self.session.query(FactorModel).filter(
            FactorModel.group == group
        ).all()
        return [self._to_entity(m) for m in models if self._to_entity(m) is not None]

    def get_by_subgroup(self, subgroup: str) -> list[F]:
        """Get all factors in a subgroup."""
        models = self.session.query(FactorModel).filter(
            FactorModel.subgroup == subgroup
        ).all()
        return [self._to_entity(m) for m in models if self._to_entity(m) is not None]

    def get_or_create(self, primary_key: str, **kwargs) -> Optional[F]:
        """
        Get or create a factor with dependency resolution.
        This method provides compatibility with the existing interface.
        """
        return self.create_or_get_factor(
            name=primary_key,
            group=kwargs.get('group', 'general'),
            subgroup=kwargs.get('subgroup', 'default'),
            **{k: v for k, v in kwargs.items() if k not in ['group', 'subgroup']}
        )