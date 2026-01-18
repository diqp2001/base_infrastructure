"""
Instrument Repository - Local repository implementation for Instrument entities.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from src.domain.ports.finance.instrument_port import InstrumentPort
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.models.finance.instrument import InstrumentModel as InstrumentModel
from src.domain.entities.finance.instrument.instrument import Instrument as InstrumentEntity
from src.infrastructure.repositories.mappers.finance.instrument_mapper import InstrumentMapper


class InstrumentRepository(BaseLocalRepository[InstrumentEntity, InstrumentModel], InstrumentPort):
    """Local repository implementation for Instrument entities."""

    def __init__(self, session: Session):
        """Initialize the repository with a database session."""
        super().__init__(session)

    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Instrument."""
        return InstrumentModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Instrument."""
        return InstrumentEntity

    def _to_entity(self, model: InstrumentModel) -> InstrumentEntity:
        """Convert ORM model to domain entity using mapper."""
        if not model:
            return None
        return InstrumentMapper.to_domain(model)

    def _to_model(self, entity: InstrumentEntity) -> InstrumentModel:
        """Convert domain entity to ORM model using mapper."""
        return InstrumentMapper.to_orm(entity)

    def _create_or_get(self):
        """Not implemented for Instrument - use specific methods instead."""
        raise NotImplementedError("Use specific get/create methods for Instrument entities.")

    # Implementation of InstrumentPort interface

    def get_by_id(self, entity_id: int) -> Optional[InstrumentEntity]:
        """Get instrument by ID."""
        model = self.get(entity_id)
        return self._to_entity(model)

    def get_by_asset_id(self, asset_id: int) -> List[InstrumentEntity]:
        """Get instruments by asset ID."""
        models = self.session.query(InstrumentModel).filter(
            InstrumentModel.asset_id == asset_id
        ).all()
        return [self._to_entity(model) for model in models]

    def get_by_source(self, source: str) -> List[InstrumentEntity]:
        """Get instruments by data source."""
        models = self.session.query(InstrumentModel).filter(
            InstrumentModel.source == source
        ).all()
        return [self._to_entity(model) for model in models]

    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[InstrumentEntity]:
        """Get instruments within a date range."""
        models = self.session.query(InstrumentModel).filter(
            and_(
                InstrumentModel.date >= start_date,
                InstrumentModel.date <= end_date
            )
        ).all()
        return [self._to_entity(model) for model in models]

    def get_by_asset_and_source(self, asset_id: int, source: str) -> List[InstrumentEntity]:
        """Get instruments by asset ID and source."""
        models = self.session.query(InstrumentModel).filter(
            and_(
                InstrumentModel.asset_id == asset_id,
                InstrumentModel.source == source
            )
        ).all()
        return [self._to_entity(model) for model in models]

    def get_latest_by_asset(self, asset_id: int) -> Optional[InstrumentEntity]:
        """Get the most recent instrument for an asset."""
        model = self.session.query(InstrumentModel).filter(
            InstrumentModel.asset_id == asset_id
        ).order_by(desc(InstrumentModel.date)).first()
        return self._to_entity(model)

    def get_all(self) -> List[InstrumentEntity]:
        """Get all instruments."""
        models = super().get_all()
        return [self._to_entity(model) for model in models]

    def add(self, entity: InstrumentEntity) -> Optional[InstrumentEntity]:
        """Add/persist an instrument entity."""
        try:
            # If entity doesn't have an ID, assign the next available one
            if not entity.id:
                entity.id = self._get_next_available_id()

            # Convert to model and save
            model = self._to_model(entity)
            saved_model = super().add(model)
            
            return self._to_entity(saved_model)
        except Exception as e:
            print(f"Error adding instrument: {str(e)}")
            self.session.rollback()
            return None

    def update(self, entity: InstrumentEntity) -> Optional[InstrumentEntity]:
        """Update an instrument entity."""
        try:
            if not entity.id:
                return None

            # Get existing model
            existing_model = self.get(entity.id)
            if not existing_model:
                return None

            # Update using mapper
            updated_model = InstrumentMapper.to_orm(entity, existing_model)
            self.session.commit()
            self.session.refresh(updated_model)
            
            return self._to_entity(updated_model)
        except Exception as e:
            print(f"Error updating instrument: {str(e)}")
            self.session.rollback()
            return None

    def delete(self, entity_id: int) -> bool:
        """Delete an instrument entity."""
        return super().delete(entity_id)

    def count_by_source(self, source: str) -> int:
        """Count instruments by source."""
        return self.session.query(InstrumentModel).filter(
            InstrumentModel.source == source
        ).count()

    def get_unique_sources(self) -> List[str]:
        """Get list of unique data sources."""
        results = self.session.query(InstrumentModel.source).distinct().all()
        return [result[0] for result in results if result[0]]

    # Additional utility methods

    def exists_by_asset_and_source_and_date(self, asset_id: int, source: str, date: datetime) -> bool:
        """Check if an instrument exists with the exact combination of asset, source, and date."""
        return self.session.query(InstrumentModel).filter(
            and_(
                InstrumentModel.asset_id == asset_id,
                InstrumentModel.source == source,
                InstrumentModel.date == date
            )
        ).first() is not None

    def add_bulk(self, entities: List[InstrumentEntity]) -> List[InstrumentEntity]:
        """Add multiple instruments in a single transaction."""
        if not entities:
            return []

        created_entities = []
        
        try:
            for entity in entities:
                # Skip if already exists
                if self.exists_by_asset_and_source_and_date(
                    entity.asset_id, entity.source, entity.date
                ):
                    continue

                # Assign ID if not set
                if not entity.id:
                    entity.id = self._get_next_available_id()

                # Convert to model and add
                model = self._to_model(entity)
                self.session.add(model)

            # Flush to get IDs
            self.session.flush()

            # Convert back to entities
            for model in self.session.new:
                if isinstance(model, InstrumentModel):
                    created_entities.append(self._to_entity(model))

            # Commit transaction
            self.session.commit()

        except Exception as e:
            self.session.rollback()
            print(f"Error in bulk add operation: {str(e)}")
            raise

        return created_entities

    def delete_bulk_by_asset(self, asset_id: int) -> int:
        """Delete all instruments for a specific asset."""
        try:
            deleted_count = self.session.query(InstrumentModel).filter(
                InstrumentModel.asset_id == asset_id
            ).delete(synchronize_session=False)
            
            self.session.commit()
            return deleted_count
        except Exception as e:
            self.session.rollback()
            print(f"Error in bulk delete operation: {str(e)}")
            raise

    def get_by_asset_latest_by_source(self, asset_id: int) -> List[InstrumentEntity]:
        """Get the latest instrument for each source for a given asset."""
        # Get unique sources for this asset
        sources = self.session.query(InstrumentModel.source).filter(
            InstrumentModel.asset_id == asset_id
        ).distinct().all()

        latest_instruments = []
        for source_tuple in sources:
            source = source_tuple[0]
            latest = self.session.query(InstrumentModel).filter(
                and_(
                    InstrumentModel.asset_id == asset_id,
                    InstrumentModel.source == source
                )
            ).order_by(desc(InstrumentModel.date)).first()
            
            if latest:
                latest_instruments.append(self._to_entity(latest))

        return latest_instruments