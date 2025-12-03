from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from src.infrastructure.models.finance.exchange import Exchange as ExchangeModel
from src.domain.entities.finance.exchange import Exchange as ExchangeEntity
from src.infrastructure.repositories.base_repository import BaseRepository


class ExchangeRepository(BaseRepository):
    """Repository for managing Exchange entities."""

    def __init__(self, session: Session):
        super().__init__(session)

    # ------------------------------------------------------------------
    # MODEL CLASS REFERENCE
    # ------------------------------------------------------------------
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Exchange."""
        return ExchangeModel

    # ------------------------------------------------------------------
    # CONVERSION METHODS
    # ------------------------------------------------------------------
    def _to_entity(self, model: ExchangeModel) -> Optional[ExchangeEntity]:
        """Convert DB model → domain entity."""
        if not model:
            return None

        return ExchangeEntity(
            id=model.id,
            name=model.name,
            legal_name=model.legal_name,
            country_id=model.country_id,
            start_date=model.start_date,
            end_date=model.end_date
        )

    def _to_model(self, entity: ExchangeEntity) -> ExchangeModel:
        """Convert domain entity → DB model."""
        if not entity:
            return None

        return ExchangeModel(
            name=entity.name,
            legal_name=entity.legal_name,
            country_id=entity.country_id,
            start_date=entity.start_date,
            end_date=entity.end_date
        )

    # ------------------------------------------------------------------
    # GETTERS
    # ------------------------------------------------------------------
    def get_all(self) -> List[ExchangeEntity]:
        models = self.session.query(ExchangeModel).all()
        return [self._to_entity(model) for model in models]

    def get_by_id(self, exchange_id: int) -> Optional[ExchangeEntity]:
        model = (
            self.session.query(ExchangeModel)
            .filter(ExchangeModel.id == exchange_id)
            .first()
        )
        return self._to_entity(model)

    def get_by_name(self, name: str) -> List[ExchangeEntity]:
        models = (
            self.session.query(ExchangeModel)
            .filter(ExchangeModel.name == name)
            .all()
        )
        return [self._to_entity(model) for model in models]

    def exists_by_name(self, name: str) -> bool:
        return (
            self.session.query(ExchangeModel)
            .filter(ExchangeModel.name == name)
            .first()
            is not None
        )

    # ------------------------------------------------------------------
    # ADD / UPDATE / DELETE
    # ------------------------------------------------------------------
    def add(self, entity: ExchangeEntity) -> ExchangeEntity:
        """Add new Exchange if not already existing."""
        if self.exists_by_name(entity.name):
            return self.get_by_name(entity.name)[0]

        model = self._to_model(entity)
        self.session.add(model)
        self.session.commit()
        return self._to_entity(model)

    def update(self, exchange_id: int, **kwargs) -> Optional[ExchangeEntity]:
        model = (
            self.session.query(ExchangeModel)
            .filter(ExchangeModel.id == exchange_id)
            .first()
        )

        if not model:
            return None

        for attr, value in kwargs.items():
            if hasattr(model, attr):
                setattr(model, attr, value)

        self.session.commit()
        return self._to_entity(model)

    def delete(self, exchange_id: int) -> bool:
        model = (
            self.session.query(ExchangeModel)
            .filter(ExchangeModel.id == exchange_id)
            .first()
        )

        if not model:
            return False

        self.session.delete(model)
        self.session.commit()
        return True

    # ------------------------------------------------------------------
    # CREATE-OR-GET PATTERN (same as CompanyRepository)
    # ------------------------------------------------------------------
    def _get_next_available_exchange_id(self) -> int:
        try:
            max_id = (
                self.session.query(ExchangeModel.id)
                .order_by(ExchangeModel.id.desc())
                .first()
            )
            return max_id[0] + 1 if max_id else 1
        except Exception as e:
            print(f"Warning: Could not determine next available exchange ID: {e}")
            return 1

    def _create_or_get_exchange(
        self,
        name: str,
        legal_name: Optional[str] = None,
        country_id: int = 1,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> ExchangeEntity:
        """
        Create exchange if it doesn't exist, otherwise return the existing one.
        Mirrors the CompanyRepository pattern.
        """

        # If exchange already exists, return existing instance
        if self.exists_by_name(name):
            return self.get_by_name(name)[0]

        try:
            next_id = self._get_next_available_exchange_id()

            exchange = ExchangeEntity(
                id=next_id,
                name=name,
                legal_name=legal_name or name,
                country_id=country_id,
                start_date=start_date or date.today(),
                end_date=end_date
            )

            return self.add(exchange)

        except Exception as e:
            print(f"Error creating exchange {name}: {str(e)}")
            return None

    # Standard CRUD interface
    def create(self, entity: ExchangeEntity) -> ExchangeEntity:
        return self.add(entity)
