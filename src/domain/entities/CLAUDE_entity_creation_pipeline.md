🧠 Key Difference vs Factor

Factor has:

dependencies

calculate()

factor_library

👉 Non-factor entities (Account, Order, Transaction):

❌ no calculate

❌ no dependency graph

✅ BUT same:

Domain entity

Mapper

ORM model

Local repository

IBKR repository

Factory wiring

Port


🧠 Core Concept (VERY IMPORTANT)
You now have 2 categories of entities
🟢 1. Static / Reference Entities

Country
Industry
Sector

👉 Source:

DB / config / manual

👉 Repositories:

LocalRepository ONLY


🔵 2. Market / IBKR Entities

Index

Stock

Future

Option

👉 Source:

IBKR + DB

👉 Repositories:
LocalRepository + IBKRRepository

FUll pipeline example:

✅ 1. DOMAIN ENTITY

📁 src/domain/entities/financial_assets/index/index.py


from typing import Optional


class Index:
    """
    Domain entity representing a financial index.
    """

    def __init__(
        self,
        id: Optional[int],
        symbol: str,
        name: str,
        currency: str,
        exchange: Optional[str] = None,
        country_code: Optional[str] = None,
    ):
        self.id = id
        self.symbol = symbol
        self.name = name
        self.currency = currency
        self.exchange = exchange
        self.country_code = country_code

    def __repr__(self):
        return f"Index(id={self.id}, symbol={self.symbol}, exchange={self.exchange})"

✅ 2. PORT

📁 src/domain/ports/financial_assets/index/index_port.py

from typing import List, Optional
from src.domain.entities.financial_assets.index.index import Index


class IndexPort:

    def get_by_id(self, id: int) -> Optional[Index]:
        pass

    def get_by_symbol(self, symbol: str) -> Optional[Index]:
        pass

    def get_all(self) -> List[Index]:
        pass

    def add(self, entity: Index) -> Optional[Index]:
        pass

    def update(self, entity: Index) -> Optional[Index]:
        pass

    def delete(self, id: int) -> bool:
        pass

✅ 3. ORM MODEL

📁 src/infrastructure/models/financial_assets/index/index.py

from sqlalchemy import Column, Integer, String
from src.infrastructure.models.base import Base


class IndexModel(Base):
    __tablename__ = "indices"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    name = Column(String)
    currency = Column(String)
    exchange = Column(String)
    country_code = Column(String)

    __mapper_args__ = {
        "polymorphic_identity": "index"
    }

✅ 4. MAPPER

📁 src/infrastructure/repositories/mappers/financial_assets/index/index_mapper.py

from typing import Optional
from src.domain.entities.financial_assets.index.index import Index
from src.infrastructure.models.financial_assets.index.index import IndexModel


class IndexMapper:

    @property
    def discriminator(self):
        return "index"

    @property
    def model_class(self):
        return IndexModel

    def get_entity(self):
        return Index

    def to_domain(self, orm_model: Optional[IndexModel]) -> Optional[Index]:
        if not orm_model:
            return None

        return Index(
            id=orm_model.id,
            symbol=orm_model.symbol,
            name=orm_model.name,
            currency=orm_model.currency,
            exchange=orm_model.exchange,
            country_code=orm_model.country_code,
        )

    def to_orm(self, entity: Index) -> IndexModel:
        return IndexModel(
            symbol=entity.symbol,
            name=entity.name,
            currency=entity.currency,
            exchange=entity.exchange,
            country_code=entity.country_code,
        )

✅ 5. LOCAL REPOSITORY

📁 src/infrastructure/repositories/local_repo/financial_assets/index/index_repository.py

from sqlalchemy.orm import Session
from typing import Optional, List

from src.domain.entities.financial_assets.index.index import Index
from src.domain.ports.financial_assets.index.index_port import IndexPort
from src.infrastructure.repositories.mappers.financial_assets.index.index_mapper import IndexMapper


class IndexRepository(IndexPort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = IndexMapper()

    @property
    def entity_class(self):
        return self.mapper.get_entity()

    @property
    def model_class(self):
        return self.mapper.model_class

    # -------------------------
    # CREATE OR GET
    # -------------------------
    def _create_or_get(self, symbol: str, **kwargs) -> Optional[Index]:

        try:
            existing = self.get_by_symbol(symbol)
            if existing:
                return existing

            entity = Index(
                id=None,
                symbol=symbol,
                name=kwargs.get("name"),
                currency=kwargs.get("currency"),
                exchange=kwargs.get("exchange"),
                country_code=kwargs.get("country_code"),
            )

            orm_obj = self.mapper.to_orm(entity)

            self.session.add(orm_obj)
            self.session.commit()

            return self.mapper.to_domain(orm_obj)

        except Exception as e:
            print(f"Error creating index {symbol}: {e}")
            return None

    # -------------------------
    # STANDARD METHODS
    # -------------------------
    def get_by_symbol(self, symbol: str) -> Optional[Index]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.symbol == symbol)\
            .one_or_none()
        return self.mapper.to_domain(obj)

    def get_by_id(self, id: int) -> Optional[Index]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == id)\
            .one_or_none()
        return self.mapper.to_domain(obj)

    def get_all(self) -> List[Index]:
        objs = self.session.query(self.model_class).all()
        return [self.mapper.to_domain(o) for o in objs]

    def add(self, entity: Index) -> Optional[Index]:
        obj = self.mapper.to_orm(entity)
        self.session.add(obj)
        self.session.commit()
        return self.mapper.to_domain(obj)

    def update(self, entity: Index) -> Optional[Index]:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == entity.id)\
            .one_or_none()

        if not obj:
            return None

        obj.name = entity.name
        obj.exchange = entity.exchange
        obj.currency = entity.currency

        self.session.commit()
        return self.mapper.to_domain(obj)

    def delete(self, id: int) -> bool:
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == id)\
            .one_or_none()

        if not obj:
            return False

        self.session.delete(obj)
        self.session.commit()
        return True

✅ 6. IBKR REPOSITORY (ONLY for market entities)

📁 src/infrastructure/repositories/ibkr/financial_assets/index/ibkr_index_repository.py

from typing import Optional
from src.domain.entities.financial_assets.index.index import Index
from src.domain.ports.financial_assets.index.index_port import IndexPort


class IBKRIndexRepository(IndexPort):

    def __init__(self, ibkr_client, factory=None):
        self.ibkr_client = ibkr_client
        self.factory = factory
        self.local_repo = factory._local_repositories.get('index') if factory else None

    def _create_or_get(self, symbol: str, **kwargs):

        try:
            ib = self.ibkr_client

            contract_details = ib.contract_details.get(symbol)

            enhanced_kwargs = {
                "name": contract_details.longName if contract_details else symbol,
                "exchange": contract_details.exchange if contract_details else None,
                "currency": contract_details.currency if contract_details else None,
            }

            if self.local_repo:
                return self.local_repo._create_or_get(
                    symbol=symbol,
                    **enhanced_kwargs
                )

            return None

        except Exception as e:
            print(f"IBKR index error {symbol}: {e}")
            return None

✅ 7. RepositoryFactory
Local

'index': IndexRepository(self.session, factory=self),
@property
def index_local_repo(self):
    return self._local_repositories.get('index')

IBKR
'index': IBKRIndexRepository(client, factory=self),

@property
def index_ibkr_repo(self):
    return self._ibkr_repositories.get('index')