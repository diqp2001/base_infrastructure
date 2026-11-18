"""
IBKR ETF Share Factor Repository - the raw IBKR series of an ETF share (open / high / low / close / volume of a
whatToShow), like IBKRCompanyShareFactorRepository for company shares. MarketDataService creates these factors
before importing the bars (IBKRFactorValueRepository builds the contract through IBKRETFShareRepository).
Persistence is delegated to the local ETFShareFactorRepository.
"""


from src.domain.ports.factor.finance.financial_assets.share_factor.etf_share.etf_share_factor_port import (
    ETFShareFactorPort,
)
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.share.etf_share.etf_share_factor_mapper import (
    ETFShareFactorMapper,
)


class IBKRETFShareFactorRepository(BaseIBKRFactorRepository, ETFShareFactorPort):

    def __init__(self, ibkr_client, factory=None):
        super().__init__(ibkr_client)
        self.factory = factory
        self.mapper = ETFShareFactorMapper()

    @property
    def local_repo(self):
        return self.factory.get_local_repository("ETFShareFactor") if self.factory else None

    @property
    def entity_class(self):
        return self.mapper.get_factor_entity()

    def _create_or_get(self, name: str, **kwargs):
        """The ETF share factor `name` (with the series' subgroup / frequency / source in kwargs), stored locally."""
        try:
            if self.local_repo:
                created = self.local_repo._create_or_get(self.local_repo.get_factor_entity(), primary_key=name,
                                                         **kwargs)
                if created:
                    return created
            print(f"Failed to create etf_share factor: {name}")
            return None
        except Exception as e:
            print(f"Error in get_or_create for etf_share factor {name}: {e}")
            return None

    def get_by_id(self, id: int):
        return self.local_repo.get_by_id(id) if self.local_repo else None

    def get_by_name(self, name: str):
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_group(self, group: str):
        return self.local_repo.get_by_group(group) if self.local_repo else []

    def get_by_subgroup(self, subgroup: str):
        return self.local_repo.get_by_subgroup(subgroup) if self.local_repo else []

    def get_all(self):
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity):
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity):
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, id: int) -> bool:
        return self.local_repo.delete(id) if self.local_repo else False
