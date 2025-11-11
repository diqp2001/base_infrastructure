"""
Base repository class for factor entities with common CRUD operations.
"""



from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Optional, Union
from datetime import date
import pandas as pd
from sqlalchemy.orm import Session

from ...base_repository import BaseRepository
from domain.entities.factor.factor import FactorBase as FactorEntity
from domain.entities.factor.factor_value import FactorValue as FactorValueEntity

from infrastructure.models.factor.factor_model import (
    Factor as FactorModel,
    FactorValue as FactorValueModel,
)

from infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
from infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper

from application.managers.database_managers.database_manager import DatabaseManager


class BaseFactorRepository(BaseRepository[FactorEntity, FactorModel], ABC):
    """Repository managing Factor entities, their values."""

    def __init__(self, db_type: str = 'sqlite'):
        """Initialize repository with a database type."""
        self.database_manager = DatabaseManager(db_type)
        # Call parent constructor with session
        super().__init__(self.database_manager.session)

    # ----------------------------- Abstract methods -----------------------------
    #@abstractmethod
    def get_factor_model(self):
        return FactorMapper().get_factor_model()
    #@abstractmethod
    def get_factor_entity(self):
        return FactorMapper().get_factor_entity()

    #@abstractmethod
    def get_factor_value_model(self):
        return FactorValueMapper().get_factor_value_model()
    #@abstractmethod
    def get_factor_value_entity(self):
        return FactorValueMapper().get_factor_value_entity()


    
    @property
    def model_class(self):
        """Return the SQLAlchemy factor model class."""
        return self.get_factor_model()
    
    def _to_entity(self, infra_obj) -> Optional[FactorEntity]:
        """Convert ORM model to domain entity."""
        return FactorMapper.to_domain(infra_obj)
    
    def _to_model(self, entity: FactorEntity) -> FactorModel:
        """Convert domain entity to ORM model."""
        model = FactorMapper.to_orm(entity)
        return model

    # ----------------------------- Mappers -----------------------------
    def _to_domain_factor(self, infra_obj) -> Optional[FactorEntity]:
        """Convert ORM factor object to domain entity."""
        

        return FactorMapper.to_domain(infra_obj)
        

    def _to_domain_value(self, infra_obj) -> Optional[FactorValueEntity]:
        """Convert ORM factor value object to domain entity."""
        
        return FactorValueMapper.to_domain(infra_obj)

  

    # ----------------------------- CRUD: Factors -----------------------------
    def create_factor(self, domain_factor: FactorEntity) -> Optional[FactorEntity]:
        """Add a new factor to the database using sequential ID generation."""
        try:
            FactorModel = self.get_factor_model()
            
            # Use sequential ID generation if factor doesn't have an ID
            if not hasattr(domain_factor, 'id') or domain_factor.id is None:
                next_id = self._get_next_available_factor_id()
                domain_factor.id = next_id
            
            # Create ORM object directly using the specific model
            orm_factor = FactorModel(
                id=domain_factor.id,  # Use sequential ID
                name=domain_factor.name,
                group=domain_factor.group,
                subgroup=domain_factor.subgroup,
                data_type=domain_factor.data_type,
                source=domain_factor.source,
                definition=domain_factor.definition
            )
            self.session.add(orm_factor)
            self.session.commit()
            return self._to_domain_factor(orm_factor)
        except Exception as e:
            self.session.rollback()
            print(f"Error creating factor: {e}")
            return None

    def get_by_name(self, name: str) -> Optional[FactorEntity]:
        """Retrieve a factor by its name."""
        try:
            FactorModel = self.get_factor_model()
            factor = self.session.query(FactorModel).filter(FactorModel.name == name).first()
            return self._to_domain_factor(factor)
        except Exception as e:
            print(f"Error retrieving factor by name: {e}")
            return None

    def get_by_id(self, factor_id: int) -> Optional[FactorEntity]:
        """Retrieve a factor by its ID."""
        try:
            FactorModel = self.get_factor_model()
            factor = self.session.query(FactorModel).filter(FactorModel.id == factor_id).first()
            return self._to_domain_factor(factor)
        except Exception as e:
            print(f"Error retrieving factor by ID: {e}")
            return None

    def list_all(self) -> List[FactorEntity]:
        """List all factors."""
        try:
            FactorModel = self.get_factor_model()
            factors = self.session.query(FactorModel).all()
            return [self._to_domain_factor(f) for f in factors]
        except Exception as e:
            print(f"Error listing factors: {e}")
            return []

    def update_factor(self, factor_id: int, **kwargs) -> Optional[FactorEntity]:
        """Update a factor's properties."""
        try:
            FactorModel = self.get_factor_model()
            factor = self.session.query(FactorModel).filter(FactorModel.id == factor_id).first()
            if not factor:
                return None
            for key, value in kwargs.items():
                if hasattr(factor, key):
                    setattr(factor, key, value)
            self.session.commit()
            return self._to_domain_factor(factor)
        except Exception as e:
            self.session.rollback()
            print(f"Error updating factor: {e}")
            return None

    def delete_factor(self, factor_id: int) -> bool:
        """Delete a factor by ID."""
        try:
            FactorModel = self.get_factor_model()
            factor = self.session.query(FactorModel).filter(FactorModel.id == factor_id).first()
            if not factor:
                return False
            self.session.delete(factor)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"Error deleting factor: {e}")
            return False

    # ----------------------------- CRUD: Factor Values -----------------------------
    def create_factor_value(self, domain_value: FactorValueEntity) -> Optional[FactorValueEntity]:
        """Add a new factor value."""
        try:
            FactorValueModel = self.get_factor_value_model()
            # Create ORM object directly using the specific model
            orm_value = FactorValueModel(
                factor_id=domain_value.factor_id,
                entity_id=domain_value.entity_id,
                date=domain_value.date,
                value=domain_value.value
            )
            self.session.add(orm_value)
            self.session.commit()
            return self._to_domain_value(orm_value)
        except Exception as e:
            self.session.rollback()
            print(f"Error creating factor value: {e}")
            return None

    def get_by_factor_and_date(self, factor_id: int, date_value: date) -> List[FactorValueEntity]:
        """Get all values for a factor on a specific date."""
        try:
            FactorValueModel = self.get_factor_value_model()
            values = (
                self.session.query(FactorValueModel)
                .filter(FactorValueModel.factor_id == factor_id, FactorValueModel.date == date_value)
                .all()
            )
            return [self._to_domain_value(v) for v in values]
        except Exception as e:
            print(f"Error retrieving factor values: {e}")
            return []

    def get_factor_values_by_entity(self, entity_id: int, factor_id: Optional[int] = None) -> List[FactorValueEntity]:
        """Get all factor values for a given entity."""
        try:
            FactorValueModel = self.get_factor_value_model()
            query = self.session.query(FactorValueModel).filter(FactorValueModel.entity_id == entity_id)
            if factor_id:
                query = query.filter(FactorValueModel.factor_id == factor_id)
            values = query.all()
            return [self._to_domain_value(v) for v in values]
        except Exception as e:
            print(f"Error retrieving factor values by entity: {e}")
            return []
        
    def get_factor_id_by_name(self, factor_name: str) -> Optional[int]:
        """
        Retrieve the ID of a factor given its name.

        Args:
            factor_name: The name of the factor to search for 
                        (e.g., 'Adj Close', 'RSI 14', etc.)

        Returns:
            The factor ID if found, otherwise None.
        """
        try:
            FactorModel = self.get_factor_model()
            factor = (
                self.session.query(FactorModel.id)
                .filter(FactorModel.name == factor_name)
                .one_or_none()
            )

            return factor.id if factor else None

        except Exception as e:
            print(f"Error retrieving factor ID by name '{factor_name}': {e}")
            return None

    def get_factor_values(
        self,
        factor_id: Union[int, List[int]],
        entity_id: Union[int, List[int]],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[FactorValueEntity]:
        """
        Get factor values for one or multiple factors and entities within a date range.
        
        Args:
            factor_id: Single factor ID or list of factor IDs.
            entity_id: Single entity ID or list of entity IDs.
            start_date: Start date in YYYY-MM-DD format (optional).
            end_date: End date in YYYY-MM-DD format (optional).
            
        Returns:
            List of factor value entities within the date range.
        """
        try:
            from datetime import datetime
            from sqlalchemy import or_

            FactorValueModel = self.get_factor_value_model()
            query = self.session.query(FactorValueModel)

            # Normalize inputs to lists
            factor_ids = [factor_id] if isinstance(factor_id, int) else factor_id
            entity_ids = [entity_id] if isinstance(entity_id, int) else entity_id

            query = query.filter(
                FactorValueModel.factor_id.in_(factor_ids),
                FactorValueModel.entity_id.in_(entity_ids)
            )

            # Apply date filters
            if start_date:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                query = query.filter(FactorValueModel.date >= start_date_obj)

            if end_date:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
                query = query.filter(FactorValueModel.date <= end_date_obj)

            # Order by date, factor, and entity for consistent results
            query = query.order_by(FactorValueModel.date, FactorValueModel.factor_id, FactorValueModel.entity_id)

            values = query.all()
            return [self._to_domain_value(v) for v in values]

        except Exception as e:
            print(f"Error retrieving factor values: {e}")
            return []



    

    def get_factor_values_df(
        self,
        factor_id: Union[int, List[int]],
        entity_id: Union[int, List[int]],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Retrieve factor values for one or multiple factors and entities within a date range,
        returned as a Pandas DataFrame.

        Args:
            factor_id: Single factor ID or list of factor IDs.
            entity_id: Single entity ID or list of entity IDs.
            start_date: Start date in YYYY-MM-DD format (optional).
            end_date: End date in YYYY-MM-DD format (optional).

        Returns:
            A Pandas DataFrame with columns:
                ['date', 'factor_id', 'entity_id', 'value']
            or an empty DataFrame if no results are found.
        """
        try:
            from datetime import datetime

            FactorValueModel = self.get_factor_value_model()
            query = self.session.query(FactorValueModel)

            # Normalize inputs to lists
            factor_ids = [factor_id] if isinstance(factor_id, int) else factor_id
            entity_ids = [entity_id] if isinstance(entity_id, int) else entity_id

            query = query.filter(
                FactorValueModel.factor_id.in_(factor_ids),
                FactorValueModel.entity_id.in_(entity_ids)
            )

            # Apply date filters
            if start_date:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                query = query.filter(FactorValueModel.date >= start_date_obj)

            if end_date:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
                query = query.filter(FactorValueModel.date <= end_date_obj)

            # Order by date, factor, and entity
            query = query.order_by(FactorValueModel.date, FactorValueModel.factor_id, FactorValueModel.entity_id)

            results = query.all()
            if not results:
                return pd.DataFrame(columns=["date", "factor_id", "entity_id", "value"])

            data = [
                {
                    "date": r.date,
                    "factor_id": r.factor_id,
                    "entity_id": r.entity_id,
                    "value": r.value,
                }
                for r in results
            ]

            return pd.DataFrame(data)

        except Exception as e:
            print(f"Error retrieving factor values as DataFrame: {e}")
            return pd.DataFrame(columns=["date", "factor_id", "entity_id", "value"])



    def get_factors_by_groups(self, groups: List[str]) -> List[FactorEntity]:
        """
        Get factors filtered by specific groups.
        
        Args:
            groups: List of group names to filter by (e.g., ['price', 'momentum', 'technical'])
            
        Returns:
            List of factor entities matching the specified groups
        """
        try:
            FactorModel = self.get_factor_model()
            query = self.session.query(FactorModel)
            
            if groups:
                # Filter by groups using IN clause
                query = query.filter(FactorModel.group.in_(groups))
            
            # Order by group and name for consistent results
            query = query.order_by(FactorModel.group, FactorModel.name)
            
            factors = query.all()
            return [self._to_domain_factor(factor) for factor in factors]
            
        except Exception as e:
            print(f"Error retrieving factors by groups: {e}")
            return []
        
    def get_factor_ids_by_groups(self, groups: List[str]) -> List[int]:
        """
        Retrieve all factor IDs belonging to specific groups.

        Args:
            groups: List of group names to filter by 
                    (e.g., ['price', 'momentum', 'technical']).

        Returns:
            List of factor IDs matching the specified groups.
        """
        try:
            FactorModel = self.get_factor_model()
            query = self.session.query(FactorModel.id)
            
            if groups:
                # Filter by groups using IN clause
                query = query.filter(FactorModel.group.in_(groups))
            
            # Order by group for deterministic output
            query = query.order_by(FactorModel.group)
            
            factor_ids = [row.id for row in query.all()]
            return factor_ids

        except Exception as e:
            print(f"Error retrieving factor IDs by groups: {e}")
            return []


    def factor_value_exists(self, factor_id: int, entity_id: int, date_value: date) -> bool:
        """
        Check if a factor value already exists for the given factor_id, entity_id, and date.
        
        Args:
            factor_id: ID of the factor
            entity_id: ID of the entity
            date_value: Date of the value
            
        Returns:
            bool: True if the value exists, False otherwise
        """
        try:
            FactorValueModel = self.get_factor_value_model()
            existing_value = (
                self.session.query(FactorValueModel)
                .filter(
                    FactorValueModel.factor_id == factor_id,
                    FactorValueModel.entity_id == entity_id,
                    FactorValueModel.date == date_value
                )
                .first()
            )
            return existing_value is not None
        except Exception as e:
            print(f"Error checking factor value existence: {e}")
            return False

    def get_existing_value_dates(self, factor_id: int, entity_id: int) -> set:
        """
        Get all existing dates for which factor values exist for a specific factor and entity.
        
        Args:
            factor_id: ID of the factor
            entity_id: ID of the entity
            
        Returns:
            set: Set of dates that already have factor values
        """
        try:
            FactorValueModel = self.get_factor_value_model()
            dates = (
                self.session.query(FactorValueModel.date)
                .filter(
                    FactorValueModel.factor_id == factor_id,
                    FactorValueModel.entity_id == entity_id
                )
                .all()
            )
            return {date_tuple[0] for date_tuple in dates}
        except Exception as e:
            print(f"Error retrieving existing value dates: {e}")
            return set()

    # ----------------------------- CRUD: Factor  -----------------------------


   

    def _get_next_available_factor_id(self) -> int:
        """
        Get the next available ID for factor creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            FactorModel = self.get_factor_model()
            max_id_result = self.session.query(FactorModel.id).order_by(FactorModel.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available factor ID: {str(e)}")
            return 1  # Default to 1 if query fails

    # ----------------------------- Standard CRUD Interface -----------------------------
    def create(self, entity: FactorEntity) -> FactorEntity:
        """Create new factor entity in database"""
        return self.create_factor(entity)

    def update(self, entity_id: int, updates: dict) -> Optional[FactorEntity]:
        """Update factor entity with new data"""
        return self.update_factor(entity_id, **updates)

    def delete(self, entity_id: int) -> bool:
        """Delete factor entity by ID"""
        return self.delete_factor(entity_id)

    # ----------------------------- Convenience Methods -----------------------------
    def add_factor(self, name: str, group: str, subgroup: str, data_type: str, source: str, definition: str) -> Optional[FactorEntity]:
        """
        Convenience method to add a new factor.
        
        Args:
            name: Factor name
            group: Factor group
            subgroup: Factor subgroup  
            data_type: Data type (e.g., 'numeric', 'string')
            source: Data source
            definition: Factor definition/description
        
        Returns:
            Created factor entity or None if failed
        """
        FactorEntity = self.get_factor_entity()
        
        domain_factor = FactorEntity(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition
        )
        return self.create_factor(domain_factor)

    def add_factor_value(self, factor_id: int, entity_id: int, date: date, value) -> Optional[FactorValueEntity]:
        """
        Convenience method to add a new factor value.
        
        Args:
            factor_id: ID of the factor
            entity_id: ID of the entity
            date: Date of the value
            value: Factor value (will be converted to Decimal)
        
        Returns:
            Created factor value entity or None if failed
        """
        
        FactorValueEntity = self.get_factor_value_entity()    
        domain_value = FactorValueEntity(
            id=None,
            factor_id=factor_id,
            entity_id=entity_id,
            date=date,
            value=value
        )
        return self.create_factor_value(domain_value)
    
    def _store_factor_values(self, factor, share, data: pd.DataFrame, column: str, overwrite: bool) -> int:
        """Store factor values for a specific factor."""
        values_stored = 0
        
        # Check if column exists in DataFrame
        if column not in data.columns:
            print(f"      ⚠️  Column '{column}' not found in DataFrame. Available columns: {list(data.columns)}")
            return 0
        
        # Get existing dates if not overwriting
        existing_dates = set()
        if not overwrite:
            existing_dates = self.get_existing_value_dates(
                factor.id, share.id
            )
        
        for date_index, row in data.iterrows():
            if pd.isna(row[column]):
                continue
            value = row[column]
            trade_date = date_index.date() if hasattr(date_index, 'date') else date_index
            
            if not overwrite and trade_date in existing_dates:
                continue
            
            try:
                self.add_factor_value(
                    factor_id=factor.id,
                    entity_id=share.id,
                    date=trade_date,
                    value=value
                )
                values_stored += 1
                
            except Exception as e:
                print(f"      ⚠️  Error storing {column} value for {trade_date}: {str(e)}")
        
        return values_stored
    
    def _create_or_get_factor(self, name: str, group: str, subgroup: str, data_type: str, source: str, definition: str):
        """Create factor if it doesn't exist, otherwise return existing."""
        existing_factor = self.get_by_name(name)
        if existing_factor:
            return existing_factor
        
        return self.add_factor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition
        )

